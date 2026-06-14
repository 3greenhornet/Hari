# hari/engine/narrative_manager.py
"""
Persistent narrative thread manager with PostgreSQL.
Cache‑first, batch updates, explicit array casting, timezone‑aware datetimes.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Set, Dict

from db.connection import get_pool
from models.narrative import NarrativeThread

logger = logging.getLogger(__name__)


class NarrativeManager:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._cache: Dict[str, NarrativeThread] = {}
        self._cache_loaded = False
        self._dirty_ids: Set[str] = set()  # IDs needing last_active_turn update

    async def _ensure_cache(self) -> None:
        """Load all active threads from DB if not already loaded."""
        if self._cache_loaded:
            return
        pool = await get_pool()
        if not pool:
            return
        rows = await pool.fetch("""
            SELECT * FROM narrative_threads
            WHERE session_id = $1 AND status = 'active'
        """, self.session_id)
        for row in rows:
            thread = NarrativeThread(
                id=row["id"],
                session_id=row["session_id"],
                title=row["title"],
                description=row["description"],
                status=row["status"],
                completion_estimate=row["completion_estimate"],
                emotional_investment=row["emotional_investment"],
                open_questions=row["open_questions"] or [],
                related_memory_ids=row["related_memory_ids"] or [],
                related_curiosity_node_ids=row["related_curiosity_node_ids"] or [],
                created_turn=row["created_turn"],
                last_active_turn=row["last_active_turn"],
                created_at=row["created_at"],
                last_modified_at=row["last_modified_at"],
            )
            self._cache[thread.id] = thread
        self._cache_loaded = True

    async def load_active_threads(self, current_turn: int, limit: int = 10) -> List[NarrativeThread]:
        """Return active threads, most recent first. Loads cache once."""
        await self._ensure_cache()
        active = [t for t in self._cache.values() if t.status == "active"]
        active.sort(key=lambda t: t.last_active_turn, reverse=True)
        return active[:limit]

    async def get_thread(self, thread_id: str) -> Optional[NarrativeThread]:
        """Get a single thread by ID (cache‑first)."""
        if thread_id in self._cache:
            return self._cache[thread_id]
        pool = await get_pool()
        if not pool:
            return None
        row = await pool.fetchrow("SELECT * FROM narrative_threads WHERE id = $1", thread_id)
        if not row:
            return None
        thread = NarrativeThread(
            id=row["id"],
            session_id=row["session_id"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            completion_estimate=row["completion_estimate"],
            emotional_investment=row["emotional_investment"],
            open_questions=row["open_questions"] or [],
            related_memory_ids=row["related_memory_ids"] or [],
            related_curiosity_node_ids=row["related_curiosity_node_ids"] or [],
            created_turn=row["created_turn"],
            last_active_turn=row["last_active_turn"],
            created_at=row["created_at"],
            last_modified_at=row["last_modified_at"],
        )
        self._cache[thread.id] = thread
        return thread

    async def create_thread(
        self,
        title: str,
        description: str,
        current_turn: int,
        completion_estimate: float = 0.0,
        emotional_investment: float = 0.5,
        open_questions: Optional[List[str]] = None,
        related_memory_ids: Optional[List[str]] = None,
    ) -> NarrativeThread:
        """Create and persist a new narrative thread."""
        thread = NarrativeThread(
            session_id=self.session_id,
            title=title.strip(),
            description=description.strip(),
            completion_estimate=completion_estimate,
            emotional_investment=emotional_investment,
            open_questions=open_questions or [],
            related_memory_ids=related_memory_ids or [],
            created_turn=current_turn,
            last_active_turn=current_turn,
        )
        pool = await get_pool()
        if pool:
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO narrative_threads (
                        id, session_id, title, description, status,
                        completion_estimate, emotional_investment,
                        open_questions, related_memory_ids, related_curiosity_node_ids,
                        created_turn, last_active_turn, created_at, last_modified_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::TEXT[], $9::TEXT[], $10::TEXT[], $11, $12, $13, $14)
                """, thread.id, thread.session_id, thread.title, thread.description, thread.status,
                   thread.completion_estimate, thread.emotional_investment,
                   thread.open_questions, thread.related_memory_ids, thread.related_curiosity_node_ids,
                   thread.created_turn, thread.last_active_turn, thread.created_at, thread.last_modified_at)
        self._cache[thread.id] = thread
        self._dirty_ids.add(thread.id)
        logger.info(json.dumps({
            "event": "narrative_thread_created",
            "session_id": self.session_id,
            "thread_id": thread.id,
            "title": thread.title,
            "turn": current_turn,
        }))
        return thread

    def mark_attended(self, thread_id: str, current_turn: int) -> None:
        """Mark thread as attended this turn – deferred batch update."""
        if thread_id in self._cache:
            self._cache[thread_id].last_active_turn = current_turn
            self._cache[thread_id].last_modified_at = datetime.now(timezone.utc)
            self._dirty_ids.add(thread_id)

    async def flush_updates(self) -> None:
        """Batch update last_active_turn and last_modified_at for all attended threads."""
        if not self._dirty_ids:
            return
        pool = await get_pool()
        if not pool:
            return
        async with pool.acquire() as conn:
            async with conn.transaction():
                for tid in list(self._dirty_ids):
                    thread = self._cache.get(tid)
                    if thread:
                        await conn.execute("""
                            UPDATE narrative_threads
                            SET last_active_turn = $1, last_modified_at = $2
                            WHERE id = $3
                        """, thread.last_active_turn, thread.last_modified_at, tid)
                    self._dirty_ids.discard(tid)

    async def update_thread(
        self,
        thread_id: str,
        completion_delta: float = 0.0,
        investment_delta: float = 0.0,
        status: Optional[str] = None,
        open_questions: Optional[List[str]] = None,
    ) -> Optional[NarrativeThread]:
        """Update a thread's metrics (both cache and database)."""
        if thread_id not in self._cache:
            return None
        thread = self._cache[thread_id]
        new_completion = max(0.0, min(1.0, thread.completion_estimate + completion_delta))
        new_investment = max(0.0, min(1.0, thread.emotional_investment + investment_delta))
        new_status = status if status else thread.status
        new_questions = open_questions if open_questions is not None else thread.open_questions
        pool = await get_pool()
        if pool:
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE narrative_threads
                    SET completion_estimate = $1,
                        emotional_investment = $2,
                        status = $3,
                        open_questions = $4::TEXT[],
                        last_modified_at = $5
                    WHERE id = $6
                """, new_completion, new_investment, new_status, new_questions,
                   datetime.now(timezone.utc), thread_id)
        thread.completion_estimate = new_completion
        thread.emotional_investment = new_investment
        thread.status = new_status
        thread.open_questions = new_questions
        thread.last_modified_at = datetime.now(timezone.utc)
        return thread

    # Alias for backward compatibility if any code expects get_active_threads
    async def get_active_threads(self, current_turn: int, limit: int = 10) -> List[NarrativeThread]:
        return await self.load_active_threads(current_turn, limit)