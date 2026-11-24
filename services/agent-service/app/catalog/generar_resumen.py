"""3.5 generar_resumen: datos del informe del curso (métricas, hallazgos y alertas activas) para que el agente los presente.

Gateway: GET /api/v1/courses/{id}/analytics/report. No calcula nada: analytics-service entrega las métricas y los hallazgos con su
evidencia (regla, valor observado, umbral y fuentes); el agente los cita y les pone el nombre del estudiante, que sale de la lista
de estudiantes del curso. Contrato: docs/contracts/analytics.v1.yaml (ReportFinding).
"""
from pydantic import BaseModel, Field, model_validator

from ..gateway import gateway_get
from ..tools import Tool, ToolContext, ok_output
from ._resolve import course_students, resolve_course
from .common import fecha, num, plural
from .identificar_alertas import RULES
from .obtener_progreso import QUALITY, metric_fact

MAX_ALERT_FINDINGS_AS_FACTS = 15
UNITS = {"submissionRate": " %", "gradingRate": " %", "completionRate": " %", "pendingGradingRate": " %",
         "averageScore10": " sobre 10"}  # unidad del valor observado y del umbral de cada hallazgo
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
    students, _error = course_students(ctx, cid)  # los nombres son un complemento: si faltan, el hecho nombra el id
    names = {s["id"]: s["fullName"] for s in students or []}
    # El número de hallazgos que se muestran va en los datos: el validador de salida solo admite cifras que existan en ellos
    data = {"courseId": cid, "courseName": course["shortName"], "report": body, "studentNames": names,
            "alertFindings": len(alert_findings), "shown": min(len(alert_findings), MAX_ALERT_FINDINGS_AS_FACTS)}
    return ok_output(data, f"GET /api/v1/courses/{cid}/analytics/report", ctx.request_id)


# ---------------------------------------------------------------- hechos redactados por código
def alert_fact(finding: dict, names: dict) -> str:
    """Un hallazgo de alerta con su estudiante, su regla y su evidencia. Sin valor ni umbral se cita el texto de analytics tal cual."""
    observed, threshold = finding.get("observedValue"), finding.get("threshold")
    if observed is None and threshold is None:
        return finding["text"]
    student = finding.get("studentId")
    who = names.get(student) or (f"Estudiante {student}" if student is not None else "Curso")
    rule = RULES.get(finding.get("ruleCode"), finding.get("ruleCode") or "Hallazgo")
    unit = UNITS.get(finding.get("metric"), "")
    evidence = []
    if observed is not None:
        evidence.append(f"valor observado {num(observed)}{unit}")
    if threshold is not None:
        evidence.append(f"umbral {num(threshold)}{unit}")
    return f"{who}, {rule}: {finding['text']} ({'; '.join(evidence)})."


def facts(data: dict) -> list[str]:
    r = data["report"]
    course = data["courseName"] or f"curso {data['courseId']}"
    snap = r["snapshot"]
    head = f"Informe de {course}: datos calculados el {fecha(snap['calculatedAt'])}; calidad de los datos {QUALITY.get(snap['dataQuality'], snap['dataQuality'])}"
    if r.get("periodStart") and r.get("periodEnd"):
        head += f"; observaciones sincronizadas del {fecha(r['periodStart'])} al {fecha(r['periodEnd'])}"
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
    names = {int(k): v for k, v in data.get("studentNames", {}).items()}
    out += [alert_fact(f, names) for f in alerts[:data["shown"]]]
    if len(alerts) > data["shown"]:
        out.append(f"Se muestran los primeros {data['shown']} de {data['alertFindings']} hallazgos de alertas.")
    return out


TOOL = Tool(
    name="generar_resumen",
    description="Devuelve los datos del informe o resumen de un curso: indicadores (promedio, entrega, calificación, "
                "finalización y pendientes), hallazgos y alertas activas con su evidencia (valor observado y umbral). El curso se indica por su nombre "
                "tal como lo escribió el docente; nunca inventes números. Úsala cuando el docente pida un informe, reporte o "
                "resumen del curso.",
    input_model=Args,
    run=run,
    facts=facts,
    hidden=("course_id", "snapshot_id"),
)
