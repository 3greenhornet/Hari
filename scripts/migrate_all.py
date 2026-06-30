# hari/scripts/migrate_all.py
"""
Centralized database migration script for Hari.
Manages schema changes across all components (memories, hypotheses, etc.).
"""

import asyncio
import logging
from db.connection import get_pool
from engine.memory_consolidation import CONSOLIDATION_SCHEMA

logger = logging.getLogger(__name__)

async def migrate_database() -> None:
    """Applies all necessary SQL migrations to the PostgreSQL database."""
    pool = await get_pool()
    if not pool:
        logger.error("Failed to get database connection pool. Exiting migration.")
        return

    async with pool.acquire() as conn:
        logger.info("Applying migrations...")

        # Apply Memory Consolidation schema (includes memories, archived_memories, hypotheses)
        await conn.execute(CONSOLIDATION_SCHEMA)

        # Add self_beliefs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS self_beliefs (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                belief_text TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE
            );
            CREATE INDEX IF NOT EXISTS idx_self_beliefs_session ON self_beliefs(session_id);
        """)

        logger.info("All migrations applied successfully.")

    await pool.close()

async def main():
    logging.basicConfig(level=logging.INFO)
    await migrate_database()

if __name__ == "__main__":
    asyncio.run(main())
