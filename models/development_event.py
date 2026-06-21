# models/development_event.py
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import List, Optional, Literal, Dict, Any
import uuid


class SourceContribution(BaseModel):
    id: str
    item_type: Literal["memory", "curiosity", "narrative", "identity", "user_message"]
    contribution_weight: float = Field(ge=0.0, le=1.0)


class DevelopmentEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    turn_number: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    event_type: Literal[
        "promotion_attempt",
        "promotion_success",
        "promotion_decay",
        "interest_formed",
        "interest_strengthened",
        "interest_weakened",
        "identity_anchor_formed",
        "narrative_created",
        "narrative_archived"
    ]

    source_attribution: List[SourceContribution] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = Field(..., min_length=1)

    # Foreign key to system_interests
    interest_id: Optional[str] = None
    old_strength: Optional[float] = Field(None, ge=0.0, le=1.0)
    new_strength: Optional[float] = Field(None, ge=0.0, le=1.0)

    narrative_id: Optional[str] = None
    narrative_title: Optional[str] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_persistence_payload(self) -> Dict[str, Any]:
        """Convert nested models to primitives for asyncpg."""
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "turn_number": self.turn_number,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "source_attribution": [src.model_dump() for src in self.source_attribution],
            "confidence": self.confidence,
            "reason": self.reason,
            "interest_id": self.interest_id,
            "old_strength": self.old_strength,
            "new_strength": self.new_strength,
            "narrative_id": self.narrative_id,
            "narrative_title": self.narrative_title,
            "metadata": self.metadata
        }