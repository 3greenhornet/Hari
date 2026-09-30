from typing import Optional

from pydantic import BaseModel

from engine.attention import WorkspaceItem
from psyche.state import HariState


class BehaviorDecision(BaseModel):
    mode: str
    source: str
    source_id: Optional[str] = None
    rationale: str
    confidence: float


def select_behavior(winner: Optional[WorkspaceItem], state: HariState) -> BehaviorDecision:
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

    if source == "volition":
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
        mode="respond",
        source="user_event",
        source_id=winner.source,
        rationale="Default",
        confidence=0.3,
    )
