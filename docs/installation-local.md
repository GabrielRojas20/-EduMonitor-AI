# Guía de instalación local de EduMonitor AI

**Responsable:** Gabriel
**Fecha:** 11 de noviembre de 2026
**Objetivo:** levantar el entorno local y validar el recorrido del Sprint 2.

## 1. Requisitos

En Windows se necesita:

- Docker Desktop iniciado y usando Linux containers.
- Git.
- PowerShell 5.1 o PowerShell 7.
- Para ejecutar el Agent fuera de Docker: Python 3.11 o superior y Ollama.

No es necesario instalar SQL Server, MariaDB ni Moodle directamente en Windows: Docker los ejecuta en contenedores.

## 2. Descargar y configurar

```powershell
git clone https://github.com/GabrielRojas20/-EduMonitor-AI.git
cd .\-EduMonitor-AI
git switch develop
git pull origin develop
Copy-Item .env.example .env
```

Edita `.env` y completa o verifica estos valores:

- `MSSQL_SA_PASSWORD`: contraseña de SQL Server. Si se usa `MSSQL_PORT=11433`, SQL Server se abre en `localhost,11433`; dentro de Docker sigue usando `sqlserver,1433`.
- `JWT_SECRET`: secreto de al menos 32 caracteres.
- `JWT_ISSUER`, `JWT_AUDIENCE` y `JWT_EXPIRES_MINUTES`.
- `AUTH_SEED_PASSWORD`: contraseña local de los usuarios ficticios de Auth.
- `ConnectionStrings__Auth`: debe usar la misma contraseña de `MSSQL_SA_PASSWORD`.
- `MOODLE_WS_TOKEN`: token del servicio web de Moodle. Es necesario para sincronizar; no lo subas al repositorio.
- `MOODLE_WS_SERVICE`: nombre del servicio web habilitado en Moodle, si corresponde.
- `MOODLE_ADMIN_USER` y `MOODLE_ADMIN_PASSWORD`: credenciales del administrador local de Moodle.
- `MOODLE_ADMIN_EMAIL`, `MOODLE_DB_PASSWORD` y `MOODLE_DB_ROOT_PASSWORD`, si necesitas cambiar los valores de desarrollo.

El archivo `.env` es local y nunca debe subirse a GitHub.

## 3. Levantar Docker

Primera instalación o después de cambiar código o Dockerfiles:

```powershell
docker compose up -d --build
```

Ejecuciones posteriores:

```powershell
docker compose up -d
docker compose ps
```

Puertos publicados por el entorno:

- SQL Server: `1433` por defecto o `11433` si se configuró `MSSQL_PORT=11433`.
- Moodle: `8080`.
- Ollama: `11434`.
- API Gateway: `5000`.
- Auth Courses: `5001`.
- Moodle Sync: `5002`.
- Analytics: `5003`.
- Agent local: `5004`, cuando se ejecuta fuera de Docker.

`analytics-db-init` y `auth-db-init` pueden aparecer como `Exited (0)`: son inicializadores que terminaron correctamente.

## 4. Validar las bases y los servicios

Comprueba que SQL Server y los servicios estén levantados:

```powershell
docker compose ps
docker compose logs sqlserver
docker compose logs analytics-db-init
docker compose logs auth-db-init
```

En SSMS usa `localhost,11433` si configuraste ese puerto; de lo contrario usa `localhost,1433`. El usuario es `sa`, la contraseña es `MSSQL_SA_PASSWORD` y la base principal es `EduMonitor`.

Analytics debe responder HTTP 200 y conservar los indicadores en escala `score_0_10`. Los datos `not_available` no deben convertirse en cero.

## 5. Iniciar sesión y sincronizar Moodle

Los usuarios ficticios creados por Auth son:

- `docente1@edumonitor.test`: docente con acceso al curso `2` (`PRUEBA01`).
- `docente2@edumonitor.test`: docente con acceso al curso `3` (`PRUEBA02`).
- `admin@edumonitor.test`: administrador técnico sin cursos asignados.

Todos usan el valor local de `AUTH_SEED_PASSWORD`.

Para obtener un JWT desde PowerShell:

```powershell
$login = Invoke-RestMethod -Method Post `
  -Uri http://localhost:5000/api/v1/auth/login `
  -ContentType 'application/json' `
  -Body (@{
    email = 'docente1@edumonitor.test'
    password = $env:AUTH_SEED_PASSWORD
  } | ConvertTo-Json)

$token = $login.accessToken
```

