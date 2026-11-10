"""Herramienta listar_cursos contra un gateway simulado."""
import json

import httpx
import pytest

from app.graph import Agent
from app.tools import ToolContext
from app.catalog.common import NoArgs
from app.catalog.listar_cursos import TOOL as LISTAR_CURSOS
from app.toolset import default_registry
from conftest import make_token

COURSES = [
    {"id": 2, "shortName": "PRUEBA01", "fullName": "Curso de Prueba EduMonitor", "studentCount": 5,
     "lastSyncAt": "2026-10-22T15:04:05Z"},
    {"id": 3, "shortName": "PRUEBA02", "fullName": "Curso sin sincronizar", "lastSyncAt": None},  # sin studentCount
]
TOKEN = make_token()


def gateway(handler):
    return httpx.MockTransport(handler)


def ctx(handler, token=TOKEN):
    return ToolContext("http://gateway.test", token, "req-42", 2.0, gateway(handler))


def run(handler, token=TOKEN):
    return LISTAR_CURSOS.run(ctx(handler, token), NoArgs())


def problem(status, code=None, **extra):
    body = {"title": "Error", "status": status, **({"code": code} if code else {}), **extra}
    return httpx.Response(status, json=body, headers={"content-type": "application/problem+json"})


def test_success_returns_the_common_output():
    out = run(lambda r: httpx.Response(200, json=COURSES))
    assert out["ok"] is True and out["error"] is None
    assert out["source"]["endpoint"] == "GET /api/v1/courses" and out["source"]["requestId"] == "req-42"
    assert out["data"]["total"] == 2
    assert out["data"]["courses"][0] == {"id": 2, "shortName": "PRUEBA01", "fullName": "Curso de Prueba EduMonitor",
                                         "studentCount": 5, "lastSyncAt": "2026-10-22T15:04:05Z"}
    assert out["data"]["courses"][1]["studentCount"] is None  # un curso sin sincronizar no tiene conteo


def test_no_courses_is_a_valid_empty_answer():
    out = run(lambda r: httpx.Response(200, json=[]))
    assert out["ok"] is True and out["data"] == {"courses": [], "total": 0}


def test_forwards_the_teacher_jwt_and_the_request_id():
    seen = {}

    def handler(request: httpx.Request):
        seen.update(method=request.method, path=request.url.path, auth=request.headers.get("authorization"),
                    rid=request.headers.get("x-request-id"))
        return httpx.Response(200, json=COURSES)

    run(handler)
    assert seen == {"method": "GET", "path": "/api/v1/courses", "auth": f"Bearer {TOKEN}", "rid": "req-42"}


@pytest.mark.parametrize("response,expected_code,retryable", [
    (problem(401, "TOKEN_EXPIRED"), "TOKEN_EXPIRED", False),
    (problem(401, "TOKEN_INVALID"), "TOKEN_INVALID", False),
    (problem(403, "COURSE_NOT_AUTHORIZED"), "COURSE_NOT_AUTHORIZED", False),
    (problem(503, "MOODLE_UNAVAILABLE"), "MOODLE_UNAVAILABLE", True),
    (problem(503, "DATA_NOT_AVAILABLE"), "DATA_NOT_AVAILABLE", False),
    (problem(401), "TOKEN_INVALID", False),                       # sin código: se deduce del estado
    (problem(503, "CODIGO_RARO"), "MOODLE_UNAVAILABLE", True),     # código que el agente no conoce
    (httpx.Response(502, text="<html>Bad Gateway</html>"), "MOODLE_UNAVAILABLE", True),
])
def test_gateway_errors_become_tool_errors(response, expected_code, retryable):
    out = run(lambda r: response)
    assert out["ok"] is False and out["data"] is None
    assert out["error"]["code"] == expected_code and out["error"]["retryable"] is retryable
    assert out["error"]["message"]


def test_timeout_and_connection_failures():
    def timeout(request):
        raise httpx.ReadTimeout("lento", request=request)

    def refused(request):
        raise httpx.ConnectError("sin conexión", request=request)

    assert run(timeout)["error"] == {"code": "TOOL_TIMEOUT", "message": "El gateway tardó demasiado en responder.",
                                     "retryable": True}
    assert run(refused)["error"]["code"] == "MOODLE_UNAVAILABLE"


