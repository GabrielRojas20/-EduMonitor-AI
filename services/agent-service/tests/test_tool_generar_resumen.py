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
    assert f[0] == "Informe de PRUEBA01: datos calculados el 22/10/2026; calidad de los datos parcial; período del 21/10/2026 al 21/10/2027."
    assert f[1:4] == ["El promedio del curso es 5,50 sobre 10 (4 calificaciones).", "Se recibieron 5 de 10 entregas esperadas (50,00 %).",
                      "Hay 1 actividad(es) pendiente(s) de calificar (10,00 %)."]
    # gradingRate y completionRate no tienen hallazgo propio: salen de las métricas
    assert "Tasa de calificación: 80 % (4 de 5)." in f
    assert any(x.startswith("Tasa de finalización: 44,44 % (4 de 9) (dato parcial).") for x in f)
    assert not any(x.startswith("Promedio de notas") for x in f)         # ya está en el hallazgo
    assert f[-2:] == ["1 alerta activa en el curso.", ALERT["text"]]


def test_without_period_or_alerts():
    report = dict(REPORT, periodStart=None, periodEnd=None, activeAlertCount=0, findings=REPORT["findings"][:3])
    f = facts(run({"course_id": 2}, gateway(report))["data"])
    assert "período" not in f[0] and f[-1] == "No hay alertas activas en el curso."


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
