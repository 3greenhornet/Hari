# models/decision_trace.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class WorkspaceItemTrace(BaseModel):
    item_id: str
    item_type: str
    source: str
    raw_score: float
    final_score: float
    attention_weight: float
    content_snapshot: str
    is_winner: bool
    
    # NEW: provenance fields
    origin: Optional[str] = None          # where did this candidate come from?
    activated_by: Optional[str] = None    # which event activated it?
    intrinsic_relevance: float = Field(default=0.0)
    persistence: float = Field(default=0.0)

class Metrics(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0

class DecisionTrace(BaseModel):
    trace_id: str
    session_id: str
    turn_number: int
    timestamp: datetime = Field(default_factory=datetime.now)
    model_used: str
    system_prompt_version: str = "1.0"
    temperature: float
    user_input: str
    reasoning_chain: Optional[str] = None
    generated_response: str = ""
    retrieved_candidate_count: int
    selected_winner_count: int
    drives_before: dict
    drives_after: dict = {}
    perceived_user_intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    thematic_continuity: Optional[float] = None
    workspace_items: List[WorkspaceItemTrace] = Field(default_factory=list)
    metrics: Metrics = Field(default_factory=Metrics)
    error: Optional[str] = None