"""Herramientas que el agente tiene disponibles.

Se descubren solas: cada archivo de `app/catalog/` (salvo `common.py`) define una variable `TOOL`. Para añadir una
herramienta basta con crear su archivo; no hay que registrarla aquí.
"""
import importlib
import pkgutil

from . import catalog
from .tools import Tool, ToolRegistry


def discover() -> list[Tool]:
    tools = []
    for info in sorted(pkgutil.iter_modules(catalog.__path__), key=lambda i: i.name):
        if info.name.startswith("_") or info.name == "common":
            continue
        module = importlib.import_module(f"{catalog.__name__}.{info.name}")
        tool = getattr(module, "TOOL", None)
        if not isinstance(tool, Tool):
            raise RuntimeError(f"{module.__name__} debe definir TOOL (una instancia de Tool)")
        tools.append(tool)
    return tools


def default_registry() -> ToolRegistry:
    return ToolRegistry(discover())
