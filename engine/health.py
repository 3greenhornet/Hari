# engine/health.py  (corrected)
from datetime import datetime, UTC
from typing import Dict, Any
import logging

from db.connection import get_pool

logger = logging.getLogger(__name__)

async def get_health_metrics(session_id: str) -> Dict[str, Any]:
    """
    Single-pass health metric aggregation.
    Uses DISTINCT ON to get the latest state of each unique interest.
    """
    pool = await get_pool()
    if not pool:
        return {"error": "Database connection pool unavailable"}

    metrics_sql = """
        WITH trace_stats AS (
            SELECT 
                COUNT(*) as total_turns,
                COUNT(*) FILTER (WHERE retrieved_candidate_count = 0) as empty_turns,
                MAX(timestamp) as last_turn_time
            FROM decision_traces
            WHERE session_id = $1
        ),
        ledger_stats AS (
            SELECT
                COUNT(*) FILTER (WHERE event_type = 'promotion_attempt') as attempts,
                COUNT(*) FILTER (WHERE event_type = 'promotion_success') as successes
            FROM development_events
            WHERE session_id = $1
        ),
        current_interest_strengths AS (
            SELECT DISTINCT ON (interest_id) 
                interest_name,
                new_strength,
                event_type
            FROM development_events
            WHERE session_id = $1 
              AND interest_id IS NOT NULL
            ORDER BY interest_id, sequence_number DESC
        )
        SELECT 
            COALESCE(ts.total_turns, 0) as total_turns,
            COALESCE(ts.empty_turns, 0) as empty_turns,
            ts.last_turn_time,
            COALESCE(ls.attempts, 0) as attempts,
            COALESCE(ls.successes, 0) as successes,
            COALESCE(jsonb_agg(cis.interest_name) FILTER (
                WHERE cis.new_strength > 0.0 AND cis.event_type != 'promotion_decay'
            ), '[]'::jsonb) as active_interests,
            COALESCE(jsonb_agg(cis.interest_name) FILTER (
                WHERE cis.event_type = 'identity_anchor_formed'
            ), '[]'::jsonb) as identity_anchors
        FROM trace_stats ts
        CROSS JOIN ledger_stats ls
        CROSS JOIN current_interest_strengths cis
        GROUP BY ts.total_turns, ts.empty_turns, ts.last_turn_time, ls.attempts, ls.successes;
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(metrics_sql, session_id)
            if not row:
                return {
                    "turns": 0,
                    "workspace_empty_rate": 0.0,
                    "promotion_attempts": 0,
                    "promotion_successes": 0,
                    "active_interests": [],
                    "identity_anchors": [],
                    "status": "initialized",
                    "timestamp": datetime.now(UTC).isoformat()
                }

            turns = row["total_turns"]
            empty_turns = row["empty_turns"] or 0
            empty_rate = (empty_turns / turns) if turns > 0 else 0.0

            return {
                "turns": turns,
                "workspace_empty_rate": round(empty_rate, 4),
                "promotion_attempts": row["attempts"] or 0,
                "promotion_successes": row["successes"] or 0,
                "active_interests": list(set(row["active_interests"] or [])),
                "identity_anchors": list(set(row["identity_anchors"] or [])),
                "last_activity": row["last_turn_time"].isoformat() if row["last_turn_time"] else None,
                "status": "healthy" if empty_rate < 0.01 else "degraded",
                "timestamp": datetime.now(UTC).isoformat()
            }
    except Exception as err:
        logger.error(f"Failed to generate health metrics: {err}", exc_info=True)
        return {"error": f"Metrics compilation failed: {str(err)}"}