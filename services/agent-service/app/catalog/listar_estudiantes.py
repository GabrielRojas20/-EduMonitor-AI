"""3.6 listar_estudiantes: lista de los estudiantes de un curso, numerados dentro del curso.

Gateway: GET /api/v1/courses/{courseId}/students (paginado). Nunca incluye el correo (diseño, sección 3.8: privacidad).
La numeración (N.º 1, 2, 3…) va por orden alfabético y es la misma que muestra la tabla del curso en la interfaz: el id de Moodle
es global y no sirve para contar a los estudiantes de un curso.

No se le ofrece al modelo (`offered_to_model=False`): el código la elige cuando la pregunta pide la lista de estudiantes
(graph.wants_student_list), así que no cambia la forma en que el modelo elige las demás herramientas.
"""
from pydantic import BaseModel, Field

from ..tools import Tool, ToolContext, ok_output
from ._resolve import course_label, course_students, norm, resolve_course

MAX_LISTED = 50  # por encima, los hechos listan los primeros y avisan cuántos hay


class Args(BaseModel):
    course_id: int | None = Field(default=None, ge=1, description="Id del curso en Moodle")
    course_name: str | None = Field(default=None, description="Nombre o código del curso, tal como lo escribió el docente")


def run(ctx: ToolContext, args: Args) -> dict:
    course, error = resolve_course(ctx, args.course_id, args.course_name)
    if error:
        return error
    cid = course["id"]
    students, error = course_students(ctx, cid)
    if error:
        return error
    ordered = sorted(students, key=lambda s: (norm(s["fullName"]), s["id"]))
    items = [{"n": i, "studentId": s["id"], "fullName": s["fullName"]} for i, s in enumerate(ordered, 1)]
    data = {"courseId": cid, "courseName": course_label(course), "total": len(items), "items": items}
    return ok_output(data, f"GET /api/v1/courses/{cid}/students", ctx.request_id)


def facts(data: dict) -> list[str]:
    """Hechos redactados por código: una frase de apertura y un estudiante por línea."""
    course, total = data["courseName"], data["total"]
    if total == 0:
        return [f"No hay estudiantes sincronizados en {course}."]
    shown = data["items"][:MAX_LISTED]
    opening = "Este es el 1 estudiante" if total == 1 else f"Estos son los {total} estudiantes"
    out = [f"{opening} de {course}, por orden alfabético:"]
    out += [f"N.º {s['n']} · {s['fullName']}" for s in shown]
    if total > len(shown):
        out.append(f"Se muestran los primeros {len(shown)} de {total} estudiantes.")
    return out


TOOL = Tool(
    name="listar_estudiantes",
    description="Lista los estudiantes de un curso, numerados dentro del curso, por orden alfabético. Úsala cuando el docente "
                "pida la lista o los nombres de sus estudiantes.",
    input_model=Args,
    run=run,
    facts=facts,
    hidden=("course_id",),
    offered_to_model=False,
)
