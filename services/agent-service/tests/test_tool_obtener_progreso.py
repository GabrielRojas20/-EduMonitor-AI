"""Herramienta obtener_progreso contra un gateway simulado (formas tomadas del mock del gateway)."""
import json

import httpx
import pytest

from app.catalog.obtener_progreso import TOOL, Args, facts
from app.tools import ToolContext
from app.toolset import default_registry
from conftest import make_token

TOKEN = make_token()
COURSES = [{"id": 2, "shortName": "PRUEBA01", "fullName": "Curso de Prueba EduMonitor"},
           {"id": 3, "shortName": "PRUEBA02", "fullName": "Curso sin sincronizar"}]
STUDENTS = {"items": [{"id": 4, "fullName": "Estudiante Uno", "email": "uno@example.com"},
                      {"id": 5, "fullName": "Estudiante Dos", "email": "dos@example.com"}], "total": 2}


def metric(value, unit, status="available", num=None, den=None, detail=None):
    return {"value": value, "unit": unit, "status": status, "code": None, "detail": detail, "numerator": num, "denominator": den}


SNAP = {"snapshotId": "snap-2", "syncId": "sync-2", "calculatedAt": "2026-10-22T15:04:05Z", "dataQuality": "partial"}
COURSE_AN = {"courseId": 2, "snapshot": SNAP,
             "averageScore10": metric(5.5, "score_0_10", den=4),
             "submissionRate": metric(50.0, "percent", num=5, den=10),
             "gradingRate": metric(80.0, "percent", num=4, den=5),
             "completionRate": metric(44.44, "percent", "partial", 4, 9, "Una actividad sin seguimiento no entra al cálculo."),
             "pendingGradingRate": metric(10.0, "percent", num=1, den=10),
             "counts": {"gradedCount": 4, "pendingGradingCount": 1, "notSubmittedCount": 5, "draftCount": 1}}
STUDENT_AN = dict(COURSE_AN, studentId=5, averageScore10=metric(4.5, "score_0_10", den=2),
                  counts={"gradedCount": 2, "pendingGradingCount": 0, "notSubmittedCount": 0, "draftCount": 0})
DETAIL = {"student": {"id": 5, "fullName": "Estudiante Dos", "email": "dos@example.com"},
          "grades": [{"studentId": 5, "activityId": 2, "activityName": "Tarea 1"},
                     {"studentId": 5, "activityId": 3, "activityName": "Tarea 2"}],
          "activities": [{"activityId": 2, "activityType": "assign", "completionState": "complete"},
                         {"activityId": 3, "activityType": "assign", "completionState": "not_available"}]}


def problem(status, code):
    return httpx.Response(status, json={"status": status, "code": code}, headers={"content-type": "application/problem+json"})


def gateway(seen=None):
    def handler(r: httpx.Request):
        path = r.url.path
        if seen is not None:
            seen.append((path, dict(r.url.params)))
        routes = {"/api/v1/courses": httpx.Response(200, json=COURSES),
                  "/api/v1/courses/2": httpx.Response(200, json=COURSES[0]),
                  "/api/v1/courses/2/students": httpx.Response(200, json=STUDENTS),
                  "/api/v1/courses/2/analytics": httpx.Response(200, json=COURSE_AN),
                  "/api/v1/courses/2/analytics/students/5": httpx.Response(200, json=STUDENT_AN),
                  "/api/v1/courses/2/students/5": httpx.Response(200, json=DETAIL),
                  "/api/v1/courses/3": httpx.Response(200, json=COURSES[1]),
                  "/api/v1/courses/3/analytics": problem(503, "DATA_NOT_AVAILABLE"),
                  "/api/v1/courses/4": problem(403, "COURSE_NOT_AUTHORIZED")}
        return routes.get(path, httpx.Response(404, json={"status": 404}))
    return handler


def run(args, handler=None):
    ctx = ToolContext("http://gateway.test", TOKEN, "req-1", 2.0, httpx.MockTransport(handler or gateway()))
    return TOOL.run(ctx, Args(**args))


def test_course_progress_is_the_analytics_body_untouched():
    out = run({"course_name": "PRUEBA01"})
    assert out["ok"] and out["data"]["analytics"] == COURSE_AN and out["data"]["courseName"] == "PRUEBA01"
    assert out["source"]["endpoint"] == "GET /api/v1/courses/2/analytics"


def test_student_progress_merges_indicators_and_activity_completion_without_email():
    out = run({"course_id": 2, "student_name": "estudiante dos"})
    d = out["data"]
    assert out["ok"] and d["studentId"] == 5 and d["studentName"] == "Estudiante Dos"
    assert d["analytics"] == STUDENT_AN
    assert d["activities"] == [{"activityId": 2, "activityName": "Tarea 1", "completionState": "complete"},
                               {"activityId": 3, "activityName": "Tarea 2", "completionState": "not_available"}]
    assert "example.com" not in json.dumps(out)


def test_snapshot_is_forwarded_only_when_given():
    seen = []
    run({"course_id": 2, "snapshot_id": "snap-9"}, gateway(seen))
    assert ("/api/v1/courses/2/analytics", {"snapshotId": "snap-9"}) in seen
    seen.clear()
    run({"course_id": 2}, gateway(seen))
    assert ("/api/v1/courses/2/analytics", {}) in seen


@pytest.mark.parametrize("args,code", [
    ({"course_id": 3}, "DATA_NOT_AVAILABLE"),
    ({"course_id": 4}, "COURSE_NOT_AUTHORIZED"),
    ({"course_id": 2, "student_name": "Pedro"}, "STUDENT_NOT_FOUND"),
    ({"course_name": "Física"}, "COURSE_NOT_FOUND"),
    ({}, "VALIDATION_ERROR"),  # dos cursos: pide indicar cuál
])
def test_errors(args, code):
    out = run(args)
    assert out["ok"] is False and out["error"]["code"] == code


def test_course_facts_are_written_by_code_with_numerators_and_partial_notice():
    f = facts(run({"course_id": 2})["data"])
    assert f[0] == "PRUEBA01: indicadores calculados el 22/10/2026; calidad de los datos parcial."
    assert "Promedio de notas (escala de 0 a 10): 5,5." in f
    assert "Tasa de entrega: 50 % (5 de 10)." in f
    assert "Tasa de finalización: 44,44 % (4 de 9) (dato parcial). Una actividad sin seguimiento no entra al cálculo." in f
    assert f[-1] == "Registros: 4 calificados, 1 pendiente de calificar, 5 sin entrega (de ellos, 1 con borrador sin enviar)."


def test_unavailable_indicator_is_never_shown_as_zero():
    unavailable = metric(None, "percent", "unavailable", detail="Moodle no configuró el seguimiento de finalización.")
    data = {"courseId": 2, "courseName": "P", "analytics": dict(COURSE_AN, completionRate=unavailable)}
    assert "Tasa de finalización: no disponible. Moodle no configuró el seguimiento de finalización." in facts(data)


def test_student_facts_include_completion_by_activity():
    f = facts(run({"course_id": 2, "student_name": "Estudiante Dos"})["data"])
    assert f[0].startswith("Estudiante Dos en PRUEBA01:")
    assert "Estudiante Dos, Tarea 1: completada." in f
    assert "Estudiante Dos, Tarea 2: sin dato de finalización en Moodle." in f


def test_ids_and_snapshot_are_not_offered_to_the_model():
    assert "obtener_progreso" in default_registry().names()
    props = TOOL.schema()["function"]["parameters"]["properties"]
    assert set(props) == {"course_name", "student_name"}
