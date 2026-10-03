"""Persistent cognitive state across turns."""

import os
from typing import Dict, List

from pydantic import BaseModel, Field


MAX_ITEMS = int(os.getenv("MAX_ACTIVE_THOUGHTS", "20"))
DECAY_RATE = float(os.getenv("THOUGHT_DECAY", "0.92"))
FLOOR = float(os.getenv("THOUGHT_FLOOR", "0.08"))
PROMOTE_THRESHOLD = float(os.getenv("THOUGHT_PROMOTE_THRESHOLD", "0.45"))


class ActiveThought(BaseModel):
    """A single persistent thought."""

    text: str
    activation: float = Field(ge=0.0, le=1.0)
    origin: str = "internal"
    created_turn: int = 0
    last_turn: int = 0
    updates: int = 0
    source_type: str = "unknown"


class ActiveThoughtStore:
    """Working memory that survives turns."""

    def __init__(
        self,
        max_items: int = MAX_ITEMS,
        decay_rate: float = DECAY_RATE,
        floor: float = FLOOR,
        promote_threshold: float = PROMOTE_THRESHOLD,
    ):
        self._items: Dict[str, ActiveThought] = {}
        self.max_items = max_items
        self.decay_rate = decay_rate
        self.floor = floor
        self.promote_threshold = promote_threshold

    @staticmethod
    def _key(text: str) -> str:
        return text.strip().lower()

    def upsert(
        self,
        text: str,
        activation: float,
        origin: str,
        turn: int,
        source_type: str = "unknown",
    ) -> None:
        """Add or reinforce a thought without lowering its activation."""
        key = self._key(text)
        if not key:
            return
        existing = self._items.get(key)
        if existing:
            existing.activation = min(1.0, max(existing.activation, activation))
            existing.last_turn = turn
            existing.updates += 1
        else:
            self._items[key] = ActiveThought(
                text=text.strip(),
                activation=min(1.0, max(0.0, activation)),
                origin=origin,
                created_turn=turn,
                last_turn=turn,
                source_type=source_type,
            )

    def observe_winners(self, winners: List, turn: int) -> int:
        """Persist eligible strong workspace items and return the count."""
        promoted = 0
        for winner in winners:
            content = getattr(winner, "content", "") or ""
            if not content.strip():
                continue
            item_type = getattr(winner, "item_type", "unknown")
            payload = getattr(winner, "payload", {}) or {}
            source = payload.get("source", "")

            eligible = (
                item_type
                in ("open_thought", "curiosity_node", "narrative_thread", "hypothesis")
                or source
                in (
                    "internal_cognition",
                    "volition",
                    "curiosity_spreading",
                    "volition_persistent",
                )
            )
            if not eligible:
                continue

            activation = float(payload.get("_total_salience", 0.0) or 0.0)
            if activation < self.promote_threshold:
                continue

            self.upsert(
                text=content,
                activation=activation,
                origin=source or "internal",
                turn=turn,
                source_type=item_type,
            )
            promoted += 1
        return promoted

    def decay_all(self) -> None:
        """Apply geometric decay and drop thoughts below the floor."""
        for key, item in list(self._items.items()):
            item.activation *= self.decay_rate
            if item.activation < self.floor:
                del self._items[key]

    def trim(self) -> None:
        """Keep the top-N thoughts by activation."""
        if len(self._items) <= self.max_items:
            return
        sorted_items = sorted(
            self._items.values(), key=lambda thought: thought.activation, reverse=True
        )
        self._items = {
            self._key(thought.text): thought
            for thought in sorted_items[: self.max_items]
        }

    def top(self, n: int = 8) -> List[ActiveThought]:
        """Return the top-n thoughts by activation."""
        return sorted(
            self._items.values(), key=lambda thought: thought.activation, reverse=True
        )[:n]

    def texts(self, n: int = 8) -> List[str]:
        """Return the text of the top-n thoughts."""
        return [thought.text for thought in self.top(n)]

    def resolve(self, substring: str) -> None:
        """Drop thoughts containing the supplied substring."""
        normalized = substring.strip().lower()
        if not normalized:
            return
        for key in [key for key in self._items if normalized in key]:
            del self._items[key]

    def all(self) -> List[ActiveThought]:
        """Return every stored thought."""
        return list(self._items.values())

    def snapshot(self) -> dict:
        """Return a diagnostic snapshot for telemetry."""
        return {
            "count": len(self._items),
            "top": [
                {
                    "text": thought.text[:80],
                    "activation": round(thought.activation, 3),
                    "updates": thought.updates,
                    "source_type": thought.source_type,
                }
                for thought in self.top(5)
            ],
        }
