# scripts/reset_db.ps1
$sql = @"
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
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hari_user;
CREATE INDEX memories_session_idx ON memories(session_id);
CREATE INDEX memories_embedding_idx ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
"@

$sql | docker exec -i hari-postgres psql -U postgres -d hari_cognitive
Write-Host "✅ Database reset with vector(768) and correct ownership"