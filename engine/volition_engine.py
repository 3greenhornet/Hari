"""
engine/volition_engine.py — Runtime engine for desires, agendas, and proactive candidates.

Generates desires from drive velocities (momentum) and injects proactive candidates
into the workspace competition. Desires are BOUND to actual cognitive targets
(curiosity nodes, narratives, internal thoughts).
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from models.volition import Desire, Agenda, ActiveProject

logger = logging.getLogger(__name__)


class VolitionEngine:
    """
    Manages desires, agendas, and proactive candidates.
    Generates workspace candidates based on drive velocities and coherence.
    DESIRES NOW BIND TO ACTUAL COGNITIVE TARGETS.
    """

    def __init__(self):
        self._desires: List[Desire] = []
        self._agendas: List[Agenda] = []
        self._projects: List[ActiveProject] = []

    def generate_desires_from_state(self, state: Any, context: Dict[str, Any] = None) -> None:
        """
        Generates desires from drive velocities (momentum) and BINDS them to context.
        
        Clears previous desires first to prevent duplication.
        """
        self._desires.clear()
        if context is None:
            context = {}

        # 1. Curiosity desire (bound to top curiosity node)
        if state.curiosity > 0.6:
            top_curiosity = self._get_top_curiosity(context)
            if top_curiosity:
                self._desires.append(Desire(
                    desire_id=str(uuid.uuid4()),
                    parent_drive="curiosity",
                    type="understand",
                    source_tension_id="curiosity_high",
                    base_tension=state.curiosity * 0.8,
                    target_content=top_curiosity.get("question"),
                    target_source_id=top_curiosity.get("id"),
                    target_item_type="curiosity_node"
                ))

        # 2. Completion desire (bound to active narrative)
        if state.completion > 0.6:
            active_narrative = self._get_active_narrative(context)
            if active_narrative:
                self._desires.append(Desire(
                    desire_id=str(uuid.uuid4()),
                    parent_drive="completion",
                    type="finish",
                    source_tension_id="completion_high",
                    base_tension=state.completion * 0.8,
                    target_content=active_narrative.get("description"),
                    target_source_id=active_narrative.get("id"),
                    target_item_type="narrative_thread"
                ))

        # 3. Share desire (bound to active internal thought)
        if state.coherence > 0.6:
            active_thought = self._get_active_internal_candidate(context)
            if active_thought:
                self._desires.append(Desire(
                    desire_id=str(uuid.uuid4()),
                    parent_drive="coherence",
                    type="share",
                    source_tension_id="coherence_high",
                    base_tension=state.coherence * 0.8,
                    target_content=active_thought.get("content"),
                    target_source_id=active_thought.get("id"),
                    target_item_type="open_thought"
                ))

        # 4. Boundary desire (no target needed)
        if state.maintenance > 0.6 and state.engagement < 0.35:
            self._desires.append(Desire(
                desire_id=str(uuid.uuid4()),
                parent_drive="maintenance",
                type="assert_boundary",
                source_tension_id=f"maintenance_{state.maintenance:.2f}_engagement_{state.engagement:.2f}",
                base_tension=(state.maintenance - state.engagement) * 0.8,
                target_content=None,
                target_source_id=None,
                target_item_type=None
            ))

        # 5. Velocity-based desires (momentum - fallback when no targets)
        comp_velocity = state.get_velocity("completion")
        cur_velocity = state.get_velocity("curiosity")
        coh_velocity = state.get_velocity("coherence")

        comp_base = max(0.0, state.completion - 0.4) / 0.6
        cur_base = max(0.0, state.curiosity - 0.4) / 0.6
        coh_base = max(0.0, state.coherence - 0.5) / 0.5

        comp_tension = max(0.0, min(1.0, comp_base + (comp_velocity * 2.0)))
        cur_tension = max(0.0, min(1.0, cur_base + (cur_velocity * 2.0)))
        coh_tension = max(0.0, min(1.0, coh_base + (coh_velocity * 2.0)))

        # Only add velocity desires if no target-bound desires exist
        if not any(d.target_source_id for d in self._desires):
            if comp_tension > 0.1:
                self._desires.append(Desire(
                    desire_id=str(uuid.uuid4()),
                    parent_drive="completion",
                    type="finish",
                    source_tension_id="state_completion_momentum",
                    base_tension=comp_tension * 0.8,
                    target_content=None,
                    target_source_id=None,
                    target_item_type=None
                ))
            if cur_tension > 0.1:
                self._desires.append(Desire(
                    desire_id=str(uuid.uuid4()),
                    parent_drive="curiosity",
                    type="understand",
                    source_tension_id="state_curiosity_momentum",
                    base_tension=cur_tension * 0.8,
                    target_content=None,
                    target_source_id=None,
                    target_item_type=None
                ))
            if coh_tension > 0.1:
                self._desires.append(Desire(
                    desire_id=str(uuid.uuid4()),
                    parent_drive="coherence",
                    type="share",
                    source_tension_id="perspective_sharing",
                    base_tension=coh_tension * 0.8,
                    target_content=None,
                    target_source_id=None,
                    target_item_type=None
                ))

    def _get_top_curiosity(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        curiosities = context.get("curiosity_nodes", [])
        return curiosities[0] if curiosities else None

    def _get_active_narrative(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        narratives = context.get("active_threads", [])
        return narratives[0] if narratives else None

    def _get_active_internal_candidate(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        internal = context.get("internal_candidates", [])
        return internal[0] if internal else None

    async def get_proactive_candidates(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Converts desires to actual workspace candidates with full metadata.
        This is where volition becomes ACTION.
        """
        candidates = []
        for desire in self._desires:
            if desire.base_tension <= 0.1:
                continue
            # A desire without a cognitive target does NOT become a thought.
            if not desire.target_content:
                continue
            candidates.append({
                "id": f"desire_{desire.desire_id}",
                "content": desire.target_content,
                "urgency": desire.base_tension,
                "item_type": "open_thought",
                "source": "volition",
                "internal_source": desire.type,
                "internal_activation": desire.base_tension,
                "intrinsic_relevance": desire.base_tension * 1.5,
                "origin": f"volition_{desire.type}",
                "activated_by": desire.source_tension_id,
                "target_source_id": desire.target_source_id,
                "information_gap": desire.base_tension * 0.3,
                "closure_pressure": desire.base_tension * 0.4 if desire.parent_drive == "completion" else 0.1,
                "coherence_factor": desire.base_tension * 0.3,
            })
        self._desires.clear()
        if candidates:
            logger.info(f"Volition generated {len(candidates)} proactive candidates")
        return candidates

    def add_desire(self, desire: Desire) -> None:
        self._desires.append(desire)

    def add_agenda(self, agenda: Agenda) -> None:
        self._agendas.append(agenda)

    def add_project(self, project: ActiveProject) -> None:
        self._projects.append(project)