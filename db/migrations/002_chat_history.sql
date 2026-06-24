-- Chat history persistence (run with admin privileges on the MES PostgreSQL instance)
--
-- Usage: psql "$DATABASE_URL" -f db/migrations/002_chat_history.sql
-- Required before server-side chat history will work in the frontend.
CREATE TABLE IF NOT EXISTS n2admin.chat_messages (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workshop_id   VARCHAR(64) NOT NULL,
    role          VARCHAR(16) NOT NULL CHECK (role IN ('user', 'assistant', 'error')),
    content       TEXT NOT NULL,
    response_json JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_workshop_created
    ON n2admin.chat_messages (workshop_id, created_at);
