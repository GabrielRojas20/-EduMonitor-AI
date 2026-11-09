"""Errores en el formato Problem (RFC 7807) que define el contrato del gateway."""

# código estable -> (estado HTTP, título)
PROBLEMS = {
    "INVALID_CREDENTIALS": (401, "Credenciales inválidas"),
    "TOKEN_INVALID": (401, "Token ausente o inválido"),
    "TOKEN_EXPIRED": (401, "Token vencido"),
    "COURSE_NOT_AUTHORIZED": (403, "El docente no tiene acceso a este curso"),
    "COURSE_NOT_FOUND": (404, "Curso no encontrado"),
    "STUDENT_NOT_FOUND": (404, "Estudiante no encontrado"),
    "SYNC_IN_PROGRESS": (409, "Ya hay una sincronización en curso"),
    "MOODLE_UNAVAILABLE": (503, "Moodle o un servicio interno no responde"),
    "DATA_NOT_AVAILABLE": (503, "No se puede obtener el recurso o la fuente de datos completa"),
    "VALIDATION_ERROR": (400, "Parámetros inválidos"),
}


class ApiError(Exception):
    def __init__(self, code: str, detail: str | None = None):
        status, title = PROBLEMS[code]
        super().__init__(f"{code}: {detail or title}")
        self.code = code
        self.status = status
        self.title = title
        self.detail = detail

    def body(self, trace_id: str) -> dict:
        out = {
            "type": f"https://edumonitor.local/problems/{self.code.lower().replace('_', '-')}",
            "title": self.title,
            "status": self.status,
            "code": self.code,
            "traceId": trace_id,
        }
        if self.detail:
            out["detail"] = self.detail
        return out
