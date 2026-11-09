"""Prueba rápida del modelo local con el flujo real del agente (sin gateway ni Moodle).

Uso (desde services/agent-service):
    .\\.venv\\Scripts\\python scripts\\probar_modelo.py
    .\\.venv\\Scripts\\python scripts\\probar_modelo.py "¿Qué cursos tengo?"

Muestra el tiempo del modelo, qué herramienta eligió y la respuesta en hechos, inferencias y recomendaciones.
Las herramientas son de ejemplo (en memoria); las reales llaman al gateway.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import BaseModel  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.graph import Agent  # noqa: E402
from app.llm import OllamaClient  # noqa: E402
from app.tools import Tool, ToolRegistry, ok_output  # noqa: E402

COURSES = {"courses": [{"id": 2, "shortName": "PRUEBA01", "fullName": "Curso de Prueba EduMonitor",
                        "studentCount": 5, "lastSyncAt": "2026-10-22T15:04:05Z"}], "total": 1}


class NoArgs(BaseModel):
    pass


def main() -> None:
    message = " ".join(sys.argv[1:]) or "¿Qué cursos tengo?"
    settings = get_settings()
    llm = OllamaClient(settings)
    print(f"Modelo: {settings.model} en {settings.ollama_url}")
    print(f"Estado de Ollama: {llm.status()}\n")

    t0 = time.monotonic()
    hello = llm.chat([{"role": "user", "content": "Responde solo con la palabra: listo"}])
    print(f"1) Respuesta simple: «{hello['content'].strip()}» ({time.monotonic() - t0:.1f} s, incluye la carga del modelo si estaba frío)\n")

    tools = ToolRegistry([Tool("listar_cursos", "Lista los cursos a los que el docente tiene acceso.", NoArgs,
                               lambda ctx, args: ok_output(COURSES, "GET /api/v1/courses", ctx.request_id))])
    traces: list = []
    agent = Agent(settings, llm, tools, trace_sink=traces.append)
    print(f"2) Pregunta al agente: «{message}»")
    t0 = time.monotonic()
    result = agent.run(message, None, "token-de-prueba", "3", "prueba-1")
    print(f"   Tiempo total: {time.monotonic() - t0:.1f} s\n")
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    print("\nTraza (pasos):")
    for step in traces[0]["steps"]:
        print(f"   {step['n']}. {step['node']:<24} herramienta={step.get('tool')} ok={step['ok']} {step['durationMs']} ms")


if __name__ == "__main__":
    main()
