"""Herramienta listar_cursos contra un gateway simulado."""
import json

import httpx
import pytest

from app.graph import Agent
from app.tools import ToolContext
from app.catalog.common import NoArgs
from app.catalog.listar_cursos import TOOL as LISTAR_CURSOS
from app.toolset import default_registry
from conftest import make_token

COURSES = [
    {"id": 2, "shortName": "PRUEBA01", "fullName": "Curso de Prueba EduMonitor", "studentCount": 5,
     "lastSyncAt": "2026-10-22T15:04:05Z"},
    {"id": 3, "shortName": "PRUEBA02", "fullName": "Curso sin sincronizar", "lastSyncAt": None},  # sin studentCount
]
TOKEN = make_token()


def gateway(handler):
    return httpx.MockTransport(handler)


def ctx(handler, token=TOKEN):
    return ToolContext("http://gateway.test", token, "req-42", 2.0, gateway(handler))


def run(handler, token=TOKEN):
    return LISTAR_CURSOS.run(ctx(handler, token), NoArgs())


def problem(status, code=None, **extra):
    body = {"title": "Error", "status": status, **({"code": code} if code else {}), **extra}
    return httpx.Response(status, json=body, headers={"content-type": "application/problem+json"})


def test_success_returns_the_common_output():
    out = run(lambda r: httpx.Response(200, json=COURSES))
    assert out["ok"] is True and out["error"] is None
    assert out["source"]["endpoint"] == "GET /api/v1/courses" and out["source"]["requestId"] == "req-42"
    assert out["data"]["total"] == 2
    assert out["data"]["courses"][0] == {"id": 2, "shortName": "PRUEBA01", "fullName": "Curso de Prueba EduMonitor",
                                         "studentCount": 5, "lastSyncAt": "2026-10-22T15:04:05Z"}
    assert out["data"]["courses"][1]["studentCount"] is None  # un curso sin sincronizar no tiene conteo


def test_no_courses_is_a_valid_empty_answer():
    out = run(lambda r: httpx.Response(200, json=[]))
    assert out["ok"] is True and out["data"] == {"courses": [], "total": 0}


def test_forwards_the_teacher_jwt_and_the_request_id():
    seen = {}

    def handler(request: httpx.Request):
        seen.update(method=request.method, path=request.url.path, auth=request.headers.get("authorization"),
                    rid=request.headers.get("x-request-id"))
        return httpx.Response(200, json=COURSES)

    run(handler)
    assert seen == {"method": "GET", "path": "/api/v1/courses", "auth": f"Bearer {TOKEN}", "rid": "req-42"}


@pytest.mark.parametrize("response,expected_code,retryable", [
    (problem(401, "TOKEN_EXPIRED"), "TOKEN_EXPIRED", False),
    (problem(401, "TOKEN_INVALID"), "TOKEN_INVALID", False),
    (problem(403, "COURSE_NOT_AUTHORIZED"), "COURSE_NOT_AUTHORIZED", False),
    (problem(503, "MOODLE_UNAVAILABLE"), "MOODLE_UNAVAILABLE", True),
    (problem(503, "DATA_NOT_AVAILABLE"), "DATA_NOT_AVAILABLE", False),
    (problem(401), "TOKEN_INVALID", False),                       # sin código: se deduce del estado
    (problem(503, "CODIGO_RARO"), "MOODLE_UNAVAILABLE", True),     # código que el agente no conoce
    (httpx.Response(502, text="<html>Bad Gateway</html>"), "MOODLE_UNAVAILABLE", True),
])
def test_gateway_errors_become_tool_errors(response, expected_code, retryable):
    out = run(lambda r: response)
    assert out["ok"] is False and out["data"] is None
    assert out["error"]["code"] == expected_code and out["error"]["retryable"] is retryable
    assert out["error"]["message"]


