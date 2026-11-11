"""3.5 generar_resumen: datos del informe del curso (métricas, hallazgos y alertas activas) para que el agente los presente.

Gateway: GET /api/v1/courses/{id}/analytics/report. No calcula nada: analytics-service entrega las métricas y los hallazgos ya
redactados (con los nombres de los estudiantes); el agente los cita. El formato exacto del informe depende de la pregunta 2 al
Product Owner (diseño, sección 3.5).
"""
from pydantic import BaseModel, Field, model_validator

from ..gateway import gateway_get
from ..tools import Tool, ToolContext, ok_output
from ._resolve import resolve_course
from .common import fecha, plural
from .obtener_progreso import QUALITY, metric_fact

MAX_ALERT_FINDINGS_AS_FACTS = 15
METRIC_LABELS = {"averageScore10": "Promedio de notas (escala de 0 a 10)", "submissionRate": "Tasa de entrega",
                 "gradingRate": "Tasa de calificación", "completionRate": "Tasa de finalización",
                 "pendingGradingRate": "Tasa de entregas pendientes de calificar"}


class Args(BaseModel):
    course_id: int | None = Field(default=None, ge=1, description="Id del curso en Moodle")
    course_name: str | None = Field(default=None, description="Nombre o código del curso, tal como lo escribió el docente")
    snapshot_id: str | None = Field(default=None, description="Sincronización a consultar; por defecto, la última")

    @model_validator(mode="after")
    def only_one_course(self):
        if self.course_id is not None and self.course_name:
            raise ValueError("indica course_id o course_name, no los dos")
        return self


def run(ctx: ToolContext, args: Args) -> dict:
    course, error = resolve_course(ctx, args.course_id, args.course_name)
    if error:
        return error
    cid = course["id"]
    body, error = gateway_get(ctx, f"/api/v1/courses/{cid}/analytics/report", {"snapshotId": args.snapshot_id} if args.snapshot_id else None)
    if error:
        return error
    alert_findings = [f for f in body.get("findings", []) if f.get("alertId")]
    # El número de hallazgos que se muestran va en los datos: el validador de salida solo admite cifras que existan en ellos
    data = {"courseId": cid, "courseName": course["shortName"], "report": body,
            "alertFindings": len(alert_findings), "shown": min(len(alert_findings), MAX_ALERT_FINDINGS_AS_FACTS)}
    return ok_output(data, f"GET /api/v1/courses/{cid}/analytics/report", ctx.request_id)


# ---------------------------------------------------------------- hechos redactados por código
def facts(data: dict) -> list[str]:
    r = data["report"]
    course = data["courseName"] or f"curso {data['courseId']}"
    snap = r["snapshot"]
    head = f"Informe de {course}: datos calculados el {fecha(snap['calculatedAt'])}; calidad de los datos {QUALITY.get(snap['dataQuality'], snap['dataQuality'])}"
    if r.get("periodStart") and r.get("periodEnd"):
        head += f"; período del {fecha(r['periodStart'])} al {fecha(r['periodEnd'])}"
    out = [head + "."]

    findings = r.get("findings", [])
    course_findings = [f for f in findings if not f.get("alertId")]
    covered = {f.get("metric") for f in course_findings}
    out += [f["text"] for f in course_findings]                      # redacción de analytics, tal cual
    metrics = r.get("metrics", {})
    out += [metric_fact(label, metrics[key]) for key, label in METRIC_LABELS.items() if key in metrics and key not in covered]

    n = r.get("activeAlertCount", 0)
    out.append(f"{plural(n, 'alerta activa', 'alertas activas')} en el curso." if n else "No hay alertas activas en el curso.")
    alerts = [f for f in findings if f.get("alertId")]
    out += [f["text"] for f in alerts[:data["shown"]]]
    if len(alerts) > data["shown"]:
        out.append(f"Se muestran los primeros {data['shown']} de {data['alertFindings']} hallazgos de alertas.")
    return out


TOOL = Tool(
    name="generar_resumen",
    description="Devuelve los datos del informe o resumen de un curso: indicadores (promedio, entrega, calificación, "
                "finalización y pendientes), hallazgos y alertas activas con su evidencia. El curso se indica por su nombre "
                "tal como lo escribió el docente; nunca inventes números. Úsala cuando el docente pida un informe, reporte o "
                "resumen del curso.",
    input_model=Args,
    run=run,
    facts=facts,
    hidden=("course_id", "snapshot_id"),
)
