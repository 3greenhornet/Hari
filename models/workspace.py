"""Canonical workspace data model."""

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional


@dataclass
class ActivationMetrics:
    activation: float = 1.0
    last_attended_turn: int = 0
    reentry_count: int = 0
    decay_rate: float = 0.15


class WorkspaceItem:
    def __init__(
        self,
        id: str,
        item_type: Literal[
            "memory", "hypothesis", "curiosity_node", "narrative_thread",
            "open_thought", "minimal", "incoming_event",
        ],
        source: str,
        payload: Dict[str, Any],
        attention_weight: float = 0.0,
        metrics: Optional[ActivationMetrics] = None,
    ):
        self.id = id
        self.item_type = item_type
        self.source = source
        self.payload = payload
        self.attention_weight = attention_weight
        self.metrics = metrics or ActivationMetrics()

    @property
    def content(self) -> str:
        return self.payload.get("content") or self.payload.get("statement") or str(self.payload)

    @property
    def activation(self) -> float:
        return self.metrics.activation

    @activation.setter
    def activation(self, value: float):
        self.metrics.activation = value

    @property
    def turn_loaded(self) -> int:
        return self.metrics.last_attended_turn

    @turn_loaded.setter
    def turn_loaded(self, value: int):
        self.metrics.last_attended_turn = value