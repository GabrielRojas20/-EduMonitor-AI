"""Entrada y salida de `POST /chat` (docs/agent-design/diseno-agente.md, secciones 2.1 y 6)."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str
    courseId: int | None = Field(default=None, ge=1, description="Curso de referencia que el docente elige en el chat")

    @field_validator("message")
    @classmethod
    def not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("el mensaje no puede estar vacío")
        return value[:2000]


class Source(BaseModel):
    tool: str
    stepN: int


class Fact(BaseModel):
    text: str
    sources: list[Source] = []


class Inference(BaseModel):
    text: str
    basedOn: list[int] = []


class Recommendation(BaseModel):
    text: str
    relatedFinding: int | None = None


class Answer(BaseModel):
    facts: list[Fact] = []
    inferences: list[Inference] = []
    recommendations: list[Recommendation] = []
    unavailable: list[str] = []
    # Texto breve para saludos y ayuda (propuesta de añadido al diseño; no hay datos que citar)
    message: str | None = None


class Meta(BaseModel):
    courseId: int | None = None
    lastSyncAt: str | None = None
    status: Literal["ok", "partial", "refused", "error"]


class ChatResponse(BaseModel):
    traceId: str
    answer: Answer
    meta: Meta
