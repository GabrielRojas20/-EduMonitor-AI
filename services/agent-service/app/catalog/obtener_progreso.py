"""3.3 obtener_progreso: indicadores de un curso o de un estudiante, y el progreso por actividad de un estudiante.

Gateway: GET /api/v1/courses/{id}/analytics; con estudiante, también .../analytics/students/{sid} y
GET /api/v1/courses/{id}/students/{sid} (de ahí solo se toman `activities` y los nombres de las actividades).
Los indicadores los calcula analytics-service: el agente no calcula nada.
"""
from pydantic import BaseModel, Field, model_validator

from ..gateway import gateway_get
from ..tools import Tool, ToolContext, ok_output
from ._resolve import course_students, resolve_course, resolve_student
from .common import fecha, num, plural


class Args(BaseModel):
    course_id: int | None = Field(default=None, ge=1, description="Id del curso en Moodle")
    course_name: str | None = Field(default=None, description="Nombre o código del curso, tal como lo escribió el docente")
    student_id: int | None = Field(default=None, ge=1, description="Id del estudiante en Moodle")
    student_name: str | None = Field(default=None, description="Nombre del estudiante; si no se indica, devuelve el progreso del curso")
    snapshot_id: str | None = Field(default=None, description="Sincronización a consultar; por defecto, la última")

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
    snapshot = {"snapshotId": args.snapshot_id} if args.snapshot_id else None
    data = {"courseId": cid, "courseName": course["shortName"]}

    if args.student_id is None and not args.student_name:
        endpoint = f"GET /api/v1/courses/{cid}/analytics"
        body, error = gateway_get(ctx, f"/api/v1/courses/{cid}/analytics", snapshot)
        if error:
            return error
        data["analytics"] = body
        return ok_output(data, endpoint, ctx.request_id)

    students, error = course_students(ctx, cid)
    if error:
        return error
    student, error = resolve_student(ctx, cid, students, args.student_id, args.student_name)
    if error:
        return error
    sid = student["id"]
    endpoint = f"GET /api/v1/courses/{cid}/analytics/students/{sid}"
    body, error = gateway_get(ctx, f"/api/v1/courses/{cid}/analytics/students/{sid}", snapshot)
    if error:
        return error
    detail, error = gateway_get(ctx, f"/api/v1/courses/{cid}/students/{sid}")
    if error:
        return error
    names = {g["activityId"]: g.get("activityName") for g in detail.get("grades", [])}
    data.update(studentId=sid, studentName=student["fullName"], analytics=body,
                activities=[{"activityId": a["activityId"], "activityName": names.get(a["activityId"]),
                             "completionState": a["completionState"]} for a in detail.get("activities", [])])
    return ok_output(data, endpoint, ctx.request_id)


# ---------------------------------------------------------------- hechos redactados por código
COMPLETION = {"complete": "completada", "incomplete": "sin completar", "passed": "aprobada", "failed": "no aprobada",
              "not_available": "sin dato de finalización en Moodle"}
QUALITY = {"complete": "completa", "partial": "parcial"}
RATES = [("submissionRate", "Tasa de entrega"), ("gradingRate", "Tasa de calificación"),
         ("completionRate", "Tasa de finalización"), ("pendingGradingRate", "Tasa de entregas pendientes de calificar")]


def metric_fact(label: str, m: dict) -> str:
    detail = f" {m['detail']}" if m.get("detail") else ""
    if m.get("status") == "unavailable" or m.get("value") is None:
        return f"{label}: no disponible.{detail}"
    if m["unit"] == "percent":
        base = f"{label}: {num(m['value'])} %"
        if m.get("numerator") is not None and m.get("denominator") is not None:
            base += f" ({num(m['numerator'])} de {num(m['denominator'])})"
    else:
        base = f"{label}: {num(m['value'])}"
    return base + ("." if m.get("status") == "available" else f" (dato parcial).{detail}")


def facts(data: dict) -> list[str]:
    a = data["analytics"]
    course = data["courseName"] or f"curso {data['courseId']}"
    scope = f"{data['studentName']} en {course}" if data.get("studentName") else course
    snap = a["snapshot"]
    out = [f"{scope}: indicadores calculados el {fecha(snap['calculatedAt'])}; calidad de los datos {QUALITY.get(snap['dataQuality'], snap['dataQuality'])}."]
    out.append(metric_fact("Promedio de notas (escala de 0 a 10)", a["averageScore10"]))
    out += [metric_fact(label, a[key]) for key, label in RATES]
    c = a["counts"]
    line = (f"Registros: {plural(c['gradedCount'], 'calificado', 'calificados')}, "
            f"{plural(c['pendingGradingCount'], 'pendiente de calificar', 'pendientes de calificar')}, "
            f"{c['notSubmittedCount']} sin entrega")
    out.append(line + (f" (de ellos, {plural(c['draftCount'], 'con borrador sin enviar', 'con borrador sin enviar')})." if c["draftCount"] else "."))
    for act in data.get("activities", []):
        name = act["activityName"] or f"actividad {act['activityId']}"
        out.append(f"{data['studentName']}, {name}: {COMPLETION.get(act['completionState'], act['completionState'])}.")
    return out


TOOL = Tool(
    name="obtener_progreso",
    description="Devuelve los indicadores de progreso de un curso (promedio de notas, tasas de entrega, calificación y "
                "finalización, entregas pendientes y conteos) o, si se indica un estudiante, los de ese estudiante y su "
                "finalización por actividad. El curso y el estudiante se indican por su nombre tal como los escribió el docente; "
                "nunca inventes números. Úsala para preguntas sobre cómo va el curso o un estudiante, "
                "promedios, tasas o avance.",
    input_model=Args,
    run=run,
    facts=facts,
    hidden=("course_id", "student_id", "snapshot_id"),
)
