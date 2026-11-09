# gateway-mock

**Responsable:** Juan

Servidor mock del api-gateway (contrato `docs/contracts/api-gateway.v1.yaml`, v1.1.0). Responde con datos
ficticios para que la interfaz y el agente se desarrollen sin esperar al backend real. Tiene las 13 operaciones
de las 12 rutas del contrato, con los mismos errores (formato Problem, RFC 7807).

## Cómo ejecutarlo

Requiere Python 3.11 o superior (probado con 3.13).

```powershell
cd mocks/gateway-mock
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m uvicorn app.main:app --port 5000 --reload
```

- Documentación interactiva (probar rutas con «Try it out»): <http://localhost:5000/docs>
- Estado: <http://localhost:5000/health>
- El puerto 5000 es el del api-gateway en la tabla de puertos de los contratos, así que quien use el mock solo
  cambia la dirección base cuando pase al gateway real.

## Cómo entrar

| Usuario | Correo | Rol | Cursos |
|---|---|---|---|
| Docente Prueba (id 3) | `docente1@example.com` | teacher | 2 y 3 |
| Docente Dos (id 9) | `docente2@example.com` | teacher | 4 |
| Administrador (id 1) | `admin@example.com` | admin | ninguno (la restricción del rol admin es un supuesto del MVP) |

Contraseña de todos: `Prueba123!` (solo para el mock; se puede cambiar con la variable `MOCK_PASSWORD`).

1. `POST /api/v1/auth/login` devuelve un JWT (`accessToken`).
2. En `/docs`, pulsa **Authorize** y pega el token. Desde otro cliente, envía `Authorization: Bearer <token>`.

## Datos

Todo es ficticio y sale de `data/dataset.json`.

| Curso | Qué es |
|---|---|
| **2 · PRUEBA01** | Es el curso de la evidencia S1-06 del Moodle de laboratorio: mismos ids de curso, estudiantes (4 a 8), Tarea 1 (cmid 2, sobre 10) y Tarea 2 (cmid 3, sobre 100). Ya está sincronizado. |
| **3 · PRUEBA02** | Nunca sincronizado, con 3 estudiantes. Las lecturas responden 503 `DATA_NOT_AVAILABLE` hasta que se llama a `POST /sync`; entonces aparecen los datos. |
| **4 · PRUEBA03** | Del docente 2. Sirve para probar el 403 `COURSE_NOT_AUTHORIZED` con el docente 1. |

El curso 2 cubre los casos que el contrato pide distinguir: nota cero (estudiante 5), entregado y pendiente de
calificar (6), sin entrega (7), borrador sin enviar (4, Tarea 2) y una actividad sin seguimiento de finalización (7, Tarea 2).

Los indicadores, las alertas y el informe **se calculan** a partir de esos datos con las fórmulas de
`docs/analytics-rules/reglas-iniciales.md`, por lo que son coherentes entre sí. Para el curso 2:
promedio 5,5 sobre 10, tasa de entrega 50 %, tasa de calificación 80 %, finalización 44,44 % (parcial),
pendientes de calificar 10 % y 12 alertas activas.

## Fallas a pedido

Cualquier ruta `/api/v1/...` (menos el login) acepta estos encabezados:

| Encabezado | Efecto |
|---|---|
| `X-Mock-Error: <CÓDIGO>` | Responde ese error del contrato. Códigos: `TOKEN_INVALID`, `TOKEN_EXPIRED`, `COURSE_NOT_AUTHORIZED`, `COURSE_NOT_FOUND`, `STUDENT_NOT_FOUND`, `SYNC_IN_PROGRESS`, `MOODLE_UNAVAILABLE`, `DATA_NOT_AVAILABLE`, `VALIDATION_ERROR` |
| `X-Mock-Delay: <ms>` | Espera esos milisegundos antes de responder (máximo 30 000) |
| `X-Request-Id: <valor>` | Se devuelve igual y aparece como `traceId` en los errores |

Ejemplo: `curl -H "Authorization: Bearer <token>" -H "X-Mock-Error: MOODLE_UNAVAILABLE" http://localhost:5000/api/v1/courses/2/students`

## Utilidades del mock (no son del contrato)

- `POST /_mock/token` con `{"userId": 3, "expiresIn": -10}` genera un token, por ejemplo uno ya vencido.
- `POST /_mock/reset` restablece los datos y las sincronizaciones.
- La sincronización simulada dura `MOCK_SYNC_SECONDS` segundos (3 por defecto).

## Pruebas

```powershell
.\.venv\Scripts\python -m pytest
```

- `tests/test_contract.py` valida cada respuesta contra el contrato OpenAPI (incluidos los esquemas de
  `analytics.v1.yaml`) y comprueba que todas las rutas del contrato existen en el mock.
  **Si el contrato cambia y el mock no se actualiza en la misma PR, esta prueba falla.**
- `tests/test_behavior.py` comprueba los estados de las calificaciones, las fórmulas, las alertas, el control
  de acceso y la sincronización.

## Límites

- No valida contraseñas reales ni firmas de un emisor real; la clave del JWT es de pruebas (`MOCK_JWT_SECRET`).
- Los datos son de solo lectura, salvo el estado de la sincronización; no hay alertas resueltas.
- No habla con Moodle ni con la base de datos.
- Falta su `Dockerfile` y su entrada en `docker-compose.yml`, que está a cargo de Gabriel.
