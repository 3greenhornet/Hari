"""
models/interaction.py — Rich social interpretation output schema.
Phase 7 stub.
"""

from typing import List, Literal, Dict, Any
from pydantic import BaseModel, Field


class InteractionModel(BaseModel):
    """Rich social interpretation of a user turn."""

    conversation_move: Literal[
        "asked_question", "changed_topic", "shared_opinion", "gave_command",
        "avoided_topic", "tested_agent", "disengaged", "returned_to_topic",
        "made_joke", "challenged_belief", "asked_self_disclosure", "other"
    ] = "other"
    move_confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    shift_magnitude: float = Field(default=0.0, ge=0.0, le=1.0)
    shift_abruptness: float = Field(default=0.0, ge=0.0, le=1.0)
    shift_intentionality: float = Field(default=0.5, ge=0.0, le=1.0)

    possible_meanings: List[Dict[str, Any]] = Field(default_factory=list)
    social_ambiguity: float = Field(default=0.0, ge=0.0, le=1.0)
    sincerity_estimate: float = Field(default=0.7, ge=0.0, le=1.0)

    relationship_delta: float = Field(default=0.0, ge=-0.3, le=0.3)