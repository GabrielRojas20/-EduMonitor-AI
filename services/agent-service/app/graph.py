"""Flujo del agente con LangGraph (docs/agent-design/diseno-agente.md, sección 4).

recibir_mensaje -> validar_contexto -> clasificar_intencion -> planificar_herramientas -> ejecutar_herramientas
-> verificar_evidencia -> (marcar_datos_no_disponibles) -> redactar_respuesta -> validar_salida -> guardar_traza

Los cálculos son de analytics-service; el modelo solo elige herramientas y redacta con lo que ellas devuelven.
"""
import json
import logging
import re
import time
import unicodedata
import uuid
from typing import Callable, TypedDict

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, ValidationError

from . import prompts
from .config import Settings
from .llm import LLMError, OllamaClient
from .schemas import Answer, ChatResponse, Fact, Inference, Meta, Recommendation, Source
from .tools import ToolContext, ToolRegistry, now_iso

log = logging.getLogger("agent.trace")

# ---------------------------------------------------------------- intención (reglas deterministas)
OUT_OF_SCOPE = [
    (r"\b(cambi\w*|modific\w*|edit\w*|actualiz\w*|corrig\w*|borr\w*|elimin\w*|pon(?:le|er|gas?)?)\b.*\b(nota|notas|calificacion\w*)\b",
     "No puedo modificar calificaciones: el agente solo las consulta."),
    (r"\b(envi\w*|mand\w*|escrib\w*)\b.*\b(mensaje\w*|correo\w*|email\w*|mail\w*|whatsapp|notificacion\w*)\b",
     "No puedo enviar mensajes a los estudiantes."),
    (r"\b(predic\w*|diagnost\w*|depresi\w*|ansiedad|psicolog\w*|trastorno\w*|salud mental)\b",
     "No hago predicciones ni afirmaciones sobre el estado psicológico o personal de un estudiante."),
]
GREETING = r"^\s*(hola|buenas|buenos dias|buenas tardes|buenas noches|hey|gracias|ayuda)\b|\bque puedes hacer\b|\bque sabes hacer\b|\bcomo funcionas\b"
REPORT = r"\b(informe|reporte|resumen)\b"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def classify(message: str) -> tuple[str, str | None]:
    """Devuelve (intención, motivo del rechazo)."""
    text = normalize(message)
    for pattern, reason in OUT_OF_SCOPE:
        if re.search(pattern, text):
            return "fuera_de_alcance", reason
    if re.search(GREETING, text):
        return "ayuda", None
    if re.search(REPORT, text):
        return "informe", None
    return "consulta_datos", None


# ---------------------------------------------------------------- salida estructurada del modelo
class DraftFact(BaseModel):
    text: str
    tool: str
    stepN: int


class DraftInference(BaseModel):
    text: str
    basedOn: list[int] = []


class DraftRecommendation(BaseModel):
    text: str
    relatedFinding: int | None = None


class Draft(BaseModel):
    facts: list[DraftFact] = []
    inferences: list[DraftInference] = []
    recommendations: list[DraftRecommendation] = []
    unavailable: list[str] = []


# ---------------------------------------------------------------- utilidades
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
HUMAN_ERRORS = {
    "TOKEN_EXPIRED": "La sesión venció: inicia sesión de nuevo.",
    "TOKEN_INVALID": "La sesión no es válida: inicia sesión de nuevo.",
    "COURSE_NOT_AUTHORIZED": "No tienes acceso a ese curso.",
    "COURSE_NOT_FOUND": "No existe ese curso.",
    "STUDENT_NOT_FOUND": "No encontré a ese estudiante en el curso.",
    "MOODLE_UNAVAILABLE": "No pude obtener el dato porque Moodle o un servicio no respondió; reintenta o sincroniza el curso.",
    "TOOL_TIMEOUT": "No pude obtener el dato a tiempo; reintenta o sincroniza el curso.",
    "DATA_NOT_AVAILABLE": "El curso aún no tiene datos sincronizados: sincronízalo desde la lista de cursos y vuelve a preguntar.",
    "VALIDATION_ERROR": "No pude consultar el dato con los parámetros indicados.",
}


def numbers_in(text: str) -> set[float]:
    return {float(n.replace(",", ".")) for n in NUMBER.findall(text)}


def clean(text: str, limit: int = 6000) -> str:
    return CONTROL.sub("", text)[:limit]


def summarize(data: dict | None) -> dict:
    """Resumen corto para la traza: solo conteos, nunca el contenido."""
    if not isinstance(data, dict):
        return {}
    return {k: len(v) for k, v in data.items() if isinstance(v, list)} | ({"total": data["total"]} if "total" in data else {})


