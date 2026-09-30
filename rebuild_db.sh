#!/bin/bash
set -e

echo "Stopping and removing old container..."
docker stop hari-postgres 2>/dev/null || true
docker rm hari-postgres 2>/dev/null || true

echo "Creating volume..."
docker volume create hari_postgres_data

echo "Starting new pgvector container..."
docker run -d --name hari-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=hari_cognitive \
  -p 5432:5432 \
  -v hari_postgres_data:/var/lib/postgresql/data \
  pgvector/pgvector:pg16

echo "Waiting for Postgres to be ready..."
sleep 8

echo "Creating vector extension..."
docker exec -i hari-postgres psql -U postgres -d hari_cognitive -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo "Running init_db.sql..."
docker exec -i hari-postgres psql -U postgres -d hari_cognitive < scripts/init_db.sql

echo "Running migrations..."
docker exec -i hari-postgres psql -U postgres -d hari_cognitive < db/migrations/002_decision_trace.sql
docker exec -i hari-postgres psql -U postgres -d hari_cognitive < db/migrations/003_development_ledger.sql
docker exec -i hari-postgres psql -U postgres -d hari_cognitive < db/migrations/004_hybrid_retrieval.sql

echo "Adding custom columns and indexes..."
docker exec -i hari-postgres psql -U postgres -d hari_cognitive -c "
ALTER TABLE memories ADD COLUMN IF NOT EXISTS valence FLOAT DEFAULT 0.0;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS arousal FLOAT DEFAULT 0.0;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS behavior_mode TEXT;
ALTER TABLE decision_traces ADD COLUMN IF NOT EXISTS behavior_source TEXT;
ALTER TABLE trace_workspace_items ADD COLUMN IF NOT EXISTS origin TEXT;
ALTER TABLE trace_workspace_items ADD COLUMN IF NOT EXISTS activated_by TEXT;
ALTER TABLE trace_workspace_items ADD COLUMN IF NOT EXISTS intrinsic_relevance REAL DEFAULT 0.0;
ALTER TABLE trace_workspace_items ADD COLUMN IF NOT EXISTS persistence REAL DEFAULT 0.0;
UPDATE hypotheses SET type = 'other' WHERE type = 'user';
DROP INDEX IF EXISTS memories_embedding_idx;
CREATE INDEX IF NOT EXISTS memories_embedding_hnsw_idx ON memories USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE TABLE IF NOT EXISTS patterns (
    pattern_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    description TEXT NOT NULL,
    supporting_memory_ids TEXT[],
    supporting_trace_ids TEXT[],
    cluster_similarity FLOAT,
    significance FLOAT,
    status TEXT,
    created_turn INT,
    last_updated_turn INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS contradictions (
    contradiction_id TEXT PRIMARY KEY,
    belief_a TEXT,
    belief_b TEXT,
    source_a TEXT,
    source_b TEXT,
    severity FLOAT,
    status TEXT,
    exposure_count INT DEFAULT 0,
    linked_curiosity_node_ids TEXT[],
    resolution_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);
"

echo "Verification..."
docker exec -i hari-postgres psql -U postgres -d hari_cognitive -c "\dt"

echo "✅ Database rebuilt successfully!"
echo "You can now run: python scripts/run_observatory.py"