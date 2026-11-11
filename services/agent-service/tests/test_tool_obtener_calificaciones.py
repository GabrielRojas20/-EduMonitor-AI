"""Herramienta obtener_calificaciones contra un gateway simulado."""
import json

import httpx
import pytest

from app.catalog.obtener_calificaciones import Args, TOOL, facts
from app.tools import ToolContext
from app.toolset import default_registry
from conftest import make_token

TOKEN = make_token()
COURSES = [{"id": 2, "shortName": "PRUEBA01", "fullName": "Curso de Prueba EduMonitor"},
           {"id": 3, "shortName": "PRUEBA02", "fullName": "Curso sin sincronizar"}]
STUDENTS = [{"id": 4, "fullName": "Estudiante Uno", "email": "uno@example.com"},
            {"id": 5, "fullName": "Estudiante Dos", "email": "dos@example.com"}]
GRADES = [
    {"studentId": 4, "activityId": 2, "activityName": "Tarea 1", "status": "graded", "submissionStatus": "submitted",
     "score": 8.0, "maxScore": 10.0},
    {"studentId": 5, "activityId": 2, "activityName": "Tarea 1", "status": "graded", "submissionStatus": "submitted",
     "score": 0.0, "maxScore": 10.0},
    {"studentId": 4, "activityId": 3, "activityName": "Tarea 2", "status": "pending_grading", "submissionStatus": "submitted"},
    {"studentId": 5, "activityId": 3, "activityName": "Tarea 2", "status": "not_submitted", "submissionStatus": "draft"},
]


def page(items, total=None):
    return httpx.Response(200, json={"items": items, "total": len(items) if total is None else total})


def gateway(grades=GRADES, seen=None):
    def handler(request: httpx.Request):
        path = request.url.path
        if seen is not None:
            seen.append((path, dict(request.url.params)))
        if path == "/api/v1/courses":
            return httpx.Response(200, json=COURSES)
        if path == "/api/v1/courses/2":
            return httpx.Response(200, json=COURSES[0])
        if path == "/api/v1/courses/4":
            return httpx.Response(403, json={"status": 403, "code": "COURSE_NOT_AUTHORIZED"},
                                  headers={"content-type": "application/problem+json"})
        if path == "/api/v1/courses/2/students":
            return page(STUDENTS)
        if path == "/api/v1/courses/2/grades":
            return page(grades)
        return httpx.Response(404, json={"status": 404})
    return handler


def run(args, handler=None):
    ctx = ToolContext("http://gateway.test", TOKEN, "req-1", 2.0, httpx.MockTransport(handler or gateway()))
    return TOOL.run(ctx, Args(**args))


def test_by_course_name_adds_student_names_and_never_the_email():
    out = run({"course_name": "prueba01"})
    assert out["ok"] and out["data"]["courseName"] == "PRUEBA01" and out["data"]["total"] == 4
    assert out["data"]["items"][0]["studentName"] == "Estudiante Uno"
    assert "example.com" not in json.dumps(out)
    assert out["source"]["endpoint"] == "GET /api/v1/courses/2/grades"


def test_single_course_is_used_when_none_is_given():
    handler = lambda r: httpx.Response(200, json=COURSES[:1]) if r.url.path == "/api/v1/courses" else gateway()(r)
    assert run({}, handler)["data"]["courseId"] == 2


def test_several_courses_ask_which_one():
    out = run({})
    assert out["error"]["code"] == "VALIDATION_ERROR" and "PRUEBA01, PRUEBA02" in out["error"]["message"]


def test_student_name_without_accents_filters_by_student_id():
    seen = []
    out = run({"course_id": 2, "student_name": "estudiante dos", "activity_id": 3}, gateway(seen=seen))
    assert out["ok"]
    grades_call = [p for path, p in seen if path.endswith("/grades")][0]
    assert grades_call["studentId"] == "5" and grades_call["activityId"] == "3"


@pytest.mark.parametrize("args,code", [
    ({"course_id": 2, "student_name": "Pedro"}, "STUDENT_NOT_FOUND"),
    ({"course_id": 2, "student_id": 99}, "STUDENT_NOT_FOUND"),
    ({"course_id": 2, "student_name": "Estudiante"}, "VALIDATION_ERROR"),
    ({"course_name": "Física"}, "COURSE_NOT_FOUND"),
    ({"course_id": 4}, "COURSE_NOT_AUTHORIZED"),
])
def test_resolution_errors(args, code):
    out = run(args)
    assert out["ok"] is False and out["error"]["code"] == code


def test_course_id_and_name_together_are_rejected():
    with pytest.raises(ValueError):
        Args(course_id=2, course_name="PRUEBA01")


def test_unsynced_course_error_comes_from_the_gateway():
    def handler(r):
        if r.url.path == "/api/v1/courses/2/grades":
            return httpx.Response(503, json={"status": 503, "code": "DATA_NOT_AVAILABLE"},
                                  headers={"content-type": "application/problem+json"})
        return gateway()(r)
    assert run({"course_id": 2}, handler)["error"]["code"] == "DATA_NOT_AVAILABLE"