def test_timeout_and_connection_failures():
    def timeout(request):
        raise httpx.ReadTimeout("lento", request=request)

    def refused(request):
        raise httpx.ConnectError("sin conexión", request=request)

    assert run(timeout)["error"] == {"code": "TOOL_TIMEOUT", "message": "El gateway tardó demasiado en responder.",
                                     "retryable": True}
    assert run(refused)["error"]["code"] == "MOODLE_UNAVAILABLE"


def test_a_200_that_is_not_json_is_an_error():
    out = run(lambda r: httpx.Response(200, text="no soy json"))
    assert out["ok"] is False and out["error"]["code"] == "MOODLE_UNAVAILABLE"


def test_the_jwt_never_appears_in_any_output():
    outputs = [run(lambda r: httpx.Response(200, json=COURSES)), run(lambda r: problem(401, "TOKEN_EXPIRED", detail="venció")),
               run(lambda r: httpx.Response(502, text="x"))]
    assert all(TOKEN not in json.dumps(o) for o in outputs)


def test_schema_offered_to_the_model():
    schema = LISTAR_CURSOS.schema()["function"]
    assert schema["name"] == "listar_cursos" and schema["parameters"] == {"properties": {}, "type": "object"}
    assert "cursos" in schema["description"]
    assert "listar_cursos" in default_registry().names()


# ---- flujo completo: modelo simulado + herramienta real + gateway simulado
CALL = [{"function": {"name": "listar_cursos", "arguments": {}}}]


def draft(text):
    return json.dumps({"facts": [{"text": text, "tool": "listar_cursos", "stepN": 1}], "inferences": [],
                       "recommendations": [], "unavailable": []})


def agent(settings, ollama, traces, handler):
    return Agent(settings, ollama.client(settings), default_registry(), trace_sink=traces.append,
                 tool_transport=gateway(handler))


def test_facts_are_written_by_code_and_the_model_is_not_needed_for_a_simple_list(settings, ollama, traces):
    ollama.reply(tool_calls=CALL)  # solo se usa el modelo para elegir la herramienta
    res = agent(settings, ollama, traces, lambda r: httpx.Response(200, json=COURSES)).run(
        "¿Qué cursos tengo?", None, TOKEN, "3", "req-42")
    assert [f.text for f in res.answer.facts] == [
        "Tienes acceso a 2 cursos.",
        "PRUEBA01 (Curso de Prueba EduMonitor): 5 estudiantes; última sincronización con Moodle el 22/10/2026.",
        "PRUEBA02 (Curso sin sincronizar): aún no se sincronizó con Moodle, por lo que el número de estudiantes no está disponible.",
    ]
    assert all(f.sources[0].tool == "listar_cursos" and f.sources[0].stepN == 1 for f in res.answer.facts)
    assert res.meta.status == "ok" and res.meta.lastSyncAt == "2026-10-22T15:04:05Z"
    assert len(ollama.calls) == 1                      # no hubo redacción: nada que el modelo pueda inventar
    assert traces[0]["steps"][1]["resultSummary"] == {"courses": 2, "total": 2}
    assert TOKEN not in json.dumps(traces[0])


def test_a_dato_no_disponible_is_never_attributed_to_another_course(settings, ollama, traces):
    """Un modelo pequeño escribió «PRUEBA02 tiene 5 estudiantes» (el 5 era de PRUEBA01). Ya no redacta los hechos."""
    ollama.reply(tool_calls=CALL)
    res = agent(settings, ollama, traces, lambda r: httpx.Response(200, json=COURSES)).run(
        "¿Qué cursos tengo?", None, TOKEN, "3", "req-42")
    sin_sincronizar = next(f.text for f in res.answer.facts if f.text.startswith("PRUEBA02"))
    assert "5" not in sin_sincronizar and "no está disponible" in sin_sincronizar


