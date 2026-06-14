# hari/psyche/grace.py
"""
Grace system: rolling window of user engagement estimates from monologue.
Used to modulate negative deltas (encourage reciprocity).
"""

from collections import deque
from typing import List

class GraceTracker:
    def __init__(self, window_size: int = 15, decay_factor: float = 0.98):
        self.window = deque(maxlen=window_size)
        self.decay_factor = decay_factor

    def add_engagement_score(self, score: float) -> None:
        """Called with monologue.user_engagement_estimate."""
        self.window.append(max(0.0, min(1.0, score)))

    def get_weighted_average(self) -> float:
        """Exponentially weighted average, favoring recent turns."""
        if not self.window:
            return 0.5
        total, weight_sum = 0.0, 0.0
        for i, val in enumerate(self.window):
            weight = self.decay_factor ** (len(self.window) - i - 1)
            total += val * weight
            weight_sum += weight
        return total / weight_sum if weight_sum > 0 else 0.5

    def modulate_delta(self, delta: float) -> float:
        """
        If engagement is high, reduce negative deltas (be nicer).
        If engagement is low, amplify negative deltas (reciprocate coldness).
        """
        avg = self.get_weighted_average()
        if avg > 0.6:
            # engaged user: halve negative deltas
            return delta * 0.5 if delta < 0 else delta
        elif avg < 0.4:
            # disengaged user: double negative deltas
            return delta * 2.0 if delta < 0 else delta
        return delta