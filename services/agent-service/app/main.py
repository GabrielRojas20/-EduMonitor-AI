"""agent-service: API del agente de IA (FastAPI). `POST /chat` recibe la pregunta del docente con su JWT."""
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import get_settings
from .errors import ApiError
from .graph import Agent
from .llm import OllamaClient
from .schemas import ChatRequest, ChatResponse
from .security import check_token
from .toolset import default_registry

PROBLEM_JSON = "application/problem+json"
bearer = HTTPBearer(auto_error=False, description="JWT del docente (el mismo que devuelve el login del gateway)")


def create_app(agent: Agent | None = None) -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="EduMonitor AI · agent-service",
        version="0.1.0",
        description=("Agente de IA que consulta datos del curso a través del api-gateway, con el JWT del docente. "
                     "Separa **hechos**, **inferencias** y **recomendaciones**, y no inventa datos."),
    )
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"],
                       allow_headers=["*"], expose_headers=["X-Request-Id"])
    llm = OllamaClient(settings) if agent is None else agent.llm
    app.state.agent = agent or Agent(settings, llm, default_registry())

    def trace_id(request: Request) -> str:
        return getattr(request.state, "request_id", uuid.uuid4().hex)

    @app.middleware("http")
    async def request_id_header(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        return response

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return JSONResponse(exc.body(trace_id(request)), status_code=exc.status, media_type=PROBLEM_JSON)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", []) if p != "body") or "solicitud"
        err = ApiError("VALIDATION_ERROR", f"Parámetro inválido: {where}. {first.get('msg', '')}".strip())
        return JSONResponse(err.body(trace_id(request)), status_code=err.status, media_type=PROBLEM_JSON)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 400:  # cuerpo que no es JSON válido en UTF-8
            err = ApiError("VALIDATION_ERROR", "El cuerpo de la petición no es un JSON válido en UTF-8.")
            return JSONResponse(err.body(trace_id(request)), status_code=err.status, media_type=PROBLEM_JSON)
        return await http_exception_handler(request, exc)

    def authenticate(request: Request, _credentials=Depends(bearer)):
        # Se comprueba antes que el cuerpo: sin token válido no se llama al modelo ni a las herramientas.
        return check_token(request.headers.get("Authorization"))

    @app.get("/health", tags=["agent"], summary="El servicio está vivo y Ollama responde")
    def health():
        return {"status": "ok", "service": "agent-service", "ollama": app.state.agent.llm.status()}

    @app.post("/chat", tags=["agent"], response_model=ChatResponse, summary="Pregunta del docente al agente")
    def chat(body: ChatRequest, request: Request, auth=Depends(authenticate)):
        token, teacher_id = auth
        return app.state.agent.run(body.message, body.courseId, token, teacher_id, trace_id(request))

    return app


app = create_app()
