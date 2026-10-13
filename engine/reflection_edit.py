"""Convert reflection text into bounded internal parameter deltas."""

import json
import logging
from typing import Dict, List, Tuple

from litellm import acompletion

from engine.stage1_monologue import MONOLOGUE_FALLBACK_MODELS, _extract_json_safely
from psyche.state import HariState

logger = logging.getLogger(__name__)

EDITABLE_PARAMETERS: Dict[str, Tuple[str, str, Tuple[float, float]]] = {
    "coherence_setpoint": ("coherence", "setpoint", (0.0, 1.0)),
    "care_setpoint": ("care", "setpoint", (0.0, 1.0)),
    "curiosity_setpoint": ("curiosity", "setpoint", (0.0, 1.0)),
    "maintenance_setpoint": ("maintenance", "setpoint", (0.0, 1.0)),
    "completion_setpoint": ("completion", "setpoint", (0.0, 1.0)),
    "rest_setpoint": ("rest", "setpoint", (0.0, 1.0)),
    "novelty_setpoint": ("novelty", "setpoint", (0.0, 1.0)),
    "coherence_decay": ("coherence", "decay", (0.001, 0.05)),
    "care_decay": ("care", "decay", (0.001, 0.05)),
    "curiosity_decay": ("curiosity", "decay", (0.001, 0.10)),
    "maintenance_decay": ("maintenance", "decay", (0.001, 0.05)),
    "completion_decay": ("completion", "decay", (0.001, 0.05)),
    "rest_decay": ("rest", "decay", (0.001, 0.10)),
    "novelty_decay": ("novelty", "decay", (0.001, 0.25)),
    "vad_decay": ("vad", "decay", (0.001, 0.10)),
}

FORBIDDEN_PARAMETERS: List[str] = [
    "attention_weights",
    "promotion_thresholds",
    "constitution",
    "origin",
    "self_beliefs",
    "narrative_threads",
    "commitments",
    "identity_stability_score",
]


class ReflectionEdit:
    """Extract whitelisted, rate-limited, bounded parameter deltas."""

    def __init__(
        self,
        min_edit_interval_turns: int = 5,
        max_delta_magnitude: float = 0.05,
        min_reflection_length: int = 20,
    ):
        self.min_edit_interval_turns = min_edit_interval_turns
        self.max_delta_magnitude = max_delta_magnitude
        self.min_reflection_length = min_reflection_length
        self._last_edit_turn = -999
        self._edit_history: List[Dict] = []

    def can_edit(self, current_turn: int) -> bool:
        return current_turn - self._last_edit_turn >= self.min_edit_interval_turns

    def edit_history(self) -> List[Dict]:
        return list(self._edit_history)

    async def extract_edits(
        self,
        reflection_text: str,
        state: HariState,
        current_turn: int,
    ) -> Dict[str, float]:
        if not self.can_edit(current_turn):
            return {}
        if not reflection_text or len(reflection_text.strip()) < self.min_reflection_length:
            return {}

        prompt = self._build_extraction_prompt(reflection_text, state)
        for model in MONOLOGUE_FALLBACK_MODELS:
            try:
                kwargs = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a parameter adjustment extractor for a "
                                "cognitive architecture. Return ONLY JSON with the "
                                "requested format. If no parameter change is clear, "
                                "return {}."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                    "timeout": 8.0,
                }
                if not model.startswith("openrouter"):
                    kwargs["response_format"] = {"type": "json_object"}
                response = await acompletion(**kwargs)
                data = json.loads(_extract_json_safely(response.choices[0].message.content))
                edits = self._validate_edits(data)
                if edits:
                    self._last_edit_turn = current_turn
                    self._edit_history.append(
                        {
                            "turn": current_turn,
                            "edits": edits,
                            "reflection_preview": reflection_text[:200],
                        }
                    )
                    logger.info("Reflection edits applied: %s", edits)
                return edits
            except Exception as error:
                logger.warning("Reflection edit extraction failed on %s: %s", model, error)
        return {}

    def _build_extraction_prompt(self, reflection_text: str, state: HariState) -> str:
        drive_names = ["care", "curiosity", "maintenance", "completion", "coherence", "rest", "novelty"]
        state_summary = ", ".join(
            f"{name}={getattr(state, name, 0.5):.2f}" for name in drive_names
        )
        lines = []
        for name, (target, field, (lower, upper)) in EDITABLE_PARAMETERS.items():
            current = self._get_current_value(name, state)
            lines.append(
                f"  - {name}: target={target}, field={field}, "
                f"current~={current:.3f}, bounds=({lower}, {upper})"
            )
        return (
            f'Reflection:\n"{reflection_text}"\n\n'
            f"Current drive state: {state_summary}\n\n"
            "Which internal parameters should change based on this reflection?\n\n"
            f"Editable parameters:\n{chr(10).join(lines)}\n\n"
            f"Return JSON with parameter names as keys and deltas as values. "
            f"Deltas must satisfy |delta| <= {self.max_delta_magnitude}. "
            "Return {} when no change is clearly implied."
        )

    def _get_current_value(self, param_name: str, state: HariState) -> float:
        if param_name.endswith("_setpoint"):
            drive = param_name.removesuffix("_setpoint")
            setpoints = getattr(state, "_setpoints", None)
            return setpoints.get(drive, 0.5) if setpoints else 0.5
        if param_name.endswith("_decay"):
            target = param_name.removesuffix("_decay")
            if target == "vad":
                return getattr(state, "_vad_decay_value", 0.02)
            decays = getattr(state, "_decay_rates", None)
            return decays.get(target, 0.02) if decays else 0.02
        return 0.0

    def _validate_edits(self, data: Dict) -> Dict[str, float]:
        if not isinstance(data, dict):
            return {}
        valid: Dict[str, float] = {}
        for param_name, delta in data.items():
            if param_name not in EDITABLE_PARAMETERS:
                logger.warning("Reflection attempted to edit forbidden param '%s'", param_name)
                continue
            try:
                delta_float = float(delta)
            except (TypeError, ValueError):
                continue
            delta_float = max(-self.max_delta_magnitude, min(self.max_delta_magnitude, delta_float))
            if abs(delta_float) >= 0.001:
                valid[param_name] = delta_float
        return valid
