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

_DEFAULT_SETPOINTS: Dict[str, float] = {
    "coherence": 0.7,
    "care": 0.5,
    "curiosity": 0.5,
    "completion": 0.4,
    "maintenance": 0.4,
    "rest": 0.5,
    "novelty": 0.3,
}

_VIABILITY_WEIGHTS: Dict[str, float] = {
    "coherence": 2.0,
    "care": 1.0,
    "curiosity": 1.0,
    "completion": 0.7,
    "maintenance": 1.5,
    "rest": 0.5,
    "novelty": 0.3,
}

_VIABILITY_TOLERANCE = 0.35
FROZEN = {"engagement"}

# Per‑field decay configuration
_DECAY_CONFIG = {
    "care": {"baseline": 0.5, "decay": 0.01, "rise": 0.05},
    "curiosity": {"baseline": 0.4, "decay": 0.04, "rise": 0.08},
    "maintenance": {"baseline": 0.4, "decay": 0.02, "rise": 0.06},
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
    source: Literal["MONOLOGUE", "PREDICTION_ERROR", "DRIFT", "GRACE", "BROADCAST", "REFLEXION"]
    reason: Optional[str] = None


@dataclass
class HariState:
    # Homeostatic drives (0.0 to 1.0)
    care: float = 0.5
    curiosity: float = 0.5
    maintenance: float = 0.5
    completion: float = 0.5
    coherence: float = 0.5
    rest: float = 0.5  # neutral ground state
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
    presence: float = 0.0  # Sprint 2.0A: Ability to "be" without performing

    # Telemetry and history (excluded from serialisation)
    _transitions: List[StateTransition] = field(default_factory=list, repr=False, init=False)
    _history_window: deque = field(default_factory=lambda: deque(maxlen=5), repr=False, init=False)

    def __post_init__(self):
        if not hasattr(self, '_transitions'):
            self._transitions = []
        if not hasattr(self, '_history_window'):
            self._history_window = deque(maxlen=5)
        if not hasattr(self, '_setpoints'):
            self._setpoints = dict(_DEFAULT_SETPOINTS)
        if not hasattr(self, '_decay_rates'):
            self._decay_rates = {key: value["decay"] for key, value in _DECAY_CONFIG.items()}
        if not hasattr(self, '_vad_decay_value'):
            self._vad_decay_value = _VAD_DECAY

    def asymptotic_update(self, current: float, delta: float, bounds: tuple = (0.0, 1.0)) -> float:
        """
        Control Theory: Bounded asymptotic update.
        Normalizes the current value to [0, 1] space to apply the delta,
        then scales it back to the original bounds.
        """
        low, high = bounds
        scale = high - low

        # Normalize current to [0, 1]
        norm_current = (current - low) / scale

        # Apply delta in normalized space
        if delta >= 0:
            norm_new = norm_current + ALPHA * delta * (1.0 - norm_current)
        else:
            norm_new = norm_current + ALPHA * delta * norm_current

        # Denormalize back to original bounds
        new = (norm_new * scale) + low
        return max(low, min(high, new))

    def update(self, deltas: Dict[str, float], source: Literal["MONOLOGUE", "PREDICTION_ERROR", "DRIFT", "GRACE", "BROADCAST", "REFLEXION"] = "DRIFT", reason: Optional[str] = None) -> None:
        for key, delta in deltas.items():
            if not hasattr(self, key) or key in FROZEN:
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
        # Drives — skip frozen keys.
        for key, config in _DECAY_CONFIG.items():
            if not hasattr(self, key) or key in FROZEN:
                continue
            old = getattr(self, key)
            baseline = config["baseline"]
            decay_rate = self._decay_rates.get(key, config["decay"])
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
        # VAD fields drift toward 0 using the instance-level rate.
        for key in ("valence", "arousal", "dominance"):
            old = getattr(self, key)
            new = old * (1 - self._vad_decay_value)
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

    @property
    def economy_pressure(self) -> float:
        """
        Economy of Presence: Only activates when rest is high AND engagement is low.
        """
        rest_excess = max(0.0, self.rest - 0.4)
        disengagement_excess = max(0.0, (1.0 - self.engagement) - 0.5)
        return min(1.0, (rest_excess + disengagement_excess) / 1.1)

    def get_transition_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [t.__dict__ for t in self._transitions[-limit:]]

    def compute_homeostatic_reward(self) -> float:
        """Return the negative weighted squared distance from setpoints."""
        distance = 0.0
        for drive, setpoint in self._setpoints.items():
            weight = _VIABILITY_WEIGHTS.get(drive, 1.0)
            value = float(getattr(self, drive, 0.5))
            distance += weight * (value - setpoint) ** 2
        return -distance

    def viability_zone_violated(self) -> List[str]:
        """Return drives outside the configured viability tolerance."""
        violated: List[str] = []
        for drive, setpoint in self._setpoints.items():
            value = float(getattr(self, drive, 0.5))
            if abs(value - setpoint) > _VIABILITY_TOLERANCE:
                violated.append(drive)
        return violated

    def get_setpoints_snapshot(self) -> Dict[str, float]:
        """Return a copy of the current setpoints."""
        return dict(self._setpoints)

    def apply_reflection_edits(self, edits: Dict[str, float]) -> None:
        """Apply bounded deltas to instance-owned editable parameters."""
        from engine.reflection_edit import EDITABLE_PARAMETERS

        for param_name, delta in edits.items():
            if param_name not in EDITABLE_PARAMETERS:
                continue
            target, field_name, (lower, upper) = EDITABLE_PARAMETERS[param_name]
            if field_name == "setpoint" and target in self._setpoints:
                value = self._setpoints[target] + delta
                self._setpoints[target] = max(lower, min(upper, value))
            elif field_name == "decay":
                if target == "vad":
                    value = self._vad_decay_value + delta
                    self._vad_decay_value = max(lower, min(upper, value))
                elif target in self._decay_rates:
                    value = self._decay_rates[target] + delta
                    self._decay_rates[target] = max(lower, min(upper, value))

    def to_prompt_context(self) -> str:
        return (
            f"Drives: care={self.care:.2f}, curiosity={self.curiosity:.2f}, "
            f"maintenance={self.maintenance:.2f}, completion={self.completion:.2f}, "
            f"coherence={self.coherence:.2f}, rest={self.rest:.2f}, novelty={self.novelty:.2f}\n"
            f"Mood (VAD): valence={self.valence:.2f}, arousal={self.arousal:.2f}, dominance={self.dominance:.2f}"
        )