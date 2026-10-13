"""Per-session persistent pursuit registry."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

import numpy as np

from db.connection import get_pool
from models.pursuit import Pursuit
from models.volition import Desire

logger = logging.getLogger(__name__)

DEFAULT_ACTIVE_THRESHOLD = 0.30
DEFAULT_DEAD_THRESHOLD = 0.10
DEFAULT_DECAY_FACTOR = 0.95
DEFAULT_REINFORCE_WINNER = 0.08
DEFAULT_REINFORCE_TOP3 = 0.04
DEFAULT_SIMILARITY_THRESHOLD = 0.85
DEFAULT_MAX_HISTORY = 100


class PursuitRegistry:
    """Authoritative in-memory registry persisted per session."""

    def __init__(
        self,
        session_id: str,
        active_threshold: float = DEFAULT_ACTIVE_THRESHOLD,
        dead_threshold: float = DEFAULT_DEAD_THRESHOLD,
        decay_factor: float = DEFAULT_DECAY_FACTOR,
        reinforce_winner: float = DEFAULT_REINFORCE_WINNER,
        reinforce_top3: float = DEFAULT_REINFORCE_TOP3,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        max_history: int = DEFAULT_MAX_HISTORY,
    ):
        self.session_id = session_id
        self.active_threshold = active_threshold
        self.dead_threshold = dead_threshold
        self.decay_factor = decay_factor
        self.reinforce_winner = reinforce_winner
        self.reinforce_top3 = reinforce_top3
        self.similarity_threshold = similarity_threshold
        self.max_history = max_history
        self._pursuits: Dict[str, Pursuit] = {}
        self._embeddings: Dict[str, np.ndarray] = {}
        self._dirty_ids: Set[str] = set()
        self._loaded = False

    async def _ensure_loaded(self) -> None:
        """Load active pursuits once from the session-scoped database."""
        if self._loaded:
            return
        pool = await get_pool()
        if not pool:
            self._loaded = True
            return
        async with pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT id, content, source, created_turn, last_reinforced_turn,
                       strength, reinforcement_history, origin_signature,
                       target_source_id, target_item_type, is_active,
                       created_at, updated_at
                FROM pursuits
                WHERE session_id = $1 AND is_active = TRUE
                """,
                self.session_id,
            )
        for row in rows:
            pursuit = Pursuit(
                id=row["id"],
                content=row["content"],
                source=row["source"],
                created_turn=row["created_turn"],
                last_reinforced_turn=row["last_reinforced_turn"],
                strength=row["strength"],
                reinforcement_history=list(row["reinforcement_history"] or []),
                origin_signature=row["origin_signature"],
                target_source_id=row["target_source_id"],
                target_item_type=row["target_item_type"],
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            self._pursuits[pursuit.id] = pursuit
        self._loaded = True
        logger.info("Loaded %d active pursuits for session %s", len(self._pursuits), self.session_id)

    def decay(self, current_turn: int) -> None:
        """Decay strengths and deactivate pursuits below the dead threshold."""
        for pursuit_id, pursuit in self._pursuits.items():
            if not pursuit.is_active:
                continue
            pursuit.strength *= self.decay_factor
            if pursuit.strength < self.dead_threshold:
                pursuit.is_active = False
            self._dirty_ids.add(pursuit_id)

    def reinforce(self, pursuit_id: str, current_turn: int, delta: Optional[float] = None) -> None:
        """Increase an active pursuit's strength and record the turn."""
        pursuit = self._pursuits.get(pursuit_id)
        if pursuit is None or not pursuit.is_active:
            return
        pursuit.strength = min(1.0, pursuit.strength + (delta if delta is not None else self.reinforce_winner))
        pursuit.last_reinforced_turn = current_turn
        pursuit.reinforcement_history.append(current_turn)
        pursuit.reinforcement_history = pursuit.reinforcement_history[-self.max_history :]
        pursuit.updated_at = datetime.now(timezone.utc)
        self._dirty_ids.add(pursuit_id)

    def spawn_or_strengthen(
        self,
        desire: Desire,
        current_turn: int,
        desire_embedding: Optional[np.ndarray] = None,
    ) -> Optional[str]:
        """Create a pursuit or reinforce an existing semantically similar one."""
        if not desire.target_content or not desire.target_content.strip():
            return None
        existing_id = self._find_similar_pursuit(desire.target_content, desire_embedding)
        if existing_id is not None:
            self.reinforce(existing_id, current_turn, delta=self.reinforce_top3)
            return existing_id

        pursuit_id = str(uuid.uuid4())
        pursuit = Pursuit(
            id=pursuit_id,
            content=desire.target_content.strip(),
            source=desire.parent_drive,
            created_turn=current_turn,
            last_reinforced_turn=current_turn,
            strength=min(1.0, max(0.0, desire.base_tension)),
            reinforcement_history=[current_turn],
            origin_signature=desire.source_tension_id or "unknown",
            target_source_id=desire.target_source_id,
            target_item_type=desire.target_item_type,
        )
        self._pursuits[pursuit_id] = pursuit
        if desire_embedding is not None:
            self._embeddings[pursuit_id] = desire_embedding
        self._dirty_ids.add(pursuit_id)
        return pursuit_id

    def _find_similar_pursuit(
        self,
        content: str,
        content_embedding: Optional[np.ndarray],
    ) -> Optional[str]:
        """Find an active pursuit by cosine similarity or exact text fallback."""
        if content_embedding is None:
            target = content.strip().lower()
            return next(
                (
                    pursuit_id
                    for pursuit_id, pursuit in self._pursuits.items()
                    if pursuit.is_active and pursuit.content.strip().lower() == target
                ),
                None,
            )
        try:
            target_vector = content_embedding / (np.linalg.norm(content_embedding) + 1e-8)
        except Exception:
            return None
        best_id: Optional[str] = None
        best_similarity = 0.0
        for pursuit_id, pursuit in self._pursuits.items():
            if not pursuit.is_active or pursuit_id not in self._embeddings:
                continue
            try:
                existing_vector = self._embeddings[pursuit_id]
                existing_vector = existing_vector / (np.linalg.norm(existing_vector) + 1e-8)
                similarity = float(np.dot(target_vector, existing_vector))
            except Exception:
                continue
            if similarity > best_similarity:
                best_similarity = similarity
                best_id = pursuit_id
        return best_id if best_id is not None and best_similarity >= self.similarity_threshold else None

    def get_active(self) -> List[Pursuit]:
        """Return active pursuits at or above the active threshold."""
        active = [
            pursuit
            for pursuit in self._pursuits.values()
            if pursuit.is_active and pursuit.strength >= self.active_threshold
        ]
        return sorted(active, key=lambda pursuit: pursuit.strength, reverse=True)

    def get_all_active(self) -> List[Pursuit]:
        """Return all pursuits marked active, including weak ones."""
        return [pursuit for pursuit in self._pursuits.values() if pursuit.is_active]

    async def flush_updates(self) -> None:
        """Persist dirty pursuits and retain dirty IDs if persistence fails."""
        if not self._dirty_ids:
            return
        pool = await get_pool()
        if not pool:
            return
        dirty = list(self._dirty_ids)
        self._dirty_ids = set()
        try:
            async with pool.acquire() as connection:
                async with connection.transaction():
                    for pursuit_id in dirty:
                        pursuit = self._pursuits.get(pursuit_id)
                        if pursuit is None:
                            continue
                        await connection.execute(
                            """
                            INSERT INTO pursuits (
                                id, session_id, content, source, created_turn,
                                last_reinforced_turn, strength, reinforcement_history,
                                origin_signature, target_source_id, target_item_type,
                                is_active, created_at, updated_at
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::int[],
                                      $9, $10, $11, $12, $13, $14)
                            ON CONFLICT (id) DO UPDATE SET
                                strength = EXCLUDED.strength,
                                last_reinforced_turn = EXCLUDED.last_reinforced_turn,
                                reinforcement_history = EXCLUDED.reinforcement_history,
                                is_active = EXCLUDED.is_active,
                                updated_at = EXCLUDED.updated_at
                            """,
                            pursuit.id,
                            self.session_id,
                            pursuit.content,
                            pursuit.source,
                            pursuit.created_turn,
                            pursuit.last_reinforced_turn,
                            pursuit.strength,
                            pursuit.reinforcement_history,
                            pursuit.origin_signature,
                            pursuit.target_source_id,
                            pursuit.target_item_type,
                            pursuit.is_active,
                            pursuit.created_at,
                            pursuit.updated_at,
                        )
        except Exception:
            logger.exception("Failed to flush pursuit updates")
            self._dirty_ids.update(dirty)

    def snapshot(self) -> dict:
        """Return a diagnostic snapshot."""
        active = self.get_active()
        return {
            "active_count": len(active),
            "total_count": len(self._pursuits),
            "top_pursuits": [
                {
                    "content": pursuit.content[:100],
                    "strength": round(pursuit.strength, 3),
                    "reinforcements": len(pursuit.reinforcement_history),
                    "age_turns": pursuit.last_reinforced_turn - pursuit.created_turn,
                }
                for pursuit in active[:5]
            ],
        }
