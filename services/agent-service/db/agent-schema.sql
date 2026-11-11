-- Esquema `agent` de SQL Server: una traza por mensaje del chat (docs/agent-design/diseno-agente.md, sección 5).
-- Idempotente: se puede ejecutar varias veces. No guarda el JWT ni la salida completa de las herramientas.
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'agent') EXEC('CREATE SCHEMA agent');
GO

IF OBJECT_ID('agent.trace', 'U') IS NULL
CREATE TABLE agent.trace (
    trace_id     NVARCHAR(64)  NOT NULL PRIMARY KEY,
    request_id   NVARCHAR(64)  NULL,
    teacher_id   INT           NULL,          -- id del docente en auth.user (el `sub` del JWT)
    course_id    INT           NULL,          -- solo si la interfaz indicó un curso de referencia
    started_at   DATETIME2(0)  NOT NULL,
    finished_at  DATETIME2(0)  NOT NULL,
    status       NVARCHAR(16)  NOT NULL,      -- ok | partial | refused | error
    intent       NVARCHAR(32)  NULL,
    model        NVARCHAR(64)  NULL,
    tool_calls   INT           NOT NULL DEFAULT 0,
    duration_ms  INT           NULL,
    trace_json   NVARCHAR(MAX) NOT NULL,      -- la traza completa de la sección 5, sin nombres de estudiante en los argumentos
    CONSTRAINT ck_agent_trace_json CHECK (ISJSON(trace_json) = 1),
    CONSTRAINT ck_agent_trace_status CHECK (status IN ('ok', 'partial', 'refused', 'error'))
);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_agent_trace_teacher' AND object_id = OBJECT_ID('agent.trace'))
CREATE INDEX ix_agent_trace_teacher ON agent.trace (teacher_id, started_at DESC);
GO
