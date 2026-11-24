"""Herramienta generar_resumen contra un gateway simulado (forma tomada del mock del gateway)."""
import json

import httpx
import pytest

from app.catalog.generar_resumen import TOOL, Args, facts
from app.tools import ToolContext
from app.toolset import default_registry
from conftest import make_token

TOKEN = make_token()
COURSES = [{"id": 2, "shortName": "PRUEBA01", "fullName": "Curso de Prueba EduMonitor"},
           {"id": 3, "shortName": "PRUEBA02", "fullName": "Curso sin sincronizar"}]


def metric(value, unit, status="available", num=None, den=None, detail=None):
    return {"value": value, "unit": unit, "status": status, "code": None, "detail": detail, "numerator": num, "denominator": den}


ALERT = {"alertId": "a-1", "ruleCode": "LOW_SUBMISSION", "studentId": 4, "metric": "submissionRate",
         "text": "Estudiante Uno: Entregó 1 de 2 actividades (50,00 %); el umbral es 80 %."}
REPORT = {"courseId": 2,
          "snapshot": {"snapshotId": "snap-2", "syncId": "sync-2", "calculatedAt": "2026-10-22T15:04:05Z", "dataQuality": "partial"},
          "periodStart": "2026-10-21T23:00:00Z", "periodEnd": "2027-10-21T23:00:00Z",
          "metrics": {"averageScore10": metric(5.5, "score_0_10", den=4),
                      "submissionRate": metric(50.0, "percent", num=5, den=10),
                      "gradingRate": metric(80.0, "percent", num=4, den=5),
                      "completionRate": metric(44.44, "percent", "partial", 4, 9, "Una actividad sin seguimiento no entra al cálculo."),
                      "pendingGradingRate": metric(10.0, "percent", num=1, den=10)},
          "findings": [{"metric": "averageScore10", "text": "El promedio del curso es 5,50 sobre 10 (4 calificaciones)."},
                       {"metric": "submissionRate", "text": "Se recibieron 5 de 10 entregas esperadas (50,00 %)."},
                       {"metric": "pendingGradingRate", "text": "Hay 1 actividad(es) pendiente(s) de calificar (10,00 %)."}, ALERT],
          "activeAlertCount": 1}


def problem(status, code):
    return httpx.Response(status, json={"status": status, "code": code}, headers={"content-type": "application/problem+json"})


def gateway(report=REPORT, seen=None):
    def handler(r: httpx.Request):
        if seen is not None:
            seen.append((r.url.path, dict(r.url.params)))
        routes = {"/api/v1/courses": httpx.Response(200, json=COURSES), "/api/v1/courses/2": httpx.Response(200, json=COURSES[0]),
                  "/api/v1/courses/2/analytics/report": httpx.Response(200, json=report),
                  "/api/v1/courses/3": httpx.Response(200, json=COURSES[1]),
                  "/api/v1/courses/3/analytics/report": problem(503, "DATA_NOT_AVAILABLE"),
                  "/api/v1/courses/4": problem(403, "COURSE_NOT_AUTHORIZED")}
        return routes.get(r.url.path, httpx.Response(404, json={"status": 404}))
    return handler


def run(args, handler=None):
    ctx = ToolContext("http://gateway.test", TOKEN, "req-1", 2.0, httpx.MockTransport(handler or gateway()))
    return TOOL.run(ctx, Args(**args))


def test_report_by_course_name_keeps_the_analytics_body():
    out = run({"course_name": "prueba01"})
    assert out["ok"] and out["data"]["report"] == REPORT and out["data"]["courseName"] == "PRUEBA01"
    assert out["source"]["endpoint"] == "GET /api/v1/courses/2/analytics/report"


def test_snapshot_is_forwarded_only_when_given():
    seen = []
    run({"course_id": 2, "snapshot_id": "snap-9"}, gateway(seen=seen))
    assert ("/api/v1/courses/2/analytics/report", {"snapshotId": "snap-9"}) in seen


@pytest.mark.parametrize("args,code", [
    ({"course_id": 3}, "DATA_NOT_AVAILABLE"), ({"course_id": 4}, "COURSE_NOT_AUTHORIZED"),
    ({"course_name": "Física"}, "COURSE_NOT_FOUND"), ({}, "VALIDATION_ERROR")])
def test_errors(args, code):
    out = run(args)
    assert out["ok"] is False and out["error"]["code"] == code


def test_facts_use_the_analytics_wording_and_add_only_the_metrics_without_a_finding():
    f = facts(run({"course_id": 2})["data"])
    assert f[0] == "Informe de PRUEBA01: datos calculados el 22/10/2026; calidad de los datos parcial; observaciones sincronizadas del 21/10/2026 al 21/10/2027."
    assert f[1:4] == ["El promedio del curso es 5,50 sobre 10 (4 calificaciones).", "Se recibieron 5 de 10 entregas esperadas (50,00 %).",
                      "Hay 1 actividad(es) pendiente(s) de calificar (10,00 %)."]
    # gradingRate y completionRate no tienen hallazgo propio: salen de las métricas
    assert "Tasa de calificación: 80 % (4 de 5)." in f
    assert any(x.startswith("Tasa de finalización: 44,44 % (4 de 9) (dato parcial).") for x in f)
    assert not any(x.startswith("Promedio de notas") for x in f)         # ya está en el hallazgo
    assert f[-2:] == ["1 alerta activa en el curso.", ALERT["text"]]


