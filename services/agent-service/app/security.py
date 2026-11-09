"""Comprobación del JWT del docente.

Diseño (nodo `validar_contexto`): el agente solo comprueba que el token exista y no esté vencido.
La firma y el acceso al curso los valida el gateway en cada llamada. El token nunca se escribe en
trazas ni en registros.
"""
import base64
import json
import time

from .errors import ApiError


def check_token(authorization: str | None) -> tuple[str, str | None]:
    """Devuelve (token, id del docente) o lanza TOKEN_INVALID / TOKEN_EXPIRED."""
    if not authorization or not authorization.lower().startswith("bearer ") or not authorization[7:].strip():
        raise ApiError("TOKEN_INVALID", "Falta el encabezado Authorization: Bearer <JWT>.")
    token = authorization[7:].strip()
    parts = token.split(".")
    if len(parts) != 3:
        raise ApiError("TOKEN_INVALID", "El token no tiene el formato de un JWT.")
    try:
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
        exp = int(payload["exp"])
    except Exception:
        raise ApiError("TOKEN_INVALID", "No se pudo leer el contenido del token.")
    if exp <= int(time.time()):
        raise ApiError("TOKEN_EXPIRED", "El token venció; inicie sesión de nuevo.")
    sub = payload.get("sub")
    return token, str(sub) if sub is not None else None
