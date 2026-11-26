"""Herramienta listar_estudiantes: la lista de estudiantes de un curso, numerada dentro del curso."""
import json

import httpx
import pytest

from app.graph import Agent, wants_student_list
from app.tools import ToolContext
from app.catalog.listar_estudiantes import TOOL, Args, facts, MAX_LISTED
from app.toolset import default_registry
from conftest import make_token

TOKEN = make_token()
# Ids de Moodle globales y fuera de orden: la numeración no debe depender de ellos
STUDENTS = [{"id": 307, "fullName": "Zoe Zambrano", "email": "zoe@example.test"},
            {"id": 12, "fullName": "Ana Sofía Acosta", "email": "ana@example.test"},
            {"id": 308, "fullName": "Bruno Benítez", "email": "bruno@example.test"}]
COURSE = {"id": 2, "shortName": "PRUEBA01", "fullName": "Curso de Prueba EduMonitor", "studentCount": 3, "lastSyncAt": "2026-11-24T15:43:00Z"}


def students_gw(students=STUDENTS):
    def handler(request):
        path = request.url.path
        if path == "/api/v1/courses":
            return httpx.Response(200, json=[COURSE])
        if path == "/api/v1/courses/2":
            return httpx.Response(200, json=COURSE)
        if path == "/api/v1/courses/2/students":
            return httpx.Response(200, json={"items": students, "total": len(students), "page": 1, "pageSize": 200})
        return httpx.Response(404, json={"status": 404})
    return handler


def run(args, handler):
    ctx = ToolContext("http://gateway.test", TOKEN, "req-1", 2.0, httpx.MockTransport(handler))
    return TOOL.run(ctx, Args(**args))


def test_students_are_numbered_alphabetically_inside_the_course_and_never_show_the_email():
    out = run({"course_id": 2}, students_gw())
    assert out["ok"] and out["data"]["total"] == 3
    assert [(i["n"], i["fullName"]) for i in out["data"]["items"]] == [(1, "Ana Sofía Acosta"), (2, "Bruno Benítez"), (3, "Zoe Zambrano")]
    assert "email" not in json.dumps(out["data"])
    assert out["source"]["endpoint"] == "GET /api/v1/courses/2/students"


def test_facts_open_with_a_sentence_and_list_one_student_per_line():
    f = facts(run({"course_name": "PRUEBA01"}, students_gw())["data"])
    assert f == ["Estos son los 3 estudiantes de Curso de Prueba EduMonitor, por orden alfabético:",
                 "N.º 1 · Ana Sofía Acosta", "N.º 2 · Bruno Benítez", "N.º 3 · Zoe Zambrano"]


def test_one_student_and_no_students_have_their_own_wording():
    one = facts(run({"course_id": 2}, students_gw(STUDENTS[:1]))["data"])
    assert one[0] == "Este es el único estudiante de Curso de Prueba EduMonitor:"
    assert facts({"courseName": "Física", "total": 0, "items": []}) == ["No hay estudiantes sincronizados en Física."]


def test_a_long_list_shows_the_first_ones_and_says_how_many_there_are():
    items = [{"n": i, "studentId": i, "fullName": f"Estudiante {i:03d}"} for i in range(1, MAX_LISTED + 11)]
    f = facts({"courseName": "Física", "total": len(items), "items": items})
    assert len(f) == 1 + MAX_LISTED + 1 and f[-1] == f"Se muestran los primeros {MAX_LISTED} de {MAX_LISTED + 10} estudiantes."


def test_every_figure_in_the_facts_exists_in_the_tool_data():
    from app.graph import numbers_in
    data = run({"course_id": 2}, students_gw())["data"]
    assert numbers_in(" ".join(facts(data))) - numbers_in(json.dumps(data)) == set()


def test_an_unsynced_course_returns_the_gateway_error():
    def gw(request):
        if request.url.path == "/api/v1/courses/2":
            return httpx.Response(200, json=COURSE)
        return httpx.Response(503, json={"title": "x", "status": 503, "code": "DATA_NOT_AVAILABLE"}, headers={"content-type": "application/problem+json"})
    out = run({"course_id": 2}, gw)
    assert out["ok"] is False and out["error"]["code"] == "DATA_NOT_AVAILABLE"


def test_the_model_is_not_offered_the_tool_but_the_registry_has_it():
    registry = default_registry()
    assert "listar_estudiantes" in registry.names()
    assert "listar_estudiantes" not in {s["function"]["name"] for s in registry.schemas()}


