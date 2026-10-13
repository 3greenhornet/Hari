"""Persistent pursuit data model."""

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class Pursuit(BaseModel):
    """A persistent goal maintained across turns."""

    id: str = Field(..., description="Unique identifier (UUID string)")
    content: str = Field(..., description="What Hari is pursuing")
    source: str = Field(..., description="Which drive generated this pursuit")
    created_turn: int = Field(..., description="Turn of creation")
    last_reinforced_turn: int = Field(..., description="Turn of last reinforcement")
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    reinforcement_history: List[int] = Field(default_factory=list)
    origin_signature: str = Field(..., description="Internal pattern that produced this pursuit")
    target_source_id: Optional[str] = None
    target_item_type: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