def test_the_model_only_interprets_when_the_teacher_asks_for_it(settings, ollama, traces):
    ollama.reply(tool_calls=CALL)
    ollama.reply(json.dumps({
        "facts": [{"text": "Hecho inventado por el modelo: 99 cursos.", "tool": "listar_cursos", "stepN": 1}],  # se ignora
        "inferences": [{"text": "El curso sin sincronizar podría estar pendiente de carga.", "basedOn": [2]},
                       {"text": "Sin base.", "basedOn": []}],
        "recommendations": [{"text": "Sincroniza PRUEBA02 desde la lista de cursos.", "relatedFinding": 2},
                            {"text": "Revisa los 77 estudiantes.", "relatedFinding": 1},   # cifra sin fuente
                            {"text": "Sin hallazgo.", "relatedFinding": None}],
        "unavailable": []}))
    res = agent(settings, ollama, traces, lambda r: httpx.Response(200, json=COURSES)).run(
        "¿Qué cursos tengo y qué me recomiendas?", None, TOKEN, "3", "req-42")
    assert all("99" not in f.text for f in res.answer.facts)                          # los hechos siguen siendo del código
    assert [(i.text, i.basedOn) for i in res.answer.inferences] == [
        ("El curso sin sincronizar podría estar pendiente de carga.", [2])]
    assert [(r.text, r.relatedFinding) for r in res.answer.recommendations] == [
        ("Sincroniza PRUEBA02 desde la lista de cursos.", 2)]
    assert any("omitió una cifra" in u for u in res.answer.unavailable)
    prompt = ollama.calls[1]["messages"][1]["content"]
    assert "[2] PRUEBA02" in prompt and "no está disponible" in prompt and "null" not in prompt


def test_if_the_interpretation_fails_the_facts_are_still_shown(settings, ollama, traces):
    ollama.reply(tool_calls=CALL)
    ollama.fail(500)
    res = agent(settings, ollama, traces, lambda r: httpx.Response(200, json=COURSES)).run(
        "¿Qué me recomiendas hacer con mis cursos?", None, TOKEN, "3", "req-42")
    assert len(res.answer.facts) == 3 and res.answer.inferences == [] and res.answer.recommendations == []
    assert "solo los hechos" in res.answer.unavailable[0] and res.meta.status == "partial"


@pytest.mark.parametrize("message,expected", [
    ("¿Qué cursos tengo?", False), ("Lista mis cursos", False), ("¿Cuántos estudiantes tiene PRUEBA01?", False),
    ("¿Qué me recomiendas?", True), ("Analiza mis cursos", True), ("¿Qué debo hacer con PRUEBA02?", True),
    ("¿Por qué no tiene estudiantes?", True),
])
def test_when_the_model_is_asked_to_interpret(message, expected):
    from app.graph import needs_interpretation
    assert needs_interpretation(message) is expected


def test_course_facts_wording():
    from app.catalog.listar_cursos import facts as listar_cursos_facts
    assert listar_cursos_facts({"courses": [], "total": 0}) == ["No tienes cursos con acceso autorizado."]
    one = {"courses": [{"id": 2, "shortName": "A", "fullName": "Uno", "studentCount": 1, "lastSyncAt": "2026-01-05T00:00:00Z"}],
           "total": 1}
    assert listar_cursos_facts(one) == ["Tienes acceso a 1 curso.",
                                        "A (Uno): 1 estudiante; última sincronización con Moodle el 05/01/2026."]
    partial = {"courses": [{"id": 2, "shortName": "A", "fullName": "Uno", "studentCount": None,
                            "lastSyncAt": "2026-01-05T00:00:00Z"}], "total": 1}
    assert "el número de estudiantes no está disponible" in listar_cursos_facts(partial)[1]


def test_expired_session_in_the_gateway_is_explained_to_the_teacher(settings, ollama, traces):
    ollama.reply(tool_calls=CALL)
    res = agent(settings, ollama, traces, lambda r: problem(401, "TOKEN_EXPIRED")).run(
        "¿Qué cursos tengo?", None, TOKEN, "3", "req-42")
    assert res.meta.status == "error" and res.answer.facts == []
    assert "inicia sesión" in res.answer.unavailable[0]
    assert len(ollama.calls) == 1  # sin datos no se le pide al modelo que redacte


