#models/curiosity_node.py
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class CuriosityNode(BaseModel):
    id: str
    core_question: str
    importance: float = 0.5
    exploration_progress: float = 0.0
    last_referenced: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))