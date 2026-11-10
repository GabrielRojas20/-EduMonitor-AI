"""3.4 identificar_alertas: alertas del curso (o de un estudiante) con su evidencia: regla, valor observado, umbral y explicación.

Gateway: GET /api/v1/courses/{id}/analytics/alerts (paginado; filtros studentId, severity, status).
El agente cita la evidencia que entrega analytics-service y no la reinterpreta.
"""
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from ..tools import Tool, ToolContext, ok_output
from ._resolve import course_students, fetch_all, norm, resolve_course, resolve_student
from .common import plural

MAX_ALERTS_AS_FACTS = 15
RULES = {"LOW_AVERAGE": "Promedio bajo", "LOW_SUBMISSION": "Entrega baja", "PENDING_GRADING": "Calificaciones pendientes",
         "LOW_COMPLETION": "Finalización baja", "NO_DATA": "Sin datos"}  # docs/analytics-rules/reglas-iniciales.md
SEVERITY = {"critical": "crítica", "warning": "de atención", "info": "informativa"}
RANK = {"critical": 0, "warning": 1, "info": 2}


class Args(BaseModel):
    course_id: int | None = Field(default=None, ge=1, description="Id del curso en Moodle")
    course_name: str | None = Field(default=None, description="Nombre o código del curso, por ejemplo PRUEBA01")
    student_id: int | None = Field(default=None, ge=1, description="Id del estudiante en Moodle")
    student_name: str | None = Field(default=None, description="Nombre del estudiante; si no se indica, devuelve las alertas de todo el curso")
    severity: Literal["info", "warning", "critical"] | None = Field(default=None, description="Solo si el docente nombra una severidad (crítica, de atención o informativa); en otro caso no lo uses")
    status: Literal["active", "resolved"] = Field(default="active", description="Alertas activas (por defecto) o ya resueltas")
    snapshot_id: str | None = Field(default=None, description="Sincronización a consultar; por defecto, la última")

    @field_validator("severity", mode="before")
    @classmethod
    def forgive_severity(cls, value):
        """Un modelo pequeño manda «crítica», «all» o ''; se traduce lo conocido y lo demás se ignora (sin filtro)."""
        known = {"info": "info", "informativa": "info", "warning": "warning", "atencion": "warning", "de atencion": "warning",
                 "critical": "critical", "critica": "critical", "critico": "critical"}
        return known.get(norm(value)) if isinstance(value, str) else value

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
    endpoint = f"GET /api/v1/courses/{cid}/analytics/alerts"

    students, error = course_students(ctx, cid)
    if error:
        return error
    names = {s["id"]: s["fullName"] for s in students}
    params = {"status": args.status}
    if args.student_id is not None or args.student_name:
        student, error = resolve_student(ctx, cid, students, args.student_id, args.student_name)
        if error:
            return error
        params["studentId"] = student["id"]
    if args.severity:
        params["severity"] = args.severity
    if args.snapshot_id:
        params["snapshotId"] = args.snapshot_id

    rows, total, truncated, error = fetch_all(ctx, f"/api/v1/courses/{cid}/analytics/alerts", params)
    if error:
        return error
    rows = sorted(rows, key=lambda a: (RANK.get(a["severity"], 9), a.get("studentId") or 0, a["ruleCode"]))
    items = [{"alertId": a["alertId"], "ruleCode": a["ruleCode"], "studentId": a.get("studentId"),
              "studentName": names.get(a.get("studentId")), "severity": a["severity"], "status": a["status"],
              "detectedAt": a.get("detectedAt"), "evidence": a.get("evidence", [])} for a in rows]
    # Los conteos van en los datos: el validador de salida solo admite cifras que existan en lo que devolvió la herramienta
    counts = {sev: sum(1 for a in items if a["severity"] == sev) for sev in RANK}
    data = {"courseId": cid, "courseName": course["shortName"], "status": args.status, "severity": args.severity,
            "studentName": student["fullName"] if params.get("studentId") else None, "items": items, "total": total,
            "truncated": truncated, "counts": counts, "analyzed": len(items), "shown": min(len(items), MAX_ALERTS_AS_FACTS)}
    return ok_output(data, endpoint, ctx.request_id)


# ---------------------------------------------------------------- hechos redactados por código
def alert_fact(a: dict) -> str:
    who = a["studentName"] or (f"Estudiante {a['studentId']}" if a["studentId"] is not None else "Curso")
    rule = RULES.get(a["ruleCode"], a["ruleCode"])
    explanation = " ".join(e["explanation"] for e in a["evidence"] if e.get("explanation")) or "Sin explicación disponible."
    return f"{who}, {rule} ({SEVERITY.get(a['severity'], a['severity'])}): {explanation}"


def facts(data: dict) -> list[str]:
    course = data["courseName"] or f"curso {data['courseId']}"
    kind = "activas" if data["status"] == "active" else "resueltas"
    items = data["items"]
    if not items:
        # el mensaje nombra los filtros aplicados: «no hay alertas críticas» no equivale a «no hay alertas»
        sev = f" de severidad {SEVERITY[data['severity']]}" if data.get("severity") else ""
        who = f" de {data['studentName']}" if data.get("studentName") else ""
        return [f"No hay alertas {kind}{sev}{who} en {course}."]
    c = data["counts"]
    sev = f" de severidad {SEVERITY[data['severity']]}" if data.get("severity") else ""
    who = f" de {data['studentName']}" if data.get("studentName") else ""
    summary = (f"{course}: {plural(data['total'], 'alerta', 'alertas')} {kind[:-1] if data['total'] == 1 else kind}{sev}{who} "
               f"({c['critical']} {'crítica' if c['critical'] == 1 else 'críticas'}, {c['warning']} de atención, "
               f"{c['info']} {'informativa' if c['info'] == 1 else 'informativas'}).")
    out = [summary] + [alert_fact(a) for a in items[:data["shown"]]]
    if len(items) > data["shown"]:
        out.append(f"Se muestran las primeras {data['shown']} de {data['analyzed']} alertas, de más a menos grave.")
    if data["truncated"]:
        out.append(f"Solo se analizaron las primeras {data['analyzed']} alertas de {data['total']}.")
    return out


TOOL = Tool(
    name="identificar_alertas",
    description="Devuelve las alertas del curso, con la regla que las activó, el valor observado, el umbral y su explicación: "
                "promedio bajo, entrega baja, calificaciones pendientes, finalización baja o sin datos. Puede limitarse a un "
                "estudiante o a una severidad (info, warning, critical). El curso y el estudiante se indican por su nombre "
                "(por ejemplo PRUEBA01 o «Estudiante Dos»); nunca inventes números. Úsala para preguntas sobre alertas, "
                "riesgos, estudiantes en riesgo o a quién prestar atención.",
    input_model=Args,
    run=run,
    facts=facts,
    hidden=("course_id", "student_id", "snapshot_id"),
)