def test_gateway_down_does_not_invent_courses(settings, ollama, traces):
    def refused(request):
        raise httpx.ConnectError("caído", request=request)

    ollama.reply(tool_calls=CALL)
    res = agent(settings, ollama, traces, refused).run("¿Qué cursos tengo?", None, TOKEN, "3", "req-42")
    assert res.meta.status == "error" and res.answer.facts == []
    assert "no respondió" in res.answer.unavailable[0]


# ---- respaldo del planificador cuando el modelo no elige ninguna herramienta
@pytest.mark.parametrize("message,tool", [
    ("¿Qué alertas hay en PRUEBA01?", "identificar_alertas"), ("¿Qué estudiantes están en riesgo?", "identificar_alertas"),
    ("¿Qué notas tiene Estudiante Dos?", "obtener_calificaciones"), ("¿Quién tiene entregas pendientes?", "obtener_calificaciones"),
    ("¿Cómo va el curso PRUEBA01?", "obtener_progreso"), ("¿Cuál es el promedio del curso?", "obtener_progreso"),
    ("Genera un informe del curso PRUEBA01", "generar_resumen"), ("Dame un resumen de PRUEBA01", "generar_resumen"),
    ("¿Qué cursos tengo y qué me recomiendas?", "listar_cursos"), ("¿Cuántos estudiantes tiene mi curso?", "listar_cursos"),
    ("cuéntame un chiste", None),
])
def test_fallback_tool_by_keywords(message, tool):
    from app.graph import fallback_tool
    assert fallback_tool(message, default_registry().names()) == tool


def test_fallback_only_offers_tools_that_exist():
    from app.graph import fallback_tool
    assert fallback_tool("¿Qué alertas hay?", ["listar_cursos"]) is None


def test_when_the_model_picks_no_tool_the_fallback_answers_a_data_question(settings, ollama, traces):
    ollama.reply(tool_calls=[])  # el modelo no eligió nada
    res = agent(settings, ollama, traces, lambda r: httpx.Response(200, json=COURSES)).run(
        "¿Qué cursos tengo?", None, TOKEN, "3", "req-42")
    assert res.meta.status == "ok" and res.answer.facts[0].text == "Tienes acceso a 2 cursos."
    assert traces[0]["steps"][0]["resultSummary"]["fallbackTool"] == "listar_cursos"


def test_the_fallback_is_not_used_when_the_model_chose_a_tool(settings, ollama, traces):
    ollama.reply(tool_calls=CALL)
    agent(settings, ollama, traces, lambda r: httpx.Response(200, json=COURSES)).run("¿Qué cursos tengo?", None, TOKEN, "3", "req-42")
    assert "fallbackTool" not in traces[0]["steps"][0]["resultSummary"]


def test_a_greeting_or_out_of_scope_message_never_reaches_the_fallback(settings, ollama, traces):
    res = agent(settings, ollama, traces, lambda r: httpx.Response(200, json=COURSES)).run(
        "Cambia la nota de mis cursos a 10", None, TOKEN, "3", "req-42")
    assert res.meta.status == "refused" and ollama.calls == []


@pytest.mark.parametrize("message,expected", [
    ("¿Hay alertas críticas en PRUEBA01?", {"course_name": "PRUEBA01"}), ("¿Cómo va prueba02?", {"course_name": "prueba02"}),
    ("¿Qué notas tienen mis estudiantes?", {}), ("Hola 2026", {})])
def test_fallback_arguments_take_the_course_code_from_the_message(message, expected):
    from app.graph import fallback_arguments
    assert fallback_arguments(message) == expected


# ---- el estado que pide el docente lo deduce el código del texto de la pregunta
@pytest.mark.parametrize("message,expected", [
    ("¿Qué actividades están pendientes de calificar?", {"status": "pending_grading"}),
    ("¿Qué entregas están por calificar en PRUEBA01?", {"status": "pending_grading"}),
    ("¿Qué falta calificar?", {"status": "pending_grading"}),
    ("¿Quiénes no han entregado la tarea?", {"status": "not_submitted"}),
    ("¿Quién está sin entrega?", {"status": "not_submitted"}),
    ("¿Qué notas tiene Estudiante Dos?", {}), ("¿Cómo va el curso?", {}),
])
def test_status_hint_from_the_message(message, expected):
    from app.graph import hint_arguments
    assert hint_arguments("obtener_calificaciones", message) == expected


