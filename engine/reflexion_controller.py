import math
from typing import Any, Dict


class ReflexionController:
    def __init__(self, g_threshold: float = 0.8, gamma: float = 0.25):
        self.g_threshold = g_threshold
        self.gamma = gamma

    def process_prediction_failure(self, state, prediction_error: float) -> Dict[str, Any]:
        if prediction_error > self.g_threshold:
            delta = 1.0 / (1.0 + math.exp(-(prediction_error - self.g_threshold)))
            state.update(
                {
                    "arousal": self.gamma * delta,
                    "cognitive_tension": self.gamma * delta * 1.5,
                },
                source="REFLEXION",
                reason="high_prediction_error",
            )
            tension = float(state.cognitive_tension)
            return {
                "temperature": max(0.2, 0.7 - (0.4 * tension)),
                "workspace_weight": 1.0 + tension,
            }
        return {}
