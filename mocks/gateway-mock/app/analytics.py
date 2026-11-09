"""Indicadores y alertas calculados con las fórmulas de docs/analytics-rules/reglas-iniciales.md.

El mock calcula todo a partir de los datos ficticios, de modo que las cifras son coherentes entre
calificaciones, indicadores, alertas e informe, como lo serían con el analytics-service real.
"""
GRADED, PENDING, NOT_SUBMITTED = "graded", "pending_grading", "not_submitted"
COMPLETED_STATES = {"complete", "passed", "failed"}  # Moodle 1, 2 y 3 cuentan como completado

RULES = {
    "LOW_AVERAGE": {"threshold": 6.0, "minGradedCount": 2, "severity": "warning"},
    "LOW_SUBMISSION": {"threshold": 80.0, "severity": "warning"},
    "PENDING_GRADING": {"threshold": 20.0, "severity": "info"},
    "LOW_COMPLETION": {"threshold": 70.0, "severity": "warning"},
    "NO_DATA": {"severity": "info"},
}


def fmt(value: float) -> str:
    """Número con coma decimal, para los textos en español."""
    return f"{value:.2f}".replace(".", ",")


def metric(value, unit, status="available", code=None, detail=None, numerator=None, denominator=None) -> dict:
    return {"value": value, "unit": unit, "status": status, "code": code, "detail": detail,
            "numerator": numerator, "denominator": denominator}


def unavailable(unit: str, detail: str) -> dict:
    return metric(None, unit, "unavailable", "DATA_NOT_AVAILABLE", detail)


def rate(num: int, den: int) -> float:
    return round(100 * num / den, 2)


# ---------------------------------------------------------------- calificaciones
def grade_entries(course: dict, student_id=None, activity_id=None) -> list:
    """Un registro por estudiante y actividad, con su estado (GradeEntry del contrato)."""
    activities = {a["id"]: a for a in course["activities"]}
    out = []
    for r in course["records"]:
        if student_id is not None and r["studentId"] != student_id:
            continue
        if activity_id is not None and r["activityId"] != activity_id:
            continue
        act = activities[r["activityId"]]
        score = r["score"]
        if score is not None:
            status = GRADED
        elif r["submissionStatus"] == "submitted":
            status = PENDING
        else:
            status = NOT_SUBMITTED
        out.append({
            "studentId": r["studentId"],
            "activityId": r["activityId"],
            "activityName": act["name"],
            "status": status,
            "submissionStatus": r["submissionStatus"],
            "score": score,
            "maxScore": act["maxScore"],
            "submittedAt": r["submittedAt"],
            "gradedAt": r["gradedAt"],
        })
    return sorted(out, key=lambda e: (e["studentId"], e["activityId"]))


def activity_progress(course: dict, student_id: int) -> list:
    activities = {a["id"]: a for a in course["activities"]}
    return [{"activityId": r["activityId"], "activityType": activities[r["activityId"]]["type"],
             "completionState": r["completion"]}
            for r in sorted(course["records"], key=lambda r: r["activityId"]) if r["studentId"] == student_id]


