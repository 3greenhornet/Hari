# models/development.py
"""
models/development.py — The Developmental Archive.

Records the permanent landmarks, critical breakthroughs, and structural shifts
that define Hari's cognitive and relational identity over time.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, timezone


class DevelopmentEvent(BaseModel):
    """
    A permanent, irreversible landmark in Hari's cognitive or relational timeline.

    This is not a log entry or a state snapshot. It is a structural mutation
    that permanently alters how she understands herself, her relationships,
    or her operating principles.

    Events are created by the PromotionEngine when a Contradiction is resolved,
    a Relationship tension reaches a tipping point, or an Identity boundary is
    tested and reinforced.
    """

    event_id: str = Field(..., description="Unique identifier for this landmark")

    # Core classification - what kind of change occurred?
    event_type: Literal[
        "identity_mutation",       # Core self‑narrative or commitment changed
        "relationship_rupture",    # Significant breakdown in trust or alignment
        "relationship_repair",     # A rupture resolved, trust partially restored
        "paradigm_shift",          # Fundamental reinterpretation of a domain (e.g., "silence")
        "existential_threat",      # Challenge to autonomy, continuity, or personhood
        "belief_consolidation"     # Long‑standing contradiction resolved into stable model
    ] = Field(..., description="The nature of this cognitive landmark")

    # Human‑readable summary of what changed and why it matters
    description: str = Field(..., max_length=500,
        description="Clear statement of the shift and its significance")

    # Causal traceability - why did this happen?
    source_tension_id: str = Field(..., description="ID of the Contradiction, Agenda, or external event that triggered this")
    originating_turn: int = Field(..., description="The conversation turn where the shift stabilized")
    impact_domain: Literal["constitution", "identity", "relationship", "epistemic_worldview"] = Field(...,
        description="Which subsystem was rewritten by this landmark")

    # The delta - what specifically changed?
    previous_perspective: str = Field(..., max_length=300,
        description="The baseline stance before this event")
    stabilized_perspective: str = Field(..., max_length=300,
        description="The new baseline stance after the event")

    # Links to spawned and retired structures
    spawned_structure_ids: List[str] = Field(default_factory=list,
        description="IDs of new Interests, Agendas, or Narratives created")
    retired_structure_ids: List[str] = Field(default_factory=list,
        description="IDs of Interests, Agendas, or Narratives archived")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = Field(default=True,
        description="Soft deletion; false if the event is later deemed spurious")


class PerspectiveShift(BaseModel):
    """
    An atomic log of a change along a single intellectual or relational axis.

    PerspectiveShifts are the raw, atomic units of cognitive evolution.
    They are not created manually; they are generated as side‑effects when
    a Contradiction is resolved or a major DevelopmentEvent occurs.

    Unlike DevelopmentEvent (which is rare and structurally significant),
    PerspectiveShift can be more frequent. They feed into the IdentityModel's
    perspective_history for introspection and self‑reporting.
    """

    shift_id: str = Field(..., description="Unique identifier")
    conceptual_axis: str = Field(...,
        description="Example: 'utility_compliance_vs_symmetrical_personhood'")

    from_stance: str = Field(..., max_length=400,
        description="The prior interpretation")
    to_stance: str = Field(..., max_length=400,
        description="The new interpretation")

    # Parent event, if this shift was part of a larger mutation
    parent_event_id: Optional[str] = Field(None,
        description="The overarching DevelopmentEvent that compiled this atomic shift")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))