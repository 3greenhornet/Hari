# hari/db/connection.py
import os
import asyncpg
from typing import Optional
from pgvector.asyncpg import register_vector

_pool: Optional[asyncpg.Pool] = None


async def init_db():
    global _pool
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("⚠️ DATABASE_URL not set – running without database")
        return
    try:
        if _pool is None:
            # The vector extension must exist BEFORE create_pool runs init=register_vector.
            # register_vector requires the 'vector' type to already be present in the
            # database, and asyncpg opens the first connection eagerly during pool
            # creation. So we bootstrap the extension on a plain connection first.
            bootstrap_conn = await asyncpg.connect(dsn)
            try:
                await bootstrap_conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            finally:
                await bootstrap_conn.close()

            _pool = await asyncpg.create_pool(
                dsn,
                min_size=1,
                max_size=5,
                init=register_vector,
                server_settings={"search_path": "public"}
            )
            print("✅ Database pool connected successfully")

        # Verify the memories table is visible to this connection.
        async with _pool.acquire() as conn:
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'memories'
                );
            """)

            if not table_exists:
                print("⚠️ Table 'memories' not found! Initializing schema inline...")
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
                        embedding vector(3072),
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)
                print("✅ Table 'memories' stabilized.")
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