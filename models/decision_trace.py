# models/decision_trace.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, List, Optional


class WorkspaceItemTrace(BaseModel):
    item_id: str
    item_type: str
    source: str
    raw_score: float
    final_score: float
    attention_weight: float
    content_snapshot: str
    is_winner: bool
    origin: Optional[str] = None
    activated_by: Optional[str] = None
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
    system_prompt_version: str = "2.0"
    temperature: float
    incoming_text: str = ""
    reasoning_chain: Optional[str] = None
    generated_response: Optional[str] = None
    retrieved_candidate_count: int
    selected_winner_count: int
    drives_before: dict
    drives_after: dict = {}
    perceived_intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    thematic_continuity: Optional[float] = None
    workspace_items: List[WorkspaceItemTrace] = Field(default_factory=list)
    metrics: Metrics = Field(default_factory=Metrics)
    error: Optional[str] = None

    # Behavior fields (added 2026-08-21)
    behavior_mode: Optional[str] = None
    behavior_source: Optional[str] = None
    prior_behavior_mode: Optional[str] = None
    contamination_hits: int = 0
    expression_mode: Optional[str] = None
    # Reserved for post-hoc gravity probe results; not populated at runtime.
    thread_survival: Optional[float] = None
    held: bool = False
    internal_candidates_count: int = 0
    active_thought_count: int = 0
    feedback_summary: Optional[dict] = None
    homeostatic_reward: Optional[float] = None
    viability_violations: Optional[List[str]] = None
    reflection_edits_applied: Optional[Dict[str, float]] = None
    focus_stability_ratio: Optional[float] = None
    winner_origin: Optional[str] = None
    pursuit_registry_snapshot: Optional[dict] = None
    event_present: bool = False
    event_was_winner: bool = False
    event_was_supporting: bool = False
    event_was_ignored: bool = True
    social_update_applied: bool = False
    expression_permitted: bool = False
    expression_reason: Optional[str] = None