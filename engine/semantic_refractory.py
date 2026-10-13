"""Semantic-level suppression after a workspace win."""

import logging
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class SemanticRefractory:
    """Suppress semantically similar thoughts after a win."""

    def __init__(
        self,
        refractory_turns: int = 2,
        similarity_threshold: float = 0.85,
        max_penalty: float = 0.5,
    ):
        self.refractory_turns = refractory_turns
        self.similarity_threshold = similarity_threshold
        self.max_penalty = max_penalty
        self._suppressed: List[Tuple[int, np.ndarray, str]] = []

    def prune(self, current_turn: int) -> None:
        """Drop entries past the refractory window."""
        self._suppressed = [
            (turn, embedding, thought_id)
            for (turn, embedding, thought_id) in self._suppressed
            if current_turn - turn <= self.refractory_turns
        ]

    def register_winner(
        self,
        thought_id: str,
        embedding: Optional[List[float]],
        current_turn: int,
    ) -> None:
        """Register a winner's embedding for suppression."""
        if embedding is None:
            return
        try:
            array = np.array(embedding, dtype=np.float32)
            self._suppressed = [
                (turn, stored, item_id)
                for (turn, stored, item_id) in self._suppressed
                if item_id != thought_id
            ]
            self._suppressed.append((current_turn, array, thought_id))
        except Exception as error:
            logger.debug("Refractory register failed: %s", error)

    def apply_penalty(
        self,
        candidate_id: str,
        candidate_embedding: Optional[List[float]],
        current_turn: int,
    ) -> float:
        """Return a multiplier in ``[1.0 - max_penalty, 1.0]``."""
        if candidate_embedding is None:
            return 1.0
        try:
            candidate_vector = np.array(candidate_embedding, dtype=np.float32)
        except Exception:
            return 1.0

        candidate_norm = candidate_vector / (np.linalg.norm(candidate_vector) + 1e-8)
        penalty = 1.0

        for turn, embedding, thought_id in self._suppressed:
            if thought_id == candidate_id:
                continue
            age = current_turn - turn
            if age <= 0 or age > self.refractory_turns:
                continue
            embedding_norm = embedding / (np.linalg.norm(embedding) + 1e-8)
            similarity = float(np.dot(candidate_norm, embedding_norm))
            if similarity >= self.similarity_threshold:
                strength = 1.0 - (
                    (age - 1) / max(1, self.refractory_turns)
                )
                strength = max(0.0, min(1.0, strength))
                penalty *= 1.0 - self.max_penalty * strength

        return max(1.0 - self.max_penalty, penalty)

    def snapshot(self) -> dict:
        return {
            "suppressed_count": len(self._suppressed),
            "entries": [
                {"thought_id": thought_id, "turn": turn}
                for (turn, _embedding, thought_id) in self._suppressed
            ],
        }