def test_pagination_collects_every_page_and_flags_truncation():
    calls = []

    def handler(r):
        if r.url.path == "/api/v1/courses/2/grades":
            n = int(r.url.params["page"])
            calls.append(n)
            return httpx.Response(200, json={"items": [dict(GRADES[0], activityId=n * 1000 + i) for i in range(200)], "total": 700})
        return gateway()(r)
    out = run({"course_id": 2}, handler)
    assert calls == [1, 2, 3] and len(out["data"]["items"]) == 500 and out["data"]["truncated"] is True


def test_facts_are_written_by_code():
    f = facts(run({"course_id": 2})["data"])
    assert f[0] == "PRUEBA01: 4 registros de calificación (2 calificados, 1 pendiente de calificar, 1 borrador sin enviar, 0 sin entrega)."
    assert "Estudiante Uno, Tarea 1: 8 sobre 10." in f
    assert "Estudiante Dos, Tarea 1: 0 sobre 10 (nota cero)." in f
    assert "Estudiante Uno, Tarea 2: entregada, pendiente de calificar." in f
    assert "Estudiante Dos, Tarea 2: borrador sin enviar." in f


def test_facts_without_records_and_with_many_records():
    assert "No hay calificaciones" in facts({"courseId": 2, "courseName": "P", "items": [], "total": 0, "truncated": False})[0]
    many = run({"course_id": 2}, gateway([dict(GRADES[0], activityId=i) for i in range(20)]))["data"]
    f = facts(many)
    assert len(f) == 1 + 15 + 1 and "primeros 15 de 20" in f[-1]


def test_decimal_scores_use_a_comma():
    row = dict(GRADES[0], score=7.5)
    assert "7,5 sobre 10" in facts(run({"course_id": 2}, gateway([row]))["data"])[1]


def test_registered_and_schema_is_simple():
    assert "obtener_calificaciones" in default_registry().names()
    params = TOOL.schema()["function"]["parameters"]
    assert set(params["properties"]) == {"course_name", "student_name", "activity_name"}
    assert "required" not in params
    assert "course_id" not in params["properties"] and "anyOf" not in params["properties"]["course_name"]
    assert params["properties"]["course_name"]["type"] == "string"


def test_activity_by_name_keeps_only_that_activity():
    out = run({"course_id": 2, "activity_name": "tarea 2"})
    assert out["data"]["total"] == 2 and {i["activityName"] for i in out["data"]["items"]} == {"Tarea 2"}


def test_unknown_activity_lists_the_real_ones():
    out = run({"course_id": 2, "activity_name": "Examen"})
    assert out["error"]["code"] == "ACTIVITY_NOT_FOUND" and "Tarea 1, Tarea 2" in out["error"]["message"]


def test_ambiguous_activity_asks_which_one():
    out = run({"course_id": 2, "activity_name": "Tarea"})
    assert out["error"]["code"] == "VALIDATION_ERROR" and "Tarea 1, Tarea 2" in out["error"]["message"]


def test_ids_invented_by_the_model_are_ignored():
    """Si el modelo manda ids que no ofrecimos, llegan como argumentos extra y no deben usarse en lugar del nombre."""
    from app.toolset import default_registry
    ctx = ToolContext("http://gateway.test", TOKEN, "req-1", 2.0, httpx.MockTransport(gateway()))
    out = default_registry().execute("obtener_calificaciones", {"course_name": "PRUEBA01", "activity_name": "Tarea 2"}, ctx)
    assert out["ok"] and out["data"]["total"] == 2


# ---- estado pedido («pendientes de calificar», «sin entrega»): lo deduce el código, no el modelo
def test_status_filter_keeps_only_those_records_and_the_summary_says_so():
    out = run({"course_id": 2, "status": "pending_grading"})
    assert [(i["studentName"], i["activityName"]) for i in out["data"]["items"]] == [("Estudiante Uno", "Tarea 2")]
    f = facts(out["data"])
    assert f == ["PRUEBA01: 1 registro pendiente de calificar (de 4 registros del curso).",
                 "Estudiante Uno, Tarea 2: entregada, pendiente de calificar."]


def test_not_submitted_includes_drafts_and_each_row_says_which():
    f = facts(run({"course_id": 2, "status": "not_submitted"})["data"])
    assert f[0] == "PRUEBA01: 1 registro sin entrega (de 4 registros del curso)." and "Estudiante Dos, Tarea 2: borrador sin enviar." in f


def test_status_filter_with_no_matches_is_a_clear_answer_not_a_failure():
    only_graded = [g for g in GRADES if g["status"] == "graded"]
    out = run({"course_id": 2, "status": "pending_grading"}, gateway(only_graded))
    assert out["ok"] and facts(out["data"]) == ["No hay registros pendientes de calificar en PRUEBA01 (de 2 registros del curso)."]


def test_an_unknown_status_is_ignored_instead_of_failing():
    out = run({"course_id": 2, "status": "raro"})
    assert out["ok"] and out["data"]["statusFilter"] is None and out["data"]["matching"] == 4


def test_status_combines_with_a_student_filter():
    out = run({"course_id": 2, "student_name": "Estudiante Uno", "status": "pending_grading"})
    assert out["data"]["matching"] == 1


def test_the_model_is_not_offered_the_status():
    assert "status" not in TOOL.schema()["function"]["parameters"]["properties"]
