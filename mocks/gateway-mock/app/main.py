"""gateway-mock: servidor simulado del api-gateway (docs/contracts/api-gateway.v1.yaml).

Responde con datos ficticios coherentes (curso 2 de la evidencia S1-06). No valida firmas reales
ni habla con Moodle: sirve para desarrollar y probar el agente y la interfaz sin el backend real.
"""
import asyncio
import uuid

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from . import analytics
from .auth import create_token, decode_token
from .errors import PROBLEMS, ApiError
from .store import store

PROBLEM_JSON = "application/problem+json"
ALERT_SEVERITIES = {"info", "warning", "critical"}
ALERT_STATUSES = {"active", "resolved"}

app = FastAPI(
    title="EduMonitor AI · gateway-mock",
    version="1.1.0-mock",
    description=(
        "Servidor simulado del api-gateway (contrato v1.1.0). Datos ficticios.\n\n"
        "**Cómo entrar:** `POST /api/v1/auth/login` con `docente1@example.com` y la contraseña `Prueba123!`, "
        "y pulsa **Authorize** con el `accessToken`.\n\n"
        "**Fallas a pedido:** envía el encabezado `X-Mock-Error` con un código del contrato "
        "(por ejemplo `MOODLE_UNAVAILABLE`) en cualquier ruta `/api/v1/...`. `X-Mock-Delay` añade una espera en milisegundos."
    ),
)
bearer = HTTPBearer(auto_error=False, description="JWT que devuelve /api/v1/auth/login")

# La interfaz React llama al mock desde el navegador (otro origen, con Authorization): hace falta CORS abierto.
# El gateway real restringe el origen; el mock no, porque solo corre en el computador de cada integrante.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
                   expose_headers=["X-Request-Id"])


