# Infraestructura de EduMonitor

## Agent Service

`agent-service` se ejecuta fuera de Docker Compose en esta PR.

Ubicación: `services/agent-service`

Es un servicio Python/FastAPI. Para instalarlo y ejecutarlo desde el host:

```bash
cd services/agent-service
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
export GATEWAY_URL=http://localhost:5000
export OLLAMA_URL=http://localhost:11434
python -m uvicorn app.main:app --host 0.0.0.0 --port 5004
```

El agente queda disponible en `http://localhost:5004`.

Desde el host usa `GATEWAY_URL=http://localhost:5000` y `OLLAMA_URL=http://localhost:11434`.

Si se ejecuta dentro de Docker Compose, debe usar `GATEWAY_URL=http://api-gateway:5000` y `OLLAMA_URL=http://ollama:11434`. Dentro de un contenedor no debe usarse `localhost` para comunicarse con otros servicios.

Compose continúa levantando API Gateway, Auth Courses, Moodle Sync, Analytics, Moodle, MariaDB, SQL Server y Ollama.
