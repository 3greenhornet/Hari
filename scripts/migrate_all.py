#!/usr/bin/env python
# scripts/migrate_all.py
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def run_migration():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("❌ DATABASE_URL not set")
        return
    
    conn = await asyncpg.connect(dsn)
    try:
        # Enable vector extension if not already
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # ===== 1. Update memories table with new columns =====
        # Add columns one by one (IF NOT EXISTS)
        await conn.execute("""
            ALTER TABLE memories 
            ADD COLUMN IF NOT EXISTS usage_count INT DEFAULT 0,
            ADD COLUMN IF NOT EXISTS last_retrieved_turn INT DEFAULT 0,
            ADD COLUMN IF NOT EXISTS explanatory_power FLOAT DEFAULT 0.5,
            ADD COLUMN IF NOT EXISTS promoted_to_hypothesis BOOLEAN DEFAULT FALSE;
        """)
        print("✅ memories table updated with new columns.")
        
        # ===== 2. Create archived_memories if not exists =====
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS archived_memories (
                id TEXT PRIMARY KEY,
                original_id TEXT,
                session_id TEXT NOT NULL,
                compressed_content TEXT,
                original_significance FLOAT,
                archived_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # ===== 3. Create hypotheses if not exists =====
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS hypotheses (
                id SERIAL PRIMARY KEY,
                type TEXT NOT NULL,
                statement TEXT NOT NULL,
                confidence FLOAT DEFAULT 0.5,
                supporting_event_ids TEXT[],
                contradicting_event_ids TEXT[],
                last_updated TIMESTAMP,
                UNIQUE(type, statement)
            );
        """)
        
        # ===== 4. Create memory_retrieval_logs if not exists =====
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_retrieval_logs (
                id SERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                query_text TEXT,
                retrieved_count INTEGER,
                similarity_avg FLOAT,
                latency_ms FLOAT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # ===== 5. Create evaluation_results if not exists =====
        await conn.execute("""
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
        """)
        
        # ===== 6. Create narrative_threads table =====
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS narrative_threads (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT CHECK (status IN ('active', 'paused', 'completed', 'abandoned')) DEFAULT 'active',
                completion_estimate FLOAT DEFAULT 0.0,
                emotional_investment FLOAT DEFAULT 0.5,
                open_questions TEXT[] DEFAULT '{}',
                related_memory_ids TEXT[] DEFAULT '{}',
                related_curiosity_node_ids TEXT[] DEFAULT '{}',
                created_turn INT NOT NULL,
                last_active_turn INT NOT NULL,
                created_at TIMESTAMP NOT NULL
            );
        """)
        # ===== 8. Create curiosity_nodes and curiosity_edges =====
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS curiosity_nodes (
                id TEXT PRIMARY KEY,
                core_question TEXT NOT NULL,
                importance FLOAT DEFAULT 0.5,
                exploration_progress FLOAT DEFAULT 0.0,
                last_referenced TIMESTAMP DEFAULT NOW(),
                properties JSONB DEFAULT '{}'
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS curiosity_edges (
                source_id TEXT REFERENCES curiosity_nodes(id) ON DELETE CASCADE,
                target_id TEXT REFERENCES curiosity_nodes(id) ON DELETE CASCADE,
                weight FLOAT DEFAULT 0.0,
                PRIMARY KEY (source_id, target_id)
            );
        """)

        # Optional: Add index on curiosity_nodes for faster queries
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_curiosity_nodes_importance ON curiosity_nodes(importance DESC);")
                
        # ===== 7. Create missing indexes =====
        await conn.execute("CREATE INDEX IF NOT EXISTS memories_session_idx ON memories(session_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_promoted ON memories(promoted_to_hypothesis, significance);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_narrative_threads_session ON narrative_threads(session_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_narrative_threads_status ON narrative_threads(status);")
        
        print("✅ All migrations completed successfully.")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())