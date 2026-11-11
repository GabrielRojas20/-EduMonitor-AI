# Guía de instalación local de EduMonitor AI

**Responsable de la guía:** Gabriel
**Fecha:** 10 de noviembre de 2026
**Objetivo:** levantar el entorno local y validar el recorrido del Super Sprint 2.

## 1. Requisitos

En Windows se necesita:

- Docker Desktop iniciado y usando Linux containers.
- Git.
- PowerShell 5.1 o PowerShell 7.
- Para ejecutar el agente fuera de Docker: Python 3.11 o superior y Ollama.

No es obligatorio instalar SQL Server, MariaDB ni Moodle directamente en Windows. Docker los ejecuta en contenedores.

## 2. Descargar el repositorio

```powershell
git clone https://github.com/GabrielRojas20/-EduMonitor-AI.git
cd -EduMonitor-AI
git checkout develop
git pull origin develop
```

Si ya existe una copia local:

```powershell
git checkout develop
git pull origin develop
```

## 3. Crear la configuración local

Nunca se debe subir `.env` a GitHub. Se crea a partir del ejemplo:

```powershell
Copy-Item .env.example .env
notepad .env
```

Como mínimo, verificar que existan valores para:

```text
MSSQL_SA_PASSWORD=UnaClaveSegura123!
MSSQL_PORT=1433
JWT_SECRET=una-clave-local-de-al-menos-32-caracteres
JWT_ISSUER=edumonitor
JWT_AUDIENCE=edumonitor-api
AUTH_SEED_PASSWORD=Prueba123!
MOODLE_ADMIN_USER=admin
MOODLE_ADMIN_PASSWORD=Admin123!
MOODLE_WS_TOKEN=
```

La contraseña de `MSSQL_SA_PASSWORD` debe cumplir las reglas de SQL Server. Si el puerto 1433 está ocupado, cambiar solamente el puerto externo:

```text
MSSQL_PORT=11433
```

Dentro de Docker SQL Server continúa escuchando en `1433`; desde Windows se usaría `localhost,11433`.

El servicio del agente usa por defecto:

```text
AGENT_URL=http://localhost:5004
```

## 4. Levantar la infraestructura

Desde la raíz del repositorio:

```powershell
docker compose up -d --build
```

Ver el estado:

```powershell
docker compose ps
```

Los servicios principales del recorrido son:

| Servicio | Puerto local | Uso |
|---|---:|---|
| SQL Server | 1433 o 11433 | Persistencia |
| Moodle | 8080 | Fuente Moodle |
| Ollama | 11434 | Modelo local |
| API Gateway | 5000 | Entrada REST |
| Auth Courses | 5001 | Login y permisos |
| Moodle Sync | 5002 | Sincronización |
| Analytics | 5003 | Indicadores y alertas |
| Agent Service | 5004 | Chat del agente |

La infraestructura de SQL Server, Moodle, Auth Courses, Moodle Sync, API Gateway y Analytics ya está incluida en Compose. El `agent-service`
se ejecuta temporalmente fuera de Docker siguiendo la sección 8, porque todavía no tiene una imagen propia dentro de este Compose.

## 5. Validar la base de datos

Cuando SQL Server esté saludable, el inicializador ejecuta `services/analytics-service/database.sql`. Consultar los contenedores:

```powershell
docker compose ps sqlserver analytics-db-init
docker compose logs analytics-db-init
```

Para conectarse desde SSMS:

```text
Servidor: localhost,1433
```

Si se configuró `MSSQL_PORT=11433`:

```text
Servidor: localhost,11433
Usuario: sa
Base: EduMonitor
```

El esquema de Analytics usa `analytics.*` y la sincronización usa `sync.*`.

## 6. Pruebas rápidas

El smoke test automatizado se ejecuta así:

```powershell
.\scripts\smoke-test.ps1
```

También se puede indicar otro puerto:

```powershell
.\scripts\smoke-test.ps1 -AnalyticsUrl http://localhost:5003 -GatewayUrl http://localhost:5000
```

Prueba manual mínima de Analytics:

```powershell
curl.exe http://localhost:5003/health
curl.exe http://localhost:5003/api/v1/courses/101/analytics
curl.exe http://localhost:5003/api/v1/courses/101/analytics/alerts
curl.exe http://localhost:5003/api/v1/courses/101/analytics/report
```

