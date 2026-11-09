"""Herramientas que el agente tiene disponibles. Se añaden aquí a medida que se implementan."""
from .tools import ToolRegistry


def default_registry() -> ToolRegistry:
    return ToolRegistry([])
