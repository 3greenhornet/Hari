# hari/psyche/state.py
"""
Hari's internal state: drives, VAD, conversational metrics.
Now with historical window and derived pressure properties.
"""

import math
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal, Any

ALPHA = float(os.getenv("ASYMPTOTIC_ALPHA", "0.25"))

# Drive keys for snapshot
DRIVE_KEYS = ["care", "curiosity", "maintenance", "completion", "coherence", "rest", "novelty"]

# Per‑field decay configuration
_DECAY_CONFIG = {
    "care": {"baseline": 0.5, "decay": 0.01, "rise": 0.05},
    "curiosity": {"baseline": 0.4, "decay": 0.04, "rise": 0.08},
    "maintenance": {"baseline": 0.6, "decay": 0.02, "rise": 0.06},
    "completion": {"baseline": 0.3, "decay": 0.03, "rise": 0.07},
    "coherence": {"baseline": 0.7, "decay": 0.01, "rise": 0.04},
    "rest": {"baseline": 0.2, "decay": 0.08, "rise": 0.02},
    "novelty": {"baseline": 0.1, "decay": 0.25, "rise": 0.15},
}
_VAD_DECAY = 0.02


@dataclass
class StateTransition:
    timestamp: float
    field: str
    old_value: float
    delta: float
    new_value: float
    source: Literal["MONOLOGUE", "PREDICTION_ERROR", "DRIFT", "GRACE"]
    reason: Optional[str] = None


@dataclass
class HariState:
    # Homeostatic drives (0.0 to 1.0)
    care: float = 0.5
    curiosity: float = 0.5
    maintenance: float = 0.5
    completion: float = 0.5
    coherence: float = 0.5
    rest: float = 0.2
    novelty: float = 0.5

    # Affective VAD (-1.0 to +1.0)
    valence: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.0

    # Conversational state
    momentum: float = 0.5
    stability: float = 0.5
    engagement: float = 0.5

    # Meta-cognitive
    uncertainty: float = 0.0
    social_ambiguity: float = 0.0
    cognitive_tension: float = 0.0

    # Telemetry and history (excluded from serialisation)
    _transitions: List[StateTransition] = field(default_factory=list, repr=False, init=False)
    _history_window: deque = field(default_factory=lambda: deque(maxlen=5), repr=False, init=False)

    def __post_init__(self):
        if not hasattr(self, '_transitions'):
            self._transitions = []
        if not hasattr(self, '_history_window'):
            self._history_window = deque(maxlen=5)

    def asymptotic_update(self, current: float, delta: float, bounds: tuple = (0.0, 1.0)) -> float:
        if delta >= 0:
            new = current + ALPHA * delta * (1.0 - current)
        else:
            new = current + ALPHA * delta * current
        low, high = bounds
        return max(low, min(high, new))

    def update(self, deltas: Dict[str, float], source: Literal["MONOLOGUE", "PREDICTION_ERROR", "DRIFT", "GRACE"] = "DRIFT", reason: Optional[str] = None) -> None:
        for key, delta in deltas.items():
            if not hasattr(self, key):
                continue
            old = getattr(self, key)
            bounds = (-1.0, 1.0) if key in ("valence", "arousal", "dominance") else (0.0, 1.0)
            new_val = self.asymptotic_update(old, delta, bounds)
            setattr(self, key, new_val)
            self._transitions.append(StateTransition(
                timestamp=time.time(),
                field=key,
                old_value=old,
                delta=delta,
                new_value=new_val,
                source=source,
                reason=reason,
            ))
            if len(self._transitions) > 1000:
                self._transitions.pop(0)
        self.record_snapshot()

    def natural_drift(self) -> None:
        # Drives
        for key, config in _DECAY_CONFIG.items():
            if not hasattr(self, key):
                continue
            old = getattr(self, key)
            baseline = config["baseline"]
            decay_rate = config["decay"]
            new = old * (1 - decay_rate) + baseline * decay_rate
            setattr(self, key, new)
            self._transitions.append(StateTransition(
                timestamp=time.time(),
                field=key,
                old_value=old,
                delta=new - old,
                new_value=new,
                source="DRIFT",
                reason="natural_drift",
            ))
            if len(self._transitions) > 1000:
                self._transitions.pop(0)
        # VAD fields drift toward 0
        for key in ("valence", "arousal", "dominance"):
            old = getattr(self, key)
            new = old * (1 - _VAD_DECAY)
            setattr(self, key, new)
            self._transitions.append(StateTransition(
                timestamp=time.time(),
                field=key,
                old_value=old,
                delta=new - old,
                new_value=new,
                source="DRIFT",
                reason="natural_drift",
            ))
            if len(self._transitions) > 1000:
                self._transitions.pop(0)
        self.record_snapshot()

    def record_snapshot(self):
        """Store current drive values into history window."""
        snapshot = {k: getattr(self, k) for k in DRIVE_KEYS}
        self._history_window.append(snapshot)

    def get_velocity(self, key: str) -> float:
        """Compute velocity (trend) of a drive over the history window."""
        if not self._history_window or key not in DRIVE_KEYS:
            return 0.0
        avg = sum(s[key] for s in self._history_window) / len(self._history_window)
        return getattr(self, key) - avg

    @property
    def completion_pressure(self) -> float:
        """Derived pressure: base completion + small velocity contribution."""
        return min(1.0, self.completion + (self.get_velocity("completion") * 0.2))

    def get_transition_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [t.__dict__ for t in self._transitions[-limit:]]

    def to_prompt_context(self) -> str:
        return (
            f"Drives: care={self.care:.2f}, curiosity={self.curiosity:.2f}, "
            f"maintenance={self.maintenance:.2f}, completion={self.completion:.2f}, "
            f"coherence={self.coherence:.2f}, rest={self.rest:.2f}, novelty={self.novelty:.2f}\n"
            f"Mood (VAD): valence={self.valence:.2f}, arousal={self.arousal:.2f}, dominance={self.dominance:.2f}"
        )