"""
engine/social_cognition.py — Social interpretation synthesis.

Ticket 015: Synthesizes social interpretation from multiple signals:
- Thematic continuity (monologue)
- Trajectory deviation (Ticket 014)
- User engagement (monologue)
- Conversation history (V1 placeholder)

Updates state asymptotically and applies glacial deltas to relationship model.
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
    
    Signals fused:
    1. Thematic continuity from monologue (inverted: 1.0 - continuity)
    2. Trajectory deviation (from Ticket 014)
    3. User engagement estimate (inverted: 1.0 - engagement)
    4. Conversation history (V1 placeholder, currently 0.0)
    
    Updates state asymptotically and applies glacial deltas to relationship.
    
    Args:
        user_input: The current user message (unused but kept for interface consistency)
        state: Hari's current internal state
        monologue_output: The monologue perception output
        recent_history: List of recent conversation turns
        turn_count: Current turn number
        relational_manager: Optional relationship manager for updating trust/familiarity
    
    Returns:
        InteractionModel with shift_magnitude, sincerity_estimate, relationship_delta
    """
    interaction = InteractionModel()
    params = SOCIAL
    
    # 1. Retrieve trajectory deviation from monologue (Ticket 014)
    trajectory_deviation = getattr(monologue_output, 'trajectory_deviation', 0.0)
    
    # 2. History shift (V1 placeholder - will be refined with observatory data)
    # TODO: Replace with semantic distance between recent turns or topic tracking
    history_shift = 0.0  # V1: neutral until we have a better signal
    
    # 3. Synthesize Shift Magnitude from multiple signals
    shift_magnitude = (
        params.thematic_continuity_weight * (1.0 - monologue_output.thematic_continuity) +
        params.trajectory_deviation_weight * trajectory_deviation +
        params.engagement_weight * (1.0 - monologue_output.user_engagement_estimate) +
        params.history_weight * history_shift
    )
    shift_magnitude = max(0.0, min(1.0, shift_magnitude))
    interaction.shift_magnitude = shift_magnitude
    
    # 4. Sincerity Estimate (how genuine the user appears)
    # Combines intent confidence, engagement, and lack of trajectory deviation
    interaction.sincerity_estimate = (
        monologue_output.intent_confidence * 0.5 +
        monologue_output.user_engagement_estimate * 0.3 +
        (1.0 - trajectory_deviation) * 0.2
    )
    
    # 5. Update Cognitive State (Asymptotic, Continuous)
    # Scale updates by both shift magnitude and intent confidence
    effective_shift = shift_magnitude * monologue_output.intent_confidence
    
    # Only apply if there's a non-trivial signal
    if effective_shift > 0.001 or abs(monologue_output.user_engagement_estimate - 0.5) > 0.05:
        state.update({
            "uncertainty": effective_shift * params.uncertainty_coeff,
            "engagement": (monologue_output.user_engagement_estimate * params.engagement_coeff) - (effective_shift * 0.02),
            "social_ambiguity": effective_shift * (1.0 - monologue_output.intent_confidence) * params.social_ambiguity_coeff
        }, source="MONOLOGUE", reason="social_synthesis")
    
    # 6. Update Relationship Model (Glacial, Continuous Deltas)
    if relational_manager:
        rel = relational_manager.get_model()
        
        # Familiarity: grows with engagement, shrinks slightly with abrupt shifts
        familiarity_delta = (
            monologue_output.user_engagement_estimate * params.familiarity_growth_coeff -
            shift_magnitude * params.familiarity_shift_decay_coeff
        )
        rel.update_familiarity(familiarity_delta)
        
        # Trust: grows with perceived sincerity, shrinks with deviation/avoidance
        trust_delta = (
            interaction.sincerity_estimate * params.trust_sincerity_coeff -
            trajectory_deviation * params.trust_avoidance_coeff
        )
        rel.update_trust(trust_delta)
        
        # Store relationship delta for logging
        interaction.relationship_delta = trust_delta + familiarity_delta
    
    # Debug logging (only in development)
    logger.debug(
        f"Social synthesis: shift={shift_magnitude:.2f}, "
        f"sincerity={interaction.sincerity_estimate:.2f}, "
        f"trajectory={trajectory_deviation:.2f}, "
        f"rel_delta={interaction.relationship_delta:.4f}"
    )
    
    return interaction


# ============================================================================
# Legacy stub kept for backward compatibility (in case anything imports it)
# ============================================================================

async def interpret_turn(
    user_input: str,
    state: HariState,
    recent_history: List[Dict[str, str]],
    turn_count: int,
) -> InteractionModel:
    """
    Legacy stub: kept for backward compatibility.
    Redirects to the new implementation with default monologue values.
    """
    logger.warning("interpret_turn() is deprecated; use interpret_turn_and_update_state() instead.")
    
    # Create a minimal monologue_output from available data (best effort)
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
        user_input=user_input,
        state=state,
        monologue_output=monologue_output,
        recent_history=recent_history,
        turn_count=turn_count,
        relational_manager=None
    )