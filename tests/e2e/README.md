# Pruebas end-to-end

**Responsable:** Gabriel

Este directorio contiene la validación del recorrido de integración del Super Sprint 2 y posteriores:

```text
login → api-gateway → moodle-sync → SQL Server → analytics → agent-service
```

## Smoke test local

Desde la raíz del repositorio, con Docker Desktop iniciado:

```powershell
.\scripts\smoke-test.ps1
```

El script comprueba Analytics y marca como opcionales Gateway, Auth, Moodle Sync y Agent mientras la PR de infraestructura todavía no esté fusionada o esos procesos no estén levantados.

Para exigir que el Gateway esté disponible:

```powershell
.\scripts\smoke-test.ps1 -RequireGateway
```

Para exigir también el healthcheck del agente:

```powershell
.\scripts\smoke-test.ps1 -RequireGateway -RunAgentHealth
```

Para probar otro curso:

```powershell
.\scripts\smoke-test.ps1 -CourseId 102
```

La guía completa está en [`docs/installation-local.md`](../../docs/installation-local.md).

## Criterios de aceptación

- SQL Server aparece como `healthy`.
- `analytics-db-init` termina con código `0`.
- `GET /health` de Analytics devuelve `200`.
- Analytics devuelve indicadores en escala `0-10` y porcentajes donde corresponde.
- Las alertas incluyen regla, severidad, estado y evidencia explicable.
- Moodle Sync conserva el ID de Moodle y persiste en el esquema `sync`.
- `onlinetext` no aparece en ninguna respuesta ni tabla de datos sincronizados.
- Un flujo autenticado conserva el JWT entre login, gateway y servicios internos.
- El agente recibe datos únicamente mediante el gateway y no expone el JWT en sus trazas.
