"""El mock debe cumplir el contrato docs/contracts/api-gateway.v1.yaml.

Si alguien cambia el contrato (rutas, campos o errores) y el mock no se actualiza en la misma PR,
estas pruebas fallan.
"""
import jsonschema
import pytest

from app.main import app
from openapi_loader import operations, response_schema


def test_every_contract_operation_exists_in_the_mock():
    mock_routes = {(r.path, m.lower()) for r in app.routes if hasattr(r, "methods") for m in r.methods}
    missing = [f"{m.upper()} {p}" for p, m in operations() if (p, m) not in mock_routes]
    assert not missing, f"Faltan en el mock rutas del contrato: {missing}"


def validate(client, method, template, path, status, headers=None, json=None, params=None):
    r = client.request(method, path, headers=headers, json=json, params=params)
    assert r.status_code == status, f"{method.upper()} {path} -> {r.status_code}: {r.text}"
    media = r.headers["content-type"].split(";")[0]
    schema = response_schema(template, method, status, media)
    assert schema is not None, f"El contrato no documenta {status} en {method.upper()} {template}"
    jsonschema.Draft7Validator(schema).validate(r.json())
    return r


C = "/api/v1/courses"
# (método, ruta del contrato, ruta concreta, estado esperado, quién llama, parámetros)
OK_CASES = [
    ("get", "/api/v1/me", "/api/v1/me", 200, "t1", None),
    ("get", C, C, 200, "t1", None),
    ("get", C + "/{courseId}", C + "/2", 200, "t1", None),
    ("get", C + "/{courseId}/students", C + "/2/students", 200, "t1", {"page": 1, "pageSize": 3}),
    ("get", C + "/{courseId}/students/{studentId}", C + "/2/students/4", 200, "t1", None),
    ("get", C + "/{courseId}/grades", C + "/2/grades", 200, "t1", None),
    ("get", C + "/{courseId}/grades", C + "/2/grades", 200, "t1", {"studentId": 5, "activityId": 3}),
    ("get", C + "/{courseId}/sync", C + "/2/sync", 200, "t1", None),
    ("get", C + "/{courseId}/sync", C + "/3/sync", 200, "t1", None),
    ("post", C + "/{courseId}/sync", C + "/3/sync", 202, "t1", None),
    ("get", C + "/{courseId}/analytics", C + "/2/analytics", 200, "t1", None),
    ("get", C + "/{courseId}/analytics/students/{studentId}", C + "/2/analytics/students/6", 200, "t1", None),
    ("get", C + "/{courseId}/analytics/alerts", C + "/2/analytics/alerts", 200, "t1", None),
    ("get", C + "/{courseId}/analytics/alerts", C + "/2/analytics/alerts", 200, "t1", {"severity": "info", "studentId": 6}),
    ("get", C + "/{courseId}/analytics/report", C + "/2/analytics/report", 200, "t1", None),
]
ERROR_CASES = [
    ("get", C + "/{courseId}", C + "/99", 404, "t1", None),
    ("get", C + "/{courseId}", C + "/4", 403, "t1", None),
    ("get", C + "/{courseId}/students/{studentId}", C + "/2/students/99", 404, "t1", None),
    ("get", C + "/{courseId}/students", C + "/3/students", 503, "t1", None),  # curso sin sincronizar
    ("get", C + "/{courseId}/analytics", C + "/3/analytics", 503, "t1", None),
    ("get", C + "/{courseId}/analytics/alerts", C + "/2/analytics/alerts", 400, "t1", {"severity": "mala"}),
    ("get", C + "/{courseId}/analytics/alerts", C + "/2/analytics/alerts", 400, "t1", {"page": 0}),
    ("get", "/api/v1/me", "/api/v1/me", 401, "none", None),
    ("get", C, C, 401, "bad", None),
    ("get", C, C, 401, "expired", None),
]


def headers_for(who, client, teacher):
    if who == "t1":
        return teacher
    if who == "bad":
        return {"Authorization": "Bearer esto.no.es-un-jwt"}
    if who == "expired":
        token = client.post("/_mock/token", json={"userId": 3, "expiresIn": -10}).json()["accessToken"]
        return {"Authorization": f"Bearer {token}"}
    return {}


@pytest.mark.parametrize("method,template,path,status,who,params", OK_CASES + ERROR_CASES,
                         ids=[f"{c[0]} {c[2]} {c[3]}" + (f" {c[5]}" if c[5] else "") for c in OK_CASES + ERROR_CASES])
def test_response_matches_contract(client, teacher, method, template, path, status, who, params):
    validate(client, method, template, path, status, headers_for(who, client, teacher), params=params)


def test_login_matches_contract(client):
    ok = validate(client, "post", "/api/v1/auth/login", "/api/v1/auth/login", 200,
                  json={"email": "docente1@example.com", "password": "Prueba123!"})
    assert ok.json()["tokenType"] == "Bearer"
    validate(client, "post", "/api/v1/auth/login", "/api/v1/auth/login", 401,
             json={"email": "docente1@example.com", "password": "incorrecta"})


@pytest.mark.parametrize("code,status,method,template,path", [
    ("MOODLE_UNAVAILABLE", 503, "get", C + "/{courseId}/students", C + "/2/students"),
    ("DATA_NOT_AVAILABLE", 503, "get", C + "/{courseId}/grades", C + "/2/grades"),
    ("TOKEN_EXPIRED", 401, "get", "/api/v1/me", "/api/v1/me"),
    ("COURSE_NOT_AUTHORIZED", 403, "get", C + "/{courseId}/analytics", C + "/2/analytics"),
    ("COURSE_NOT_FOUND", 404, "get", C + "/{courseId}", C + "/2"),
    ("SYNC_IN_PROGRESS", 409, "post", C + "/{courseId}/sync", C + "/2/sync"),
    ("VALIDATION_ERROR", 400, "get", C + "/{courseId}/analytics/report", C + "/2/analytics/report"),
])
def test_injected_failures_match_contract(client, teacher, code, status, method, template, path):
    r = validate(client, method, template, path, status, headers={**teacher, "X-Mock-Error": code})
    assert r.json()["code"] == code
    assert r.headers["content-type"].startswith("application/problem+json")