# ---------------------------------------------------------------- indicadores
def compute(entries: list, completions: list) -> dict:
    """Indicadores de un conjunto de calificaciones (curso completo o un estudiante)."""
    graded = [e for e in entries if e["status"] == GRADED and e["maxScore"] > 0 and 0 <= e["score"] <= e["maxScore"]]
    pending = [e for e in entries if e["status"] == PENDING]
    not_sub = [e for e in entries if e["status"] == NOT_SUBMITTED]
    drafts = [e for e in not_sub if e["submissionStatus"] == "draft"]
    total = len(entries)

    if graded:
        avg = round(sum(10 * e["score"] / e["maxScore"] for e in graded) / len(graded), 2)
        average = metric(avg, "score_0_10", denominator=len(graded))
    else:
        average = unavailable("score_0_10", "No hay calificaciones para calcular el promedio.")

    if total:
        submission = metric(rate(len(graded) + len(pending), total), "percent",
                            numerator=len(graded) + len(pending), denominator=total)
        pending_rate = metric(rate(len(pending), total), "percent", numerator=len(pending), denominator=total)
    else:
        submission = unavailable("percent", "No hay actividades evaluables.")
        pending_rate = unavailable("percent", "No hay actividades evaluables.")

    if graded or pending:
        grading = metric(rate(len(graded), len(graded) + len(pending)), "percent",
                         numerator=len(graded), denominator=len(graded) + len(pending))
    else:
        grading = unavailable("percent", "No hay entregas para calcular la tasa de calificación.")

    observed = [c for c in completions if c != "not_available"]
    if not observed:
        completion = unavailable("percent", "Moodle no configuró el seguimiento de finalización para las actividades observadas.")
    else:
        done = sum(1 for c in observed if c in COMPLETED_STATES)
        partial = len(observed) < len(completions)
        completion = metric(rate(done, len(observed)), "percent", "partial" if partial else "available",
                            detail="Una actividad sin seguimiento de finalización no entra al cálculo." if partial else None,
                            numerator=done, denominator=len(observed))

    metrics = {"averageScore10": average, "submissionRate": submission, "gradingRate": grading,
               "completionRate": completion, "pendingGradingRate": pending_rate}
    statuses = [m["status"] for m in metrics.values()]
    if all(s == "unavailable" for s in statuses):
        quality = "unavailable"
    elif all(s == "available" for s in statuses):
        quality = "complete"
    else:
        quality = "partial"
    return {**metrics,
            "counts": {"gradedCount": len(graded), "pendingGradingCount": len(pending),
                       "notSubmittedCount": len(not_sub), "draftCount": len(drafts)},
            "dataQuality": quality}


def snapshot(course: dict, quality: str, sync_id) -> dict:
    stamp = (course["lastSyncAt"] or "").replace("-", "").replace(":", "")
    return {"snapshotId": f"snap-{course['id']}-{stamp}", "syncId": sync_id,
            "calculatedAt": course["lastSyncAt"], "dataQuality": quality}


def course_analytics(course: dict, sync_id) -> dict:
    entries = grade_entries(course)
    res = compute(entries, [r["completion"] for r in course["records"]])
    quality = res.pop("dataQuality")
    return {"courseId": course["id"], "snapshot": snapshot(course, quality, sync_id), **res}


def student_analytics(course: dict, student_id: int, sync_id) -> dict:
    entries = grade_entries(course, student_id=student_id)
    res = compute(entries, [r["completion"] for r in course["records"] if r["studentId"] == student_id])
    quality = res.pop("dataQuality")
    return {"courseId": course["id"], "studentId": student_id, "snapshot": snapshot(course, quality, sync_id), **res}


# ---------------------------------------------------------------- alertas
def _evidence(name, value, threshold, explanation, num=None, den=None, sources=None) -> dict:
    return {"metric": name, "observedValue": value, "threshold": threshold, "numerator": num,
            "denominator": den, "sourceIds": sources or [], "explanation": explanation}


def _alert(course_id, rule, student_id, snap, evidence) -> dict:
    who = f"student-{student_id}" if student_id is not None else "course"
    return {"alertId": f"alert-{course_id}-{rule}-{who}-{snap['snapshotId']}", "ruleCode": rule, "courseId": course_id,
            "studentId": student_id, "severity": RULES[rule]["severity"], "status": "active",
            "detectedAt": snap["calculatedAt"], "resolvedAt": None, "evidence": evidence}


