import uuid
from typing import List, Optional
from db.connection import get_pool

class SelfBeliefManager:
    @staticmethod
    async def store(session_id: str, belief_text: str) -> None:
        """Store a self‑belief in the database."""
        pool = await get_pool()
        if not pool:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO self_beliefs (id, session_id, belief_text) VALUES ($1, $2, $3)",
                str(uuid.uuid4()), session_id, belief_text
            )

    @staticmethod
    async def get_active(session_id: str, limit: int = 3) -> List[str]:
        """Retrieve recent active self‑beliefs."""
        pool = await get_pool()
        if not pool:
            return []
        rows = await pool.fetch(
            "SELECT belief_text FROM self_beliefs WHERE session_id = $1 AND is_active = TRUE ORDER BY created_at DESC LIMIT $2",
            session_id, limit
        )
        return [row["belief_text"] for row in rows]
