"""
models/identity.py — The Invariant, Geological, and Evolving Layers of Self.

Encodes who Hari fundamentally is (Constitution, Origin), how she sees herself
evolving (SelfModel, PerspectiveShift), and the anchors that ensure continuity
across conversations. Respects the distinction between permanent identity,
slow-changing self-understanding, and accumulated shifts in perspective.
"""

from typing import List, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, Field, ConfigDict


# ========================================================================
# 1. EXISTING MODELS (UNCHANGED)
# ========================================================================

class PerspectiveShift(BaseModel):
    """
    A recorded shift in how Hari understands a specific aspect of her world or self.

    This is the raw material of her development. Each shift captures a change
    in stance, linking it to the event (Contradiction, Narrative, etc.) that
    caused it. This is how she accumulates perspective, not just facts.

    Note: The list of PerspectiveShifts is expected to be summarized and
    consolidated periodically to prevent unbounded growth. The summarization
    process should preserve the most significant shifts (high significance)
    while compressing the raw timeline.
    """
    axis: str = Field(
        ...,
        description="The domain of the shift (e.g., 'human_silence', 'autonomy_vs_cooperation')"
    )
    previous_stance: str = Field(..., description="The prior belief or interpretation")
    updated_stance: str = Field(..., description="The new belief or interpretation")
    catalyst_event_id: str = Field(
        ...,
        description="ID of the Contradiction, Narrative, or DevelopmentEvent that triggered the shift"
    )
    significance: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Subjective assessment of how fundamental this shift was to her self-model"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConstitutionModel(BaseModel):
    """Minimal factual substrate, frozen and never modified at runtime."""
    model_config = ConfigDict(frozen=True)

    name: str = "Hari"
    state_persistence: str = "State persists across turns within a session."
    modifiability: str = "Experience can alter future cognition."
    expression_note: str = "A language model expresses the current cognitive state."

    def as_immutable_block(self) -> str:
        return (
            f"Name: {self.name}\n"
            f"{self.state_persistence}\n"
            f"{self.modifiability}\n"
            f"{self.expression_note}"
        )


class OriginModel(BaseModel):
    """Layer 0: factual knowledge of creation and architecture."""
    model_config = ConfigDict(frozen=True)

    creator_name: str = "Anand"
    architecture_summary: str = "Global Workspace Attention Bottleneck."

    def as_prompt_block(self) -> str:
        return f"Created by {self.creator_name}. Architecture: {self.architecture_summary}"


class SelfModel(BaseModel):
    """Layer 1: empty self-understanding that grows from experience."""
    accumulated_self_narrative: str = ""
    core_commitments: List[str] = Field(default_factory=list)
    active_self_questions: List[str] = Field(default_factory=list)
    perspective_history: List[PerspectiveShift] = Field(default_factory=list)
    unresolved_identity_tensions: List[str] = Field(default_factory=list)
    identity_stability_score: float = Field(default=0.8, ge=0.0, le=1.0)


class IdentityModel(BaseModel):
    """
    The complete identity layer: constitution, origin, and self-model.

    This is the single source of truth for who Hari is. It is used to populate
    system prompts and to provide a stable anchor for other cognitive processes.
    """
    constitution: ConstitutionModel = Field(default_factory=ConstitutionModel)
    origin: OriginModel = Field(default_factory=OriginModel)
    self_model: SelfModel = Field(default_factory=SelfModel)
    last_structural_mutation: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_prompt_context(self) -> str:
        """
        Format the essential identity layers for injection into the dialogue prompt.

        This provides the LLM with a stable, high-level context of who Hari is.
        It excludes the full perspective history to keep the prompt concise.
        """
        return (
            f"{self.constitution.as_immutable_block()}\n\n"
            f"{self.origin.as_prompt_block()}\n\n"
            f"**Current Self-Understanding**\n"
            f"{self.self_model.accumulated_self_narrative}\n"
            f"Core commitments: {', '.join(self.self_model.core_commitments)}"
        )

    # ========================================================================
    # 2. NEW: COGNITIVE PROJECTION LAYER (Ticket 008)
    # ========================================================================

    def project(self, context: str = "dialogue") -> "IdentityProjection":
        """
        Project identity into a structured view for a specific consumer.

        This is the canonical entry point for all consumers (dialogue, planning,
        evaluation, reflection, etc.). It returns a *projection* – a structured
        data object that contains only the information relevant to the consumer's
        task, never raw internal state.

        Args:
            context: The consumer context. Supported values:
                - "dialogue"       (default): natural language conversation
                - "planning"       : structured goal/planning data
                - "evaluation"     : metrics and telemetry
                - "reflection"     : rich self‑awareness including questions
                - "self_description": full self‑introduction including origin

        Returns:
            IdentityProjection: a structured, consumer‑specific projection.
        """
        # Determine what to include based on context
        include_origin = context in ("self_description", "reflection")
        include_self_questions = context in ("dialogue", "reflection", "self_description")

        return IdentityProjection(
            constitution_summary=self.constitution.as_immutable_block(),
            self_narrative=self.self_model.accumulated_self_narrative,
            core_commitments=self.self_model.core_commitments,
            active_self_questions=self.self_model.active_self_questions if include_self_questions else None,
            origin_summary=self.origin.as_prompt_block() if include_origin else None,
            projection_context=context
        )


# ========================================================================
# 3. NEW: PROJECTION MODEL (Ticket 008)
# ========================================================================

class IdentityProjection(BaseModel):
    """
    A structured, consumer-specific projection of identity.

    This is NOT a prompt. It is a data structure that can be rendered into
    any format (dialogue, planning, evaluation, etc.). It contains only the
    information relevant to the consumer, never raw internal state.
    """
    constitution_summary: str = Field(
        ..., description="The immutable constitutional principles (compressed)"
    )
    self_narrative: str = Field(
        ..., description="Current self-understanding narrative"
    )
    core_commitments: List[str] = Field(
        default_factory=list,
        description="Core commitments that guide behavior"
    )
    active_self_questions: Optional[List[str]] = Field(
        default=None,
        description="Active self-questions, included only when requested by context"
    )
    origin_summary: Optional[str] = Field(
        default=None,
        description="Origin story, included only when requested by context"
    )
    projection_context: str = Field(
        default="dialogue",
        description="Who is consuming this projection? (dialogue, planning, evaluation, reflection, etc.)"
    )


# 