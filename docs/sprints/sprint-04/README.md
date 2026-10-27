# Sprint 4: Alertas y agente con trazas

**Estado:** pendiente

**Objetivo:** Hay alertas que se explican con evidencias y al menos dos herramientas del agente conectadas.

**Entregable:** Alertas explicables y al menos dos herramientas conectadas.

**Punto de decisión:** En el Sprint 4: si el conjunto de evaluación del agente no llega al 90 %, se prioriza corregir prompts y herramientas antes de agregar otras nuevas.

## Roles del sprint

| Rol | Responsable |
|---|---|
| Facilitador del sprint | Benjamín |
| Responsable de la demostración | Juan |
| Responsable del repositorio | Gabriel |
| Responsable de la documentación | Juan |

## Tareas por integrante (según el plan de proyecto)

**Benjamín**
- [ ] Pantalla de alertas con sus evidencias (2,0)
- [ ] Interfaz base del chat (1,0)

**Mikel**
- [ ] Auditoría de las sincronizaciones (1,0)
- [ ] Soporte para la integración con el agente: token y errores (1,0)
- [ ] Refuerzo de seguridad: JWT, CORS y secretos (1,0)

**Gabriel**
- [ ] Reglas de alerta configurables (2,0)
- [ ] Endpoint de evidencias por alerta (1,0)

**Juan**
- [ ] Herramienta `identificar_alertas` (1,0)
- [ ] Trazas guardadas en el esquema `agent` (1,0)
- [ ] Primera versión de los prompts, separando hechos, inferencias y recomendaciones (1,0)

## Dónde van los entregables

Carpetas principales: `services/`, `database/`, `docs/agent-design/`.

Cada tarea entra por pull request revisada por otra persona (ver `CONTRIBUTING.md`). Al cerrar el sprint se agregan aquí la revisión y la retrospectiva (`revision-y-retrospectiva.md`) y, en `docs/product-owner/`, el acta de la reunión con el Product Owner.