def test_a_200_that_is_not_json_is_an_error():
    out = run(lambda r: httpx.Response(200, text="no soy json"))
    assert out["ok"] is False and out["error"]["code"] == "MOODLE_UNAVAILABLE"


def test_the_jwt_never_appears_in_any_output():
    outputs = [run(lambda r: httpx.Response(200, json=COURSES)), run(lambda r: problem(401, "TOKEN_EXPIRED", detail="venció")),
               run(lambda r: httpx.Response(502, text="x"))]
    assert all(TOKEN not in json.dumps(o) for o in outputs)


def test_schema_offered_to_the_model():
    schema = LISTAR_CURSOS.schema()["function"]
    assert schema["name"] == "listar_cursos" and schema["parameters"] == {"properties": {}, "type": "object"}
    assert "cursos" in schema["description"]
    assert "listar_cursos" in default_registry().names()


# ---- flujo completo: modelo simulado + herramienta real + gateway simulado
CALL = [{"function": {"name": "listar_cursos", "arguments": {}}}]


def draft(text):
    return json.dumps({"facts": [{"text": text, "tool": "listar_cursos", "stepN": 1}], "inferences": [],
                       "recommendations": [], "unavailable": []})


def agent(settings, ollama, traces, handler):
    return Agent(settings, ollama.client(settings), default_registry(), trace_sink=traces.append,
                 tool_transport=gateway(handler))


def test_facts_are_written_by_code_and_the_model_is_not_needed_for_a_simple_list(settings, ollama, traces):
    ollama.reply(tool_calls=CALL)  # solo se usa el modelo para elegir la herramienta
    res = agent(settings, ollama, traces, lambda r: httpx.Response(200, json=COURSES)).run(
        "¿Qué cursos tengo?", None, TOKEN, "3", "req-42")
    assert [f.text for f in res.answer.facts] == [
        "Tienes acceso a 2 cursos.",
        "PRUEBA01 (Curso de Prueba EduMonitor): 5 estudiantes; última sincronización con Moodle el 22/10/2026.",
        "PRUEBA02 (Curso sin sincronizar): aún no se sincronizó con Moodle, por lo que el número de estudiantes no está disponible.",
    ]
    assert all(f.sources[0].tool == "listar_cursos" and f.sources[0].stepN == 1 for f in res.answer.facts)
    assert res.meta.status == "ok" and res.meta.lastSyncAt == "2026-10-22T15:04:05Z"
    assert len(ollama.calls) == 1                      # no hubo redacción: nada que el modelo pueda inventar
    assert traces[0]["steps"][1]["resultSummary"] == {"courses": 2, "total": 2}
    assert TOKEN not in json.dumps(traces[0])


def test_a_dato_no_disponible_is_never_attributed_to_another_course(settings, ollama, traces):
    """Un modelo pequeño escribió «PRUEBA02 tiene 5 estudiantes» (el 5 era de PRUEBA01). Ya no redacta los hechos."""
    ollama.reply(tool_calls=CALL)
    res = agent(settings, ollama, traces, lambda r: httpx.Response(200, json=COURSES)).run(
        "¿Qué cursos tengo?", None, TOKEN, "3", "req-42")
    sin_sincronizar = next(f.text for f in res.answer.facts if f.text.startswith("PRUEBA02"))
    assert "5" not in sin_sincronizar and "no está disponible" in sin_sincronizar