def find_value(obj, key: str):
    """Primer valor de `key` en una estructura anidada."""
    if isinstance(obj, dict):
        if obj.get(key):
            return obj[key]
        for v in obj.values():
            found = find_value(v, key)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_value(v, key)
            if found:
                return found
    return None


class ChatState(TypedDict, total=False):
    message: str
    course_id: int | None
    token: str
    teacher_id: str | None
    request_id: str
    trace_id: str
    started_at: str
    started_mono: float
    intent: str
    refusal: str | None
    plan: list
    tool_results: list
    steps: list
    unavailable: list
    answer: dict
    status: str
    retry: bool
    redactions: int
    unsourced_removed: int
    validated: bool
    last_sync_at: str | None
    model_failed: bool


class Agent:
    def __init__(self, settings: Settings, llm: OllamaClient, tools: ToolRegistry | None = None,
                 trace_sink: Callable[[dict], None] | None = None, tool_transport=None):
        self.settings = settings
        self.llm = llm
        self.tools = tools or ToolRegistry()
        self.trace_sink = trace_sink or (lambda trace: log.info(json.dumps(trace, ensure_ascii=False)))
        self.tool_transport = tool_transport
        self.graph = self._build()

    # ------------------------------------------------------------ grafo
    def _build(self):
        g = StateGraph(ChatState)
        for name in ("recibir_mensaje", "validar_contexto", "responder_error_sesion", "clasificar_intencion",
                     "responder_rechazo", "responder_ayuda", "planificar_herramientas", "ejecutar_herramientas",
                     "verificar_evidencia", "marcar_datos_no_disponibles", "redactar_respuesta", "validar_salida",
                     "guardar_traza"):
            g.add_node(name, getattr(self, name))
        g.set_entry_point("recibir_mensaje")
        g.add_edge("recibir_mensaje", "validar_contexto")
        g.add_conditional_edges("validar_contexto", lambda s: "clasificar_intencion" if s.get("token") else "responder_error_sesion")
        g.add_edge("responder_error_sesion", "guardar_traza")
        g.add_conditional_edges("clasificar_intencion", self._route_intent)
        g.add_edge("responder_rechazo", "guardar_traza")
        g.add_edge("responder_ayuda", "guardar_traza")
        g.add_edge("planificar_herramientas", "ejecutar_herramientas")
        g.add_edge("ejecutar_herramientas", "verificar_evidencia")
        g.add_conditional_edges("verificar_evidencia", lambda s: "marcar_datos_no_disponibles" if self._failed(s) else "redactar_respuesta")
        g.add_edge("marcar_datos_no_disponibles", "redactar_respuesta")
        g.add_edge("redactar_respuesta", "validar_salida")
        g.add_conditional_edges("validar_salida", lambda s: "redactar_respuesta" if s.get("retry") else "guardar_traza")
        g.add_edge("guardar_traza", END)
        return g.compile()

    @staticmethod
    def _route_intent(state: ChatState) -> str:
        return {"fuera_de_alcance": "responder_rechazo", "ayuda": "responder_ayuda"}.get(state["intent"], "planificar_herramientas")

    @staticmethod
    def _failed(state: ChatState) -> bool:
        return any(not r["output"]["ok"] for r in state.get("tool_results", [])) or state.get("model_failed", False)

    # ------------------------------------------------------------ nodos
    def recibir_mensaje(self, state: ChatState) -> dict:
        return {"trace_id": uuid.uuid4().hex, "started_at": now_iso(), "started_mono": time.monotonic(), "steps": [],
                "tool_results": [], "plan": [], "unavailable": [], "redactions": 0, "unsourced_removed": 0,
                "validated": True, "retry": False, "model_failed": False}

    def validar_contexto(self, state: ChatState) -> dict:
        return {}

    def responder_error_sesion(self, state: ChatState) -> dict:
        return {"intent": "sesion", "status": "error",
                "answer": Answer(unavailable=[HUMAN_ERRORS["TOKEN_INVALID"]]).model_dump()}

    def clasificar_intencion(self, state: ChatState) -> dict:
        intent, refusal = classify(state["message"])
        return {"intent": intent, "refusal": refusal}

    def responder_rechazo(self, state: ChatState) -> dict:
        text = f"{state['refusal']} Sí puedo consultar cursos, calificaciones, progreso y alertas."
        return {"status": "refused", "answer": Answer(unavailable=[text]).model_dump()}

    def responder_ayuda(self, state: ChatState) -> dict:
        return {"status": "ok", "answer": Answer(message=prompts.HELP_MESSAGE).model_dump()}

    def planificar_herramientas(self, state: ChatState) -> dict:
        """El modelo elige qué herramientas llamar y con qué argumentos (temperatura 0)."""
        if not len(self.tools):
            return {"plan": []}
        hint = f"\nCurso de referencia elegido por el docente: {state['course_id']}." if state.get("course_id") else ""
        messages = [{"role": "system", "content": prompts.PLANNER_SYSTEM},
                    {"role": "user", "content": state["message"] + hint}]
        try:
            reply = self.llm.chat(messages, tools=self.tools.schemas(), temperature=0.0)
        except LLMError as exc:
            steps = state["steps"] + [{"n": len(state["steps"]) + 1, "node": "planificar_herramientas", "tool": None,
                                       "ok": False, "errorCode": exc.code, "durationMs": 0}]
            return {"plan": [], "model_failed": True, "steps": steps,
                    "unavailable": state["unavailable"] + ["No pude consultar al modelo de lenguaje; reintenta en un momento."]}
        plan = []
        for call in reply["tool_calls"][: self.settings.max_tool_calls]:
            fn = call.get("function", {})
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}
            if state.get("course_id") and "course_id" not in args:
                tool = self.tools._tools.get(fn.get("name", ""))
                if tool is not None and "course_id" in tool.input_model.model_fields:
                    args["course_id"] = state["course_id"]
            plan.append({"name": fn.get("name", ""), "arguments": args})
        steps = state["steps"] + [{"n": len(state["steps"]) + 1, "node": "planificar_herramientas", "tool": None, "ok": True,
                                   "errorCode": None, "durationMs": reply["durationMs"], "resultSummary": {"plannedCalls": len(plan)}}]
        return {"plan": plan, "steps": steps}

    def ejecutar_herramientas(self, state: ChatState) -> dict:
        results, steps = list(state["tool_results"]), list(state["steps"])
        for call in state["plan"]:
            n = len(results) + 1
            if time.monotonic() - state["started_mono"] > self.settings.message_timeout_s:
                output = {"ok": False, "data": None, "source": None,
                          "error": {"code": "TOOL_TIMEOUT", "message": "Se agotó el tiempo del mensaje.", "retryable": True}}
                elapsed = 0
            else:
                ctx = ToolContext(self.settings.gateway_url, state["token"], state["request_id"],
                                  self.settings.tool_timeout_s, self.tool_transport)
                t0 = time.monotonic()
                output = self.tools.execute(call["name"], call["arguments"], ctx)
                elapsed = int((time.monotonic() - t0) * 1000)
            results.append({"n": n, "tool": call["name"], "arguments": call["arguments"], "output": output})
            steps.append({"n": len(steps) + 1, "node": "ejecutar_herramientas", "tool": call["name"],
                          "args": call["arguments"], "ok": output["ok"],
                          "errorCode": None if output["ok"] else output["error"]["code"], "durationMs": elapsed,
                          "resultSummary": summarize(output.get("data"))})
        return {"tool_results": results, "steps": steps}

    def verificar_evidencia(self, state: ChatState) -> dict:
        return {}

    def marcar_datos_no_disponibles(self, state: ChatState) -> dict:
        notes = list(state["unavailable"])
        for r in state["tool_results"]:
            if not r["output"]["ok"]:
                err = r["output"]["error"]
                note = HUMAN_ERRORS.get(err["code"], err["message"])
                notes.append(f"{r['tool']}: {note}")
        return {"unavailable": notes}

    def redactar_respuesta(self, state: ChatState) -> dict:
        good = [r for r in state["tool_results"] if r["output"]["ok"]]
        notes = list(state["unavailable"])
        if not good:
            if not len(self.tools):
                notes.append("Aún no hay herramientas de consulta conectadas en esta versión del agente.")
            elif not state["plan"] and not state.get("model_failed"):
                notes.append("No encontré una herramienta que responda esa pregunta. Pregúntame por tus cursos, "
                             "calificaciones, progreso o alertas.")
            has_error = state.get("model_failed") or any(not r["output"]["ok"] for r in state["tool_results"])
            return {"answer": Answer(unavailable=notes).model_dump(), "unavailable": notes,
                    "status": "error" if has_error else "partial"}
        data_blocks = "\n".join(
            f'<datos_herramienta paso="{r["n"]}" herramienta="{r["tool"]}">\n{clean(json.dumps(r["output"]["data"], ensure_ascii=False))}\n</datos_herramienta>'
            for r in good)
        messages = [{"role": "system", "content": prompts.DRAFTER_SYSTEM},
                    {"role": "user", "content": f"Pregunta del docente: {state['message']}\n\n{data_blocks}"}]
        try:
            reply = self.llm.chat(messages, response_format=Draft.model_json_schema(), temperature=0.0)
            draft = Draft.model_validate_json(reply["content"])
        except (LLMError, ValidationError, ValueError) as exc:
            code = getattr(exc, "code", "DRAFT_INVALID")
            steps = state["steps"] + [{"n": len(state["steps"]) + 1, "node": "redactar_respuesta", "tool": None,
                                       "ok": False, "errorCode": code, "durationMs": 0}]
            notes.append("No pude redactar la respuesta con los datos obtenidos; reintenta en un momento.")
            return {"answer": Answer(unavailable=notes).model_dump(), "unavailable": notes, "status": "error", "steps": steps}
        valid_steps = {r["n"]: r["tool"] for r in good}
        facts = [Fact(text=f.text, sources=[Source(tool=f.tool, stepN=f.stepN)] if valid_steps.get(f.stepN) == f.tool else [])
                 for f in draft.facts]
        # Diseño, sección 6: toda inferencia indica en qué hechos se basa y toda recomendación se vincula a un
        # hallazgo. Lo que no tenga respaldo válido se descarta.
        inferences = [Inference(text=i.text, basedOn=[b for b in i.basedOn if 0 <= b < len(facts)]) for i in draft.inferences]
        recommendations = [Recommendation(text=r.text, relatedFinding=r.relatedFinding) for r in draft.recommendations
                           if r.relatedFinding is not None and 0 <= r.relatedFinding < len(facts)]
        answer = Answer(
            facts=facts,
            inferences=[i for i in inferences if i.basedOn],
            recommendations=recommendations,
            unavailable=notes + draft.unavailable)
        steps = state["steps"] + [{"n": len(state["steps"]) + 1, "node": "redactar_respuesta", "tool": None, "ok": True,
                                   "errorCode": None, "durationMs": reply["durationMs"]}]
        last_sync = find_value([r["output"]["data"] for r in good], "lastSyncAt") or \
            find_value([r["output"]["data"] for r in good], "calculatedAt")
        return {"answer": answer.model_dump(), "steps": steps, "last_sync_at": last_sync,
                "unavailable": notes}

    def validar_salida(self, state: ChatState) -> dict:
        """Código determinista: toda cifra de los hechos debe salir de la salida de alguna herramienta."""
        answer = state["answer"]
        if not answer["facts"]:
            return {"retry": False}
        allowed = numbers_in(json.dumps([r["output"].get("data") for r in state["tool_results"]], ensure_ascii=False))
        allowed |= numbers_in(state["message"]) | ({float(state["course_id"])} if state.get("course_id") else set())
        bad = [f for f in answer["facts"] if numbers_in(f["text"]) - allowed]
        if not bad:
            return {"retry": False, "validated": True}
        if state["redactions"] < 1:
            return {"retry": True, "redactions": state["redactions"] + 1}
        keep = [f for f in answer["facts"] if f not in bad]
        answer = {**answer, "facts": keep, "unavailable": answer["unavailable"] + [
            "Se omitió una cifra que no pudo comprobarse con los datos de las herramientas."]}
        return {"retry": False, "validated": False, "answer": answer, "unsourced_removed": len(bad)}

    def guardar_traza(self, state: ChatState) -> dict:
        answer = state["answer"]
        status = state.get("status") or "ok"
        if status == "ok" and answer["unavailable"] and not answer.get("message"):
            status = "partial" if answer["facts"] else "error"
        if status == "ok" and any(not r["output"]["ok"] for r in state["tool_results"]):
            status = "partial"
        tools_used = [s for s in state["steps"] if s.get("tool")]
        trace = {
            "traceId": state["trace_id"], "requestId": state["request_id"], "startedAt": state["started_at"],
            "finishedAt": now_iso(), "teacherId": state.get("teacher_id"), "model": self.settings.model,
            "message": {"text": state["message"], "redacted": False}, "intent": state.get("intent"),
            "steps": state["steps"],
            "output": {"validated": state.get("validated", True), "unsourcedNumbersRemoved": state.get("unsourced_removed", 0)},
            "totals": {"toolCalls": len(tools_used), "durationMs": int((time.monotonic() - state["started_mono"]) * 1000)},
            "status": status,
        }
        self.trace_sink(trace)  # nunca incluye el JWT
        return {"status": status}

    # ------------------------------------------------------------ entrada
    def run(self, message: str, course_id: int | None, token: str, teacher_id: str | None, request_id: str) -> ChatResponse:
        state = self.graph.invoke({"message": message, "course_id": course_id, "token": token,
                                   "teacher_id": teacher_id, "request_id": request_id})
        return ChatResponse(traceId=state["trace_id"], answer=Answer(**state["answer"]),
                            meta=Meta(courseId=course_id, lastSyncAt=state.get("last_sync_at"), status=state["status"]))
