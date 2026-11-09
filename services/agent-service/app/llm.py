"""Cliente de Ollama (API /api/chat). El modelo se elige en S1-12 y se configura con AGENT_MODEL."""
import httpx

from .config import Settings


class LLMError(Exception):
    """El modelo no respondió. `code` es LLM_TIMEOUT o LLM_UNAVAILABLE."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class OllamaClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        self.settings = settings
        self._http = httpx.Client(base_url=settings.ollama_url, transport=transport, timeout=settings.message_timeout_s)

    def chat(self, messages: list, *, tools: list | None = None, response_format: dict | None = None,
             temperature: float = 0.0, timeout: float | None = None) -> dict:
        """Una petición al modelo. Devuelve {content, tool_calls, durationMs}.

        `think: false` desactiva el razonamiento de qwen3 (más rápido, como en el benchmark de S1-12).
        `response_format` es un JSON Schema para obtener una salida estructurada.
        """
        payload = {
            "model": self.settings.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "keep_alive": self.settings.keep_alive,
            "options": {"temperature": temperature},
        }
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["format"] = response_format
        try:
            response = self._http.post("/api/chat", json=payload, timeout=timeout or self.settings.message_timeout_s)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMError("LLM_TIMEOUT", "El modelo tardó demasiado en responder.") from exc
        except httpx.HTTPError as exc:
            raise LLMError("LLM_UNAVAILABLE", f"No se pudo consultar al modelo: {exc.__class__.__name__}.") from exc
        data = response.json()
        message = data.get("message", {})
        return {
            "content": message.get("content", "") or "",
            "tool_calls": message.get("tool_calls") or [],
            "durationMs": int(data.get("total_duration", 0) / 1_000_000),
        }

    def status(self) -> dict:
        """Estado para /health: si Ollama responde y si el modelo configurado está descargado."""
        try:
            r = self._http.get("/api/tags", timeout=3)
            r.raise_for_status()
            names = [m.get("name", "") for m in r.json().get("models", [])]
        except httpx.HTTPError:
            return {"reachable": False, "model": self.settings.model, "modelAvailable": False}
        return {"reachable": True, "model": self.settings.model, "modelAvailable": self.settings.model in names}
