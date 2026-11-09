# api-gateway

**Responsable:** Mikel

Único punto de entrada de EduMonitor AI (puerto 5000). Valida el JWT, comprueba el acceso al curso y reenvía a los servicios internos con YARP. Contrato: `docs/contracts/api-gateway.v1.yaml`.

## Qué hace

1. **Valida el JWT** (firma, vencimiento, emisor y audiencia). Sin token o con token inválido responde 401 `TOKEN_INVALID`; vencido, 401 `TOKEN_EXPIRED`.
2. **Comprueba el curso:** antes de enrutar `/api/v1/courses/{courseId}/...` llama a auth-courses `GET /internal/courses/{courseId}/access` con el JWT del docente. 403 `COURSE_NOT_AUTHORIZED` si el curso no es suyo, 404 `COURSE_NOT_FOUND` si no existe. Si no pasa, la petición no llega al servicio.
3. **Enruta** según la tabla de abajo. Las rutas `/internal/...` no se publican.
4. **Servicio caído:** 503 `MOODLE_UNAVAILABLE` con el formato Problem.
5. **CORS** solo para `CORS_ALLOWED_ORIGINS` (por defecto `http://localhost:5173`).
6. **X-Request-Id:** se genera si no llega, se reenvía a los servicios y vuelve en la respuesta. El token no se escribe en los registros.

## Rutas

| Ruta pública | Servicio | Ruta interna |
|---|---|---|
| `POST /api/v1/auth/login` (sin token) | auth-courses | `/auth/login` |
| `GET /api/v1/me` | auth-courses | `/users/me` |
| `GET /api/v1/courses` y `/courses/{id}` | auth-courses | `/courses` y `/courses/{id}` |
| `/api/v1/courses/{id}/students`, `/grades`, `/sync` | moodle-sync | misma ruta sin `/api/v1` |
| `/api/v1/courses/{id}/analytics/...` | analytics | misma ruta, con `/api/v1` |

Pendiente: la ruta del chat hacia agent-service (el contrato del gateway aún no la define).

## Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `JWT_SECRET` | Sí | El mismo secreto que auth-courses (mínimo 32 caracteres) |
| `JWT_ISSUER` / `JWT_AUDIENCE` | No | Por defecto `edumonitor` y `edumonitor-api` |
| `CORS_ALLOWED_ORIGINS` | No | Orígenes del front, separados por coma |
| `ReverseProxy__Clusters__auth__Destinations__d1__Address` | No | Por defecto `http://localhost:5001/` |
| `ReverseProxy__Clusters__sync__Destinations__d1__Address` | No | Por defecto `http://localhost:5002/` |
| `ReverseProxy__Clusters__analytics__Destinations__d1__Address` | No | Por defecto `http://localhost:5003/` |

## Ejecutar y probar

```bash
export JWT_SECRET="una-clave-larga-de-al-menos-32-caracteres"
dotnet run --project src/ApiGateway
dotnet test tests/ApiGateway.Tests
```
