"""Llamadas de lectura al api-gateway, con el JWT del docente.

El agente nunca accede a la base de datos ni a Moodle: toda la información pasa por aquí. El gateway valida la
firma, el vencimiento y el acceso al curso; el agente solo traduce su respuesta a la salida común de las herramientas.
El JWT se reenvía en la cabecera y no se escribe en ninguna salida, traza ni mensaje de error.
"""
import httpx

from .tools import ToolContext, error_output

# Códigos del gateway que el agente reconoce (diseño, sección 3); TOOL_TIMEOUT lo añade el propio agente.
KNOWN_CODES = {"TOKEN_EXPIRED", "TOKEN_INVALID", "COURSE_NOT_AUTHORIZED", "COURSE_NOT_FOUND", "STUDENT_NOT_FOUND",
               "MOODLE_UNAVAILABLE", "DATA_NOT_AVAILABLE", "VALIDATION_ERROR"}
RETRYABLE = {"MOODLE_UNAVAILABLE", "TOOL_TIMEOUT"}
CODE_BY_STATUS = {400: "VALIDATION_ERROR", 401: "TOKEN_INVALID", 403: "COURSE_NOT_AUTHORIZED", 404: "COURSE_NOT_FOUND",
                  503: "MOODLE_UNAVAILABLE"}


def gateway_get(ctx: ToolContext, path: str, params: dict | None = None) -> tuple[dict | list | None, dict | None]:
    """GET al gateway. Devuelve (cuerpo JSON, None) si sale bien o (None, salida de error de la herramienta)."""
    endpoint = f"GET {path}"
    headers = {"Authorization": f"Bearer {ctx.token}", "X-Request-Id": ctx.request_id, "Accept": "application/json"}
    try:
        with httpx.Client(base_url=ctx.gateway_url, transport=ctx.transport, timeout=ctx.timeout_s) as http:
            response = http.get(path, params=params, headers=headers)
    except httpx.TimeoutException:
        return None, error_output("TOOL_TIMEOUT", "El gateway tardó demasiado en responder.", True, endpoint, ctx.request_id)
    except httpx.HTTPError:
        return None, error_output("MOODLE_UNAVAILABLE", "No se pudo conectar con el gateway.", True, endpoint, ctx.request_id)

    if response.status_code == 200:
        try:
            return response.json(), None
        except ValueError:
            return None, error_output("MOODLE_UNAVAILABLE", "El gateway devolvió una respuesta que no es JSON.", True,
                                      endpoint, ctx.request_id)
    try:
        problem = response.json()
    except ValueError:
        problem = {}
    code = problem.get("code") if isinstance(problem, dict) else None
    if code not in KNOWN_CODES:
        code = CODE_BY_STATUS.get(response.status_code, "MOODLE_UNAVAILABLE")
    message = (problem.get("detail") or problem.get("title") or f"El gateway respondió {response.status_code}.") \
        if isinstance(problem, dict) else f"El gateway respondió {response.status_code}."
    return None, error_output(code, str(message)[:300], code in RETRYABLE, endpoint, ctx.request_id)
