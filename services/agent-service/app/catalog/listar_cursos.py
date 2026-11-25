"""3.1 listar_cursos: cursos a los que el docente tiene acceso (GET /api/v1/courses)."""
from pydantic import BaseModel, Field

from ..gateway import gateway_get
from ..tools import Tool, ToolContext, ok_output
from .common import fecha, plural


class ListarCursosArgs(BaseModel):
    """Sin parámetros para el modelo. `course_id` lo pone el código cuando el docente está dentro de un curso."""
    course_id: int | None = Field(default=None, ge=1, description="Id del curso en que está el docente")


def run(ctx: ToolContext, args: ListarCursosArgs) -> dict:
    body, error = gateway_get(ctx, "/api/v1/courses")
    if error:
        return error
    # El gateway entrega studentCount y lastSyncAt desde sus datos sincronizados; sin fecha, el curso no tiene una sincronización completada
    courses = [{"id": c["id"], "shortName": c.get("shortName"), "fullName": c.get("fullName"),
                "studentCount": c.get("studentCount"), "lastSyncAt": c.get("lastSyncAt")} for c in body]
    # `total` lo cuenta el código: así el modelo no tiene que contar y la cifra tiene fuente
    scoped = args.course_id is not None  # dentro de un curso, «¿cuántos estudiantes tengo?» se refiere a ese curso
    if scoped:
        courses = [c for c in courses if c["id"] == args.course_id]
    return ok_output({"courses": courses, "total": len(courses), **({"scoped": True} if scoped else {})}, "GET /api/v1/courses", ctx.request_id)


def facts(data: dict) -> list[str]:
    """Hechos de la lista de cursos, redactados por código a partir de la salida de la herramienta."""
    if data["total"] == 0:
        return ["No encontré ese curso entre los que tienes autorizados." if data.get("scoped") else "No tienes cursos con acceso autorizado."]
    out = [] if data.get("scoped") else [f"Tienes acceso a {plural(data['total'], 'curso', 'cursos')}."]
    for c in data["courses"]:
        name = f"{c['shortName']} ({c['fullName']})"
        count, synced = c["studentCount"], c["lastSyncAt"]
        if count is not None and synced:
            out.append(f"{name}: {plural(count, 'estudiante', 'estudiantes')}; última sincronización con Moodle el {fecha(synced)}.")
        elif synced:
            out.append(f"{name}: última sincronización con Moodle el {fecha(synced)}; el número de estudiantes no está disponible.")
        else:  # sin fecha: no hay una sincronización completada, y sin ella no hay número de estudiantes
            out.append(f"{name}: aún no se sincronizó con Moodle, por lo que el número de estudiantes no está disponible.")
    return out


TOOL = Tool(
    name="listar_cursos",
    description="Lista los cursos a los que el docente tiene acceso, con su nombre, la cantidad de estudiantes y la "
                "fecha de la última sincronización con Moodle. Úsala para cualquier pregunta sobre los cursos del docente: cuáles "
                "son, cuántos estudiantes tiene uno en concreto o cuándo se sincronizó por última vez. No necesita parámetros.",
    input_model=ListarCursosArgs,
    hidden=("course_id",),
    run=run,
    facts=facts,
)
