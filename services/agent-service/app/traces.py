"""Guardado de trazas (diseño, sección 5): una por mensaje, en la tabla `agent.trace` de SQL Server.

- Opcional: sin `AGENT_DB_CONNECTION` las trazas solo se escriben en el registro, como hasta ahora.
- Nunca retrasa ni rompe el chat: el guardado va a una cola y lo hace un hilo aparte; si la base falla, se avisa en el registro y se
  sigue. Si la cola se llena (base caída), se descartan las trazas nuevas en lugar de acumular memoria.
- Privacidad: no se guarda el JWT (la traza no lo trae) y se enmascara el nombre de estudiante que el agente usó como argumento
  (también dentro del texto de la pregunta), porque el diseño dice que las trazas llevan identificadores y no nombres mientras el Product Owner no responda la pregunta 9.
"""
import copy
import json
import logging
import queue
import re
import threading
from datetime import datetime
from typing import Callable

log = logging.getLogger("agent.traces")

MASK = "[nombre omitido]"
MASKED_ARGS = ("student_name",)

INSERT_SQL = ("INSERT INTO agent.trace (trace_id, request_id, teacher_id, course_id, started_at, finished_at, status, intent, "
              "model, tool_calls, duration_ms, trace_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")


def mask_trace(trace: dict) -> dict:
    """Copia de la traza sin los nombres de estudiante que el agente usó como argumento.

    Se enmascaran en los argumentos de las herramientas y también dentro del texto de la pregunta, y el mensaje queda marcado como
    redactado. Solo cubre los nombres que el agente llegó a usar; cualquier otro nombre que el docente escriba sigue en el texto
    hasta que el Product Owner responda la pregunta 9 del diseño.
    """
    safe = copy.deepcopy(trace)
    names = set()
    for step in safe.get("steps", []):
        args = step.get("args")
        if isinstance(args, dict):
            for key in MASKED_ARGS:
                if args.get(key):
                    names.add(str(args[key]))
                    args[key] = MASK
    message = safe.get("message")
    if names and isinstance(message, dict) and message.get("text"):
        text = message["text"]
        for name in sorted(names, key=len, reverse=True):
            text = re.sub(re.escape(name), MASK, text, flags=re.IGNORECASE)
        if text != message["text"]:
            message["text"], message["redacted"] = text, True
    return safe


def _int_or_none(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _datetime(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).replace(tzinfo=None)


def to_row(trace: dict) -> tuple:
    """Fila de `agent.trace` a partir de la traza (ya enmascarada)."""
    totals = trace.get("totals", {})
    return (trace["traceId"], trace.get("requestId"), _int_or_none(trace.get("teacherId")), _int_or_none(trace.get("courseId")),
            _datetime(trace["startedAt"]), _datetime(trace["finishedAt"]), trace["status"], trace.get("intent"),
            trace.get("model"), totals.get("toolCalls", 0), totals.get("durationMs"), json.dumps(trace, ensure_ascii=False))


class SqlServerTraceStore:
    """Inserta trazas en SQL Server con pyodbc. `connect` se puede reemplazar (las pruebas usan una conexión simulada)."""

    def __init__(self, connection_string: str, connect: Callable | None = None, timeout_s: int = 5):
        self.connection_string = connection_string
        self.timeout_s = timeout_s
        self._connect = connect

    def _open(self):
        if self._connect is not None:
            return self._connect(self.connection_string, self.timeout_s)
        import pyodbc  # se importa aquí: solo hace falta si se configuró la base
        return pyodbc.connect(self.connection_string, timeout=self.timeout_s, autocommit=True)

    def save(self, trace: dict) -> None:
        conn = self._open()
        try:
            conn.cursor().execute(INSERT_SQL, *to_row(mask_trace(trace)))
        finally:
            conn.close()


class TraceWriter:
    """Cola + hilo que guarda las trazas sin bloquear la respuesta del chat."""

    def __init__(self, store, max_queue: int = 200):
        self.store = store
        self.queue: queue.Queue = queue.Queue(maxsize=max_queue)
        self.dropped = 0
        self.failed = 0
        self._thread = threading.Thread(target=self._work, name="trace-writer", daemon=True)
        self._thread.start()

    def submit(self, trace: dict) -> None:
        try:
            self.queue.put_nowait(trace)
        except queue.Full:
            self.dropped += 1
            log.warning("Cola de trazas llena: se descarta la traza %s", trace.get("traceId"))

    def _work(self) -> None:
        while True:
            trace = self.queue.get()
            try:
                self.store.save(trace)
            except Exception as exc:  # la base caída no debe afectar al chat
                self.failed += 1
                log.warning("No se pudo guardar la traza %s en SQL Server: %s", trace.get("traceId"), type(exc).__name__)
            finally:
                self.queue.task_done()

    def flush(self, timeout_s: float = 5.0) -> bool:
        """Espera a que se vacíe la cola (para pruebas y para el apagado)."""
        done = threading.Event()
        threading.Thread(target=lambda: (self.queue.join(), done.set()), daemon=True).start()
        return done.wait(timeout_s)


def build_trace_sink(connection_string: str | None, log_sink: Callable[[dict], None]) -> Callable[[dict], None]:
    """Sumidero de trazas: siempre al registro y, si hay conexión configurada, también a SQL Server."""
    if not connection_string:
        return log_sink
    writer = TraceWriter(SqlServerTraceStore(connection_string))

    def sink(trace: dict) -> None:
        log_sink(trace)
        writer.submit(trace)

    sink.writer = writer  # type: ignore[attr-defined]
    return sink
