# analytics-service

**Responsable:** Gabriel

Indicadores deterministas y reglas de alerta configurables, con evidencias por alerta (esquema SQL `analytics`). Pruebas con xUnit, cobertura mínima 70 %.

## Vertical slice implementada

Servicio ASP.NET Core 8 que calcula indicadores normalizados a escala 0-10 y alertas explicables a partir de SQL Server.

### Endpoints

- `GET /health`
- `GET /api/v1/courses/{courseId}/analytics`
- `GET /api/v1/courses/{courseId}/analytics/summary` (alias compatible)
- `GET /api/v1/courses/{courseId}/analytics/students/{studentId}`
- `GET /api/v1/courses/{courseId}/students/{studentId}/analytics` (alias compatible)
- `GET /api/v1/courses/{courseId}/analytics/alerts`

Las observaciones `not_available` no se convierten en cero: producen `DATA_NOT_AVAILABLE`. Las calificaciones en cero sí son datos válidos.

### Ejecución local en PowerShell

```powershell
dotnet restore
dotnet run --urls http://localhost:5003
dotnet test .\AnalyticsService.Tests\AnalyticsService.Tests.csproj
```

Antes de ejecutar, crear la base con `database.sql` y configurar `ConnectionStrings__EduMonitor` o `MSSQL_SA_PASSWORD`.
