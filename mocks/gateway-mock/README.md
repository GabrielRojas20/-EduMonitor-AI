# gateway-mock

**Responsable:** Juan

Servidor mock del api-gateway (contrato `docs/contracts/api-gateway.v1.yaml`, v1.1.0). Responde con datos
ficticios para que la interfaz y el agente se desarrollen sin esperar al backend real. Tiene las 13 operaciones
de las 12 rutas del contrato, con los mismos errores (formato Problem, RFC 7807).

## Cómo tenerlo en tu computador (paso a paso)

No necesitas Docker, ni base de datos, ni Moodle: solo Git y Python.

### Antes de empezar

| Herramienta | Cómo comprobarla | Si falta |
|---|---|---|
| Git | `git --version` | Instalar desde <https://git-scm.com> |
| Python 3.11 o superior (probado con 3.13) | `python --version` | Instalar desde <https://www.python.org/downloads/> y marcar **Add Python to PATH**. En Windows también sirve `py --version`. |

### 1. Obtener el código

Si **todavía no tienes el repositorio**:

```powershell
git clone https://github.com/GabrielRojas20/-EduMonitor-AI.git EduMonitor-AI
cd EduMonitor-AI
```

El nombre de la carpeta (`EduMonitor-AI`) se escribe a propósito sin el guion inicial, porque `cd -EduMonitor-AI`
falla en la terminal. Si **ya lo tienes**, entra a su carpeta (por ejemplo `cd .\-EduMonitor-AI`) y sigue.

### 2. Ponerte en la rama correcta

Mientras el pull request del mock no se haya unido a `develop`:

```powershell
git fetch origin
git checkout feat/S2-mock-gateway
```

Cuando ya esté unido, basta con `git checkout develop` y `git pull`.

### 3. Entrar a la carpeta del mock

```powershell
cd mocks/gateway-mock
```

### 4. Crear el entorno de Python e instalar lo necesario (solo la primera vez)

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
```

macOS o Linux:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements-dev.txt
```

`requirements-dev.txt` incluye lo necesario para ejecutar el mock y para correr sus pruebas. No hace falta
«activar» el entorno: los comandos de abajo llaman directamente a su Python.

### 5. Arrancar el mock

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --port 5000
```

En macOS o Linux: `./.venv/bin/python -m uvicorn app.main:app --port 5000`.

Cuando funciona, la terminal muestra `Uvicorn running on http://127.0.0.1:5000`. **Deja esa terminal abierta**:
mientras esté abierta, el mock está funcionando.

### 6. Comprobar que funciona

1. Abre <http://localhost:5000/health>. Debe mostrar `{"status":"ok","service":"gateway-mock"}`.
2. Abre <http://localhost:5000/docs>, la documentación interactiva.
3. En `POST /api/v1/auth/login` pulsa **Try it out**, escribe `docente1@example.com` y `Prueba123!`, y pulsa **Execute**.
4. Copia el `accessToken` de la respuesta, pulsa **Authorize** (arriba a la derecha) y pégalo.
5. Prueba `GET /api/v1/courses`: debe devolver el curso `PRUEBA01`.

Desde PowerShell también sirve: `Invoke-RestMethod http://localhost:5000/health`.

### 7. Usarlo desde tu parte del proyecto

La dirección base es **`http://localhost:5000`**: la misma que tendrá el gateway real, así que más adelante solo cambia
esa dirección.

- **Interfaz (web-ui):** apunta tu variable de entorno de la API, por ejemplo `VITE_API_URL=http://localhost:5000`. El mock
  acepta llamadas desde el navegador (CORS abierto).
- **Agente u otros servicios:** usa esa dirección base y reenvía el JWT en `Authorization: Bearer <token>`.

### Apagarlo, actualizarlo y volver a arrancarlo

- **Apagar:** `Ctrl+C` en la terminal donde corre.
- **Actualizar** (cuando alguien cambie el mock o el contrato): `git pull` en la rama y arrancarlo otra vez. No hace falta
  repetir el paso 4, salvo que cambie `requirements.txt`.
- **Volver a arrancarlo otro día:** pasos 3 y 5.
- **Dejar los datos como al inicio:** reiniciarlo, o llamar a `POST /_mock/reset`.

### Si algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `python` no se reconoce | Python no está instalado o no está en el PATH | Reinstalarlo marcando **Add Python to PATH**, o usar `py -m venv .venv` |
| `Address already in use` o `error while attempting to bind` | Otro programa usa el puerto 5000 | Arrancar en otro puerto (`--port 5001`) y usar `http://localhost:5001` como dirección base |
| `No module named 'fastapi'` | No se instalaron las dependencias o se usó otro Python | Repetir el paso 4 y arrancar con `.\.venv\Scripts\python`, no con `python` a secas |
| `/docs` abre pero devuelve 401 | Falta el token | Hacer login y pulsar **Authorize** (paso 6) |
| El navegador muestra un error de CORS | Se está llamando a otra dirección o el mock no está encendido | Comprobar que el mock corre y que la dirección base es la del mock |
| `cd -EduMonitor-AI` falla | El nombre de la carpeta empieza con un guion | Usar `cd .\-EduMonitor-AI` o clonar con otro nombre (paso 1) |

## Atajo para quien ya lo tiene instalado

```powershell
cd mocks/gateway-mock
.\.venv\Scripts\python -m uvicorn app.main:app --port 5000 --reload
```

`--reload` reinicia el mock solo cuando cambian los archivos; es útil si lo estás modificando.

- Documentación interactiva: <http://localhost:5000/docs>
- Estado: <http://localhost:5000/health>
- El puerto 5000 es el del api-gateway en la tabla de puertos de los contratos.

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
- `MOCK_DATASET` arranca el mock con otro archivo de datos. `data/dataset-hostil.json` es una copia con instrucciones escondidas en un nombre de curso y de actividad; sirve para el escenario de seguridad `S03` de `evaluation/agent-scenarios`.

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
- Tiene CORS abierto a cualquier origen para que la interfaz lo llame desde el navegador; el gateway real lo restringe.
- Los datos son de solo lectura, salvo el estado de la sincronización; no hay alertas resueltas.
- No habla con Moodle ni con la base de datos.
- Falta su `Dockerfile` y su entrada en `docker-compose.yml`, que está a cargo de Gabriel.
