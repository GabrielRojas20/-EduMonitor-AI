# Acuerdo de equipo (S1-01)

**Estado:** borrador. Se da por acordado cuando los cuatro integrantes lo confirmen (por ejemplo, aprobando el PR que lo incorpore).

Recoge lo que el plan de proyecto y el repositorio ya establecen, para que el acuerdo quede registrado en un solo lugar. No agrega reglas nuevas.

## 1. Alcance

El alcance del producto mínimo y lo que queda fuera están en [`docs/requirements/requisitos.md`](../../requirements/requisitos.md), sección 1.

## 2. Roles

| Integrante | Frente | Responsabilidades |
|---|---|---|
| Benjamín | Interfaz y experiencia de usuario | `web-ui`, wireframes, tablero y requisitos de interfaz |
| Mikel | Backend y Moodle | `api-gateway`, `auth-courses`, `moodle-sync` e instancia de Moodle |
| Gabriel | Datos, analítica e infraestructura | `analytics`, SQL Server, `docker-compose` y CI. Responsable del repositorio |
| Juan | Agente de IA | `agent-service`, Ollama, mocks del gateway y evaluación. Responsable de la documentación |

Los roles rotativos (facilitador del sprint y responsable de la demostración) están en [`docs/sprints/README.md`](../README.md). El Product Owner es el ingeniero de la materia: prioriza el backlog y acepta o rechaza lo entregado al final de cada sprint.

## 3. Reglas de trabajo

**Carga**
- Cada integrante planifica como máximo 4 días por sprint (3 de tareas individuales y 1 compartido) y deja 1 día de reserva.
- Quien facilita el sprint dedica medio día a esa labor, que sale de su reserva.
- Si una persona usa más de la mitad de su reserva dos sprints seguidos, el equipo redistribuye el trabajo.
- Si un retraso afecta al camino crítico, se avisa en la reunión diaria del mismo día.

**Código y documentos**
- Nadie sube directo a `main` ni a `develop`: todo entra por pull request hacia `develop`, revisada por otra persona y con CI en verde. Los PR a `main` los hace Gabriel al cerrar el sprint.
- Ramas desde `develop` con el ID de la tarea (`docs/S1-07-requisitos`, `feat/S2-04-login`). Commits en español, en imperativo y con el ID de tarea.
- Está prohibido subir secretos o datos reales de estudiantes. Solo se versiona `.env.example`.

**Contratos**
- Los contratos OpenAPI se congelan el cuarto día del Sprint 1. Los cambios posteriores van por PR, versionados (v1, v2), y los aprueban los consumidores afectados.
- Se pueden añadir campos opcionales sin cambiar de versión. Quitar o renombrar un campo exige una versión nueva y aviso en la reunión diaria.
- El mock del gateway se actualiza en la misma PR que cambie el contrato.

**Cuándo una tarea está terminada**
- Está en el repositorio mediante una PR revisada por otra persona.
- Sus contratos están publicados y los consumidores los aprobaron.
- No hay secretos en el repositorio.
- Existe evidencia de que se cumple el criterio.
- El Product Owner la acepta en la revisión del sprint.

**Cambios del Product Owner a mitad de sprint:** se anotan y se negocian para el sprint siguiente.

Detalle del flujo de contribución: [`CONTRIBUTING.md`](../../../CONTRIBUTING.md).

## 4. Confirmación

| Integrante | Confirma | Fecha |
|---|---|---|
| Benjamín | | |
| Mikel | | |
| Gabriel | | |
| Juan | | |
