"""
engine/social_cognition.py — Social interpretation synthesis.

Ticket 015: Synthesizes social interpretation from trajectory deviation.

Updates state asymptotically and applies glacial deltas to relationship model.
Includes Social Meaning Synthesis (intent-based drive updates).
"""

import logging
from typing import List, Dict, Any, Optional

from models.interaction import InteractionModel
from models.monologue_output import MonologueOutput
from psyche.state import HariState
from engine.cognitive_params import SOCIAL

logger = logging.getLogger(__name__)


async def interpret_turn_and_update_state(
    user_input: str,
    state: HariState,
    monologue_output: MonologueOutput,
    recent_history: List[Dict[str, str]],
    turn_count: int,
    relational_manager: Optional[Any] = None
) -> InteractionModel:
    """
    Synthesizes social interpretation from monologue output and history.
    Updates state asymptotically and applies glacial deltas to relationship.
    """
    interaction = InteractionModel()
    params = SOCIAL
    
    # 1. Retrieve trajectory deviation from monologue (Ticket 014)
    trajectory_deviation = getattr(monologue_output, 'trajectory_deviation', 0.0)
    
    # 2. Shift magnitude is the sensory trajectory deviation.
    shift_magnitude = max(0.0, min(1.0, trajectory_deviation))
    interaction.shift_magnitude = shift_magnitude
    
    # 5. Update Cognitive State (Asymptotic, Continuous)
    effective_shift = shift_magnitude * 0.5
    
    # Base state updates.
    state_updates = {
        "uncertainty": effective_shift * params.uncertainty_coeff,
        "social_ambiguity": effective_shift * 0.5 * params.social_ambiguity_coeff,
    }
    
    # ------------------------------------------------------------------
    # Social event synthesis – describes the interaction, not the user
    # ------------------------------------------------------------------

    state.update(state_updates, source="MONOLOGUE", reason="interaction_event")
    
    # 6. Update Relationship Model (Glacial, Continuous Deltas)
    if relational_manager:
        rel = relational_manager.get_model()
        
        familiarity_delta = (
            0.5 * params.familiarity_growth_coeff -
            shift_magnitude * params.familiarity_shift_decay_coeff
        )
        rel.update_familiarity(familiarity_delta)
        
        trust_delta = -trajectory_deviation * params.trust_avoidance_coeff
        rel.update_trust(trust_delta)
    
    logger.debug(
        f"Social synthesis: shift={shift_magnitude:.2f}, "
        f"trajectory={trajectory_deviation:.2f}, "
        f"reason=interaction_event"
    )
    
    return interaction

# ============================================================================
# Legacy stub kept for backward compatibility
# ============================================================================

async def interpret_turn(
    user_input: str,
    state: HariState,
    recent_history: List[Dict[str, str]],
    turn_count: int,
) -> InteractionModel:
    logger.warning("interpret_turn() is deprecated; use interpret_turn_and_update_state() instead.")
    from models.monologue_output import MonologueOutput
    monologue_output = MonologueOutput(
        trajectory_deviation=0.2,
    )
    return await interpret_turn_and_update_state(
        user_input=user_input, state=state, monologue_output=monologue_output,
        recent_history=recent_history, turn_count=turn_count, relational_manager=None
    )