Una respuesta correcta de Analytics debe tener `200` y mostrar, entre otros campos:

```json
{
  "courseId": 101,
  "averageScore10": { "unit": "score_0_10" },
  "submissionRate": { "unit": "percent" },
  "completionRate": { "unit": "percent" }
}
```

Las alertas deben explicar la regla aplicada y no deben convertir `not_available` en cero.

## 7. Flujo completo esperado

Con la infraestructura fusionada, la demostración debe seguir este orden:

1. `POST /api/v1/auth/login` en el gateway.
2. Guardar el `accessToken` solamente en memoria o en una variable local.
3. Consultar `GET /api/v1/courses` con `Authorization: Bearer <token>`.
4. Iniciar `POST /api/v1/courses/{courseId}/sync`.
5. Consultar el estado con `GET /api/v1/courses/{courseId}/sync`.
6. Leer estudiantes y calificaciones desde el gateway.
7. Consultar Analytics para indicadores y alertas.
8. Enviar una pregunta a `POST http://localhost:5004/chat` usando el mismo JWT.

Ejemplo de login:

```powershell
$login = @{ email = "docente1@example.com"; password = "Prueba123!" } | ConvertTo-Json
$response = Invoke-RestMethod -Method Post `
  -Uri http://localhost:5000/api/v1/auth/login `
  -ContentType "application/json" `
  -Body $login
$token = $response.accessToken
```

Ejemplo de consulta autenticada:

```powershell
$headers = @{ Authorization = "Bearer $token" }
Invoke-RestMethod -Headers $headers `
  http://localhost:5000/api/v1/courses
```

## 8. Ejecutar el agente fuera de Docker

Mientras el `agent-service` todavía no tenga una imagen en Compose, abrir otra terminal:

```powershell
cd services/agent-service
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
ollama pull qwen3:1.7b
$env:GATEWAY_URL="http://localhost:5000"
$env:OLLAMA_URL="http://localhost:11434"
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 5004
```

Validar:

```powershell
curl.exe http://localhost:5004/health
```

Las herramientas `listar_cursos`, `obtener_calificaciones`, `obtener_progreso` e `identificar_alertas` consultan el gateway.
La única herramienta del diseño todavía pendiente es `generar_resumen`, necesaria para los escenarios de informe `I01` e `I02`.

## 9. Ejecutar pruebas automatizadas

Analytics:

```powershell
dotnet test services/analytics-service/AnalyticsService.Tests/AnalyticsService.Tests.csproj
```

Moodle Sync:

```powershell
dotnet test services/moodle-sync-service/tests/MoodleSync.Tests/MoodleSync.Tests.csproj
```

Auth Courses:

```powershell
dotnet test services/auth-courses-service/tests/AuthCourses.Tests/AuthCourses.Tests.csproj
```

Gateway:

```powershell
dotnet test services/api-gateway/tests/ApiGateway.Tests/ApiGateway.Tests.csproj
```

Agente:

```powershell
cd services/agent-service
.\.venv\Scripts\python -m pytest
```

## 10. Problemas frecuentes

### Puerto 1433 ocupado

Cambiar `MSSQL_PORT=11433` en `.env` y recrear solamente SQL Server:

```powershell
docker compose down
docker compose up -d --build
```

### El servicio no inicia

```powershell
docker compose ps -a
docker compose logs --tail=100 analytics
```

### SQL Server todavía no está saludable

Esperar entre 30 y 60 segundos:

```powershell
docker compose logs -f sqlserver
```

### Falta `MOODLE_WS_TOKEN`

El servicio puede iniciar, pero la sincronización real devolverá `MOODLE_UNAVAILABLE` o un error de configuración. El token se obtiene desde el servicio web configurado en Moodle y nunca debe guardarse en GitHub.

### Moodle todavía está instalándose

Esperar a que el healthcheck sea `healthy` antes de iniciar Moodle Sync.

### Reiniciar todo sin borrar datos

```powershell
docker compose down
docker compose up -d
```

### Reiniciar eliminando volúmenes de desarrollo

Esto borra la base local, usuarios y datos de Moodle:

```powershell
docker compose down -v
docker compose up -d --build
```

Usar esta última opción únicamente si se desea comenzar desde cero.
