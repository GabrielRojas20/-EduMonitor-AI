"""Catálogo de herramientas del agente (docs/agent-design/diseno-agente.md, sección 3).

Cada herramienta vive en su propio archivo y define una variable `TOOL`. `app/toolset.py` las descubre solas, así que
añadir una herramienta no obliga a editar ningún archivo compartido (y los PR de herramientas distintas no chocan).
Todas son de solo lectura.
"""
