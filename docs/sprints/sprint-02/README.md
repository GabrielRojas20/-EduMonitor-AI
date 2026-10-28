# Sprint 2: Autenticación, sincronización y una base que ya se puede ejecutar

**Estado:** pendiente

**Objetivo:** El repositorio se ejecuta con docker-compose, hay login, listado de cursos y una primera carga de datos que se puede verificar. Además, el equipo decide si conviene fusionar `auth-courses` y `moodle-sync`.

**Entregable:** Repositorio ejecutable, listado de cursos y primera carga verificable. Decisión sobre fusionar servicios.

**Punto de decisión:** Al final del sprint: si `auth-courses` y `moodle-sync` no cumplen el entregable, se fusionan en un solo servicio.

## Roles del sprint

| Rol | Responsable |
|---|---|
| Facilitador del sprint | Gabriel |
| Responsable de la demostración | Benjamín |
| Responsable del repositorio | Gabriel |
| Responsable de la documentación | Juan |

## Tareas por integrante (según el plan de proyecto)

**Benjamín**
- [ ] Proyecto React: estructura, rutas, cliente HTTP y guía de estilos (1,0)
- [ ] Login (1,0)
- [ ] Listado de cursos (1,0)

**Mikel**
- [ ] Autenticación y JWT en `auth-courses` (1,5)
- [ ] Gateway YARP con políticas por rol y por curso (0,5)
- [ ] Cliente de Moodle y sincronización inicial de cursos y matrículas (1,0)

**Gabriel**
- [ ] `docker-compose` base y CI con pruebas (1,0)
- [ ] Scripts SQL y migraciones a partir del diagrama ER (1,0)
- [ ] Datos ficticios y persistencia de lo sincronizado (1,0)

**Juan**
- [ ] Servidor mock del gateway, listo el primer día (0,5)
- [ ] Esqueleto de `agent-service` con FastAPI, LangGraph y Ollama (1,0)
- [ ] Primera herramienta de lectura contra el mock (0,5)
- [ ] Conjunto de evaluación inicial con 20 escenarios (1,0)

## Dónde van los entregables

Carpetas principales: `services/` (los cinco servicios y la interfaz), `database/`, `docker-compose.yml`, `mocks/gateway-mock/`, `evaluation/agent-scenarios/`.

Cada tarea entra por pull request revisada por otra persona (ver `CONTRIBUTING.md`). Al cerrar el sprint se agregan aquí la revisión y la retrospectiva (`revision-y-retrospectiva.md`) y, en `docs/product-owner/`, el acta de la reunión con el Product Owner.

## Nota

El mock del gateway es lo que desbloquea la semana: Juan lo atiende antes que cualquier otra tarea. Depende de resolver la observación O-01 de la revisión cruzada (rutas de analytics en el contrato del gateway).
