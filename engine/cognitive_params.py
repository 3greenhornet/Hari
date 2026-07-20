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
    engagement_coeff: float = 0.05
    social_ambiguity_coeff: float = 0.2
    familiarity_growth_coeff: float = 0.01
    familiarity_shift_decay_coeff: float = 0.005
    trust_sincerity_coeff: float = 0.005
    trust_avoidance_coeff: float = 0.01


FORGETTING = ForgettingParams()
SOCIAL = SocialParams()