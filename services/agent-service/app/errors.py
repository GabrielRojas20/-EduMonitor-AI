"""Errores HTTP del agente, en el formato del gateway (RFC 7807): title, status, code, detail y traceId."""

PROBLEMS = {
    "VALIDATION_ERROR": (400, "Parámetros inválidos"),
    "TOKEN_INVALID": (401, "Token ausente o inválido"),
    "TOKEN_EXPIRED": (401, "Token vencido"),
}


class ApiError(Exception):
    def __init__(self, code: str, detail: str | None = None):
        self.status, self.title = PROBLEMS[code]
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail or self.title}")

    def body(self, trace_id: str) -> dict:
        out = {"title": self.title, "status": self.status, "code": self.code, "traceId": trace_id}
        if self.detail:
            out["detail"] = self.detail
        return out
