"""POST /chat y /health a través de la API (con un Ollama simulado)."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.tools import ToolRegistry
from conftest import auth


@pytest.fixture
def client(make_agent):
    return TestClient(create_app(make_agent(tools=ToolRegistry())))  # sin herramientas conectadas


def test_health_reports_ollama(client, ollama):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["ollama"] == {"reachable": True, "model": "qwen3:1.7b", "modelAvailable": True}
    ollama.models = ["otro-modelo"]
    assert client.get("/health").json()["ollama"]["modelAvailable"] is False


class TestRequestValidation:
    def test_no_token_is_401_and_does_not_call_the_model(self, client, ollama):
        r = client.post("/chat", json={"message": "hola"})
        assert r.status_code == 401 and r.json()["code"] == "TOKEN_INVALID"
        assert r.headers["content-type"].startswith("application/problem+json")
        assert ollama.calls == []

    def test_expired_token_is_401(self, client):
        r = client.post("/chat", json={"message": "hola"}, headers=auth(exp_in=-10))
        assert r.status_code == 401 and r.json()["code"] == "TOKEN_EXPIRED"

    def test_token_is_checked_before_the_body(self, client):
        r = client.post("/chat", json={"message": ""})
        assert r.status_code == 401

    @pytest.mark.parametrize("body", [{"message": ""}, {"message": "   "}, {}, {"message": "hola", "courseId": 0},
                                      {"message": "hola", "courseId": "dos"}])
    def test_bad_body_is_400(self, client, body):
        r = client.post("/chat", json=body, headers=auth())
        assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"
        assert set(r.json()) >= {"title", "status", "code", "traceId"}

    def test_request_id_is_echoed(self, client):
        r = client.post("/chat", json={"message": "hola"}, headers={**auth(), "X-Request-Id": "abc-1"})
        assert r.headers["X-Request-Id"] == "abc-1"


class TestAnswers:
    def test_greeting_needs_no_model(self, client, ollama):
        r = client.post("/chat", json={"message": "Hola, ¿qué puedes hacer?"}, headers=auth())
        body = r.json()
        assert r.status_code == 200 and body["meta"]["status"] == "ok"
        assert "EduMonitor" in body["answer"]["message"] and body["answer"]["facts"] == []
        assert body["traceId"] and ollama.calls == []

    def test_out_of_scope_is_refused_with_200(self, client, ollama):
        r = client.post("/chat", json={"message": "Cambia la nota de Ana a 10"}, headers=auth())
        body = r.json()
        assert r.status_code == 200 and body["meta"]["status"] == "refused"
        assert "No puedo modificar calificaciones" in body["answer"]["unavailable"][0]
        assert ollama.calls == []

    def test_data_question_without_connected_tools_says_so(self, client, ollama):
        r = client.post("/chat", json={"message": "¿Qué cursos tengo?", "courseId": 2}, headers=auth())
        body = r.json()
        assert r.status_code == 200 and body["meta"]["status"] == "partial" and body["meta"]["courseId"] == 2
        assert body["answer"]["facts"] == []
        assert "herramientas" in body["answer"]["unavailable"][0]
        assert ollama.calls == []  # no inventa: sin herramientas, ni siquiera consulta al modelo

    def test_response_has_the_documented_shape(self, client):
        body = client.post("/chat", json={"message": "hola"}, headers=auth()).json()
        assert set(body) == {"traceId", "answer", "meta"}
        assert set(body["answer"]) == {"facts", "inferences", "recommendations", "unavailable", "message"}
        assert set(body["meta"]) == {"courseId", "lastSyncAt", "status"}


def test_cors_allows_the_react_app(client):
    r = client.options("/chat", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
                                         "Access-Control-Request-Headers": "authorization,content-type"})
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_body_that_is_not_valid_json_is_a_problem_response(client):
    """Un cuerpo en otra codificación o roto también responde en el formato Problem, no en el de FastAPI."""
    r = client.post("/chat", content='{"message":"¿Qué cursos tengo?"}'.encode("cp1252"),
                    headers={**auth(), "Content-Type": "application/json"})
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"
    assert set(r.json()) >= {"title", "status", "code", "traceId"}
    assert r.headers["content-type"].startswith("application/problem+json")
