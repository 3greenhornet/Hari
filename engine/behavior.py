"""
engine/behavior.py
CAUSAL STATUS: TELEMETRY ONLY for Sprint 1.
select_behavior() is logged to the decision trace and does not influence
stance resolution, dialogue generation, or state.
Additional affordance-based action selection has been added.
"""
from typing import Optional, List, Any
from collections import namedtuple
from pydantic import BaseModel

from engine.attention import WorkspaceItem
from psyche.state import HariState

# Affordance result type: action name, free-text rationale, confidence strength
ActionAffordance = namedtuple("ActionAffordance", ["action", "rationale", "strength"])


class BehaviorDecision(BaseModel):
    mode: str
    source: str
    source_id: Optional[str] = None
    rationale: str
    confidence: float


def select_behavior(winner: Optional[WorkspaceItem], state: HariState) -> BehaviorDecision:
    """
    Select a behavioral mode based on a single workspace winner and system state.
    CAUSAL STATUS: TELEMETRY ONLY for Sprint 1.
    """
    if winner is None:
        return BehaviorDecision(mode="hold", source="none", rationale="No winner", confidence=0.5)

    source = winner.payload.get("source", "")
    urgency = float(winner.payload.get("urgency", 0.0))

    if source == "internal_cognition":
        return BehaviorDecision(
            mode="share" if urgency <= 0.7 else "continue_internal",
            source=source,
            source_id=winner.source,
            rationale="Internal thought",
            confidence=urgency,
        )

    if source in ("volition", "volition_persistent"):
        internal_source = winner.payload.get("internal_source", "")
        if internal_source == "assert_boundary":
            return BehaviorDecision(
                mode="redirect",
                source=source,
                source_id=winner.source,
                rationale="Boundary",
                confidence=urgency,
            )
        if internal_source in ("understand", "finish"):
            return BehaviorDecision(
                mode="ask",
                source=source,
                source_id=winner.source,
                rationale="Resolve",
                confidence=urgency,
            )
        return BehaviorDecision(
            mode="share",
            source=source,
            source_id=winner.source,
            rationale="Volition",
            confidence=urgency,
        )

    if source == "curiosity_spreading":
        return BehaviorDecision(
            mode="associate",
            source=source,
            source_id=winner.source,
            rationale="Association",
            confidence=urgency,
        )

    if winner.item_type == "memory":
        sig = float(winner.payload.get("significance", 0.5))
        return BehaviorDecision(
            mode="deepen" if sig > 0.7 else "follow",
            source="memory",
            source_id=winner.source,
            rationale="Memory",
            confidence=sig,
        )

    if winner.item_type == "narrative_thread":
        completion = float(winner.payload.get("completion_estimate", 0.5))
        return BehaviorDecision(
            mode="revisit" if completion > 0.6 else "deepen",
            source="narrative",
            source_id=winner.source,
            rationale="Narrative",
            confidence=completion,
        )

    return BehaviorDecision(
        mode="hold",
        source=winner.payload.get("source") or "unknown",
        source_id=winner.source,
        rationale="No specific behavioral mode established.",
        confidence=0.0,
    )


def compute_action_affordances(
    winner: Optional[WorkspaceItem],
    supporters: List[WorkspaceItem],
    state: HariState,
    relationship: Any = None,
    reciprocity: float = 0.5,
    internal_pressure: float = 0.0,
) -> ActionAffordance:
    """
    Compute action affordances based on the primary workspace winner,
    secondary supporters, system state, and relationship context.
    """
    if winner is None:
        return ActionAffordance(action="hold", rationale="No winner", strength=0.0)

    # Extract core signals from the winner
    urgency = float(winner.payload.get("urgency", 0.0)) if winner else 0.0
    significance = float(winner.payload.get("significance", 0.5)) if winner else 0.5

    # Aggregate supporter signals if available
    supporter_weight = 0.0
    if supporters:
        for supp in supporters[:3]:
            if supp and hasattr(supp, "payload"):
                supporter_weight += float(supp.payload.get("urgency", 0.0))
        supporter_weight = supporter_weight / min(len(supporters), 3) if supporters else 0.0

    # Blend state pressures (matching execute's internal_pressure computation)
    curiosity = float(getattr(state, "curiosity", 0.5))
    completion = float(getattr(state, "completion", 0.5))
    coherence = float(getattr(state, "coherence", 0.5))
    cognitive_tension = float(getattr(state, "cognitive_tension", 0.0))
    computed_internal_pressure = max(curiosity, completion, coherence, cognitive_tension)
    # Use the provided internal_pressure if given, else computed
    effective_internal_pressure = internal_pressure if internal_pressure > 0 else computed_internal_pressure

    # Determine primary action mode
    if urgency > 0.7:
        action = "share"
        rationale = "High urgency internal thought"
    elif significance > 0.7:
        action = "deepen"
        rationale = "High significance memory"
    elif effective_internal_pressure > 0.6:
        action = "associate"
        rationale = "High internal pressure driving association"
    else:
        action = "follow"
        rationale = "Proceed with current cognition"

    # Compute strength as blended confidence, modulated by reciprocity
    strength = (urgency + significance + effective_internal_pressure) / 3.0
    strength = strength * reciprocity  # Modulate by relationship reciprocity
    strength = min(max(strength, 0.0), 1.0)  # Clamp to [0, 1]

    return ActionAffordance(action=action, rationale=rationale, strength=strength)


def select_action(affordance: ActionAffordance) -> ActionAffordance:
    """
    Select the final action from computed affordances.
    Currently a pass-through; future extensions may include
    multi-affordance selection or heuristics.
    """
    return affordance
