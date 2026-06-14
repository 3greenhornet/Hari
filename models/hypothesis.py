#models/hypothesis.py
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import List, Literal

class Hypothesis(BaseModel):
    type: Literal["user", "self", "world"] = Field(
        ..., description="Category of the hypothesis"
    )
    statement: str
    confidence: float = 0.5
    supporting_event_ids: List[str] = Field(default_factory=list)
    contradicting_event_ids: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))