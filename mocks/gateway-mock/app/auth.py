"""JWT HS256 mínimo para el mock. La clave es de pruebas y no protege nada real."""
import base64
import hashlib
import hmac
import json
import os
import time

from .errors import ApiError


def _secret() -> bytes:
    return os.environ.get("MOCK_JWT_SECRET", "clave-solo-para-el-mock").encode()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(signing_input: str) -> str:
    return _b64(hmac.new(_secret(), signing_input.encode(), hashlib.sha256).digest())


def create_token(user: dict, expires_in: int = 3600) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = _b64(json.dumps({
        "sub": str(user["id"]),
        "name": user["name"],
        "role": user["role"],
        "iat": now,
        "exp": now + int(expires_in),
    }).encode())
    return f"{header}.{payload}.{_sign(header + '.' + payload)}"


def decode_token(token: str) -> dict:
    """Devuelve los datos del token o lanza TOKEN_INVALID / TOKEN_EXPIRED."""
    try:
        header, payload, signature = token.split(".")
        if not hmac.compare_digest(signature, _sign(f"{header}.{payload}")):
            raise ValueError("firma")
        data = json.loads(_unb64(payload))
    except Exception:
        raise ApiError("TOKEN_INVALID", "El token no es válido.")
    if int(data.get("exp", 0)) <= int(time.time()):
        raise ApiError("TOKEN_EXPIRED", "El token venció; inicie sesión de nuevo.")
    return data
