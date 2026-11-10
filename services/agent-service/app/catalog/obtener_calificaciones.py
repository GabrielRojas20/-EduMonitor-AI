"""3.2 obtener_calificaciones: calificaciones de un curso, de un estudiante o de una actividad, con su estado.

Gateway: GET /api/v1/courses/{courseId}/grades (paginado). Para mostrar nombres usa la lista de estudiantes del curso.
"""
from pydantic import BaseModel, Field, model_validator

from ..gateway import gateway_get  # noqa: F401  (las pruebas lo reemplazan por un gateway simulado)
from ..tools import Tool, ToolContext, error_output, ok_output
from .common import num
from ._resolve import course_students, fetch_all, norm, resolve_course, resolve_student

MAX_ROWS_AS_FACTS = 15  # por encima, los hechos resumen en lugar de listar cada registro


class Args(BaseModel):
    course_id: int | None = Field(default=None, ge=1, description="Id del curso en Moodle")
    course_name: str | None = Field(default=None, description="Nombre o código del curso, por ejemplo PRUEBA01; alternativa a course_id")
    student_id: int | None = Field(default=None, ge=1, description="Id del estudiante en Moodle")
    student_name: str | None = Field(default=None, description="Nombre del estudiante; alternativa a student_id")
    activity_id: int | None = Field(default=None, ge=1, description="Id de la actividad")
    activity_name: str | None = Field(default=None, description="Solo si el docente nombra una actividad concreta, por ejemplo «Tarea 2». No lo uses para estados como «pendientes de calificar»")

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
    if args.activity_name:
        rows, error = pick_activity(ctx, rows, args.activity_name, endpoint)
        if error:
            return error
        total = len(rows)
    items = [{"studentId": g["studentId"], "studentName": names.get(g["studentId"]), "activityId": g["activityId"],
              "activityName": g.get("activityName"), "status": g["status"], "submissionStatus": g.get("submissionStatus"),
              "score": g.get("score"), "maxScore": g.get("maxScore"), "submittedAt": g.get("submittedAt"),
              "gradedAt": g.get("gradedAt")} for g in rows]
    drafts = sum(1 for r in items if r["status"] == "not_submitted" and r["submissionStatus"] == "draft")
    # Los conteos van en los datos: el validador de salida solo admite cifras que existan en lo que devolvió la herramienta
    counts = {"graded": sum(1 for r in items if r["status"] == "graded"),
              "pendingGrading": sum(1 for r in items if r["status"] == "pending_grading"),
              "drafts": drafts,
              "notSubmitted": sum(1 for r in items if r["status"] == "not_submitted") - drafts}
    data = {"courseId": cid, "courseName": course["shortName"], "items": items, "total": total, "truncated": truncated,
            "counts": counts, "analyzed": len(items), "shown": min(len(items), MAX_ROWS_AS_FACTS)}
    return ok_output(data, endpoint, ctx.request_id)


def pick_activity(ctx: ToolContext, rows: list, wanted: str, endpoint: str):
    """Deja solo los registros de la actividad indicada por nombre (el modelo no conoce los ids)."""
    w = norm(wanted)
    exact = [g for g in rows if norm(g.get("activityName")) == w]
    found = exact or [g for g in rows if w and w in norm(g.get("activityName"))]
    names = sorted({g.get("activityName") for g in found})
    if len(names) > 1:
        return None, error_output("VALIDATION_ERROR", f"Hay varias actividades posibles; indica cuál: {', '.join(names)}.",
                                  False, endpoint, ctx.request_id)
    if not found:
        known = ", ".join(sorted({g.get("activityName") for g in rows if g.get("activityName")})) or "ninguna"
        return None, error_output("ACTIVITY_NOT_FOUND", f"No encontré la actividad «{wanted}». Actividades del curso: {known}.",
                                  False, endpoint, ctx.request_id)
    return found, None


# ---------------------------------------------------------------- hechos redactados por código
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
    c = data["counts"]
    graded, pending, drafts, none = c["graded"], c["pendingGrading"], c["drafts"], c["notSubmitted"]
    parts = [f"{graded} calificado{'s' if graded != 1 else ''}", f"{pending} pendiente{'s' if pending != 1 else ''} de calificar"]
    parts.append(f"{drafts} borrador{'es' if drafts != 1 else ''} sin enviar")
    parts.append(f"{none} sin entrega")
    summary = f"{course}: {data['total']} registro{'s' if data['total'] != 1 else ''} de calificación ({', '.join(parts)})."
    out = [summary]
    shown = items[:data["shown"]]
    out += [row_fact(r) for r in shown]
    if len(items) > len(shown):
        out.append(f"Se muestran los primeros {len(shown)} de {data['analyzed']} registros.")
    if data["truncated"]:
        out.append(f"Solo se analizaron los primeros {data['analyzed']} registros de {data['total']}.")
    return out


TOOL = Tool(
    name="obtener_calificaciones",
    description="Devuelve las calificaciones de un curso, con su estado (calificada, nota cero, pendiente de calificar, "
                "borrador sin enviar o sin entrega). Puede limitarse a un estudiante o a una actividad. El curso, el "
                "estudiante y la actividad se indican por su nombre (por ejemplo PRUEBA01, «Estudiante Dos» o «Tarea 2»); nunca inventes números. Úsala para "
                "preguntas sobre notas, entregas o cómo va un estudiante.",
    input_model=Args,
    run=run,
    facts=facts,
    hidden=("course_id", "student_id", "activity_id"),
)
