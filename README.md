# EduMonitor AI

Sistema inteligente de seguimiento y análisis del rendimiento académico integrado con Moodle.
Facultad de Ingeniería en Sistemas, Electrónica e Industrial.

Aplicación web independiente de Moodle: el docente inicia sesión, la app consulta sus cursos mediante servicios web autorizados, calcula indicadores verificables y un agente de IA (modelo local con Ollama) los interpreta y sugiere acciones pedagógicas. **No reemplaza el criterio del docente ni modifica calificaciones.**

## Equipo

| Integrante | Frente | Servicios / componentes |
|---|---|---|
| Benjamín Basurto | Interfaz y experiencia de usuario | `services/web-ui`, wireframes, tablero |
| Mikel Guzmán | Backend y Moodle | `services/api-gateway`, `services/auth-courses-service`, `services/moodle-sync-service`, `infra/moodle` |
| Gabriel Rojas | Datos, analítica e infraestructura | `services/analytics-service`, `database/`, `docker-compose.yml`, CI. **Responsable del repositorio** |
| Juan Pashma | Agente de IA | `services/agent-service`, `infra/ollama`, `mocks/gateway-mock`, `evaluation/`. **Responsable de la documentación** |

## Estructura del repositorio

```
.github/            Plantilla de PR, plantilla de tareas, CI (Gabriel)
docs/               Documentación (ver responsables en cada carpeta)
  requirements/     Requisitos y matriz de cumplimiento (Juan / Benjamín)
  contracts/        Contratos OpenAPI (Mikel, Gabriel, Juan)
  data-model/       Diagrama entidad-relación (Gabriel)
  analytics-rules/  Fórmulas y reglas de alerta (Gabriel)
  agent-design/     Diseño del agente y herramientas (Juan)
  architecture/     Diagrama de arquitectura (Juan)
  benchmarks/       Pruebas de Ollama (Juan)
  moodle-access/    Evidencia de acceso a Moodle (Mikel)
  wireframes/       Wireframes (Benjamín)
  reviews/          Revisiones cruzadas de contratos
  product-owner/    Preguntas y aceptación del Product Owner
  sprints/          Planificación, revisión y retrospectiva por sprint
services/           Los cinco servicios + la interfaz
mocks/              Mock del gateway (Juan)
database/           Migraciones y datos ficticios (Gabriel)
infra/              Moodle, Ollama, Docker
evaluation/         Escenarios de evaluación del agente (Juan)
tests/e2e/          Pruebas de extremo a extremo (Gabriel)
docker-compose.yml  Entorno completo (Sprint 2)
```

Cada carpeta tiene un `README.md` con su responsable.

## Arquitectura

Cinco servicios (`api-gateway`, `auth-courses`, `moodle-sync`, `analytics`, `agent-service`) más la interfaz. Una sola instancia de SQL Server 2022 con un esquema por servicio (`auth`, `sync`, `analytics`, `agent`), sin compartir tablas. Se comunican solo por API REST. El agente consulta datos únicamente por el gateway con el token del docente; los cálculos son deterministas y viven en `analytics-service`.

Tecnologías: React + TypeScript + Vite · ASP.NET Core (.NET 8), YARP, EF Core · SQL Server 2022 · Python 3.11, FastAPI, LangGraph, Pydantic · Ollama · Moodle en Docker · GitHub Actions y Docker Compose.

## Cómo empezar

```bash
cp .env.example .env   # completar valores; nunca subir .env
docker compose up -d --build
docker compose ps
```

Para la guía completa de instalación, Moodle, el seed académico y el agente, consulta [`docs/installation-local.md`](docs/installation-local.md). El entorno de Sprint 3 publica el Gateway en `5000`, Auth Courses en `5001`, Moodle Sync en `5002`, Analytics en `5003`, Agent Service en `5004`, Moodle en `8080`, Ollama en `11434` y el frontend Vite en `5173`.

## Acceso de demostración y entrega al ingeniero

Los usuarios ficticios dependen del dataset seleccionado. Con `AUTH_SEED_DATASET=minimal` se crean `docente1@edumonitor.test`, `docente2@edumonitor.test` y `admin@edumonitor.test`; con `AUTH_SEED_DATASET=massive` se crean además `docente3@edumonitor.test`, `docente4@edumonitor.test` y `docente5@edumonitor.test`. La contraseña de todos se toma de la variable local `AUTH_SEED_PASSWORD` y no está escrita en el repositorio. Para entregar el proyecto, comparte esa contraseña y el token local de Moodle por un canal privado o configura valores nuevos en el `.env` del equipo receptor. Nunca subas `.env`, `MOODLE_WS_TOKEN`, `JWT_SECRET`, contraseñas ni JWT a GitHub.

Para reproducir la demo masiva, configura `AUTH_SEED_DATASET=massive` y `DEMO_DATASET=massive` en `.env`. El usuario técnico de Moodle es `edumonitor_sync`. El token de Moodle se configura únicamente en `MOODLE_WS_TOKEN` del `.env` local. La versión utilizada por Docker Compose es Moodle `4.5` y la instalación verificada reporta `4.5.4`. El dataset de demostración masivo validado contiene 25 cursos, 25 estudiantes por curso, 50 actividades, 1.250 entregas, 1.100 calificaciones y 1.250 estados de finalización.

## Alcance

Dentro: login docente, cursos autorizados, sincronización manual con Moodle, dashboard, ficha por estudiante, alertas configurables y explicables, chat con agente (mínimo 3 herramientas) e informe del curso.
Fuera: predicción clínica/psicológica, modificar notas en Moodle, mensajes automáticos a estudiantes, entrenar modelos propios, sistemas multiagente.

## Flujo de trabajo

Ver [CONTRIBUTING.md](CONTRIBUTING.md). Resumen: nadie sube directo a `main`; todo entra por pull request revisada por otra persona y con CI en verde.
