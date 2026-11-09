import base64
import json
import time

import httpx
import pytest
from pydantic import BaseModel

from app.config import Settings
from app.graph import Agent
from app.llm import OllamaClient
from app.tools import Tool, ToolRegistry, ok_output


def b64(obj) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()


def make_token(exp_in: int = 3600, sub: str = "3") -> str:
    """JWT con la forma correcta; el agente no valida la firma (eso lo hace el gateway)."""
    return f"{b64({'alg': 'HS256', 'typ': 'JWT'})}.{b64({'sub': sub, 'exp': int(time.time()) + exp_in})}.firma"


def auth(exp_in: int = 3600) -> dict:
    return {"Authorization": f"Bearer {make_token(exp_in)}"}


@pytest.fixture
def settings():
    return Settings(ollama_url="http://ollama.test", model="qwen3:1.7b", gateway_url="http://gateway.test",
                    keep_alive="1m", max_tool_calls=5, tool_timeout_s=2.0, message_timeout_s=30.0,
                    cors_origins=("http://localhost:5173",))


class FakeOllama:
    """Ollama simulado: responde en orden con lo que se le programe y guarda cada petición."""

    def __init__(self):
        self.replies: list = []
        self.calls: list = []
        self.models = ["qwen3:1.7b"]

    def reply(self, content: str = "", tool_calls: list | None = None):
        self.replies.append({"message": {"role": "assistant", "content": content, "tool_calls": tool_calls or []},
                             "total_duration": 1_500_000_000})

    def fail(self, status: int = 500):
        self.replies.append(status)

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": m} for m in self.models]})
        self.calls.append(json.loads(request.content))
        item = self.replies.pop(0)
        if isinstance(item, int):
            return httpx.Response(item, json={"error": "falla simulada"})
        return httpx.Response(200, json=item)

    def client(self, settings) -> OllamaClient:
        return OllamaClient(settings, transport=httpx.MockTransport(self.handler))


class NoArgs(BaseModel):
    pass


class CourseArgs(BaseModel):
    course_id: int


def fake_tools(output=None) -> ToolRegistry:
    """Dos herramientas de prueba que no llaman a ninguna red."""
    courses = output or {"courses": [{"id": 2, "shortName": "PRUEBA01", "fullName": "Curso de Prueba EduMonitor",
                                      "studentCount": 5, "lastSyncAt": "2026-10-22T15:04:05Z"}], "total": 1}
    return ToolRegistry([
        Tool("listar_cursos", "Lista los cursos del docente.", NoArgs,
             lambda ctx, args: ok_output(courses, "GET /api/v1/courses", ctx.request_id)),
        Tool("obtener_progreso", "Indicadores de un curso.", CourseArgs,
             lambda ctx, args: ok_output({"courseId": args.course_id, "averageScore10": {"value": 5.5}},
                                         f"GET /api/v1/courses/{args.course_id}/analytics", ctx.request_id)),
    ])


@pytest.fixture
def ollama():
    return FakeOllama()


@pytest.fixture
def traces():
    return []


@pytest.fixture
def make_agent(settings, ollama, traces):
    def build(tools=None):
        return Agent(settings, ollama.client(settings), tools if tools is not None else fake_tools(),
                     trace_sink=traces.append)
    return build
