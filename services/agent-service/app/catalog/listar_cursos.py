"""3.1 listar_cursos: cursos a los que el docente tiene acceso (GET /api/v1/courses)."""
from ..gateway import gateway_get
from ..tools import Tool, ToolContext, ok_output
from .common import NoArgs, fecha, plural


MAX_ENRICHED = 10  # a cuántos cursos se les consulta el estado de sincronización (el docente tiene pocos)


def sync_info(ctx: ToolContext, course_id: int) -> dict:
    """Estado de sincronización y número de estudiantes de un curso.

    El gateway real devuelve `studentCount` y `lastSyncAt` en `null` en la lista de cursos (auth-courses no conoce la
    sincronización), así que un `null` NO significa «nunca se sincronizó»: hay que preguntarlo. Si la consulta falla se
    devuelve `unknown`, y el agente no afirma nada sobre el estado."""
    status, error = gateway_get(ctx, f"/api/v1/courses/{course_id}/sync")
    if error or not isinstance(status, dict) or "state" not in status:
        return {"syncState": "unknown", "lastSyncAt": None, "studentCount": None}
    last = status.get("lastSuccessAt") or (status.get("finishedAt") if status["state"] == "succeeded" else None)
    count = None
    if last or status["state"] == "succeeded":
        page, error = gateway_get(ctx, f"/api/v1/courses/{course_id}/students", {"page": 1, "pageSize": 1})
        if not error and isinstance(page, dict) and isinstance(page.get("total"), int):
            count = page["total"]
    return {"syncState": status["state"], "lastSyncAt": last, "studentCount": count}


def run(ctx: ToolContext, _args: NoArgs) -> dict:
    body, error = gateway_get(ctx, "/api/v1/courses")
    if error:
        return error
    courses = []
    for i, c in enumerate(body):
        course = {"id": c["id"], "shortName": c.get("shortName"), "fullName": c.get("fullName"),
                  "studentCount": c.get("studentCount"), "lastSyncAt": c.get("lastSyncAt"),
                  "syncState": "succeeded" if c.get("lastSyncAt") else None}
        if (course["studentCount"] is None or not course["lastSyncAt"]) and i < MAX_ENRICHED:
            info = sync_info(ctx, c["id"])
            course["syncState"] = info["syncState"]
            course["lastSyncAt"] = course["lastSyncAt"] or info["lastSyncAt"]
            if course["studentCount"] is None:
                course["studentCount"] = info["studentCount"]
        elif course["syncState"] is None:
            course["syncState"] = "unknown"
        courses.append(course)
    # `total` lo cuenta el código: así el modelo no tiene que contar y la cifra tiene fuente
    return ok_output({"courses": courses, "total": len(courses)}, "GET /api/v1/courses", ctx.request_id)


def facts(data: dict) -> list[str]:
    """Hechos de la lista de cursos, redactados por código a partir de la salida de la herramienta."""
    if data["total"] == 0:
        return ["No tienes cursos con acceso autorizado."]
    out = [f"Tienes acceso a {plural(data['total'], 'curso', 'cursos')}."]
    for c in data["courses"]:
        name = f"{c['shortName']} ({c['fullName']})"
        count, synced, state = c["studentCount"], c["lastSyncAt"], c.get("syncState")
        if count is not None and synced:
            out.append(f"{name}: {plural(count, 'estudiante', 'estudiantes')}; última sincronización con Moodle el {fecha(synced)}.")
        elif synced:
            out.append(f"{name}: última sincronización con Moodle el {fecha(synced)}; el número de estudiantes no está disponible.")
        elif state == "running":
            out.append(f"{name}: se está sincronizando con Moodle en este momento, por lo que el número de estudiantes no está disponible todavía.")
        elif state == "failed":
            out.append(f"{name}: la última sincronización con Moodle falló, por lo que el número de estudiantes no está disponible.")
        elif state == "never":
            out.append(f"{name}: aún no se sincronizó con Moodle, por lo que el número de estudiantes no está disponible.")
        else:  # unknown u otro: no se afirma nada que no se sepa
            out.append(f"{name}: no se pudo consultar su estado de sincronización, por lo que no hay fecha ni número de estudiantes.")
    return out


TOOL = Tool(
    name="listar_cursos",
    description="Lista los cursos a los que el docente tiene acceso, con su nombre, la cantidad de estudiantes y la "
                "fecha de la última sincronización con Moodle. Úsala para cualquier pregunta sobre los cursos del docente: cuáles "
                "son, cuántos estudiantes tiene uno en concreto o cuándo se sincronizó por última vez. No necesita parámetros.",
    input_model=NoArgs,
    run=run,
    facts=facts,
)
