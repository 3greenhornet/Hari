"""
models/narrative.py — First‑class narrative thread model.
Persistent cognitive concerns that compete for workspace attention.
No activation or decay logic – pure storage and formatting.
"""

# IMPORTANT: No activation, persistence, or decay fields here.
# These are computed dynamically by the workspace engine at runtime.

import uuid
from datetime import datetime, timezone
from typing import List, Literal
from pydantic import BaseModel, Field, ConfigDict


class NarrativeThread(BaseModel):
    """A persistent narrative thread – "why am I still thinking about this?" """
    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    title: str = Field(..., max_length=100)
    description: str = Field(..., max_length=500)
    status: Literal["active", "paused", "completed", "abandoned"] = "active"

    # Cognitive anchors (used by workspace to compute salience)
    completion_estimate: float = Field(0.0, ge=0.0, le=1.0)   # 0 = just started, 1 = resolved
    emotional_investment: float = Field(0.5, ge=0.0, le=1.0)   # 0 = indifferent, 1 = deeply invested

    # Relational links
    open_questions: List[str] = Field(default_factory=list)
    related_memory_ids: List[str] = Field(default_factory=list)
    related_curiosity_node_ids: List[str] = Field(default_factory=list)

    # Temporal tracking (used for fatigue calculation in workspace)
    created_turn: int
    last_active_turn: int

    # TIMESTAMP WITH TIME ZONE – follows modern Python best practices
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_workspace_string(self, max_length: int = 200) -> str:
        """Format for injection into the workspace prompt."""
        # Let the workspace handle truncation globally; this method stays pure.
        urgency = 1.0 - self.completion_estimate
        return f"[Narrative: {self.title}] (Unresolved: {urgency:.2f}): {self.description[:max_length]}"

    def should_decay(self, current_turn: int, threshold: int = 30) -> bool:
        """Determine if this thread is stale (not used for turning, just for optional pruning)."""
        return (current_turn - self.last_active_turn) > threshold