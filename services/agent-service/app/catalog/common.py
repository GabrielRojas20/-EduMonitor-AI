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


def num(value) -> str:
    """8.0 -> «8»; 8.5 -> «8,5»; 44.44 -> «44,44»."""
    value = float(value)
    return f"{value:.0f}" if value == int(value) else f"{value:.2f}".rstrip("0").replace(".", ",")
