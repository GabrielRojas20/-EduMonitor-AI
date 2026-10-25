# contracts

**Responsable:** Mikel (analytics: Gabriel, agente: Juan)

Contratos OpenAPI v1 entre servicios. Los cambios van por PR y versionados (v1, v2).

| Archivo | Servicio | Responsable |
|---|---|---|
| [`api-gateway.v1.yaml`](api-gateway.v1.yaml) | Gateway, único punto de entrada de la interfaz y del agente | Mikel |
| [`auth-courses.v1.yaml`](auth-courses.v1.yaml) | Autenticación, JWT y cursos autorizados | Mikel |
| [`moodle-sync.v1.yaml`](moodle-sync.v1.yaml) | Sincronización y datos normalizados de Moodle | Mikel |
| [`analytics.v1.yaml`](analytics.v1.yaml) | Indicadores, alertas y datos del informe | Gabriel |

El contrato de las herramientas del agente no es OpenAPI: está en la carpeta [`docs/agent-design/`](../agent-design/).
