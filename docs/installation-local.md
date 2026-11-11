# Guía de instalación local de EduMonitor AI

Responsable: Gabriel. Fecha: 11 de noviembre de 2026.

## Requisitos
Docker Desktop con Linux containers, Git y PowerShell. Docker ejecuta SQL Server, MariaDB y Moodle. Para el Agent fuera de Docker: Python 3.11+ y Ollama.

## Descargar y configurar

    git clone https://github.com/GabrielRojas20/-EduMonitor-AI.git
    cd .\-EduMonitor-AI
    git switch develop
    git pull origin develop
    Copy-Item .env.example .env

En .env verifica MSSQL_SA_PASSWORD, MSSQL_PORT=11433, JWT_SECRET de 32+ caracteres, JWT_ISSUER, JWT_AUDIENCE, JWT_EXPIRES_MINUTES, AUTH_SEED_PASSWORD y ConnectionStrings__Auth. La contraseña de Auth debe coincidir con MSSQL_SA_PASSWORD.

## Docker y validación

    docker compose up -d --build
    docker compose ps
    powershell -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1 -RequireGateway
    curl.exe http://localhost:5003/api/v1/courses/101/analytics

Los inicializadores en Exited (0) son correctos. Para SSMS usa localhost,11433, usuario sa y MSSQL_SA_PASSWORD. Analytics debe responder 200, usar score_0_10 y no convertir not_available en cero.

## Agent opcional

Usa OLLAMA_URL y AGENT_MODEL, no OLLAMA_BASE_URL u OLLAMA_MODEL. Ejecuta uvicorn con --host 127.0.0.1 --port 5004. Herramientas: listar_cursos, obtener_calificaciones, obtener_progreso, identificar_alertas y generar_resumen.

## Pruebas y problemas frecuentes

Desde services/agent-service ejecuta .\.venv\Scripts\python.exe -m pytest -q. Si 1433 está ocupado usa 11433. Si hay conflicto de nombres ejecuta docker compose down y luego docker compose up -d; no uses down -v salvo que quieras borrar datos. Si Agent aparece omitido en smoke-test es opcional. En PowerShell usa cd .\-EduMonitor-AI.

## Después de un merge

    git switch develop
    git pull origin develop
    docker compose up -d --build
    powershell -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1 -RequireGateway