def test_the_hint_only_applies_to_obtener_calificaciones():
    from app.graph import hint_arguments
    assert hint_arguments("listar_cursos", "¿Qué está pendiente de calificar?") == {}


GRADES_FOR_FLOW = {"items": [
    {"studentId": 4, "activityId": 2, "activityName": "Tarea 1", "status": "graded", "submissionStatus": "submitted", "score": 8, "maxScore": 10},
    {"studentId": 5, "activityId": 2, "activityName": "Tarea 1", "status": "pending_grading", "submissionStatus": "submitted"}], "total": 2}


def grades_gateway(request):
    routes = {"/api/v1/courses": httpx.Response(200, json=COURSES[:1]),
              "/api/v1/courses/2/students": httpx.Response(200, json={"items": [{"id": 4, "fullName": "Estudiante Uno"},
                                                                               {"id": 5, "fullName": "Estudiante Dos"}], "total": 2}),
              "/api/v1/courses/2/grades": httpx.Response(200, json=GRADES_FOR_FLOW)}
    return routes.get(request.url.path, httpx.Response(404, json={"status": 404}))


@pytest.mark.parametrize("model_arguments", [{}, {"status": "graded"}, {"status": "inventado"}])
def test_pending_question_returns_only_pending_whatever_the_model_sent(settings, ollama, traces, model_arguments):
    ollama.reply(tool_calls=[{"function": {"name": "obtener_calificaciones", "arguments": model_arguments}}])
    res = agent(settings, ollama, traces, grades_gateway).run("¿Qué actividades están pendientes de calificar?", None, TOKEN, "3", "req-42")
    assert [f.text for f in res.answer.facts] == ["PRUEBA01: 1 registro pendiente de calificar (de 2 registros del curso).",
                                                  "Estudiante Dos, Tarea 1: entregada, pendiente de calificar."]
    assert res.meta.status == "ok" and res.answer.unavailable == []


def test_a_normal_grades_question_is_not_filtered(settings, ollama, traces):
    ollama.reply(tool_calls=[{"function": {"name": "obtener_calificaciones", "arguments": {"status": "pending_grading"}}}])
    res = agent(settings, ollama, traces, grades_gateway).run("¿Qué notas hay?", None, TOKEN, "3", "req-42")
    assert len(res.answer.facts) == 3 and "2 registros de calificación" in res.answer.facts[0].text   # ignoró el filtro inventado


def test_pending_question_also_works_through_the_fallback(settings, ollama, traces):
    ollama.reply(tool_calls=[])
    res = agent(settings, ollama, traces, grades_gateway).run("¿Qué entregas están pendientes de calificar?", None, TOKEN, "3", "req-42")
    assert res.answer.facts[0].text.startswith("PRUEBA01: 1 registro pendiente de calificar")


# ---- argumentos que el código corrige al modelo
def test_course_code_put_in_the_wrong_field_is_moved_to_the_course():
    """El fallo real de qwen3:1.7b: «¿Qué está pendiente de calificar en PRUEBA01?» -> activity_name='PRUEBA01'."""
    from app.graph import fix_arguments
    assert fix_arguments("obtener_calificaciones", {"activity_name": "PRUEBA01"}, "¿Qué actividades están pendientes de calificar en PRUEBA01?") \
        == {"course_name": "PRUEBA01", "status": "pending_grading"}