Con ese token se puede iniciar una sincronización del curso autorizado. El token de Moodle debe estar configurado en `MOODLE_WS_TOKEN` antes de levantar Docker:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://localhost:5000/api/v1/courses/2/sync `
  -Headers @{ Authorization = "Bearer $token" }

Invoke-RestMethod -Method Get `
  -Uri http://localhost:5000/api/v1/courses/2/sync `
  -Headers @{ Authorization = "Bearer $token" }
```

La primera respuesta confirma que la sincronización fue aceptada. La segunda muestra su estado: `never`, `running`, `succeeded` o `failed`.

## 6. Smoke test y validación de Analytics

Ejecuta el smoke test desde la raíz del repositorio:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1 -RequireGateway
```

El resultado esperado es que los endpoints de Analytics estén correctos. Los checks de Gateway, Auth, Moodle Sync y Agent pueden omitirse si el servicio correspondiente todavía no está disponible; usa `-RunAgentHealth` cuando el Agent ya esté iniciado.

También puedes comprobar Analytics directamente:

```powershell
curl.exe http://localhost:5003/health
curl.exe http://localhost:5003/api/v1/courses/101/analytics
curl.exe "http://localhost:5003/api/v1/courses/101/analytics/alerts?page=1&pageSize=20"
curl.exe http://localhost:5003/api/v1/courses/101/analytics/report
```

## 7. Agent opcional fuera de Docker

El Agent no se levanta con el `docker-compose.yml` actual. Para ejecutarlo localmente, deja Docker y Ollama iniciados y abre otra ventana de PowerShell:

```powershell
cd .\services\agent-service
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
ollama pull qwen3:1.7b

$env:GATEWAY_URL = 'http://localhost:5000'
$env:OLLAMA_URL = 'http://localhost:11434'
$env:AGENT_MODEL = 'qwen3:1.7b'

.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 5004
```

El Agent lee `OLLAMA_URL` y `AGENT_MODEL`; no usa `OLLAMA_BASE_URL` ni `OLLAMA_MODEL`. El host `127.0.0.1` evita exponerlo innecesariamente a la red local.

Sus cinco herramientas son `listar_cursos`, `obtener_calificaciones`, `obtener_progreso`, `identificar_alertas` y `generar_resumen`.

Puedes comprobarlo con:

```powershell
curl.exe http://localhost:5004/health
```

## 8. Pruebas automatizadas

Para probar el Agent con Ollama simulado:

```powershell
cd .\services\agent-service
.\.venv\Scripts\python.exe -m pytest -q
```

Para probar los servicios .NET desde la raíz:

```powershell
dotnet test services/analytics-service/AnalyticsService.Tests/AnalyticsService.Tests.csproj
dotnet test services/auth-courses-service/tests/AuthCourses.Tests/AuthCourses.Tests.csproj
dotnet test services/moodle-sync-service/tests/MoodleSync.Tests/MoodleSync.Tests.csproj
dotnet test services/api-gateway/tests/ApiGateway.Tests/ApiGateway.Tests.csproj
```

## 9. Problemas frecuentes

- **SQL Server todavía no está saludable:** espera unos segundos y revisa `docker compose logs sqlserver`. Los inicializadores dependen de que SQL Server acepte conexiones.
- **Moodle todavía se está instalando:** revisa `docker compose logs moodle` y espera a que el servicio responda en `http://localhost:8080`.
- **Un inicializador aparece como `Exited (0)`:** es normal; significa que terminó correctamente.
- **El Agent aparece omitido en el smoke test:** es opcional y se ejecuta fuera de Docker. Inícialo siguiendo la sección 7 y usa `-RunAgentHealth`.
- **El puerto 1433 está ocupado:** configura `MSSQL_PORT=11433` en `.env` y usa `localhost,11433` desde Windows.
- **Hay un conflicto de nombres de contenedor:** ejecuta `docker compose down` y luego `docker compose up -d`. No uses `docker compose down -v` salvo que quieras borrar los volúmenes y los datos locales.
- **La sincronización falla:** verifica `MOODLE_WS_TOKEN`, `MOODLE_WS_SERVICE`, que Moodle esté disponible y que el token JWT corresponda a un docente autorizado para ese curso.

## 10. Después de un merge

```powershell
git switch develop
git pull origin develop
docker compose up -d --build
docker compose ps
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1 -RequireGateway
```

No borres los volúmenes para una actualización normal. Usa `docker compose down -v` únicamente si quieres reiniciar por completo las bases locales y los datos de Moodle.
