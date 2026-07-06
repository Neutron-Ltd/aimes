-- Chat history persistence (optional PostgreSQL deployment)
--
-- Usage: psql "$DATABASE_URL" -f db/migrations/002_chat_history.sql
-- Runtime chat store uses local SQLite (CHAT_DB_PATH); this migration documents the PG schema.
CREATE TABLE IF NOT EXISTS n2admin.chat_messages (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workshop_id       VARCHAR(64) NOT NULL,
    assistant_module  VARCHAR(32) NOT NULL,
    role              VARCHAR(16) NOT NULL CHECK (role IN ('user', 'assistant', 'error')),
    content           TEXT NOT NULL,
    response_json     JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_workshop_module_created
    ON n2admin.chat_messages (workshop_id, assistant_module, created_at);
