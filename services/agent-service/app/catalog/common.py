"""Piezas que comparten las herramientas."""
from datetime import datetime

from pydantic import BaseModel


class NoArgs(BaseModel):
    """Herramienta sin parámetros."""


def fecha(iso: str) -> str:
    """2026-10-22T15:04:05Z -> 22/10/2026"""
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%d/%m/%Y")


def plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"
