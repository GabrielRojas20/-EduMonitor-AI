# Guía de contribución

## Ramas
- `main`: protegida, siempre estable y demostrable.
- `develop`: integración del sprint.
- Ramas de trabajo desde `develop`: `feat/S2-04-login`, `fix/...`, `docs/S1-07-requisitos` (incluir el ID de tarea).

## Pull requests
1. Abrir PR hacia `develop` con la plantilla.
2. Debe revisarla al menos otra persona (los consumidores, si toca un contrato).
3. CI en verde (pruebas y linters) antes de unir.
4. Los PR a `main` los hace Gabriel al cerrar el sprint.

## Commits
Mensajes en español, imperativo, con el ID de tarea: `S1-03: agrega estructura de carpetas`.

## Reglas
- Prohibido subir secretos o datos reales de estudiantes. Solo `.env.example`.
- Contratos OpenAPI: definitivos el D4 del Sprint 1. Cambios por PR, versionados (v1, v2); quitar o renombrar campos exige versión nueva y aviso en la reunión diaria. El mock se actualiza en la misma PR.
- Una tarea está terminada cuando está en el repo vía PR revisada, con evidencia del criterio, y el Product Owner la acepta en la revisión del sprint.
- Cobertura mínima propuesta: 70 % en `analytics-service` y `agent-service`.

## Protección de ramas (configurar en GitHub, lo hace Gabriel)
Settings → Branches → regla para `main` (y `develop`): requerir PR, 1 aprobación, checks de CI y prohibir push directo.