REAL_ALERTS = [
    {"alertId": "LOW_SUBMISSION-2-3", "ruleCode": "LOW_SUBMISSION", "studentId": 3, "metric": "submissionRate",
     "text": "La tasa de entregas enviadas está por debajo del umbral configurado.", "observedValue": 66.67, "threshold": 80.0,
     "sourceIds": ["3", "5", "6"]},
    {"alertId": "LOW_AVERAGE-2-4", "ruleCode": "LOW_AVERAGE", "studentId": 4, "metric": "averageScore10",
     "text": "El promedio normalizado está por debajo del umbral configurado.", "observedValue": 0.0, "threshold": 6.0, "sourceIds": ["4"]},
    {"alertId": "NO_DATA-2-9", "ruleCode": "NO_DATA", "studentId": 9, "metric": "completionRate",
     "text": "Moodle no entregó observaciones de seguimiento de finalización.", "observedValue": None, "threshold": None, "sourceIds": []},
]


def real_gateway(report):
    base = gateway(report)

    def handler(request):
        if request.url.path == "/api/v1/courses/2/students":
            return httpx.Response(200, json={"items": [{"id": 3, "fullName": "Ana Pérez"}, {"id": 4, "fullName": "Luis Gómez"}],
                                             "page": 1, "pageSize": 200, "total": 2})
        return base(request)
    return handler


def test_alert_findings_name_the_student_the_rule_and_the_evidence_from_analytics():
    report = dict(REPORT, findings=REPORT["findings"][:3] + REAL_ALERTS, activeAlertCount=3)
    f = facts(run({"course_id": 2}, real_gateway(report))["data"])
    assert ("Ana Pérez, Entrega baja: La tasa de entregas enviadas está por debajo del umbral configurado. "
            "(valor observado 66,67 %; umbral 80 %).") in f
    assert ("Luis Gómez, Promedio bajo: El promedio normalizado está por debajo del umbral configurado. "
            "(valor observado 0 sobre 10; umbral 6 sobre 10).") in f
    # una alerta sin valor ni umbral (sin datos) conserva el texto de analytics tal cual
    assert "Moodle no entregó observaciones de seguimiento de finalización." in f


def test_a_student_missing_from_the_list_is_named_by_id_and_the_report_still_works():
    report = dict(REPORT, findings=REPORT["findings"][:3] + REAL_ALERTS[:1], activeAlertCount=1)
    handler = gateway(report)                                              # este gateway no tiene la lista de estudiantes (404)
    out = run({"course_id": 2}, handler)
    assert out["ok"] and any(x.startswith("Estudiante 3, Entrega baja:") for x in facts(out["data"]))


def test_every_number_in_the_alert_facts_exists_in_the_tool_data():
    """El validador de salida solo admite cifras que estén en los datos de la herramienta."""
    import re
    report = dict(REPORT, findings=REPORT["findings"][:3] + REAL_ALERTS, activeAlertCount=3)
    data = run({"course_id": 2}, real_gateway(report))["data"]
    en_datos = {float(n) for n in re.findall(r"\d+(?:\.\d+)?", json.dumps(data))}
    en_hechos = {float(n.replace(",", ".")) for line in facts(data) for n in re.findall(r"\d+(?:,\d+)?", line)}
    assert en_hechos - en_datos == set()


def test_without_period_or_alerts():
    report = dict(REPORT, periodStart=None, periodEnd=None, activeAlertCount=0, findings=REPORT["findings"][:3])
    f = facts(run({"course_id": 2}, gateway(report))["data"])
    assert "observaciones sincronizadas" not in f[0] and f[-1] == "No hay alertas activas en el curso."


def test_many_alert_findings_are_capped_and_say_so():
    many = [dict(ALERT, alertId=f"a-{i}") for i in range(20)]
    f = facts(run({"course_id": 2}, gateway(dict(REPORT, findings=REPORT["findings"][:3] + many, activeAlertCount=20)))["data"])
    assert sum(1 for x in f if x == ALERT["text"]) == 15 and f[-1] == "Se muestran los primeros 15 de 20 hallazgos de alertas."


def test_unavailable_metric_is_never_shown_as_zero():
    report = dict(REPORT, findings=REPORT["findings"][:1],
                  metrics=dict(REPORT["metrics"], completionRate=metric(None, "percent", "unavailable", detail="Moodle no configuró el seguimiento.")))
    assert "Tasa de finalización: no disponible. Moodle no configuró el seguimiento." in facts(run({"course_id": 2}, gateway(report))["data"])


def test_model_only_sees_the_course_name():
    assert "generar_resumen" in default_registry().names()
    assert set(TOOL.schema()["function"]["parameters"]["properties"]) == {"course_name"}
    assert "example.com" not in json.dumps(run({"course_id": 2}))
