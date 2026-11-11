# agent-service

**Responsable:** Juan

Agente de IA: FastAPI + LangGraph + Pydantic con un modelo local de Ollama. Responde a las preguntas del docente
separando **hechos**, **inferencias** y **recomendaciones**, y no inventa datos. Solo consulta información a través del
api-gateway, reenviando el JWT del docente; nunca toca la base de datos ni Moodle.

Diseño completo: [`docs/agent-design/diseno-agente.md`](../../docs/agent-design/diseno-agente.md).

## Estado

Sprint 2. Ya están el servicio, el flujo de LangGraph, el cliente de Ollama, las trazas, las pruebas y las herramientas
`listar_cursos`, `obtener_calificaciones`, `obtener_progreso` e `identificar_alertas`. Todas consultan el gateway con el
JWT del docente y redactan hechos verificables desde código. Si una consulta necesita una herramienta que aún no existe,
el agente lo dice en lugar de inventar.

## Cómo ejecutarlo

Requiere Python 3.11 o superior (probado con 3.13) y [Ollama](https://ollama.com) con el modelo descargado:

```powershell
ollama pull qwen3:1.7b
```

```powershell
cd services/agent-service
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m uvicorn app.main:app --port 5004
```

En macOS o Linux, cambia `.\.venv\Scripts\python` por `./.venv/bin/python`.

- Documentación interactiva: <http://localhost:5004/docs>
- Estado del servicio y de Ollama: <http://localhost:5004/health>
- Puerto: **5004** (los contratos fijan 5000 a 5003 para el gateway y los servicios internos; el del agente no estaba definido).

El agente llama al gateway en `http://localhost:5000`. Mientras el gateway real no esté listo, usa el mock
(`mocks/gateway-mock`, ver su README), que se arranca igual en ese mismo puerto.

### Probar el chat

1. Obtén un token: `POST http://localhost:5000/api/v1/auth/login` con `docente1@example.com` y `Prueba123!` (datos del mock).
2. En <http://localhost:5004/docs> pulsa **Authorize** y pega el `accessToken`.
3. Prueba `POST /chat` con `{"message": "Hola, ¿qué puedes hacer?"}`.

Para ver el modelo real eligiendo una herramienta y redactando (con una herramienta de ejemplo en memoria):

```powershell
.\.venv\Scripts\python scripts\probar_modelo.py "¿Qué cursos tengo?"
```

## `POST /chat`

| Elemento | Definición |
|---|---|
| Encabezado | `Authorization: Bearer <JWT>` del docente. Sin él, o vencido, se responde 401 y no se llama al modelo ni a las herramientas. |
| Cuerpo | `message` (obligatorio, no vacío) y `courseId` (entero, opcional: el curso de referencia). |
| Respuesta 200 | `traceId`, `answer` (`facts`, `inferences`, `recommendations`, `unavailable`, `message`) y `meta` (`courseId`, `lastSyncAt`, `status`). |
| `meta.status` | `ok`, `partial` (falló alguna herramienta), `refused` (fuera de alcance) o `error`. |
| Errores HTTP | `400 VALIDATION_ERROR`, `401 TOKEN_INVALID` y `401 TOKEN_EXPIRED`, en formato Problem (`title`, `status`, `code`, `detail`, `traceId`). |

Los fallos de una herramienta o del modelo **no son errores HTTP**: la respuesta es 200 con `meta.status` en `partial` o
`error` y el motivo en `answer.unavailable`.

`answer.message` es un texto breve para saludos y ayuda, donde no hay datos que citar. **Es un añadido al diseño**
(sección 6) que hay que acordar con quien muestre el chat.

## Cómo funciona

El flujo de LangGraph (`app/graph.py`) sigue la sección 4 del diseño:

```
recibir_mensaje -> validar_contexto -> clasificar_intencion -> planificar_herramientas -> ejecutar_herramientas
-> verificar_evidencia -> (marcar_datos_no_disponibles) -> redactar_respuesta -> validar_salida -> guardar_traza
```

- **Clasificación por reglas:** rechaza modificar notas, enviar mensajes y predicciones psicológicas antes de usar el modelo.
- **Planificar:** el modelo elige herramientas con temperatura 0 (máximo 5 por mensaje).
- **Redactar:** los **hechos los escribe el código**, a partir de la salida de la herramienta (cada herramienta sabe
  redactar los suyos). Así un modelo pequeño no puede equivocarse al copiar una cifra ni atribuirla a otra entidad: en una
  prueba, `qwen3:1.7b` escribió «PRUEBA02 tiene 5 estudiantes» (el 5 era de PRUEBA01), y el validador de cifras no
  lo detectó porque ese 5 sí estaba en los datos. El modelo solo interviene si el docente pide **interpretación o consejo**
  («¿qué me recomiendas?»): entonces redacta inferencias y recomendaciones sobre los hechos numerados. Para las herramientas
  que aún no tengan redactor de hechos, el modelo redacta con salida estructurada, y recibe los datos dentro de un bloque
  `<datos_herramienta>` (como datos, no como instrucciones) y con los `null` convertidos en «no disponible».
- **Validar salida (código, sin modelo):** toda cifra de un hecho debe aparecer en la salida de alguna herramienta. Si no,
  se reintenta una vez (diciéndole al modelo qué cifras corregir, y solo si cabe en los 60 s del mensaje) y, si persiste, se
  descarta el hecho. Las inferencias y recomendaciones con cifras sin fuente también se descartan. Las inferencias sin hechos en que basarse y las
  recomendaciones sin hallazgo se descartan.
- **Traza:** una por mensaje, con los pasos, las herramientas y los tiempos. **Nunca** incluye el JWT. Por ahora se escribe
  en el registro `agent.trace`; guardarla en el esquema `agent` es una tarea siguiente.

## Herramientas

| Herramienta | Estado | Ruta del gateway |
|---|---|---|
| `listar_cursos` | Disponible | `GET /api/v1/courses` |
| `obtener_calificaciones` | Disponible | `GET /api/v1/courses/{courseId}/grades` |
| `obtener_progreso` | Disponible | `GET /api/v1/courses/{courseId}/analytics` (y la del estudiante) |
| `identificar_alertas` | Disponible | `GET /api/v1/courses/{courseId}/analytics/alerts` |
| `generar_resumen` | Pendiente | `GET /api/v1/courses/{courseId}/analytics/report` |

### Cómo añadir una herramienta

Cada herramienta es un archivo de `app/catalog/` con el nombre de la herramienta (`obtener_calificaciones.py`) que define
una variable `TOOL`. **No hay que registrarla en ningún otro archivo**: `app/toolset.py` las descubre solas. Así, los PR de
herramientas distintas no tocan los mismos archivos y no chocan. Mira `app/catalog/listar_cursos.py` como modelo. Cada
archivo define:

- `run(ctx, args)`: llama al gateway con `gateway_get` y devuelve `ok_output(...)` o el error de la herramienta.
- `facts(data)`: redacta los hechos con código a partir de los datos (el modelo no los escribe).
- `TOOL = Tool(name=..., description=..., input_model=..., run=run, facts=facts)`.

Las piezas compartidas (`NoArgs`, `fecha`, `plural`) están en `app/catalog/common.py`. Las pruebas de `tests/test_toolset.py`
comprueban que cada herramienta cumple esa convención.

Todas son de solo lectura y devuelven la salida común del diseño (`ok`, `data`, `error`, `source`). Un fallo del gateway se
traduce a un código del diseño (`TOKEN_EXPIRED`, `COURSE_NOT_AUTHORIZED`, `MOODLE_UNAVAILABLE`, `DATA_NOT_AVAILABLE`,
`TOOL_TIMEOUT`...) y nunca lanza una excepción. El JWT se reenvía al gateway y no aparece en ninguna salida ni traza.

## Configuración

Variables de entorno, todas opcionales (ver `.env.example`): `OLLAMA_URL`, `AGENT_MODEL` (por defecto `qwen3:1.7b`),
`GATEWAY_URL`, `OLLAMA_KEEP_ALIVE`, `MAX_TOOL_CALLS`, `TOOL_TIMEOUT_SECONDS`, `MESSAGE_TIMEOUT_SECONDS`, `DRAFT_MAX_TOKENS` y
`AGENT_CORS_ORIGINS` (orígenes de la interfaz React que pueden llamar al agente).

## Pruebas

```powershell
.\.venv\Scripts\python -m pytest
```

Corren con un Ollama simulado, así que no necesitan el modelo ni el gateway. Cubren la validación del token y del cuerpo,
la clasificación, el flujo completo con herramientas simuladas, el reintento y el descarte de cifras sin fuente, los
fallos de herramientas y del modelo, los límites, la seguridad frente a datos hostiles y que la traza no contenga el JWT.

## Pendiente

- Implementar `generar_resumen` para completar los escenarios de informe `I01` e `I02`.
- Guardar las trazas en el esquema `agent` de SQL Server.
- Afinar los prompts con el conjunto de evaluación (`evaluation/agent-scenarios/`). Con `qwen3:1.7b`, una consulta de
  datos tarda unos 6 s (la elección de la herramienta) y una con interpretación unos 16 s en un computador sin GPU; el
  modelo a veces enlaza una recomendación al hecho equivocado.
- Incorporar el `agent-service` al `docker-compose.yml` cuando el equipo cierre su empaquetado; por ahora se ejecuta fuera de Docker
  siguiendo esta guía.