@pytest.mark.parametrize("tool,given,message,expected", [
    ("obtener_progreso", {}, "¿Cómo va PRUEBA01?", {"course_name": "PRUEBA01"}),
    ("obtener_progreso", {"course_name": "Otro"}, "¿Cómo va PRUEBA01?", {"course_name": "Otro"}),          # respeta lo que eligió el modelo
    ("obtener_progreso", {"course_id": 2}, "¿Cómo va PRUEBA01?", {"course_id": 2}),
    ("obtener_calificaciones", {"activity_name": "Tarea 2"}, "Notas de Tarea 2 en PRUEBA01", {"activity_name": "Tarea 2", "course_name": "PRUEBA01"}),
    ("identificar_alertas", {"student_name": "prueba01"}, "Alertas de PRUEBA01", {"course_name": "PRUEBA01"}),
    ("listar_cursos", {}, "¿Qué cursos tengo en PRUEBA01?", {}),                                          # sin parámetro de curso
    ("obtener_progreso", {}, "¿Cómo van mis estudiantes?", {}),                                           # sin código: no se inventa
])
def test_fix_arguments(tool, given, message, expected):
    from app.graph import fix_arguments
    assert fix_arguments(tool, given, message) == expected


def test_a_course_code_in_the_wrong_field_still_gets_answered_end_to_end(settings, ollama, traces):
    ollama.reply(tool_calls=[{"function": {"name": "obtener_calificaciones", "arguments": {"activity_name": "PRUEBA01"}}}])
    res = agent(settings, ollama, traces, grades_gateway).run("¿Qué actividades están pendientes de calificar en PRUEBA01?",
                                                              None, TOKEN, "3", "req-42")
    assert res.answer.facts[0].text == "PRUEBA01: 1 registro pendiente de calificar (de 2 registros del curso)." and res.meta.status == "ok"


# ---- curso de referencia elegido en la interfaz (courseId de POST /chat)
@pytest.mark.parametrize("given,message,expected", [
    ({}, "¿Qué falta por calificar?", {"course_id": 2}),
    ({"course_name": "Inventado"}, "¿Qué falta por calificar?", {"course_id": 2}),            # el modelo no gana al selector
    ({"course_id": 99}, "¿Qué falta por calificar?", {"course_id": 2}),
    ({"course_name": "PRUEBA02"}, "¿Cómo va PRUEBA02?", {"course_name": "PRUEBA02"}),          # lo escrito gana al selector
    ({"course_name": "PRUEBA02", "course_id": 2}, "¿Cómo va PRUEBA02?", {"course_name": "PRUEBA02"}),
])
def test_with_reference_course(given, message, expected):
    from app.graph import with_reference_course
    assert with_reference_course(given, 2, message) == expected


@pytest.mark.parametrize("model_arguments", [{}, {"course_name": "PRUEBA01"}, {"course_name": "otro"}])
def test_selected_course_never_collides_with_a_name_the_model_added(settings, ollama, traces, model_arguments):
    """El fallo real visto en el navegador: el selector manda courseId, el modelo pone course_name y la validación rechazaba los dos."""
    ollama.reply(tool_calls=[{"function": {"name": "obtener_calificaciones", "arguments": model_arguments}}])
    res = agent(settings, ollama, traces, grades_gateway_by_id).run("¿Qué actividades están pendientes de calificar?", 2, TOKEN, "3", "req-42")
    assert res.meta.status == "ok" and res.answer.unavailable == []
    assert res.answer.facts[0].text.startswith("PRUEBA01: 1 registro pendiente de calificar")
    assert traces[0]["steps"][1]["args"] == {"course_id": 2, "status": "pending_grading"}


def test_selected_course_is_also_applied_by_the_fallback(settings, ollama, traces):
    ollama.reply(tool_calls=[])
    res = agent(settings, ollama, traces, grades_gateway_by_id).run("¿Qué falta por calificar?", 2, TOKEN, "3", "req-42")
    assert res.meta.status == "ok" and traces[0]["steps"][1]["args"] == {"course_id": 2, "status": "pending_grading"}


def grades_gateway_by_id(request):
    routes = {"/api/v1/courses/2": httpx.Response(200, json=COURSES[0]),
              "/api/v1/courses/2/students": httpx.Response(200, json={"items": [{"id": 4, "fullName": "Estudiante Uno"},
                                                                               {"id": 5, "fullName": "Estudiante Dos"}], "total": 2}),
              "/api/v1/courses/2/grades": httpx.Response(200, json=GRADES_FOR_FLOW)}
    return routes.get(request.url.path, httpx.Response(404, json={"status": 404}))


