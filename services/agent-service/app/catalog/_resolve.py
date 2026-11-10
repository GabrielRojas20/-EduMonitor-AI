"""Resolución de cursos y estudiantes por nombre, y lectura paginada del gateway (diseño, secciones 3.6 y 3.8).

No es una herramienta (el guion bajo hace que `toolset.py` no la descubra): la usan las herramientas de consulta.
El docente habla de «PRUEBA01» o de «Estudiante Dos», no de ids de Moodle, y el agente hace un solo recorrido por
herramientas, así que cada herramienta resuelve el nombre por su cuenta con la misma lista que ve el docente.
"""
import unicodedata

from ..gateway import gateway_get
from ..tools import ToolContext, error_output

PAGE_SIZE = 200  # máximo del gateway
MAX_PAGES = 10  # diseño, sección 3.6: máximo de 10 páginas o 500 registros por herramienta
MAX_RECORDS = 500


def norm(text: str | None) -> str:
    """Minúsculas y sin tildes, para comparar nombres sin distinguir mayúsculas ni acentos."""
    text = unicodedata.normalize("NFD", (text or "").lower().strip())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def fetch_all(ctx: ToolContext, path: str, params: dict | None = None) -> tuple[list | None, int, bool, dict | None]:
    """Recorre las páginas de una lista del gateway. Devuelve (registros, total, truncado, error)."""
    items: list = []
    total = 0
    for page in range(1, MAX_PAGES + 1):
        body, error = gateway_get(ctx, path, {**(params or {}), "page": page, "pageSize": PAGE_SIZE})
        if error:
            return None, 0, False, error
        batch = body.get("items", [])
        total = body.get("total", len(items) + len(batch))
        items += batch
        if len(items) >= total or not batch or len(items) >= MAX_RECORDS:
            break
    kept = items[:MAX_RECORDS]
    return kept, total, total > len(kept), None


def _fail(ctx: ToolContext, code: str, message: str, endpoint: str) -> dict:
    return error_output(code, message, False, endpoint, ctx.request_id)


def resolve_course(ctx: ToolContext, course_id: int | None, course_name: str | None) -> tuple[dict | None, dict | None]:
    """Devuelve ({id, shortName, fullName}, None) o (None, error).

    Con `course_id` consulta el curso (así el gateway comprueba el acceso: 403 si no es del docente). Con un nombre lo busca
    entre los cursos del docente. Sin ninguno, usa el único curso que tenga o pide que indique cuál.
    """
    if course_id is not None:
        body, error = gateway_get(ctx, f"/api/v1/courses/{course_id}")
        if error:
            return None, error
        return {"id": body["id"], "shortName": body.get("shortName"), "fullName": body.get("fullName")}, None

    courses, error = gateway_get(ctx, "/api/v1/courses")
    if error:
        return None, error
    endpoint = "GET /api/v1/courses"
    if course_name:
        wanted = norm(course_name)
        exact = [c for c in courses if wanted in (norm(c.get("shortName")), norm(c.get("fullName")))]
        found = exact or [c for c in courses if wanted in norm(c.get("shortName")) or wanted in norm(c.get("fullName"))]
        if not found:
            return None, _fail(ctx, "COURSE_NOT_FOUND", f"No encontré un curso llamado «{course_name}» entre los tuyos.", endpoint)
    else:
        found = courses
        if not found:
            return None, _fail(ctx, "COURSE_NOT_FOUND", "No tienes cursos con acceso autorizado.", endpoint)
    if len(found) > 1:
        names = ", ".join(c.get("shortName") or str(c["id"]) for c in found)
        return None, _fail(ctx, "VALIDATION_ERROR", f"Hay más de un curso posible; indica cuál: {names}.", endpoint)
    c = found[0]
    return {"id": c["id"], "shortName": c.get("shortName"), "fullName": c.get("fullName")}, None


def course_students(ctx: ToolContext, course_id: int) -> tuple[list | None, dict | None]:
    """Estudiantes del curso como [{id, fullName}]. Nunca incluye el correo (diseño, sección 3.8: privacidad)."""
    items, _total, _truncated, error = fetch_all(ctx, f"/api/v1/courses/{course_id}/students")
    if error:
        return None, error
    return [{"id": s["id"], "fullName": s.get("fullName")} for s in items], None


def resolve_student(ctx: ToolContext, course_id: int, students: list, student_id: int | None,
                    student_name: str | None) -> tuple[dict | None, dict | None]:
    """Busca al estudiante por id o por nombre entre los del curso. Devuelve ({id, fullName}, None) o (None, error)."""
    endpoint = f"GET /api/v1/courses/{course_id}/students"
    if student_id is not None:
        found = [s for s in students if s["id"] == student_id]
        if not found:
            return None, _fail(ctx, "STUDENT_NOT_FOUND", f"No hay un estudiante con id {student_id} en el curso.", endpoint)
        return found[0], None
    wanted = norm(student_name)
    exact = [s for s in students if norm(s["fullName"]) == wanted]
    found = exact or [s for s in students if wanted and all(part in norm(s["fullName"]) for part in wanted.split())]
    if not found:
        return None, _fail(ctx, "STUDENT_NOT_FOUND", f"No encontré a «{student_name}» en el curso.", endpoint)
    if len(found) > 1:
        names = ", ".join(s["fullName"] for s in found)
        return None, _fail(ctx, "VALIDATION_ERROR", f"Hay varios estudiantes con ese nombre; indica cuál: {names}.", endpoint)
    return found[0], None
