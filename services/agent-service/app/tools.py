"""Registro de herramientas del agente (docs/agent-design/diseno-agente.md, sección 3).

Cada herramienta valida su entrada con Pydantic y devuelve la salida común:
{ok, data, error, source}. Un fallo nunca lanza una excepción hacia el flujo: se devuelve como `ok: false`.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from pydantic import BaseModel, ValidationError


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ok_output(data: dict, endpoint: str, request_id: str) -> dict:
    return {"ok": True, "data": data, "error": None,
            "source": {"endpoint": endpoint, "requestId": request_id, "fetchedAt": now_iso()}}


def error_output(code: str, message: str, retryable: bool = False, endpoint: str | None = None,
                 request_id: str | None = None) -> dict:
    source = {"endpoint": endpoint, "requestId": request_id, "fetchedAt": now_iso()} if endpoint else None
    return {"ok": False, "data": None, "error": {"code": code, "message": message, "retryable": retryable},
            "source": source}


@dataclass
class ToolContext:
    """Lo que una herramienta necesita para llamar al gateway en nombre del docente."""
    gateway_url: str
    token: str  # JWT del docente: se reenvía al gateway y no se registra
    request_id: str
    timeout_s: float
    transport: object | None = None  # para pruebas


@dataclass
class Tool:
    name: str
    description: str
    input_model: type[BaseModel]
    run: Callable[[ToolContext, BaseModel], dict]
    # Redacta los hechos a partir de los datos, con código: así un modelo pequeño no puede equivocarse al copiar cifras
    # ni atribuir un dato a la entidad equivocada. Sin esta función, el modelo redacta los hechos.
    facts: Callable[[dict], list[str]] | None = None

    def schema(self) -> dict:
        """Definición en el formato de herramientas de Ollama."""
        params = self.input_model.model_json_schema()
        params.pop("title", None)
        params.pop("description", None)  # la docstring de la clase de entrada es para quien lee el código
        for prop in params.get("properties", {}).values():
            prop.pop("title", None)
            prop.pop("default", None)
            # `int | None` se publica como {"anyOf": [{"type": "integer"}, {"type": "null"}]}; un modelo pequeño lo sigue mejor simple
            options = [o for o in prop.pop("anyOf", []) if o.get("type") != "null"]
            if len(options) == 1:
                prop.update(options[0])
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": params}}


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None):
        self._tools = {t.name: t for t in (tools or [])}

    def __len__(self) -> int:
        return len(self._tools)

    def names(self) -> list[str]:
        return list(self._tools)

    def schemas(self) -> list[dict]:
        return [t.schema() for t in self._tools.values()]

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def execute(self, name: str, arguments: dict, ctx: ToolContext) -> dict:
        """Valida los argumentos y ejecuta la herramienta. Siempre devuelve la salida común."""
        tool = self._tools.get(name)
        if tool is None:
            return error_output("VALIDATION_ERROR", f"La herramienta «{name}» no existe.")
        try:
            args = tool.input_model.model_validate(arguments or {})
        except ValidationError as exc:
            return error_output("VALIDATION_ERROR", f"Argumentos inválidos para {name}: {exc.errors()[0]['msg']}.")
        try:
            return tool.run(ctx, args)
        except Exception as exc:  # una herramienta rota no debe tumbar la conversación
            return error_output("MOODLE_UNAVAILABLE", f"La herramienta {name} falló ({exc.__class__.__name__}).", True)
