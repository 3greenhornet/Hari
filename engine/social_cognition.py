"""
engine/social_cognition.py — Social interpretation synthesis.

Ticket 015: Synthesizes social interpretation from multiple signals:
- Thematic continuity (monologue)
- Trajectory deviation (Ticket 014)
- User engagement (monologue)
- Conversation history (V1 placeholder)

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
    
    # 2. History shift (V1 placeholder)
    history_shift = 0.0 
    
    # 3. Synthesize Shift Magnitude from multiple signals
    shift_magnitude = (
        params.thematic_continuity_weight * (1.0 - monologue_output.thematic_continuity) +
        params.trajectory_deviation_weight * trajectory_deviation +
        params.engagement_weight * (1.0 - 0.5) +
        params.history_weight * history_shift
    )
    shift_magnitude = max(0.0, min(1.0, shift_magnitude))
    interaction.shift_magnitude = shift_magnitude
    
    # 4. Sincerity Estimate
    interaction.sincerity_estimate = (
        0.5 * 0.5 +
        0.5 * 0.3 +
        (1.0 - trajectory_deviation) * 0.2
    )
    
    # 5. Update Cognitive State (Asymptotic, Continuous)
    effective_shift = shift_magnitude * 0.5
    
    # Base state updates
    state_updates = {
        "uncertainty": effective_shift * params.uncertainty_coeff,
        "engagement": (0.5 * params.engagement_coeff) - (effective_shift * 0.02),
        "social_ambiguity": effective_shift * (1.0 - 0.5) * params.social_ambiguity_coeff
    }

    # Map memory emotional tone to VAD adjustments
    TONE_VALENCE = {"positive": 0.08, "frustrated": -0.1, "curious": 0.02, "calm": 0.0, "neutral": 0.0}
    TONE_AROUSAL = {"frustrated": 0.12, "curious": 0.08, "positive": 0.02, "calm": -0.05, "neutral": 0.0}
    tone = getattr(monologue_output, "memory_emotional_tone", "neutral")
    tone_confidence = 0.5
    state_updates["valence"] = state_updates.get("valence", 0.0) + TONE_VALENCE.get(tone, 0.0) * tone_confidence
    state_updates["arousal"] = state_updates.get("arousal", 0.0) + TONE_AROUSAL.get(tone, 0.0) * tone_confidence
    
    # ------------------------------------------------------------------
    # Social event synthesis – describes the interaction, not the user
    # ------------------------------------------------------------------

    social_effect = (
        monologue_output.interruption_severity * 0.35
        + monologue_output.trajectory_deviation * 0.25
        + (1.0 - monologue_output.thematic_continuity) * 0.20
        + 0.5 * 0.20
    )
    social_effect = max(0.0, min(1.0, social_effect))

    # Merge social effect into existing state_updates rather than overwriting
    state_updates["uncertainty"] = state_updates.get("uncertainty", 0.0) + (social_effect * 0.20)
    state_updates["social_ambiguity"] = state_updates.get("social_ambiguity", 0.0) + (social_effect * 0.15)
    if monologue_output.interruption_severity > 0.0:
        state_updates["cognitive_tension"] = state_updates.get("cognitive_tension", 0.0) + (monologue_output.interruption_severity * 0.15)

    state.update(state_updates, source="MONOLOGUE", reason="interaction_event")
    
    # 6. Update Relationship Model (Glacial, Continuous Deltas)
    if relational_manager:
        rel = relational_manager.get_model()
        
        familiarity_delta = (
            0.5 * params.familiarity_growth_coeff -
            shift_magnitude * params.familiarity_shift_decay_coeff
        )
        rel.update_familiarity(familiarity_delta)
        
        trust_delta = (
            interaction.sincerity_estimate * params.trust_sincerity_coeff -
            trajectory_deviation * params.trust_avoidance_coeff
        )
        rel.update_trust(trust_delta)
        
        interaction.relationship_delta = trust_delta + familiarity_delta
    
    logger.debug(
        f"Social synthesis: shift={shift_magnitude:.2f}, "
        f"sincerity={interaction.sincerity_estimate:.2f}, "
        f"trajectory={trajectory_deviation:.2f}, "
        f"rel_delta={interaction.relationship_delta:.4f}, "
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
        thematic_continuity=0.8,
        interruption_severity=0.0,
        memory_significance=0.5,
        memory_emotional_tone="neutral"
    )
    return await interpret_turn_and_update_state(
        user_input=user_input, state=state, monologue_output=monologue_output,
        recent_history=recent_history, turn_count=turn_count, relational_manager=None
    )