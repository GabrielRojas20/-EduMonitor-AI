"""3.2 obtener_calificaciones: calificaciones de un curso, de un estudiante o de una actividad, con su estado.

Gateway: GET /api/v1/courses/{courseId}/grades (paginado). Para mostrar nombres usa la lista de estudiantes del curso.
"""
from pydantic import BaseModel, Field, model_validator

from ..gateway import gateway_get  # noqa: F401  (las pruebas lo reemplazan por un gateway simulado)
from ..tools import Tool, ToolContext, error_output, ok_output
from ._resolve import course_students, fetch_all, resolve_course, resolve_student

MAX_ROWS_AS_FACTS = 15  # por encima, los hechos resumen en lugar de listar cada registro


class Args(BaseModel):
    course_id: int | None = Field(default=None, ge=1, description="Id del curso en Moodle")
    course_name: str | None = Field(default=None, description="Nombre o código del curso, por ejemplo PRUEBA01; alternativa a course_id")
    student_id: int | None = Field(default=None, ge=1, description="Id del estudiante en Moodle")
    student_name: str | None = Field(default=None, description="Nombre del estudiante; alternativa a student_id")
    activity_id: int | None = Field(default=None, ge=1, description="Id de la actividad")

    @model_validator(mode="after")
    def only_one_of_each(self):
        if self.course_id is not None and self.course_name:
            raise ValueError("indica course_id o course_name, no los dos")
        if self.student_id is not None and self.student_name:
            raise ValueError("indica student_id o student_name, no los dos")
        return self


def run(ctx: ToolContext, args: Args) -> dict:
    course, error = resolve_course(ctx, args.course_id, args.course_name)
    if error:
        return error
    cid = course["id"]
    endpoint = f"GET /api/v1/courses/{cid}/grades"

    students, error = course_students(ctx, cid)
    if error:
        return error
    names = {s["id"]: s["fullName"] for s in students}

    params = {}
    if args.student_id is not None or args.student_name:
        student, error = resolve_student(ctx, cid, students, args.student_id, args.student_name)
        if error:
            return error
        params["studentId"] = student["id"]
    if args.activity_id is not None:
        params["activityId"] = args.activity_id

    rows, total, truncated, error = fetch_all(ctx, f"/api/v1/courses/{cid}/grades", params)
    if error:
        return error
    items = [{"studentId": g["studentId"], "studentName": names.get(g["studentId"]), "activityId": g["activityId"],
              "activityName": g.get("activityName"), "status": g["status"], "submissionStatus": g.get("submissionStatus"),
              "score": g.get("score"), "maxScore": g.get("maxScore"), "submittedAt": g.get("submittedAt"),
              "gradedAt": g.get("gradedAt")} for g in rows]
    data = {"courseId": cid, "courseName": course["shortName"], "items": items, "total": total, "truncated": truncated}
    return ok_output(data, endpoint, ctx.request_id)


# ---------------------------------------------------------------- hechos redactados por código
def num(value) -> str:
    """8.0 -> «8»; 8.5 -> «8,5»."""
    value = float(value)
    return f"{value:.0f}" if value == int(value) else f"{value:.2f}".rstrip("0").replace(".", ",")


def who(row: dict) -> str:
    return row["studentName"] or f"Estudiante {row['studentId']}"


def row_fact(row: dict) -> str:
    head = f"{who(row)}, {row['activityName']}"
    status = row["status"]
    if status == "graded":
        zero = " (nota cero)" if float(row["score"]) == 0 else ""
        return f"{head}: {num(row['score'])} sobre {num(row['maxScore'])}{zero}."
    if status == "pending_grading":
        return f"{head}: entregada, pendiente de calificar."
    if row["submissionStatus"] == "draft":
        return f"{head}: borrador sin enviar."
    return f"{head}: sin entrega."


def facts(data: dict) -> list[str]:
    items, course = data["items"], data["courseName"] or f"curso {data['courseId']}"
    if not items:
        return [f"No hay calificaciones registradas en {course} con esos criterios."]
    graded = sum(1 for r in items if r["status"] == "graded")
    pending = sum(1 for r in items if r["status"] == "pending_grading")
    drafts = sum(1 for r in items if r["status"] == "not_submitted" and r["submissionStatus"] == "draft")
    none = sum(1 for r in items if r["status"] == "not_submitted") - drafts
    parts = [f"{graded} calificado{'s' if graded != 1 else ''}", f"{pending} pendiente{'s' if pending != 1 else ''} de calificar"]
    parts.append(f"{drafts} borrador{'es' if drafts != 1 else ''} sin enviar")
    parts.append(f"{none} sin entrega")
    summary = f"{course}: {data['total']} registro{'s' if data['total'] != 1 else ''} de calificación ({', '.join(parts)})."
    out = [summary]
    shown = items[:MAX_ROWS_AS_FACTS]
    out += [row_fact(r) for r in shown]
    if len(items) > len(shown):
        out.append(f"Se muestran los primeros {len(shown)} de {len(items)} registros.")
    if data["truncated"]:
        out.append(f"Solo se analizaron los primeros {len(items)} registros de {data['total']}.")
    return out


TOOL = Tool(
    name="obtener_calificaciones",
    description="Devuelve las calificaciones de un curso, con su estado (calificada, nota cero, pendiente de calificar, "
                "borrador sin enviar o sin entrega). Puede limitarse a un estudiante o a una actividad. El curso y el "
                "estudiante pueden indicarse por su nombre (por ejemplo PRUEBA01 o «Estudiante Dos»). Úsala para "
                "preguntas sobre notas, entregas o cómo va un estudiante.",
    input_model=Args,
    run=run,
    facts=facts,
)
