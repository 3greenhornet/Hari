"""
engine/attention_config.py — Configuration for attention coefficients.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import os


@dataclass
class AttentionCalibration:
    event_affinity_base: float = 0.30
    endogenous_affinity_base: float = 0.20
    novelty_base: float = 0.35
    curiosity_base: float = 0.35
    completion_base: float = 0.35
    exploratory_base: float = 0.30
    shared_significance_base: float = 0.30
    coherence_tension_base: float = 0.30

    engagement_modulation: float = 0.10
    curiosity_modulation: float = 0.50
    novelty_modulation: float = 0.50
    completion_modulation: float = 0.50
    exploratory_modulation: float = 0.40
    shared_significance_modulation: float = 0.40
    coherence_tension_modulation: float = 0.50

    max_engagement_influence: float = 0.30
    engagement_decay: float = 0.01

    normalize_weights: bool = True
    log_pressure_contributions: bool = True
    log_frequency: int = 10
    experiment_id: Optional[str] = None

    intrinsic_relevance_base: float = 0.20
    intrinsic_relevance_curiosity_modulation: float = 0.50
    intrinsic_relevance_completion_modulation: float = 0.20
    intrinsic_relevance_coherence_modulation: float = 0.20

    authority_base: float = 0.25
    persistence_base: float = 0.20
    internal_activation_base: float = 0.20
    internal_standing_base: float = 0.15
    internal_standing_modulation: float = 0.30

    @classmethod
    def from_env(cls) -> "AttentionCalibration":
        return cls(
            event_affinity_base=float(os.getenv("EVENT_AFFINITY_BASE", "0.30")),
            endogenous_affinity_base=float(os.getenv("ENDOGENOUS_AFFINITY_BASE", "0.20")),
            novelty_base=float(os.getenv("ATTENTION_NOVELTY_BASE", "0.35")),
            curiosity_base=float(os.getenv("ATTENTION_CURIOSITY_BASE", "0.35")),
            completion_base=float(os.getenv("ATTENTION_COMPLETION_BASE", "0.35")),
            exploratory_base=float(os.getenv("ATTENTION_EXPLORATORY_BASE", "0.30")),
            shared_significance_base=float(os.getenv("ATTENTION_SHARED_BASE", "0.30")),
            coherence_tension_base=float(os.getenv("ATTENTION_COHERENCE_TENSION_BASE", "0.30")),
            engagement_modulation=float(os.getenv("ATTENTION_ENGAGEMENT_MOD", "0.10")),
            curiosity_modulation=float(os.getenv("ATTENTION_CURIOSITY_MOD", "0.50")),
            novelty_modulation=float(os.getenv("ATTENTION_NOVELTY_MOD", "0.50")),
            completion_modulation=float(os.getenv("ATTENTION_COMPLETION_MOD", "0.50")),
            exploratory_modulation=float(os.getenv("ATTENTION_EXPLORATORY_MOD", "0.40")),
            shared_significance_modulation=float(os.getenv("ATTENTION_SHARED_MOD", "0.40")),
            coherence_tension_modulation=float(os.getenv("ATTENTION_COHERENCE_TENSION_MOD", "0.50")),
            max_engagement_influence=float(os.getenv("ATTENTION_MAX_ENGAGEMENT", "0.30")),
            engagement_decay=float(os.getenv("ATTENTION_ENGAGEMENT_DECAY", "0.01")),
            log_pressure_contributions=os.getenv("ATTENTION_LOG", "True").lower() == "true",
            experiment_id=os.getenv("ATTENTION_EXPERIMENT_ID", None),
            authority_base=float(os.getenv("AUTHORITY_BASE", "0.25")),
            persistence_base=float(os.getenv("PERSISTENCE_BASE", "0.20")),
            internal_activation_base=float(os.getenv("INTERNAL_ACTIVATION_BASE", "0.20")),
            internal_standing_base=float(os.getenv("INTERNAL_STANDING_BASE", "0.15")),
            internal_standing_modulation=float(os.getenv("INTERNAL_STANDING_MOD", "0.30")),
        )

    def get_weights(self, state: Any, previous_engagement: Optional[float] = None) -> Dict[str, float]:
        raw = {
            "event_affinity": self.event_affinity_base,
            "endogenous_affinity": self.endogenous_affinity_base,
            "novelty": self.novelty_base + (float(state.curiosity) * self.novelty_modulation),
            "curiosity": self.curiosity_base + (float(state.curiosity) * self.curiosity_modulation),
            "completion": self.completion_base + (float(state.completion) * self.completion_modulation),
            "exploratory_potential": self.exploratory_base + (float(state.novelty) * self.exploratory_modulation),
            "shared_significance": self.shared_significance_base + (float(state.care) * self.shared_significance_modulation),
            "coherence_tension": self.coherence_tension_base + (float(state.cognitive_tension) * self.coherence_tension_modulation),
            "persistence": self.persistence_base,
            "internal_activation": self.internal_activation_base,
            "intrinsic_relevance": (
                self.intrinsic_relevance_base
                + (float(state.curiosity) * self.intrinsic_relevance_curiosity_modulation)
                + (float(state.completion) * self.intrinsic_relevance_completion_modulation)
                + (float(state.coherence) * self.intrinsic_relevance_coherence_modulation)
            ),
            "internal_standing": (
                self.internal_standing_base
                + max(float(state.curiosity), float(state.completion), float(state.coherence))
                * self.internal_standing_modulation
            ),
        }
        if os.getenv("ENABLE_AUTHORITY_CAUSAL", "false").lower() == "true":
            raw["authority"] = self.authority_base

        for key in raw:
            raw[key] = max(0.1, raw[key])

        if self.normalize_weights:
            total = sum(raw.values())
            if total > 0:
                raw = {k: v / total for k, v in raw.items()}
        return raw


DEFAULT_ATTENTION_CONFIG = AttentionCalibration()