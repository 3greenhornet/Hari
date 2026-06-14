"""
engine/volition_engine.py — Runtime engine for desires, agendas, and proactive candidates.
Stub for Phase 7. All logic (urgency calculation, workspace injection) belongs here.
"""

from typing import List, Dict, Any
from models.volition import Desire, Agenda, ActiveProject


class VolitionEngine:
    """
    Stub: manages desires, agendas, and proactive candidates.
    In Phase 7, this will compute urgency from contextual friction
    and convert agendas into WorkspaceCandidate objects.
    """

    def __init__(self):
        self._desires: List[Desire] = []
        self._agendas: List[Agenda] = []
        self._projects: List[ActiveProject] = []

    async def get_proactive_candidates(self, context: Dict[str, Any]) -> List[Any]:
        """
        Stub: generate workspace candidates from active volition items.
        Full implementation will:
        1. Calculate urgency for each active Desire/Agenda using contextual friction.
        2. Convert high‑urgency items into WorkspaceCandidate objects.
        3. Return them to _allocate_workspace for competition.
        """
        return []

    def add_desire(self, desire: Desire) -> None:
        self._desires.append(desire)

    def add_agenda(self, agenda: Agenda) -> None:
        self._agendas.append(agenda)

    def add_project(self, project: ActiveProject) -> None:
        self._projects.append(project)