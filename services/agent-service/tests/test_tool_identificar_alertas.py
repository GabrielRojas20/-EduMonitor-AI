"""Herramienta identificar_alertas contra un gateway simulado (formas tomadas del mock del gateway)."""
import json

import httpx
import pytest

from app.catalog.identificar_alertas import TOOL, Args, facts
from app.tools import ToolContext
from app.toolset import default_registry
from conftest import make_token

TOKEN = make_token()
COURSES = [{"id": 2, "shortName": "PRUEBA01", "fullName": "Curso de Prueba EduMonitor"},
           {"id": 3, "shortName": "PRUEBA02", "fullName": "Curso sin sincronizar"}]
STUDENTS = {"items": [{"id": 4, "fullName": "Estudiante Uno", "email": "uno@example.com"},
                      {"id": 5, "fullName": "Estudiante Dos", "email": "dos@example.com"}], "total": 2}


def alert(rule, student, severity, metric, observed, threshold, explanation):
    return {"alertId": f"a-{rule}-{student}", "ruleCode": rule, "courseId": 2, "studentId": student, "severity": severity,
            "status": "active", "detectedAt": "2026-10-22T15:04:05Z", "resolvedAt": None,
            "evidence": [{"metric": metric, "observedValue": observed, "threshold": threshold, "numerator": None,
                          "denominator": 2, "sourceIds": [], "explanation": explanation}]}


ALERTS = [
    alert("PENDING_GRADING", 4, "info", "pendingGradingRate", 50.0, 20.0, "Tiene 1 de 2 entregas sin calificar (50,00 %); el umbral es 20 %."),
    alert("LOW_AVERAGE", 5, "warning", "averageScore10", 4.5, 6.0, "El promedio es 4,50 sobre 10 con 2 calificaciones; el umbral es 6,00."),
    alert("LOW_SUBMISSION", None, "critical", "submissionRate", 30.0, 80.0, "Se entregó el 30 % de lo esperado; el umbral es 80 %."),
]


def problem(status, code):
    return httpx.Response(status, json={"status": status, "code": code}, headers={"content-type": "application/problem+json"})


def gateway(alerts=ALERTS, seen=None):
    def handler(r: httpx.Request):
        path = r.url.path
        if seen is not None:
            seen.append((path, dict(r.url.params)))
        routes = {"/api/v1/courses": httpx.Response(200, json=COURSES),
                  "/api/v1/courses/2": httpx.Response(200, json=COURSES[0]),
                  "/api/v1/courses/2/students": httpx.Response(200, json=STUDENTS),
                  "/api/v1/courses/2/analytics/alerts": httpx.Response(200, json={"items": alerts, "total": len(alerts)}),
                  "/api/v1/courses/3": httpx.Response(200, json=COURSES[1]),
                  "/api/v1/courses/3/students": problem(503, "DATA_NOT_AVAILABLE"),
                  "/api/v1/courses/4": problem(403, "COURSE_NOT_AUTHORIZED")}
        return routes.get(path, httpx.Response(404, json={"status": 404}))
    return handler


def run(args, handler=None):
    ctx = ToolContext("http://gateway.test", TOKEN, "req-1", 2.0, httpx.MockTransport(handler or gateway()))
    return TOOL.run(ctx, Args(**args))


def test_alerts_are_sorted_by_severity_and_get_student_names_without_email():
    out = run({"course_name": "PRUEBA01"})
    assert out["ok"] and out["source"]["endpoint"] == "GET /api/v1/courses/2/analytics/alerts"
    assert [i["severity"] for i in out["data"]["items"]] == ["critical", "warning", "info"]
    assert [i["studentName"] for i in out["data"]["items"]] == [None, "Estudiante Dos", "Estudiante Uno"]
    assert out["data"]["counts"] == {"critical": 1, "warning": 1, "info": 1} and "example.com" not in json.dumps(out)


