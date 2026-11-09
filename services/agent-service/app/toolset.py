"""Herramientas que el agente tiene disponibles. Se añaden aquí a medida que se implementan."""
from .tools import ToolRegistry
from .tools_catalog import LISTAR_CURSOS


def default_registry() -> ToolRegistry:
    return ToolRegistry([LISTAR_CURSOS])
