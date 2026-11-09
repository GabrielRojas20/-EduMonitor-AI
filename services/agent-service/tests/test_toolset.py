"""El catálogo: cada herramienta en su archivo y descubierta sola, sin registro compartido."""
import importlib
import pkgutil

import pytest

from app import catalog
from app.tools import Tool
from app.toolset import default_registry, discover

MODULES = [m.name for m in pkgutil.iter_modules(catalog.__path__) if m.name != "common" and not m.name.startswith("_")]


def test_every_tool_file_is_discovered():
    assert sorted(t.name for t in discover()) == sorted(MODULES)
    assert default_registry().names() == sorted(MODULES)


@pytest.mark.parametrize("module", MODULES)
def test_each_tool_follows_the_conventions(module):
    tool = importlib.import_module(f"app.catalog.{module}").TOOL
    assert isinstance(tool, Tool)
    assert tool.name == module, "el archivo y la herramienta se llaman igual"
    assert tool.description and tool.facts is not None, "toda herramienta describe y redacta sus hechos por código"
    schema = tool.schema()["function"]
    assert schema["name"] == tool.name and schema["parameters"]["type"] == "object"


def test_a_file_without_tool_is_reported(monkeypatch):
    import types
    broken = types.ModuleType("app.catalog.sin_tool")
    monkeypatch.setattr(pkgutil, "iter_modules", lambda path: [pkgutil.ModuleInfo(None, "sin_tool", False)])
    monkeypatch.setitem(__import__("sys").modules, "app.catalog.sin_tool", broken)
    with pytest.raises(RuntimeError, match="debe definir TOOL"):
        discover()
