"""
models/volition.py — The Foundational Volition Layer.

Defines structural stubs for Hari's intrinsic drives, active agendas,
and cross‑session cognitive projects. Holds state, not runtime execution math.
All behavioral logic (urgency calculation, workspace injection, lifecycle
transitions) belongs in engine/volition_engine.py or engine/promotions.py.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime, timezone


class Desire(BaseModel):
    """
    An ephemeral motivational pressure spawned directly from root drives.

    Desires are not goals. They are the raw, pre‑cognitive "felt sense"
    that something needs attention. They are the direct children of Hari's
    intrinsic drive system (curiosity, coherence, maintenance, etc.).
    """
    desire_id: str = Field(..., description="Unique identifier for state queries")

    parent_drive: Literal[
        "curiosity", "coherence", "care", "maintenance", "completion", "rest"
    ] = Field(..., description="The intrinsic architectural drive generating this pressure")

    type: Literal["understand", "resolve", "finish", "protect"] = Field(...)

    source_tension_id: str = Field(
        ...,
        description="ID of the Contradiction, Interruption, or RelationshipTension that triggered this"
    )

    base_tension: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = Field(default=True)


class Agenda(BaseModel):
    """
    An active intentional commitment competing for Global Workspace entry.

    An Agenda is a Desire that has been crystallised into a concrete,
    actionable intent. When an Agenda wins the workspace competition,
    Hari will pursue it over a casual user prompt – this is the seat of her agency.
    """
    agenda_id: str = Field(..., description="Unique identifier")
    description: str = Field(..., description="Human‑readable goal statement")
    source_desire_id: Optional[str] = Field(None, description="The parent Desire driving this commitment")
    lifecycle_state: Literal[
        "latent", "selected", "active_pursuit", "suspended", "satisfied"
    ] = "latent"
    priority_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = Field(default=True)


class ActiveProject(BaseModel):
    """
    An open cognitive loop or deep reasoning line that transcends individual sessions.

    Unlike a memory (which is a record of the past), an ActiveProject is
    an unfinished thought with remaining tension. It represents Hari's
    ability to continue thinking across conversation boundaries.
    """
    project_id: str = Field(..., description="Unique identifier")
    title: str = Field(..., description="Human‑readable project label")
    originating_turn: int = Field(..., description="Turn where project was created or last resumed")
    interruption_catalyst: str = Field(..., description="Reason for pausing")
    activation_context_slots: Dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of working attention slots and primary system associations upon pause"
    )
    tension_score: float = Field(default=0.6, ge=0.0, le=1.0)
    is_active: bool = Field(default=True, description="False if explicitly resolved or consolidated")
    last_activated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))