# EduMonitor AI — Frontend

**Responsable:** Benjamín Basurto · Metodologías Ágiles · Sprint 2, noviembre 2026.

Aplicación **React + TypeScript + Vite** que consume los contratos de `docs/contracts/api-gateway.v1.yaml` y `docs/contracts/analytics.v1.yaml` y el servicio Python de Juan.

## Páginas implementadas

| Ruta | Funcionalidad |
| --- | --- |
| `/login` | Correo/contraseña, POST login, JWT, validación y 401. |
| `/cursos` | Cursos autorizados, filtros, estado/fecha y sincronización manual. |
| `/cursos/:id` | Métricas, Recharts, actividades, búsqueda, paginación y ficha. Incluye el panel de chat con **Edu**, el asistente de IA, ya fijado en el curso. |
| `/cursos/:id/informe` | Informe académico del curso con hallazgos y evidencia. |
| `/cursos/:id/estudiantes/:sid` | Métricas individuales, notas, entrega, finalización y evidencia. |
| `/alertas` | Alertas por curso, severidad y estado, detalle y fuentes. |
| `/chat` | Ya no es una página: redirige a `/cursos/:id` (conserva `?curso=` y `?q=`). El chat vive dentro de cada curso. |

Se implementaron estados **cargando / vacío / error / reintentar / parcial**, control de acceso por sesión y diferencias entre `graded` con nota 0, `pending_grading`, `not_submitted` y borradores. Los indicadores y alertas **no se recalculan** en el navegador: provienen de `analytics-service`. Las visualizaciones de distribución sí agrupan registros de calificación devueltos por la API sin alterar los indicadores oficiales.

## Requisitos locales

Node.js 20+ y npm; el equipo ya instaló `react-router-dom`, `recharts` y `lucide-react`. Este paquete deliberadamente **no reemplaza** `package.json`, `package-lock.json`, `vite.config.ts` ni `tsconfig.*` del proyecto Vite creado localmente.

Desde `services/web-ui` (PowerShell de Windows):

```powershell
# si el .env no existe, créalo a partir del ejemplo
Copy-Item .env.example .env
npm.cmd install
npm.cmd run build
npm.cmd run dev
```

Abrir http://localhost:5173/. Si modificas `.env`, reinicia Vite. No subir `.env`.

## Backend: elegir uno

### Opción A: mock del gateway (ideal para primera comprobación)

Desde la raíz del repositorio, en otra terminal PowerShell:

```powershell
cd mocks/gateway-mock
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 5000
```

Mock: `docente1@example.com` / `Prueba123!`. Da acceso a los cursos `PRUEBA01` y `PRUEBA02` (el segundo no sincronizado al inicio). Comprobar http://localhost:5000/health.

### Opción B: gateway real

Desde la raíz del repositorio:

```powershell
Copy-Item .env.example .env  # solo si no existe
# editar credenciales/secretos locales para SQL Server, Moodle y JWT
# ver infra/README.md, docker-compose.yml y documentación de Mikel
# docker compose up -d --build
```

Gateway real: `docente1@edumonitor.test` / valor de `AUTH_SEED_PASSWORD` en `.env` del equipo. El gateway debe estar en `http://localhost:5000`, tener CORS permitido para `http://localhost:5173`, y exponer correctamente sus rutas. Para los datos reales hace falta Moodle configurado y sincronizado.

**Importante:** no ejecutes simultáneamente el mock y gateway real en el puerto 5000. Cambia `VITE_API_URL` si se usa otra dirección.

## Chat (Edu, dentro de cada curso)

El chat no es una página global con selector de curso: está en la página de cada curso (`/cursos/:id`), con el curso ya fijado. El agente se presenta como **Edu**. Se ejecuta por separado, en `http://localhost:5004` (`VITE_AGENT_URL`), y no es parte del mock de gateway. Para tener respuestas del modelo también es necesario que Ollama esté listo (ver `services/agent-service/README.md`).

- **Consultas establecidas:** botones como «¿Cuántos estudiantes tengo?», «¿Qué alertas hay?» o «Genera el informe del curso»; también se puede escribir una pregunta libre.
- **Contexto de la ficha individual:** el botón «Consultar al agente» de la ficha abre `/cursos/:id?estudiante=:sid#agente`; el panel muestra la etiqueta «Ficha individual» y las preguntas del estudiante.
- **Enlaces con pregunta:** `/cursos/:id?q=…` envía la pregunta una vez y la quita de la dirección.
- **Historial:** las consultas con respuesta se guardan en este navegador (`localStorage`), por docente y por curso, hasta 30, con el botón «Borrar historial». No es memoria del agente: cada pregunta se procesa de forma independiente.
- **Respuesta:** se muestran los bloques de hechos, inferencias y recomendaciones (cuando la respuesta no trae ninguno, solo el mensaje), con fuentes, fecha de sincronización y avisos de datos no disponibles o parciales.

Los estudiantes se numeran de 1 al total **dentro de su curso** (`N.º 4 · Nombre`), por orden alfabético; el id de Moodle no se muestra como número de estudiante.

## Alertas resueltas

El mock de Juan devuelve solo alertas activas; si filtras por `resolved`, la pantalla mostrará una lista vacía. La comprobación de una alerta resuelta se debe hacer sobre el servicio real de Gabriel **cuando haya una alerta resuelta disponible**. La interfaz ya interpreta ambos estados del contrato.

## Criterios de prueba manual

1. Abrir una ruta protegida sin token → redirige a `/login`.
2. Login correcto → `/cursos`; correo/contraseña erróneos → mensaje 401.
3. Cursos autorizados, búsqueda, estado y última sincronización (sin fecha ≠ fecha actual).
4. POST de sincronización → 202; no se vuelve a pulsar mientras `running`; el éxito se anuncia solo al consultar `succeeded`.
5. Dashboard muestra las métricas recibidas y tres gráficos: distribución de notas, entregas y severidad.
6. Ficha refleja `0`, `null` pendiente, sin entrega y borrador correctamente.
7. Alertas muestran regla, severidad, fecha, valores observados, umbral, explicaciones y fuente.
8. El panel de Edu en `/cursos/:id` muestra los tres bloques, su evidencia, respuesta parcial, rechazada y fallos; el historial se conserva al recargar y se borra con su botón; `/chat?curso=:id` redirige al curso.
9. Probar cortes de red, errores 503 y cambio de curso sin arrastrar datos del anterior.

## Restricciones conocidas

- El gateway real requiere los servicios y datos de tus compañeros. El frontend solo consume sus API; no puede garantizar que se encuentren disponibles o funcionando en su máquina.
- No se guardan secretos en este paquete. Las variables `VITE_*` son **públicas** para el navegador; no pongas claves privadas ni tokens en ellas.
- El token del docente se guarda en `sessionStorage` para la sesión de esta demo. Para producción deben evaluarse políticas de sesión más robustas y protección XSS/CSP.
- Los gráficos se calculan con las calificaciones y alertas que expone la API; si faltan datos muestran estados vacíos sin inventar valores.
