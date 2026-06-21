# engine/development.py
import json
import logging
from typing import Optional
from db.connection import get_pool
from models.development_event import DevelopmentEvent

logger = logging.getLogger(__name__)


async def store_development_event(event: DevelopmentEvent) -> bool:
    """Store a development event with proper JSONB serialization."""
    pool = await get_pool()
    if not pool:
        logger.error("Database pool unavailable; event not stored.")
        return False

    payload = event.to_persistence_payload()

    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO development_events (
                    event_id, session_id, turn_number, timestamp,
                    event_type, source_attribution, confidence, reason,
                    interest_id, old_strength, new_strength,
                    narrative_id, narrative_title, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9, $10, $11, $12, $13, $14::jsonb)
            """,
                payload["event_id"],
                payload["session_id"],
                payload["turn_number"],
                payload["timestamp"],
                payload["event_type"],
                json.dumps(payload["source_attribution"]),
                payload["confidence"],
                payload["reason"],
                payload["interest_id"],
                payload["old_strength"],
                payload["new_strength"],
                payload["narrative_id"],
                payload["narrative_title"],
                json.dumps(payload["metadata"])
            )
            return True
    except Exception as e:
        logger.error(f"Failed to store development event: {e}", exc_info=True)
        return False