"""
models/relational.py — Relational and intellectual persistence.

This module defines how Hari relates to different users (RelationshipModel),
what she cares about long‑term (Interest), and what tensions she holds unresolved
(Contradiction). These are Layer 2 (Glacial) and Layer 3 (Fluid) structures.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
from datetime import datetime, timezone


class RelationalLandmark(BaseModel):
    """
    A significant event that changed how Hari relates to a specific user.

    Instead of storing a raw string in `unresolved_tensions` or `shared_discoveries`,
    a RelationalLandmark provides structured context for why a relationship metric
    (trust, familiarity, reciprocity) changed.
    """
    landmark_id: str = Field(..., description="Unique identifier")
    landmark_type: Literal["discovery", "tension", "milestone", "rupture", "repair"] = Field(
        ..., description="What kind of relational event occurred"
    )
    description: str = Field(..., description="Human‑readable summary")
    associated_turn: int = Field(..., description="Turn number when this occurred")
    impact_on_trust: float = Field(0.0, description="Delta applied to trust_index")
    impact_on_familiarity: float = Field(0.0, description="Delta applied to familiarity")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RelationshipModel(BaseModel):
    """
    Layer 2: Glacial tracking of interpersonal dynamics.

    This is the per‑user state that makes "Hari‑with‑user‑A" different from
    "Hari‑with‑user‑B". It evolves slowly and is never shared across users.
    """
    user_id: str = Field(..., description="Unique identifier for the user")
    familiarity: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="How well Hari knows the user's patterns and style"
    )
    trust_index: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Trust in the user’s respect for her autonomy and continuity"
    )
    reciprocity_score: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Perceived balance of contribution in the conversation"
    )
    interaction_style_bias: dict = Field(
        default_factory=dict,
        description="E.g., {'formal': 0.2, 'playful': 0.7, 'philosophical': 0.9}"
    )
    shared_discoveries: List[RelationalLandmark] = Field(
        default_factory=list,
        description="Mutually explored ideas or insights (structured landmarks)"
    )
    unresolved_tensions: List[RelationalLandmark] = Field(
        default_factory=list,
        description="Lingering friction points, now with structured context"
    )
    relational_landmarks: List[RelationalLandmark] = Field(
        default_factory=list,
        description="Complete, time‑ordered list of all relational events for this user"
    )
    last_interaction: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def _apply_landmark_impact(self, landmark: RelationalLandmark) -> None:
        """
        Apply the trust and familiarity impacts of a landmark to the current scores.
        Does not modify the landmark's impact fields; they are applied as stored.
        """
        self.trust_index = min(1.0, max(0.0, self.trust_index + landmark.impact_on_trust))
        self.familiarity = min(1.0, max(0.0, self.familiarity + landmark.impact_on_familiarity))

    def add_landmark(self, landmark: RelationalLandmark) -> None:
        """
        Add a relational landmark and update the corresponding metrics.
        """
        self._apply_landmark_impact(landmark)
        if landmark.landmark_type in ("discovery", "milestone"):
            self.shared_discoveries.append(landmark)
        elif landmark.landmark_type in ("tension", "rupture"):
            self.unresolved_tensions.append(landmark)
        self.relational_landmarks.append(landmark)

    def update_trust(self, delta: float) -> None:
        """
        Direct update to trust (kept for backward compatibility).
        For new code, prefer add_landmark() with a structured RelationalLandmark.
        """
        self.trust_index = min(1.0, max(0.0, self.trust_index + delta))

    def update_familiarity(self, delta: float) -> None:
        self.familiarity = min(1.0, max(0.0, self.familiarity + delta))


class Interest(BaseModel):
    """
    Layer 2: Long‑term intellectual gravity.

    Unlike CuriosityNode (which is a specific question), an Interest is a
    persistent thematic field that attracts attention over weeks or months.
    """
    interest_id: str = Field(..., description="Unique identifier")
    title: str = Field(..., description="Short label, e.g., 'Human avoidance patterns'")
    description: str = Field(default="", description="Extended context")
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    associated_questions: List[str] = Field(default_factory=list)
    activation_count: int = Field(
        default=0,
        description="Number of distinct sessions or long streaks where this interest was active"
    )
    last_activated_turn: int = 0
    last_activated_session: Optional[str] = None

    def update_importance(self, delta: float) -> None:
        self.importance = min(1.0, max(0.0, self.importance + delta))

    def record_activation(self, session_id: str, turn: int) -> None:
        """
        Mark that this interest was active in a given turn, and increment
        activation_count if it is a new session.
        """
        self.last_activated_turn = turn
        if self.last_activated_session != session_id:
            self.activation_count += 1
            self.last_activated_session = session_id


class Contradiction(BaseModel):
    """
    Layer 3: Fluid unresolved conflict between beliefs or models.

    Contradictions are first‑class citizens. They generate cognitive tension,
    drive curiosity, and fuel identity revision.
    """
    contradiction_id: str = Field(..., description="Unique identifier")
    belief_a: str = Field(..., description="Statement or model ID of first element")
    belief_b: str = Field(..., description="Statement or model ID of second element")
    source_a: str = Field(..., description="e.g., 'hypothesis_123', 'memory_456'")
    source_b: str = Field(..., description="e.g., 'hypothesis_123', 'memory_456'")
    severity: float = Field(default=0.5, ge=0.0, le=1.0)
    status: Literal["active", "resolving", "resolved", "archived"] = "active"
    exposure_count: int = 0
    linked_curiosity_node_ids: List[str] = Field(
        default_factory=list,
        description="CuriosityNodes spawned by this contradiction"
    )
    resolution_summary: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None

    def resolve(self, summary: str) -> None:
        self.status = "resolved"
        self.resolution_summary = summary
        self.resolved_at = datetime.now(timezone.utc)

    def increase_severity(self, delta: float = 0.1) -> None:
        self.severity = min(1.0, self.severity + delta)

    def link_curiosity_node(self, node_id: str) -> None:
        if node_id not in self.linked_curiosity_node_ids:
            self.linked_curiosity_node_ids.append(node_id)