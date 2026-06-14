"""
models/thought.py — Incomplete processing loops.
Thoughts are active, in‑progress cognition, not stored knowledge.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Thought(BaseModel):
    """A fragment of unfinished reasoning or interrupted cognitive process."""
    id: str
    content: str
    originating_turn: int
    last_active_turn: int
    interruption_status: bool = Field(default=False)
    execution_pressure: float = Field(default=0.6, ge=0.0, le=1.0)
    context_summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def is_stale(self, current_turn: int, threshold: int = 50) -> bool:
        """Thought that hasn't been resumed for many turns may be abandoned."""
        return (current_turn - self.last_active_turn) > threshold

    def boost_pressure(self, delta: float = 0.1) -> None:
        self.execution_pressure = min(1.0, self.execution_pressure + delta)