# hari/models/memory_event.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


class MemoryEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    turn_number: int
    role: str  # "user" or "assistant"
    content: str
    event_type: Optional[str] = None
    thematic_tags: Optional[List[str]] = None
    significance: float = Field(default=0.5, ge=0.0, le=1.0)
    meaning_summary: Optional[str] = None
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.now)

    # Phase 6 additions (living memory scaffold)
    usage_count: int = Field(default=0, description="Number of times this memory was retrieved")
    last_retrieved_turn: int = Field(default=0, description="Last turn number it was used")
    explanatory_power: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="How well this memory explains conversational ruptures"
    )