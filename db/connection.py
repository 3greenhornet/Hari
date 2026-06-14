# hari/db/connection.py
import os
import asyncpg
from typing import Optional

_pool: Optional[asyncpg.Pool] = None

async def init_db():
    global _pool
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("⚠️ DATABASE_URL not set – running without database")
        return
    try:
        if _pool is None:
            _pool = await asyncpg.create_pool(
                dsn, 
                min_size=1, 
                max_size=5,
                server_settings={"search_path": "public"}
            )
            print("✅ Database pool connected successfully")
        
        # Systemic Validation Check: Verify if the table is actually visible to this connection
        async with _pool.acquire() as conn:
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'memories'
                );
            """)
            
            if not table_exists:
                print("⚠️ Table 'memories' not found in this connection namespace! Initializing schema inline...")
                # Ensure the vector extension is alive
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                # Explicit structural build
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
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
                """)
                print("✅ Table 'memories' permanently stabilized inside active connection schema.")
            else:
                print("✅ Verified: 'memories' table found and active.")

    except Exception as e:
        print(f"❌ Database initialization failed structurally: {e}")
        _pool = None

async def get_pool() -> Optional[asyncpg.Pool]:
    global _pool
    if _pool is None:
        await init_db()
    return _pool

async def close_db():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None