def test_the_model_only_interprets_when_the_teacher_asks_for_it(settings, ollama, traces):
    ollama.reply(tool_calls=CALL)
    ollama.reply(json.dumps({
        "facts": [{"text": "Hecho inventado por el modelo: 99 cursos.", "tool": "listar_cursos", "stepN": 1}],  # se ignora
        "inferences": [{"text": "El curso sin sincronizar podría estar pendiente de carga.", "basedOn": [2]},
                       {"text": "Sin base.", "basedOn": []}],
        "recommendations": [{"text": "Sincroniza PRUEBA02 desde la lista de cursos.", "relatedFinding": 2},
                            {"text": "Revisa los 77 estudiantes.", "relatedFinding": 1},   # cifra sin fuente
                            {"text": "Sin hallazgo.", "relatedFinding": None}],
        "unavailable": []}))
    res = agent(settings, ollama, traces, lambda r: httpx.Response(200, json=COURSES)).run(
        "¿Qué cursos tengo y qué me recomiendas?", None, TOKEN, "3", "req-42")
    assert all("99" not in f.text for f in res.answer.facts)                          # los hechos siguen siendo del código
    assert [(i.text, i.basedOn) for i in res.answer.inferences] == [
        ("El curso sin sincronizar podría estar pendiente de carga.", [2])]
    assert [(r.text, r.relatedFinding) for r in res.answer.recommendations] == [
        ("Sincroniza PRUEBA02 desde la lista de cursos.", 2)]
    assert any("omitió una cifra" in u for u in res.answer.unavailable)
    prompt = ollama.calls[1]["messages"][1]["content"]
    assert "[2] PRUEBA02" in prompt and "no está disponible" in prompt and "null" not in prompt


def test_if_the_interpretation_fails_the_facts_are_still_shown(settings, ollama, traces):
    ollama.reply(tool_calls=CALL)
    ollama.fail(500)
    res = agent(settings, ollama, traces, lambda r: httpx.Response(200, json=COURSES)).run(
        "¿Qué me recomiendas hacer con mis cursos?", None, TOKEN, "3", "req-42")
    assert len(res.answer.facts) == 3 and res.answer.inferences == [] and res.answer.recommendations == []
    assert "solo los hechos" in res.answer.unavailable[0] and res.meta.status == "partial"


@pytest.mark.parametrize("message,expected", [
    ("¿Qué cursos tengo?", False), ("Lista mis cursos", False), ("¿Cuántos estudiantes tiene PRUEBA01?", False),
    ("¿Qué me recomiendas?", True), ("Analiza mis cursos", True), ("¿Qué debo hacer con PRUEBA02?", True),
    ("¿Por qué no tiene estudiantes?", True),
])
def test_when_the_model_is_asked_to_interpret(message, expected):
    from app.graph import needs_interpretation
    assert needs_interpretation(message) is expected


def test_course_facts_wording():
    from app.catalog.listar_cursos import facts as listar_cursos_facts
    assert listar_cursos_facts({"courses": [], "total": 0}) == ["No tienes cursos con acceso autorizado."]
    one = {"courses": [{"id": 2, "shortName": "A", "fullName": "Uno", "studentCount": 1, "lastSyncAt": "2026-01-05T00:00:00Z"}],
           "total": 1}
    assert listar_cursos_facts(one) == ["Tienes acceso a 1 curso.",
                                        "A (Uno): 1 estudiante; última sincronización con Moodle el 05/01/2026."]
    partial = {"courses": [{"id": 2, "shortName": "A", "fullName": "Uno", "studentCount": None,
                            "lastSyncAt": "2026-01-05T00:00:00Z"}], "total": 1}
    assert "el número de estudiantes no está disponible" in listar_cursos_facts(partial)[1]


def test_expired_session_in_the_gateway_is_explained_to_the_teacher(settings, ollama, traces):
    ollama.reply(tool_calls=CALL)
    res = agent(settings, ollama, traces, lambda r: problem(401, "TOKEN_EXPIRED")).run(
        "¿Qué cursos tengo?", None, TOKEN, "3", "req-42")
    assert res.meta.status == "error" and res.answer.facts == []
    assert "inicia sesión" in res.answer.unavailable[0]
    assert len(ollama.calls) == 1  # sin datos no se le pide al modelo que redacte


def test_gateway_down_does_not_invent_courses(settings, ollama, traces):
    def refused(request):
        raise httpx.ConnectError("caído", request=request)

    ollama.reply(tool_calls=CALL)
    res = agent(settings, ollama, traces, refused).run("¿Qué cursos tengo?", None, TOKEN, "3", "req-42")
    assert res.meta.status == "error" and res.answer.facts == []
    assert "no respondió" in res.answer.unavailable[0]
