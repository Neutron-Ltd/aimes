-- RAG pgvector migration (run with admin privileges)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS n2admin.ai_knowledge_chunks (
    id UUID PRIMARY KEY,
    doc_type VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),
    data_auth VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_knowledge_data_auth
    ON n2admin.ai_knowledge_chunks (data_auth);

CREATE INDEX IF NOT EXISTS idx_ai_knowledge_embedding
    ON n2admin.ai_knowledge_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