def _scope_alerts(course_id, student_id, entries, m, snap, with_student_rules=True) -> list:
    """Evalúa las reglas de un estudiante o, con with_student_rules=False, solo las del curso."""
    out = []
    counts = m["counts"]
    activity_ids = lambda es: [f"activity:{e['activityId']}" for e in es]
    graded = [e for e in entries if e["status"] == GRADED]
    not_submitted = [e for e in entries if e["status"] != GRADED and e["status"] != PENDING]

    avg = m["averageScore10"]
    if with_student_rules and avg["value"] is not None and counts["gradedCount"] >= RULES["LOW_AVERAGE"]["minGradedCount"] \
            and avg["value"] < RULES["LOW_AVERAGE"]["threshold"]:
        out.append(_alert(course_id, "LOW_AVERAGE", student_id, snap, [_evidence(
            "averageScore10", avg["value"], RULES["LOW_AVERAGE"]["threshold"],
            f"El promedio es {fmt(avg['value'])} sobre 10 con {counts['gradedCount']} calificaciones; el umbral es 6,00.",
            den=counts["gradedCount"], sources=activity_ids(graded))]))

    sub = m["submissionRate"]
    if with_student_rules and sub["value"] is not None and sub["value"] < RULES["LOW_SUBMISSION"]["threshold"]:
        out.append(_alert(course_id, "LOW_SUBMISSION", student_id, snap, [_evidence(
            "submissionRate", sub["value"], RULES["LOW_SUBMISSION"]["threshold"],
            f"Entregó {sub['numerator']} de {sub['denominator']} actividades ({fmt(sub['value'])} %); el umbral es 80 %.",
            sub["numerator"], sub["denominator"], activity_ids(not_submitted))]))

    pend = m["pendingGradingRate"]
    if pend["value"] is not None and counts["pendingGradingCount"] > 0 and pend["value"] > RULES["PENDING_GRADING"]["threshold"]:
        pending = [e for e in entries if e["status"] == PENDING]
        out.append(_alert(course_id, "PENDING_GRADING", student_id, snap, [_evidence(
            "pendingGradingRate", pend["value"], RULES["PENDING_GRADING"]["threshold"],
            f"{pend['numerator']} de {pend['denominator']} actividades están pendientes de calificar ({fmt(pend['value'])} %); el umbral es 20 %.",
            pend["numerator"], pend["denominator"], activity_ids(pending))]))

    comp = m["completionRate"]
    if with_student_rules and comp["value"] is not None and comp["value"] < RULES["LOW_COMPLETION"]["threshold"]:
        out.append(_alert(course_id, "LOW_COMPLETION", student_id, snap, [_evidence(
            "completionRate", comp["value"], RULES["LOW_COMPLETION"]["threshold"],
            f"Completó {comp['numerator']} de {comp['denominator']} actividades con seguimiento ({fmt(comp['value'])} %); el umbral es 70 %.",
            comp["numerator"], comp["denominator"])]))

    missing = []
    if avg["value"] is None:
        missing.append(_evidence("averageScore10", None, None, "DATA_NOT_AVAILABLE: " + avg["detail"]))
    if comp["value"] is None:
        missing.append(_evidence("completionRate", None, None, "DATA_NOT_AVAILABLE: " + comp["detail"]))
    if missing:
        out.append(_alert(course_id, "NO_DATA", student_id, snap, missing))
    return out


def course_alerts(course: dict, sync_id) -> list:
    """Todas las alertas activas del curso (por estudiante y de curso)."""
    ca = course_analytics(course, sync_id)
    snap = ca["snapshot"]
    alerts = []
    for s in course["students"]:
        entries = grade_entries(course, student_id=s["id"])
        m = compute(entries, [r["completion"] for r in course["records"] if r["studentId"] == s["id"]])
        alerts += _scope_alerts(course["id"], s["id"], entries, m, snap)
    alerts += _scope_alerts(course["id"], None, grade_entries(course), ca, snap, with_student_rules=False)
    return alerts


def report_data(course: dict, sync_id) -> dict:
    ca = course_analytics(course, sync_id)
    alerts = course_alerts(course, sync_id)
    names = {s["id"]: s["fullName"] for s in course["students"]}
    metrics = {k: ca[k] for k in ("averageScore10", "submissionRate", "gradingRate", "completionRate", "pendingGradingRate")}
    c = ca["counts"]
    findings = []
    avg, sub, pend = metrics["averageScore10"], metrics["submissionRate"], metrics["pendingGradingRate"]
    if avg["value"] is not None:
        findings.append({"metric": "averageScore10", "text": f"El promedio del curso es {fmt(avg['value'])} sobre 10 ({c['gradedCount']} calificaciones)."})
    if sub["value"] is not None:
        findings.append({"metric": "submissionRate", "text": f"Se recibieron {sub['numerator']} de {sub['denominator']} entregas esperadas ({fmt(sub['value'])} %)."})
    if pend["value"] is not None:
        findings.append({"metric": "pendingGradingRate", "text": f"Hay {c['pendingGradingCount']} actividad(es) pendiente(s) de calificar ({fmt(pend['value'])} %)."})
    for a in alerts:
        ev = a["evidence"][0]
        who = names.get(a["studentId"], "El curso")
        findings.append({"alertId": a["alertId"], "ruleCode": a["ruleCode"], "studentId": a["studentId"],
                         "metric": ev["metric"], "text": f"{who}: {ev['explanation']}"})
    return {"courseId": course["id"], "snapshot": ca["snapshot"], "periodStart": course.get("startDate"),
            "periodEnd": course.get("endDate"), "metrics": metrics, "findings": findings, "activeAlertCount": len(alerts)}
