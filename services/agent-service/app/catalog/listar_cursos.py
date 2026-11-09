"""3.1 listar_cursos: cursos a los que el docente tiene acceso (GET /api/v1/courses)."""
from ..gateway import gateway_get
from ..tools import Tool, ToolContext, ok_output
from .common import NoArgs, fecha, plural


def run(ctx: ToolContext, _args: NoArgs) -> dict:
    body, error = gateway_get(ctx, "/api/v1/courses")
    if error:
        return error
    courses = [{"id": c["id"], "shortName": c.get("shortName"), "fullName": c.get("fullName"),
                "studentCount": c.get("studentCount"),  # el gateway lo omite en un curso nunca sincronizado
                "lastSyncAt": c.get("lastSyncAt")} for c in body]
    # `total` lo cuenta el código: así el modelo no tiene que contar y la cifra tiene fuente
    return ok_output({"courses": courses, "total": len(courses)}, "GET /api/v1/courses", ctx.request_id)


def facts(data: dict) -> list[str]:
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


TOOL = Tool(
    name="listar_cursos",
    description="Lista los cursos a los que el docente tiene acceso, con su nombre, la cantidad de estudiantes y la "
                "fecha de la última sincronización con Moodle. No necesita parámetros.",
    input_model=NoArgs,
    run=run,
    facts=facts,
)
