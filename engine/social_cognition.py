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
        params.engagement_weight * (1.0 - monologue_output.user_engagement_estimate) +
        params.history_weight * history_shift
    )
    shift_magnitude = max(0.0, min(1.0, shift_magnitude))
    interaction.shift_magnitude = shift_magnitude
    
    # 4. Sincerity Estimate
    interaction.sincerity_estimate = (
        monologue_output.intent_confidence * 0.5 +
        monologue_output.user_engagement_estimate * 0.3 +
        (1.0 - trajectory_deviation) * 0.2
    )
    
    # 5. Update Cognitive State (Asymptotic, Continuous)
    effective_shift = shift_magnitude * monologue_output.intent_confidence
    
    # Base state updates
    state_updates = {
        "uncertainty": effective_shift * params.uncertainty_coeff,
        "engagement": (monologue_output.user_engagement_estimate * params.engagement_coeff) - (effective_shift * 0.02),
        "social_ambiguity": effective_shift * (1.0 - monologue_output.intent_confidence) * params.social_ambiguity_coeff
    }
    
    # NEW: Social Meaning Synthesis (Intent-based drive updates)
    # Scaled by intent confidence so low-confidence interpretations have smaller impact
    intent = monologue_output.perceived_user_intent
    confidence = monologue_output.intent_confidence
    synthesis_reason = "social_synthesis"
    
    if intent == "testing":
        state_updates["maintenance"] = 0.15 * confidence
        synthesis_reason = "user_testing_boundary"
    elif intent == "sharing" and monologue_output.user_engagement_estimate < 0.4:
        state_updates["care"] = 0.05 * confidence
        state_updates["arousal"] = -0.05 * confidence
        synthesis_reason = "user_hesitant_or_bored"
    elif intent == "help_seeking":
        state_updates["care"] = 0.1 * confidence
        synthesis_reason = "user_help_seeking"
        
    # TODO: Replace categorical intent interpretation with evidence-backed social hypotheses
    # after the epistemic layer is introduced (future milestone).
    
    # Apply the combined updates
    if effective_shift > 0.001 or abs(monologue_output.user_engagement_estimate - 0.5) > 0.05 or intent != "sharing":
        state.update(state_updates, source="MONOLOGUE", reason=synthesis_reason)
    
    # 6. Update Relationship Model (Glacial, Continuous Deltas)
    if relational_manager:
        rel = relational_manager.get_model()
        
        familiarity_delta = (
            monologue_output.user_engagement_estimate * params.familiarity_growth_coeff -
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
        f"reason={synthesis_reason}"
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
        perceived_user_intent="sharing",
        intent_confidence=0.5,
        thematic_continuity=0.8,
        user_engagement_estimate=0.5,
        interruption_severity=0.0,
        memory_significance=0.5,
        memory_emotional_tone="neutral"
    )
    return await interpret_turn_and_update_state(
        user_input=user_input, state=state, monologue_output=monologue_output,
        recent_history=recent_history, turn_count=turn_count, relational_manager=None
    )