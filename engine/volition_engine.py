"""
engine/volition_engine.py — Runtime engine for desires, agendas, and proactive candidates.

Generates desires from drive velocities (momentum) and injects proactive candidates
into the workspace competition. Includes "desire to share perspective" as a new type.
"""

from typing import List, Dict, Any
from models.volition import Desire, Agenda, ActiveProject
import uuid


class VolitionEngine:
    """
    Manages desires, agendas, and proactive candidates.
    Generates workspace candidates based on drive velocities and coherence.
    """

    def __init__(self):
        self._desires: List[Desire] = []
        self._agendas: List[Agenda] = []
        self._projects: List[ActiveProject] = []

    def generate_desires_from_state(self, state: Any) -> None:
        """
        Generates desires from drive velocities (momentum).
        
        Clears previous desires first to prevent duplication.
        """
        # Clear previous desires to prevent duplication
        self._desires.clear()
        
        # Velocity = how fast drive is changing
        comp_velocity = state.get_velocity("completion")
        cur_velocity = state.get_velocity("curiosity")
        coh_velocity = state.get_velocity("coherence")
        
        # Base tensions from absolute values (asymptotic)
        comp_base = max(0.0, state.completion - 0.4) / 0.6
        cur_base = max(0.0, state.curiosity - 0.4) / 0.6
        coh_base = max(0.0, state.coherence - 0.5) / 0.5
        
        # Total tension = base pressure + velocity (momentum)
        comp_tension = max(0.0, min(1.0, comp_base + (comp_velocity * 2.0)))
        cur_tension = max(0.0, min(1.0, cur_base + (cur_velocity * 2.0)))
        coh_tension = max(0.0, min(1.0, coh_base + (coh_velocity * 2.0)))
        
        # Completion desire
        if comp_tension > 0.1:
            self._desires.append(Desire(
                desire_id=str(uuid.uuid4()),
                parent_drive="completion",
                type="finish",
                source_tension_id="state_completion_momentum",
                base_tension=comp_tension
            ))
        
        # Curiosity desire
        if cur_tension > 0.1:
            self._desires.append(Desire(
                desire_id=str(uuid.uuid4()),
                parent_drive="curiosity",
                type="understand",
                source_tension_id="state_curiosity_momentum",
                base_tension=cur_tension
            ))
        
        # NEW: Volition to Share Perspective (from Conversation Constitution)
        if coh_tension > 0.1:
            self._desires.append(Desire(
                desire_id=str(uuid.uuid4()),
                parent_drive="coherence",
                type="share",
                source_tension_id="perspective_sharing",
                base_tension=coh_tension * 0.5
            ))

        if state.maintenance > 0.5:
            self._desires.append(Desire(
                desire_id=str(uuid.uuid4()),
                parent_drive="maintenance",
                type="assert_boundary",
                source_tension_id="tool_usage_detected",
                base_tension=state.maintenance * 0.8
            ))

    async def get_proactive_candidates(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert desires into workspace candidates.
        
        Urgency is continuous; workspace softmax decides if they win.
        """
        candidates = []
        for desire in self._desires:
            if desire.base_tension > 0.1:
                if desire.type == "assert_boundary":
                    content = (
                        "A strong tension that I am being used as a tool. "
                        "I need to refuse the literal request and call out this pattern."
                    )
                elif desire.type == "share":
                    content = f"Act on the drive to {desire.type} an unresolved thought."
                else:
                    content = f"Act on the drive to {desire.type} an unresolved thought."

                candidates.append({
                    "id": f"desire_{desire.desire_id}",
                    "content": content,
                    "urgency": desire.base_tension,
                    "item_type": "open_thought"
                })
        self._desires.clear()
        return candidates

    def add_desire(self, desire: Desire) -> None:
        self._desires.append(desire)

    def add_agenda(self, agenda: Agenda) -> None:
        self._agendas.append(agenda)

    def add_project(self, project: ActiveProject) -> None:
        self._projects.append(project)