# ---- lo que un modelo pequeño inventa: nombres que el docente no escribió, ids ocultos y la pista del curso
@pytest.mark.parametrize("given,message,expected", [
    ({"activity_name": "2"}, "¿Qué actividades están pendientes de calificar?", {"status": "pending_grading"}),     # el número del selector
    ({"activity_name": "pendientes de calificar"}, "¿Qué actividades están pendientes de calificar?", {"status": "pending_grading"}),
    ({"student_name": "Ana Pérez"}, "¿Cómo va Ana?", {}),                                                            # no escribió «Pérez»
    ({"student_name": "Estudiante Dos"}, "¿Cómo va Estudiante Dos?", {"student_name": "Estudiante Dos"}),
    ({"activity_name": "Tarea 2"}, "Notas de la Tarea 2", {"activity_name": "Tarea 2"}),
    ({"activity_name": "tarea 2"}, "Notas de la TAREA 2", {"activity_name": "tarea 2"}),                              # sin distinguir mayúsculas
])
def test_names_the_teacher_did_not_write_are_dropped(given, message, expected):
    from app.graph import fix_arguments
    assert fix_arguments("obtener_calificaciones", given, message) == expected


def test_the_real_browser_failure_selected_course_plus_activity_name_2(settings, ollama, traces):
    """Con el curso elegido, el modelo ponía el 2 del curso como nombre de actividad: filtraba la Tarea 2 y daba 0 pendientes."""
    ollama.reply(tool_calls=[{"function": {"name": "obtener_calificaciones", "arguments": {"activity_name": "2"}}}])
    res = agent(settings, ollama, traces, grades_gateway_by_id).run("¿Qué actividades están pendientes de calificar?", 2, TOKEN, "3", "req-42")
    assert res.answer.facts[0].text == "PRUEBA01: 1 registro pendiente de calificar (de 2 registros del curso)."
    assert traces[0]["steps"][1]["args"] == {"course_id": 2, "status": "pending_grading"}


def test_hidden_parameters_sent_by_the_model_are_discarded(settings, ollama, traces):
    ollama.reply(tool_calls=[{"function": {"name": "obtener_calificaciones", "arguments": {"course_id": 99, "activity_id": 7, "student_id": 5}}}])
    res = agent(settings, ollama, traces, grades_gateway_by_id).run("¿Qué notas hay?", 2, TOKEN, "3", "req-42")
    assert traces[0]["steps"][1]["args"] == {"course_id": 2}      # ni el curso 99, ni la actividad 7, ni el estudiante 5
    assert res.meta.status == "ok" and "2 registros de calificación" in res.answer.facts[0].text


def test_the_planner_does_not_see_the_selected_course_number(settings, ollama, traces):
    ollama.reply(tool_calls=CALL)
    agent(settings, ollama, traces, lambda r: httpx.Response(200, json=COURSES)).run("¿Qué cursos tengo?", 2, TOKEN, "3", "req-42")
    assert ollama.calls[0]["messages"][1]["content"] == "¿Qué cursos tengo?"


def test_a_bare_number_never_matches_an_activity():
    from app.catalog.obtener_calificaciones import pick_activity
    ctx = ToolContext("http://gateway.test", TOKEN, "req-1", 2.0, None)
    rows = [{"activityName": "Tarea 1", "status": "graded"}, {"activityName": "Tarea 2", "status": "graded"}]
    found, error = pick_activity(ctx, rows, "2", "GET /grades")
    assert found is None and error["error"]["code"] == "ACTIVITY_NOT_FOUND" and "Tarea 1, Tarea 2" in error["error"]["message"]
    assert pick_activity(ctx, rows, "tarea 2", "GET /grades")[0] == [rows[1]]        # el nombre completo sí
    assert pick_activity(ctx, rows, "Tarea 1", "GET /grades")[0] == [rows[0]]