# ---------------------------------------------------------------- errores y encabezados
def trace_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def problem(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(exc.body(trace_id(request)), status_code=exc.status, media_type=PROBLEM_JSON,
                        headers={"X-Request-Id": trace_id(request)})


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return problem(request, exc)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    return problem(request, ApiError("VALIDATION_ERROR", f"Parámetro inválido: {where or 'solicitud'}. {first.get('msg', '')}".strip()))


@app.middleware("http")
async def request_id_header(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-Id"] = request.state.request_id
    return response


# ---------------------------------------------------------------- autorización
async def guard(request: Request, course_id=None, need_data=False, student_id=None):
    """Aplica en orden: espera simulada, falla inyectada, token, acceso al curso y disponibilidad de datos."""
    delay = request.headers.get("X-Mock-Delay")
    if delay and delay.isdigit():
        await asyncio.sleep(min(int(delay), 30000) / 1000)

    injected = (request.headers.get("X-Mock-Error") or "").strip().upper()
    if injected:
        if injected not in PROBLEMS or injected == "INVALID_CREDENTIALS":
            raise ApiError("VALIDATION_ERROR", f"X-Mock-Error desconocido: {injected}. Valores: {', '.join(sorted(PROBLEMS))}.")
        raise ApiError(injected, "Falla simulada con el encabezado X-Mock-Error.")

    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer ") or not header[7:].strip():
        raise ApiError("TOKEN_INVALID", "Falta el encabezado Authorization: Bearer <JWT>.")
    claims = decode_token(header[7:].strip())
    user = store.users.get(int(claims["sub"]))
    if user is None:
        raise ApiError("TOKEN_INVALID", "El usuario del token no existe.")

    course = None
    if course_id is not None:
        course = store.course(course_id)
        if course is None:
            raise ApiError("COURSE_NOT_FOUND", f"No existe el curso {course_id}.")
        if not store.has_access(user, course):
            raise ApiError("COURSE_NOT_AUTHORIZED", f"El usuario {user['id']} no tiene acceso al curso {course_id}.")
        if need_data and not store.is_synced(course):
            raise ApiError("DATA_NOT_AVAILABLE", "El curso aún no se sincronizó. Sincronícelo (POST /sync) y vuelva a intentar.")
        if student_id is not None and student_id not in {s["id"] for s in course["students"]}:
            raise ApiError("STUDENT_NOT_FOUND", f"El estudiante {student_id} no está matriculado en el curso {course_id}.")
    return user, course


def paginate(items: list, page: int, page_size: int) -> dict:
    start = (page - 1) * page_size
    return {"items": items[start:start + page_size], "page": page, "pageSize": page_size, "total": len(items)}


PAGE = Query(1, ge=1)
PAGE_SIZE = Query(50, ge=1, le=200)


def course_dto(course: dict) -> dict:
    out = {"id": course["id"], "shortName": course["shortName"], "fullName": course["fullName"],
           "lastSyncAt": course["lastSyncAt"]}
    if course["synced"]:
        out["studentCount"] = len(course["students"])
    return out


def check_snapshot(course: dict, snapshot_id):
    sync_id = store.sync_id(course["id"])
    current = analytics.snapshot(course, "complete", sync_id)["snapshotId"]
    if snapshot_id and snapshot_id != current:
        raise ApiError("VALIDATION_ERROR", f"snapshotId desconocido. El único disponible es {current}.")
    return sync_id


# ---------------------------------------------------------------- auth
class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/v1/auth/login", tags=["auth"], summary="Iniciar sesión")
async def login(body: LoginRequest):
    user = store.user_by_email(body.email)
    if user is None or body.password != store.password:
        raise ApiError("INVALID_CREDENTIALS", "Correo o contraseña incorrectos.")
    return {"accessToken": create_token(user, 3600), "tokenType": "Bearer", "expiresIn": 3600,
            "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}}


@app.get("/api/v1/me", tags=["auth"], summary="Usuario del token")
async def get_me(request: Request, _=Depends(bearer)):
    user, _c = await guard(request)
    return {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}


# ---------------------------------------------------------------- cursos
@app.get("/api/v1/courses", tags=["courses"], summary="Cursos a los que el docente tiene acceso")
async def list_courses(request: Request, _=Depends(bearer)):
    user, _c = await guard(request)
    return [course_dto(c) for c in store.courses_for(user)]


@app.get("/api/v1/courses/{courseId}", tags=["courses"], summary="Detalle de un curso")
async def get_course(courseId: int, request: Request, _=Depends(bearer)):
    _u, course = await guard(request, courseId)
    return course_dto(course)


@app.get("/api/v1/courses/{courseId}/students", tags=["courses"], summary="Estudiantes matriculados")
async def list_students(courseId: int, request: Request, page: int = PAGE, pageSize: int = PAGE_SIZE, _=Depends(bearer)):
    _u, course = await guard(request, courseId, need_data=True)
    students = sorted(course["students"], key=lambda s: s["id"])
    return paginate(students, page, pageSize)


@app.get("/api/v1/courses/{courseId}/students/{studentId}", tags=["courses"], summary="Ficha del estudiante con sus calificaciones")
async def get_student(courseId: int, studentId: int, request: Request, _=Depends(bearer)):
    _u, course = await guard(request, courseId, need_data=True, student_id=studentId)
    student = next(s for s in course["students"] if s["id"] == studentId)
    return {"student": student, "grades": analytics.grade_entries(course, student_id=studentId),
            "activities": analytics.activity_progress(course, studentId)}


@app.get("/api/v1/courses/{courseId}/grades", tags=["courses"], summary="Calificaciones por estudiante y actividad, con su estado")
async def list_grades(courseId: int, request: Request, page: int = PAGE, pageSize: int = PAGE_SIZE,
                      studentId: int | None = None, activityId: int | None = None, _=Depends(bearer)):
    _u, course = await guard(request, courseId, need_data=True)
    return paginate(analytics.grade_entries(course, studentId, activityId), page, pageSize)


# ---------------------------------------------------------------- sincronización
@app.post("/api/v1/courses/{courseId}/sync", tags=["sync"], status_code=202, summary="Sincronizar el curso con Moodle (manual)")
async def start_sync(courseId: int, request: Request, _=Depends(bearer)):
    await guard(request, courseId)
    sync_id = store.start_sync(courseId)
    if sync_id is None:
        raise ApiError("SYNC_IN_PROGRESS", "Ya hay una sincronización en curso para este curso.")
    return {"syncId": sync_id, "state": "running"}


@app.get("/api/v1/courses/{courseId}/sync", tags=["sync"], summary="Estado y fecha de la última sincronización")
async def get_sync_status(courseId: int, request: Request, _=Depends(bearer)):
    await guard(request, courseId)
    return store.sync_status(courseId)


# ---------------------------------------------------------------- analytics
@app.get("/api/v1/courses/{courseId}/analytics", tags=["indicators"], summary="Indicadores calculados del curso")
async def get_course_analytics(courseId: int, request: Request, snapshotId: str | None = None, _=Depends(bearer)):
    _u, course = await guard(request, courseId, need_data=True)
    return analytics.course_analytics(course, check_snapshot(course, snapshotId))


@app.get("/api/v1/courses/{courseId}/analytics/students/{studentId}", tags=["indicators"], summary="Indicadores de un estudiante del curso")
async def get_student_analytics(courseId: int, studentId: int, request: Request, snapshotId: str | None = None, _=Depends(bearer)):
    _u, course = await guard(request, courseId, need_data=True, student_id=studentId)
    return analytics.student_analytics(course, studentId, check_snapshot(course, snapshotId))


@app.get("/api/v1/courses/{courseId}/analytics/alerts", tags=["alerts"], summary="Alertas explicables del curso")
async def list_course_alerts(courseId: int, request: Request, snapshotId: str | None = None, studentId: int | None = None,
                             severity: str | None = None, status: str = "active",
                             page: int = PAGE, pageSize: int = PAGE_SIZE, _=Depends(bearer)):
    _u, course = await guard(request, courseId, need_data=True)
    if severity is not None and severity not in ALERT_SEVERITIES:
        raise ApiError("VALIDATION_ERROR", f"severity debe ser uno de {sorted(ALERT_SEVERITIES)}.")
    if status not in ALERT_STATUSES:
        raise ApiError("VALIDATION_ERROR", f"status debe ser uno de {sorted(ALERT_STATUSES)}.")
    sync_id = check_snapshot(course, snapshotId)
    alerts = analytics.course_alerts(course, sync_id) if status == "active" else []  # el mock no tiene alertas resueltas
    if studentId is not None:
        alerts = [a for a in alerts if a["studentId"] == studentId]
    if severity is not None:
        alerts = [a for a in alerts if a["severity"] == severity]
    return paginate(alerts, page, pageSize)


@app.get("/api/v1/courses/{courseId}/analytics/report", tags=["reports"], summary="Datos calculados para el informe del curso")
async def get_course_report(courseId: int, request: Request, snapshotId: str | None = None, _=Depends(bearer)):
    _u, course = await guard(request, courseId, need_data=True)
    return analytics.report_data(course, check_snapshot(course, snapshotId))


# ---------------------------------------------------------------- utilidades del mock (no son del contrato)
class MockToken(BaseModel):
    userId: int
    expiresIn: int = 3600


@app.get("/health", tags=["mock"], summary="El mock está vivo")
async def health():
    return {"status": "ok", "service": "gateway-mock"}


@app.post("/_mock/token", tags=["mock"], summary="Genera un token de prueba (usa expiresIn negativo para uno vencido)")
async def mock_token(body: MockToken):
    user = store.users.get(body.userId)
    if user is None:
        raise ApiError("VALIDATION_ERROR", f"No existe el usuario {body.userId}. Usuarios: {sorted(store.users)}.")
    return {"accessToken": create_token(user, body.expiresIn), "tokenType": "Bearer", "expiresIn": body.expiresIn}


@app.post("/_mock/reset", tags=["mock"], summary="Restablece los datos y las sincronizaciones")
async def mock_reset():
    store.reset()
    return {"status": "reset"}
