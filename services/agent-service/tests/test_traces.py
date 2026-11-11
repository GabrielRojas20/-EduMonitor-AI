"""Guardado de trazas en SQL Server (con una conexión simulada) y su enmascarado."""
import json
import logging

import pytest

from app import traces
from app.traces import SqlServerTraceStore, TraceWriter, build_trace_sink, mask_trace, to_row

TOKEN = "aaa.bbb.firma"
TRACE = {"traceId": "t-1", "requestId": "r-1", "startedAt": "2026-11-11T15:04:05Z", "finishedAt": "2026-11-11T15:04:21Z",
         "teacherId": "3", "courseId": 2, "model": "qwen3:1.7b", "message": {"text": "¿Cómo va Estudiante Dos?", "redacted": False},
         "intent": "consulta_datos",
         "steps": [{"n": 1, "node": "planificar_herramientas", "tool": None, "ok": True},
                   {"n": 2, "node": "ejecutar_herramientas", "tool": "obtener_progreso",
                    "args": {"course_name": "PRUEBA01", "student_name": "Estudiante Dos"}, "ok": True, "errorCode": None,
                    "durationMs": 840, "resultSummary": {"activities": 2}}],
         "output": {"validated": True, "unsourcedNumbersRemoved": 0}, "totals": {"toolCalls": 1, "durationMs": 15800}, "status": "ok"}


class FakeConnection:
    def __init__(self, store):
        self.store = store

    def cursor(self):
        return self

    def execute(self, sql, *params):
        if self.store.fail:
            raise RuntimeError("base caída")
        self.store.executed.append((sql, params))

    def close(self):
        self.store.closed += 1


class FakeDb:
    def __init__(self, fail=False):
        self.fail, self.executed, self.closed, self.connects = fail, [], 0, []

    def connect(self, connection_string, timeout):
        self.connects.append((connection_string, timeout))
        return FakeConnection(self)


def test_student_names_are_masked_in_the_args_and_the_original_is_untouched():
    safe = mask_trace(TRACE)
    assert safe["steps"][1]["args"] == {"course_name": "PRUEBA01", "student_name": "[nombre omitido]"}
    assert TRACE["steps"][1]["args"]["student_name"] == "Estudiante Dos"      # la traza original no se toca
    assert TRACE["message"] == {"text": "¿Cómo va Estudiante Dos?", "redacted": False}
    assert safe["message"] == {"text": "¿Cómo va [nombre omitido]?", "redacted": True}
    assert "Estudiante Dos" not in json.dumps(safe, ensure_ascii=False)


def test_the_name_is_masked_in_the_message_whatever_its_case():
    trace = dict(TRACE, message={"text": "cómo va ESTUDIANTE DOS y estudiante dos", "redacted": False})
    assert "studiante" not in mask_trace(trace)["message"]["text"]


def test_a_message_without_student_names_is_left_as_it_was():
    trace = dict(TRACE, steps=[], message={"text": "¿Qué cursos tengo?", "redacted": False})
    assert mask_trace(trace)["message"] == {"text": "¿Qué cursos tengo?", "redacted": False}


def test_row_matches_the_table_columns():
    row = to_row(TRACE)
    assert len(row) == traces.INSERT_SQL.count("?") == 12
    assert row[:3] == ("t-1", "r-1", 3) and row[3] == 2                      # teacher_id y course_id como enteros
    assert row[4].isoformat() == "2026-11-11T15:04:05" and row[6] == "ok" and row[9] == 1 and row[10] == 15800
    assert json.loads(row[11])["traceId"] == "t-1"


def test_non_numeric_teacher_id_or_missing_course_become_null():
    row = to_row(dict(TRACE, teacherId="abc", courseId=None))
    assert row[2] is None and row[3] is None


def test_store_inserts_one_row_with_masked_names_and_closes_the_connection():
    db = FakeDb()
    SqlServerTraceStore("DRIVER=x;SERVER=y", connect=db.connect).save(TRACE)
    sql, params = db.executed[0]
    assert sql == traces.INSERT_SQL and params[0] == "t-1" and db.closed == 1
    assert "Estudiante Dos" not in params[11] and params[11].count("[nombre omitido]") == 2
    assert TOKEN not in json.dumps(params, default=str)


def test_store_closes_the_connection_even_if_the_insert_fails():
    db = FakeDb(fail=True)
    with pytest.raises(RuntimeError):
        SqlServerTraceStore("x", connect=db.connect).save(TRACE)
    assert db.closed == 1


def test_writer_saves_in_the_background():
    db = FakeDb()
    writer = TraceWriter(SqlServerTraceStore("x", connect=db.connect))
    writer.submit(TRACE)
    assert writer.flush() and len(db.executed) == 1


def test_a_failing_database_never_raises_into_the_chat_and_is_logged_without_the_connection_string(caplog):
    db = FakeDb(fail=True)
    writer = TraceWriter(SqlServerTraceStore("PWD=secreto", connect=db.connect))
    with caplog.at_level(logging.WARNING, logger="agent.traces"):
        writer.submit(TRACE)          # no lanza
        assert writer.flush()
    assert writer.failed == 1 and "t-1" in caplog.text and "secreto" not in caplog.text


def test_a_full_queue_drops_new_traces_instead_of_growing():
    import threading

    gate = threading.Event()

    class Blocked:
        def save(self, trace):
            gate.wait(5)

    writer = TraceWriter(Blocked(), max_queue=1)
    writer.submit(TRACE)              # el hilo la toma y se bloquea
    for _ in range(50):               # espera a que el hilo la haya tomado
        if writer.queue.empty():
            break
        threading.Event().wait(0.02)
    writer.submit(TRACE)              # llena la cola
    writer.submit(TRACE)              # se descarta
    assert writer.dropped == 1
    gate.set()


def test_without_a_connection_string_traces_only_go_to_the_log():
    seen = []
    sink = build_trace_sink(None, seen.append)
    sink(TRACE)
    assert seen == [TRACE] and not hasattr(sink, "writer")


def test_with_a_connection_string_the_log_still_gets_the_trace(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(traces, "SqlServerTraceStore", lambda cs: SqlServerTraceStore(cs, connect=db.connect))
    seen = []
    sink = build_trace_sink("DRIVER=x", seen.append)
    sink(TRACE)
    assert seen == [TRACE] and sink.writer.flush() and len(db.executed) == 1


def test_the_sql_script_creates_the_agent_schema_and_the_trace_table():
    from pathlib import Path
    sql = (Path(__file__).resolve().parents[1] / "db" / "agent-schema.sql").read_text(encoding="utf-8")
    assert "CREATE SCHEMA agent" in sql and "agent.trace" in sql and "ISJSON(trace_json) = 1" in sql
    for column in ("trace_id", "teacher_id", "course_id", "started_at", "finished_at", "status", "trace_json"):
        assert column in sql
    columns = [line.split()[0].lower() for line in sql.splitlines() if line.startswith("    ") and not line.lstrip().startswith(("CONSTRAINT", "--"))]
    assert not any("jwt" in c or "token" in c or "password" in c for c in columns)
