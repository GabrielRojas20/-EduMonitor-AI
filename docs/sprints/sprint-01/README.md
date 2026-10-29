# Sprint 1: definir, no construir

**Estado:** en cierre (revisado el 2026-10-29)

**Objetivo:** al terminar la primera semana, el equipo tiene acordados y validados con el Product Owner los requisitos, el modelo de datos, los contratos de API entre servicios, el tablero de trabajo, el repositorio base y una prueba de acceso a Moodle.

**Entregable:** documento de requisitos, tablero, contratos definitivos y evidencia de la conexión con Moodle.

## Roles del sprint

| Rol | Responsable |
|---|---|
| Facilitador del sprint | Benjamín |
| Responsable de la demostración | Mikel |
| Responsable del repositorio | Gabriel |
| Responsable de la documentación | Juan |

## Estado de las tareas

Estados: **Hecha** (en `develop` mediante PR revisada), **En revisión** (PR abierta), **Falta** (no hay evidencia en el repositorio) y **Por confirmar** (no se puede comprobar desde el repositorio).

| ID | Responsable | Tarea | Límite | Estado | Dónde está |
|---|---|---|---|---|---|
| S1-01 | Todos | Acordar alcance, roles y reglas de trabajo | D1 | Falta confirmación del equipo | Borrador en [`acuerdo-de-equipo.md`](acuerdo-de-equipo.md) |
| S1-02 | Gabriel | Repositorio, carpetas por servicio, ramas protegidas y plantilla de PR | D1 | Hecha. Ramas protegidas verificadas | [evidencia de ramas](../../repository/branch-protection.md), [`.github/`](../../../.github/), [`CONTRIBUTING.md`](../../../CONTRIBUTING.md) |
| S1-03 | Juan y Benjamín | Documento de requisitos y matriz de cumplimiento | D3 | Hecha. Falta la aceptación del Product Owner | [`requisitos.md`](../../requirements/requisitos.md) |
| S1-04 | Benjamín | Tablero con las épicas de los seis sprints y las tareas del Sprint 1 | D2 | Por confirmar: el repositorio no enlaza el tablero | _Pendiente de enlace_ |
| S1-05 | Mikel | Moodle en Docker, curso de prueba, usuarios, rol y token | D2 | Hecha (PR #25): `docker-compose.yml` y README con los pasos para levantarlo | [`infra/moodle/`](../../../infra/moodle/) |
| S1-06 | Mikel | Prueba de acceso a Moodle: versión, permisos y escalas | D3 | Hecha; evidencia con el texto de las entregas redactado (PR #24) | [`docs/moodle-access/`](../../moodle-access/) |
| S1-07 | Mikel | Contratos OpenAPI del gateway, `auth-courses` y `moodle-sync` | D3 / D4 | Hecha (PR #26 cierra las observaciones O-01 a O-11) | [`docs/contracts/`](../../contracts/) |
| S1-08 | Gabriel | Diagrama entidad-relación | D3 | Hecha | [`diagrama-er.md`](../../data-model/diagrama-er.md) |
| S1-09 | Gabriel | Fórmulas de indicadores y reglas de alerta iniciales | D4 | Hecha | [`reglas-iniciales.md`](../../analytics-rules/reglas-iniciales.md) |
| S1-10 | Gabriel | Contrato OpenAPI de `analytics-service` | D4 | Hecha (versión 1.0.0, PR #21) | [`analytics.v1.yaml`](../../contracts/analytics.v1.yaml), [`decisiones-s1-10.md`](../../analytics-rules/decisiones-s1-10.md) |
| S1-11 | Juan | Contrato de las herramientas del agente y flujo de LangGraph | D4 | Hecha, con `POST /chat` y nombres de estudiantes (PR #22) | [`diseno-agente.md`](../../agent-design/diseno-agente.md) |
| S1-12 | Juan | Ollama: modelos, tiempos, memoria y modelo elegido | D2 | Hecha | [`ollama-pruebas-modelos.md`](../../benchmarks/ollama-pruebas-modelos.md) |
| S1-13 | Benjamín | Wireframes de baja fidelidad de las seis pantallas | D4 | Hecha (PR #19) | [`docs/wireframes/`](../../wireframes/) |
| S1-14 | Juan | Revisión cruzada de contratos | D4 | Hecha. Las 20 observaciones (O-01 a O-20) resueltas (PR #21 y #26) | [`revision-cruzada-contratos.md`](../../reviews/revision-cruzada-contratos.md) |
| S1-15 | Todos | Presentar al Product Owner requisitos, alcance, contratos y preguntas abiertas | D5 | Falta | Plantilla en [`reunion-sprint-01.md`](../../product-owner/reunion-sprint-01.md) |
| S1-16 | Todos | Diagrama de arquitectura, revisión y retrospectiva del sprint | D5 | Diagrama hecho. Faltan la revisión y la retrospectiva | [`arquitectura.md`](../../architecture/arquitectura.md), plantilla en [`revision-y-retrospectiva.md`](revision-y-retrospectiva.md) |

## Pendientes por integrante

**Benjamín**
- S1-04: enlazar el tablero desde el repositorio (por ejemplo, en el `README.md` raíz) y confirmar que tiene las épicas de los seis sprints y las tareas del Sprint 1.

**Mikel**
- Sin pendientes: el PR #26 ya está unido.

**Gabriel**
- Al cerrar el sprint: PR de `develop` a `main` (hoy `main` solo tiene la estructura inicial).
- Agregar `JWT_AUDIENCE` a `.env.example`, porque el contrato de `auth-courses` exige el campo `aud`.

**Juan**
- Sus cinco tareas individuales (S1-03, S1-11, S1-12, S1-14 y la parte de S1-16) están hechas.
- Revisión del PR #26 hecha y aprobada.

**Todos**
- S1-01: confirmar el acuerdo de equipo.
- S1-15: reunión con el Product Owner y acta con sus respuestas a las 15 preguntas abiertas.
- S1-16: revisión y retrospectiva del sprint.

## Criterios de terminado del sprint (plan, sección 4.2)

- [ ] Todo el trabajo está en el repositorio mediante PR revisadas por otra persona.
- [ ] Los contratos de API están publicados y los consumidores los aprobaron.
- [x] No hay secretos en el repositorio (solo `.env.example`).
- [ ] Hay evidencia de que se cumple cada criterio.
- [ ] El Product Owner acepta lo entregado en la revisión del sprint.
