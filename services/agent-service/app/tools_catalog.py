"""Herramientas del agente (docs/agent-design/diseno-agente.md, sección 3). Todas son de solo lectura."""
from datetime import datetime

from pydantic import BaseModel

from .gateway import gateway_get
from .tools import Tool, ToolContext, ok_output


class NoArgs(BaseModel):
    """Herramienta sin parámetros."""


def listar_cursos_run(ctx: ToolContext, _args: NoArgs) -> dict:
    """3.1 listar_cursos: cursos a los que el docente tiene acceso (GET /api/v1/courses)."""
    body, error = gateway_get(ctx, "/api/v1/courses")
    if error:
        return error
    courses = [{"id": c["id"], "shortName": c.get("shortName"), "fullName": c.get("fullName"),
                "studentCount": c.get("studentCount"),  # el gateway lo omite en un curso nunca sincronizado
                "lastSyncAt": c.get("lastSyncAt")} for c in body]
    # `total` lo cuenta el código: así el modelo no tiene que contar y la cifra tiene fuente
    return ok_output({"courses": courses, "total": len(courses)}, "GET /api/v1/courses", ctx.request_id)


def fecha(iso: str) -> str:
    """2026-10-22T15:04:05Z -> 22/10/2026"""
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%d/%m/%Y")


def plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def listar_cursos_facts(data: dict) -> list[str]:
    """Hechos de la lista de cursos, redactados por código a partir de la salida de la herramienta."""
    if data["total"] == 0:
        return ["No tienes cursos con acceso autorizado."]
    out = [f"Tienes acceso a {plural(data['total'], 'curso', 'cursos')}."]
    for c in data["courses"]:
        name = f"{c['shortName']} ({c['fullName']})"
        count, synced = c["studentCount"], c["lastSyncAt"]
        if count is not None and synced:
            out.append(f"{name}: {plural(count, 'estudiante', 'estudiantes')}; última sincronización con Moodle el {fecha(synced)}.")
        elif synced:
            out.append(f"{name}: última sincronización con Moodle el {fecha(synced)}; el número de estudiantes no está disponible.")
        else:
            out.append(f"{name}: aún no se sincronizó con Moodle, por lo que el número de estudiantes no está disponible.")
    return out


LISTAR_CURSOS = Tool(
    name="listar_cursos",
    description="Lista los cursos a los que el docente tiene acceso, con su nombre, la cantidad de estudiantes y la "
                "fecha de la última sincronización con Moodle. No necesita parámetros.",
    input_model=NoArgs,
    run=listar_cursos_run,
    facts=listar_cursos_facts,
)