def test_filters_are_sent_to_the_gateway_and_status_defaults_to_active():
    seen = []
    run({"course_id": 2, "student_name": "estudiante dos", "severity": "warning"}, gateway(seen=seen))
    params = [p for path, p in seen if path.endswith("/alerts")][0]
    assert params["studentId"] == "5" and params["severity"] == "warning" and params["status"] == "active"
    seen.clear()
    run({"course_id": 2, "status": "resolved"}, gateway(seen=seen))
    assert [p for path, p in seen if path.endswith("/alerts")][0]["status"] == "resolved"


@pytest.mark.parametrize("args,code", [
    ({"course_id": 3}, "DATA_NOT_AVAILABLE"),
    ({"course_id": 4}, "COURSE_NOT_AUTHORIZED"),
    ({"course_id": 2, "student_name": "Pedro"}, "STUDENT_NOT_FOUND"),
    ({}, "VALIDATION_ERROR"),
])
def test_errors(args, code):
    out = run(args)
    assert out["ok"] is False and out["error"]["code"] == code


def test_facts_quote_the_evidence_with_readable_rule_names():
    f = facts(run({"course_id": 2})["data"])
    assert f[0] == "PRUEBA01: 3 alertas activas (1 crítica, 1 de atención, 1 informativa)."
    assert f[1] == "Curso, Entrega baja (crítica): Se entregó el 30 % de lo esperado; el umbral es 80 %."
    assert f[2] == "Estudiante Dos, Promedio bajo (de atención): El promedio es 4,50 sobre 10 con 2 calificaciones; el umbral es 6,00."
    assert f[3].startswith("Estudiante Uno, Calificaciones pendientes (informativa):")


def test_summary_names_the_filters_so_a_partial_list_is_not_read_as_the_whole_course():
    f = facts(run({"course_id": 2, "severity": "info"}, gateway([ALERTS[0]]))["data"])
    assert f[0].startswith("PRUEBA01: 1 alerta activa de severidad informativa (")
    f = facts(run({"course_id": 2, "student_name": "Estudiante Dos"}, gateway([ALERTS[1]]))["data"])
    assert f[0].startswith("PRUEBA01: 1 alerta activa de Estudiante Dos (")


def test_no_alerts_is_a_valid_answer_not_a_failure():
    out = run({"course_id": 2}, gateway([]))
    assert out["ok"] and facts(out["data"]) == ["No hay alertas activas en PRUEBA01."]


def test_empty_result_names_the_filters_so_it_is_not_read_as_all_clear():
    out = run({"course_id": 2, "student_name": "Estudiante Uno", "severity": "critical"}, gateway([]))
    assert facts(out["data"]) == ["No hay alertas activas de severidad crítica de Estudiante Uno en PRUEBA01."]


@pytest.mark.parametrize("sent,expected", [("crítica", "critical"), ("Atención", "warning"), ("informativa", "info"),
                                           ("all", None), ("", None), ("grave", None), (None, None)])
def test_severity_invented_or_spanish_is_translated_or_ignored(sent, expected):
    seen = []
    run({"course_id": 2, "severity": sent}, gateway(seen=seen))
    params = [p for path, p in seen if path.endswith("/alerts")][0]
    assert params.get("severity") == expected


def test_many_alerts_show_the_most_severe_first_and_say_so():
    many = [alert("LOW_SUBMISSION", 4, "warning", "submissionRate", 50.0, 80.0, f"Explicación {i}.") for i in range(20)]
    f = facts(run({"course_id": 2}, gateway(many))["data"])
    assert len(f) == 1 + 15 + 1 and "primeras 15 de 20 alertas, de más a menos grave" in f[-1]


def test_model_only_sees_names_and_filters():
    assert "identificar_alertas" in default_registry().names()
    props = TOOL.schema()["function"]["parameters"]["properties"]
    assert set(props) == {"course_name", "student_name", "severity", "status"}
    assert props["severity"]["enum"] == ["info", "warning", "critical"]
