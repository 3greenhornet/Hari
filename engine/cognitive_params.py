"""
engine/cognitive_params.py — Centralized cognitive calibration parameters.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ForgettingParams:
    """Primitive 19: Forgetting calibration."""
    base_decay_factor: float = 0.99
    retrieval_boost_factor: float = 0.05
    recency_protection_turns: int = 3
    significance_floor: float = 0.01
    relationship_decay_factor: float = 0.999


@dataclass(frozen=True)
class SocialParams:
    """Ticket 015: Social interpretation calibration."""
    thematic_continuity_weight: float = 0.4
    trajectory_deviation_weight: float = 0.3
    engagement_weight: float = 0.2
    history_weight: float = 0.1
    uncertainty_coeff: float = 0.3
    engagement_coeff: float = 0.25   # was 0.05
    
    social_ambiguity_coeff: float = 0.2
    familiarity_growth_coeff: float = 0.01
    familiarity_shift_decay_coeff: float = 0.005
    trust_sincerity_coeff: float = 0.005
    trust_avoidance_coeff: float = 0.01


@dataclass(frozen=True)
class PromotionParams:
    """Primitive 17-19: Ecology Pipeline calibration."""
    # Pattern formation (Memory → Pattern)
    pattern_min_memories: int = 3
    pattern_similarity_threshold: float = 0.82
    pattern_stability_cycles: int = 2
    pattern_archive_age_turns: int = 20

    # Contradiction detection (Pattern → Contradiction)
    contradiction_similarity_threshold: float = 0.6
    contradiction_severity_threshold: float = 0.3
    contradiction_check_interval: int = 5
    contradiction_llm_limit_per_cycle: int = 5

    # Curiosity formation (Contradiction → Curiosity)
    curiosity_importance_floor: float = 0.3
    curiosity_workspace_wins_threshold: int = 5

    # Interest formation (Curiosity → Interest)
    interest_activation_threshold: float = 0.6
    interest_session_repeats: int = 2

    # Identity evolution (Interest → Identity)
    identity_stabilization_threshold: float = 0.7

    # Staging evaluation
    staging_confidence_threshold: float = 0.6
    staging_max_age_turns: int = 50
    staging_batch_size: int = 20
    staging_archive_age_turns: int = 100

    # Archival
    interest_idle_sessions_threshold: int = 3

    # Performance
    llm_timeout_seconds: float = 3.0


FORGETTING = ForgettingParams()
SOCIAL = SocialParams()
PROMOTION = PromotionParams()