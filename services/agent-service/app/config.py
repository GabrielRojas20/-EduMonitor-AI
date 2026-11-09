"""Configuración del agent-service. Todo se lee de variables de entorno (ver .env.example)."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ollama_url: str
    model: str
    gateway_url: str
    keep_alive: str
    max_tool_calls: int  # máximo de llamadas a herramientas por mensaje (diseño, sección 2)
    tool_timeout_s: float  # tiempo máximo por herramienta
    message_timeout_s: float  # tiempo máximo por mensaje
    cors_origins: tuple


def get_settings() -> Settings:
    env = os.environ.get
    origins = env("AGENT_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    return Settings(
        ollama_url=env("OLLAMA_URL", "http://localhost:11434").rstrip("/"),
        model=env("AGENT_MODEL", "qwen3:1.7b"),
        gateway_url=env("GATEWAY_URL", "http://localhost:5000").rstrip("/"),
        keep_alive=env("OLLAMA_KEEP_ALIVE", "10m"),
        max_tool_calls=int(env("MAX_TOOL_CALLS", "5")),
        tool_timeout_s=float(env("TOOL_TIMEOUT_SECONDS", "10")),
        message_timeout_s=float(env("MESSAGE_TIMEOUT_SECONDS", "60")),
        cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
    )