@pytest.mark.parametrize("message", [
    "puedes darme una lista de los estudiantes que tengo en el curso",
    "¿Quiénes son mis estudiantes?",
    "Dame los nombres de los alumnos",
    "Muéstrame los estudiantes",
    "lista de estudiantes",
    "¿Qué estudiantes tengo?",
    "listado de alumnos del curso PRUEBA01",
    "¿Qué estudiantes tiene el curso?",
    "¿Qué estudiantes hay en este curso?",
    "¿Quiénes están en el curso?",
    "¿Qué alumnos cursan esta clase?",
])
def test_questions_that_ask_for_the_student_list(message):
    assert wants_student_list(message)


@pytest.mark.parametrize("message", [
    "¿Cuántos estudiantes tengo?",
    "¿Qué estudiantes tienen entregas pendientes?",
    "lista de estudiantes con alertas",
    "Dame la lista de estudiantes con promedio bajo",
    "¿Qué cursos tengo?",
    "Lista mis cursos",
    "¿Qué notas tiene Bruno?",
    "¿Cómo va el curso?",
    "¿Qué estudiantes tiene alertas?",
    "¿Qué estudiantes tiene promedio bajo?",
    "¿Cuántos estudiantes hay en el curso?",
    "¿Quiénes tienen alertas en el curso?",
])
def test_questions_that_are_not_a_student_list(message):
    assert not wants_student_list(message)


def test_the_list_is_answered_without_asking_the_model_to_choose_a_tool(settings, ollama, traces):
    res = Agent(settings, ollama.client(settings), default_registry(), trace_sink=traces.append,
                tool_transport=httpx.MockTransport(students_gw())).run(
        "puedes darme una lista de los estudiantes que tengo en el curso", 2, TOKEN, "3", "req-1")
    assert res.meta.status == "ok" and ollama.calls == []                # ni planifica ni redacta con el modelo
    assert [f.text for f in res.answer.facts][:2] == ["Estos son los 3 estudiantes de Curso de Prueba EduMonitor, por orden alfabético:",
                                                      "N.º 1 · Ana Sofía Acosta"]
    assert all(f.sources[0].tool == "listar_estudiantes" for f in res.answer.facts)
    assert traces[0]["steps"][0]["resultSummary"]["ruleTool"] == "listar_estudiantes"


def test_a_course_code_written_in_the_question_is_used(settings, ollama, traces):
    res = Agent(settings, ollama.client(settings), default_registry(), trace_sink=traces.append,
                tool_transport=httpx.MockTransport(students_gw())).run(
        "lista de los estudiantes de PRUEBA01", None, TOKEN, "3", "req-1")
    assert res.meta.status == "ok" and res.answer.facts[1].text == "N.º 1 · Ana Sofía Acosta"


def test_a_course_with_more_students_than_the_gateway_pages_reports_the_real_total_and_the_truncation():
    """Con más de 500 estudiantes la lista leída es menor que el total: el total es el real y se avisa que quedó truncada."""
    def gw(request):
        path = request.url.path
        if path == "/api/v1/courses/2":
            return httpx.Response(200, json=COURSE)
        if path == "/api/v1/courses/2/students":
            page = int(request.url.params["page"])
            size = int(request.url.params["pageSize"])
            first = (page - 1) * size
            batch = [{"id": 1000 + i, "fullName": f"Estudiante {i:04d}"} for i in range(first, min(first + size, 700))]
            return httpx.Response(200, json={"items": batch, "total": 700, "page": page, "pageSize": size})
        return httpx.Response(404, json={"status": 404})
    out = run({"course_id": 2}, gw)
    data = out["data"]
    assert out["ok"] and data["total"] == 700 and data["truncated"] is True and len(data["items"]) == 500
    f = facts(data)
    assert f[0] == "Estos son los 700 estudiantes de Curso de Prueba EduMonitor, por orden alfabético:"
    assert "Solo se leyeron los primeros 500 de 700 estudiantes, así que la numeración es parcial." in f
    assert f"Se muestran los primeros {MAX_LISTED} de 500 estudiantes leídos." in f


def test_a_complete_list_is_not_marked_as_truncated():
    data = run({"course_id": 2}, students_gw())["data"]
    assert data["total"] == 3 and data["truncated"] is False
    assert not any("Solo se leyeron" in line for line in facts(data))
