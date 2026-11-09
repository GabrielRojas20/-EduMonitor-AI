"""Comportamiento y coherencia de los datos del mock (fórmulas de docs/analytics-rules/reglas-iniciales.md)."""
import time

C = "/api/v1/courses"


def by_student(items):
    out = {}
    for a in items:
        out.setdefault(a["studentId"], []).append(a["ruleCode"])
    return out


def test_grade_states_follow_the_contract(client, teacher):
    grades = client.get(f"{C}/2/grades", headers=teacher).json()["items"]
    g = {(e["studentId"], e["activityId"]): e for e in grades}
    assert len(grades) == 10  # 5 estudiantes x 2 tareas
    assert g[(5, 2)]["status"] == "graded" and g[(5, 2)]["score"] == 0          # una nota cero es graded, no pendiente
    assert g[(6, 2)]["status"] == "pending_grading" and g[(6, 2)]["score"] is None  # entregó y falta calificar
    assert g[(7, 2)]["status"] == "not_submitted" and g[(7, 2)]["submissionStatus"] == "none"
    assert g[(4, 3)]["status"] == "not_submitted" and g[(4, 3)]["submissionStatus"] == "draft"  # borrador
    assert g[(5, 3)]["score"] == 90 and g[(5, 3)]["maxScore"] == 100


def test_course_indicators_follow_the_formulas(client, teacher):
    a = client.get(f"{C}/2/analytics", headers=teacher).json()
    assert a["averageScore10"]["value"] == 5.5            # (8 + 0 + 5 + 9) / 4; la nota cero cuenta, el pendiente no
    assert a["submissionRate"]["value"] == 50.0           # 5 de 10 actividades entregadas
    assert a["gradingRate"]["value"] == 80.0              # 4 calificadas de 5 entregadas
    assert a["pendingGradingRate"]["value"] == 10.0       # 1 de 10
    assert a["completionRate"]["value"] == 44.44          # 4 de 9 observaciones
    assert a["completionRate"]["status"] == "partial"     # una actividad sin seguimiento
    assert a["counts"] == {"gradedCount": 4, "pendingGradingCount": 1, "notSubmittedCount": 5, "draftCount": 1}
    assert a["snapshot"]["dataQuality"] == "partial"


def test_student_without_grades_has_null_average_not_zero(client, teacher):
    a = client.get(f"{C}/2/analytics/students/6", headers=teacher).json()
    assert a["averageScore10"]["value"] is None
    assert a["averageScore10"]["status"] == "unavailable"
    assert a["averageScore10"]["code"] == "DATA_NOT_AVAILABLE"


def test_alerts_follow_the_rules(client, teacher):
    alerts = client.get(f"{C}/2/analytics/alerts", headers=teacher).json()
    assert alerts["total"] == 12
    rules = by_student(alerts["items"])
    assert "LOW_AVERAGE" in rules[5]                       # nota 0 y 9 -> 4,5 < 6 con 2 calificaciones
    assert "LOW_AVERAGE" not in rules[4]                   # una sola calificación no alcanza el mínimo
    assert sorted(rules[6]) == ["LOW_COMPLETION", "LOW_SUBMISSION", "NO_DATA", "PENDING_GRADING"]
    for a in alerts["items"]:
        assert a["evidence"], "toda alerta debe traer evidencia"
        assert all(e["explanation"] for e in a["evidence"])


def test_alert_filters(client, teacher):
    info = client.get(f"{C}/2/analytics/alerts", headers=teacher, params={"severity": "info"}).json()
    assert info["total"] and all(a["severity"] == "info" for a in info["items"])
    one = client.get(f"{C}/2/analytics/alerts", headers=teacher, params={"studentId": 5}).json()
    assert one["total"] == 1 and one["items"][0]["ruleCode"] == "LOW_AVERAGE"
    assert client.get(f"{C}/2/analytics/alerts", headers=teacher, params={"status": "resolved"}).json()["total"] == 0


def test_report_is_traceable_to_alerts(client, teacher):
    rep = client.get(f"{C}/2/analytics/report", headers=teacher).json()
    assert rep["activeAlertCount"] == 12
    assert set(rep["metrics"]) == {"averageScore10", "submissionRate", "gradingRate", "completionRate", "pendingGradingRate"}
    with_alert = [f for f in rep["findings"] if f.get("alertId")]
    assert len(with_alert) == 12 and all(f["ruleCode"] for f in with_alert)


def test_access_control(client, teacher, teacher2):
    assert [c["id"] for c in client.get(C, headers=teacher).json()] == [2, 3]
    assert [c["id"] for c in client.get(C, headers=teacher2).json()] == [4]
    r = client.get(f"{C}/4", headers=teacher)
    assert r.status_code == 403 and r.json()["code"] == "COURSE_NOT_AUTHORIZED"
    r = client.get(f"{C}/2", headers=teacher2)
    assert r.status_code == 403
    assert client.get(f"{C}/99", headers=teacher).json()["code"] == "COURSE_NOT_FOUND"


def test_token_errors(client):
    assert client.get("/api/v1/me").json()["code"] == "TOKEN_INVALID"
    expired = client.post("/_mock/token", json={"userId": 3, "expiresIn": -5}).json()["accessToken"]
    r = client.get("/api/v1/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401 and r.json()["code"] == "TOKEN_EXPIRED"


def test_unsynced_course_flow(client, teacher):
    # curso nunca sincronizado: lecturas 503, estado "never"
    r = client.get(f"{C}/3/students", headers=teacher)
    assert r.status_code == 503 and r.json()["code"] == "DATA_NOT_AVAILABLE"
    assert client.get(f"{C}/3/sync", headers=teacher).json()["state"] == "never"
    # sincronizar: 202, luego 409 mientras corre
    first = client.post(f"{C}/3/sync", headers=teacher)
    assert first.status_code == 202 and first.json()["state"] == "running"
    again = client.post(f"{C}/3/sync", headers=teacher)
    assert again.status_code == 409 and again.json()["code"] == "SYNC_IN_PROGRESS"
    assert client.get(f"{C}/3/sync", headers=teacher).json()["state"] == "running"
    time.sleep(0.6)
    status = client.get(f"{C}/3/sync", headers=teacher).json()
    assert status["state"] == "succeeded" and status["lastSuccessAt"]
    # ya hay datos
    assert client.get(f"{C}/3/students", headers=teacher).json()["total"] == 3
    assert client.get(f"{C}/3", headers=teacher).json()["lastSyncAt"]


def test_request_id_is_echoed(client, teacher):
    r = client.get(f"{C}/2", headers={**teacher, "X-Request-Id": "abc-123"})
    assert r.headers["X-Request-Id"] == "abc-123"
    err = client.get(f"{C}/99", headers={**teacher, "X-Request-Id": "xyz-9"})
    assert err.json()["traceId"] == "xyz-9"


def test_pagination(client, teacher):
    page = client.get(f"{C}/2/students", headers=teacher, params={"page": 2, "pageSize": 2}).json()
    assert page["total"] == 5 and page["page"] == 2 and [s["id"] for s in page["items"]] == [6, 7]
