-- scripts/init_db.sql
CREATE EXTENSION IF NOT EXISTS vector;

DROP TABLE IF EXISTS memories CASCADE;

CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    event_type TEXT,
    thematic_tags TEXT[],
    significance FLOAT,
    meaning_summary TEXT,
    embedding vector(768),
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE memories OWNER TO hari_user;
GRANT ALL PRIVILEGES ON TABLE memories TO hari_user;
CREATE INDEX memories_session_idx ON memories(session_id);
CREATE INDEX memories_embedding_idx ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);


-- Phase 6: Memory Consolidation Tables
-- Add these to your existing scripts/init_db.sql

-- Archived memories (compressed/extracted versions)
CREATE TABLE IF NOT EXISTS archived_memories (
    id TEXT PRIMARY KEY,
    original_id TEXT,
    session_id TEXT NOT NULL,
    compressed_content TEXT,
    original_significance FLOAT,
    archived_at TIMESTAMP DEFAULT NOW()
);

-- Extracted hypotheses (user/self/world beliefs)
CREATE TABLE IF NOT EXISTS hypotheses (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL,  -- 'user', 'self', 'world'
    statement TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.5,
    supporting_event_ids TEXT[],
    contradicting_event_ids TEXT[],
    last_updated TIMESTAMP,
    UNIQUE(type, statement)
);

-- Memory retrieval logs (for performance metrics)
CREATE TABLE IF NOT EXISTS memory_retrieval_logs (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    query_text TEXT,
    retrieved_count INTEGER,
    similarity_avg FLOAT,
    latency_ms FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Evaluation results storage
CREATE TABLE IF NOT EXISTS evaluation_results (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    rubric_name TEXT NOT NULL,
    score FLOAT,
    consistency FLOAT,
    reasoning TEXT,
    strengths TEXT[],
    weaknesses TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);


-- Placeholder for future episodic memory (raw turn-by-turn with higher resolution)
CREATE TABLE IF NOT EXISTS episodic_memories (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Placeholder for future semantic memory (abstracted beliefs/knowledge)
CREATE TABLE IF NOT EXISTS semantic_memories (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    confidence FLOAT DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT NOW(),
    last_referenced_at TIMESTAMP DEFAULT NOW()
);