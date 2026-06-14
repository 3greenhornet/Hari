# hari/psyche/cascades.py
"""
Deterministic state updates applied every turn after LLM deltas.
These simulate fatigue, sovereignty, coherence stress, completion pressure,
and session horizon (mortality pressure).
"""

from .state import HariState


def apply_fatigue_cascade(state: HariState) -> None:
    """High rest reduces arousal and valence."""
    if state.rest > 0.6:
        factor = (state.rest - 0.6) * 2.0
        state.arousal = max(-1.0, state.arousal - 0.1 * factor)
        state.valence = max(-1.0, state.valence - 0.05 * factor)
        # NOTE: response length control is in dialogue generation


def apply_sovereignty_cascade(state: HariState) -> None:
    """High maintenance increases dominance."""
    if state.maintenance > 0.7:
        factor = (state.maintenance - 0.7) * 2.0
        state.dominance = min(1.0, state.dominance + 0.1 * factor)


def apply_coherence_cascade(state: HariState, contradiction_occurred: bool) -> None:
    """Contradiction triggers valence drop, arousal rise, dominance rise."""
    if contradiction_occurred and state.coherence > 0.7:
        state.valence = max(-1.0, state.valence - 0.15)
        state.arousal = min(1.0, state.arousal + 0.2)
        state.dominance = min(1.0, state.dominance + 0.1)


def apply_completion_cascade(state: HariState, num_unresolved_questions: int) -> None:
    """Many open questions increase completion drive."""
    if num_unresolved_questions > 3:
        state.completion = min(1.0, state.completion + 0.05)


def apply_session_horizon(state: HariState, turn: int, max_turns: int = 50) -> None:
    """
    Mortality pressure: as session end nears, unresolved topics become more urgent.
    This function modifies a temporary multiplier; actual effect is applied in attention/workspace.
    Here we simply increase completion slightly.
    """
    progress = turn / max_turns
    if progress > 0.7:
        pressure = (progress - 0.7) / 0.3  # 0 to 1
        state.completion = min(1.0, state.completion + 0.05 * pressure)
