"""
engine/attention_config.py — Configuration for attention coefficients.

All magic numbers are centralized here. Calibration becomes a matter of
adjusting these values, not hunting through code.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import os


@dataclass
class AttentionCalibration:
    """
    Configuration object for attention pressure weights.
    
    All weights are normalized automatically. The effective weight of each
    pressure is: weight / sum(weights)
    """
    
    # Base weights for primary pressures (will be normalized)
    relevance_base: float = 0.8
    novelty_base: float = 0.3
    curiosity_base: float = 0.2
    completion_base: float = 0.2
    
    # Base weights for derived pressures (Ticket 011, 012)
    exploratory_base: float = 0.3      # Ticket 011
    shared_significance_base: float = 0.2  # Ticket 012
    
    # State modulation factors (how much state influences each weight)
    engagement_modulation: float = 0.2    # relevance = base + engagement * this
    curiosity_modulation: float = 0.6     # curiosity = base + curiosity * this
    novelty_modulation: float = 0.5       # novelty = base + curiosity * this
    completion_modulation: float = 0.6    # completion = base + completion * this
    exploratory_modulation: float = 0.4   # exploratory = base + novelty * this (Ticket 011)
    shared_significance_modulation: float = 0.4  # shared = base + care * this (Ticket 012)
    
    # Feedback loop guards (prevent positive feedback)
    max_engagement_influence: float = 0.8  # Cap engagement's influence
    engagement_decay: float = 0.01         # Decay factor per turn
    
    # Normalization
    normalize_weights: bool = True
    
    # Instrumentation
    log_pressure_contributions: bool = True
    log_frequency: int = 10  # Log every N turns
    
    # Experiment tracking
    experiment_id: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "AttentionCalibration":
        """Create config from environment variables."""
        return cls(
            relevance_base=float(os.getenv("ATTENTION_RELEVANCE_BASE", "0.8")),
            novelty_base=float(os.getenv("ATTENTION_NOVELTY_BASE", "0.3")),
            curiosity_base=float(os.getenv("ATTENTION_CURIOSITY_BASE", "0.2")),
            completion_base=float(os.getenv("ATTENTION_COMPLETION_BASE", "0.2")),
            exploratory_base=float(os.getenv("ATTENTION_EXPLORATORY_BASE", "0.3")),
            shared_significance_base=float(os.getenv("ATTENTION_SHARED_BASE", "0.2")),
            engagement_modulation=float(os.getenv("ATTENTION_ENGAGEMENT_MOD", "0.2")),
            curiosity_modulation=float(os.getenv("ATTENTION_CURIOSITY_MOD", "0.6")),
            novelty_modulation=float(os.getenv("ATTENTION_NOVELTY_MOD", "0.5")),
            completion_modulation=float(os.getenv("ATTENTION_COMPLETION_MOD", "0.6")),
            exploratory_modulation=float(os.getenv("ATTENTION_EXPLORATORY_MOD", "0.4")),
            shared_significance_modulation=float(os.getenv("ATTENTION_SHARED_MOD", "0.4")),
            max_engagement_influence=float(os.getenv("ATTENTION_MAX_ENGAGEMENT", "0.8")),
            engagement_decay=float(os.getenv("ATTENTION_ENGAGEMENT_DECAY", "0.01")),
            log_pressure_contributions=os.getenv("ATTENTION_LOG", "True").lower() == "true",
            experiment_id=os.getenv("ATTENTION_EXPERIMENT_ID", None)
        )
    
    def get_weights(self, state: Any, previous_engagement: Optional[float] = None) -> Dict[str, float]:
        """
        Compute the current weights based on state.
        Returns a dict of raw weights (before normalization).
        """
        # Guard against positive feedback loops
        # Apply decay to prevent engagement from running away
        current_engagement = float(state.engagement)
        if previous_engagement is not None:
            # If engagement is increasing too fast, apply decay
            engagement_delta = current_engagement - previous_engagement
            if engagement_delta > 0.1:  # Sudden spike
                current_engagement = previous_engagement + (engagement_delta * 0.5)  # Halve the spike
        
        # Clip engagement's influence to prevent runaway
        engagement_influence = current_engagement * self.engagement_modulation
        engagement_influence = min(engagement_influence, self.max_engagement_influence)
        
        raw = {
            "relevance": self.relevance_base + engagement_influence,
            "novelty": self.novelty_base + (float(state.curiosity) * self.novelty_modulation),
            "curiosity": self.curiosity_base + (float(state.curiosity) * self.curiosity_modulation),
            "completion": self.completion_base + (float(state.completion) * self.completion_modulation),
            # Ticket 011: Exploratory Potential (modulated by novelty drive)
            "exploratory_potential": self.exploratory_base + (float(state.novelty) * self.exploratory_modulation),
            # Ticket 012: Shared Significance (modulated by care drive)
            "shared_significance": self.shared_significance_base + (float(state.care) * self.shared_significance_modulation),
        }
        
        # Clamp to prevent negative weights
        for key in raw:
            raw[key] = max(0.1, raw[key])
        
        if self.normalize_weights:
            total = sum(raw.values())
            if total > 0:
                raw = {k: v / total for k, v in raw.items()}
        
        return raw


# Default configuration
DEFAULT_ATTENTION_CONFIG = AttentionCalibration()