"""
engine/prediction.py — Deterministic prediction error using cosine similarity.
No LLM calls. Local, fast, observable.
"""

import math
import logging
from typing import List

from engine.memory import embed

logger = logging.getLogger(__name__)

async def compute_prediction_error(
    last_assistant_response: str,
    current_user_input: str
) -> float:
    """
    Compute prediction error as 1 - cosine_similarity(embed(last), embed(current)).
    Returns 0.0 (no surprise) to 1.0 (complete surprise).
    """
    if not last_assistant_response or not current_user_input:
        return 0.5

    try:
        emb_expected = await embed(last_assistant_response)
        emb_actual = await embed(current_user_input)
        similarity = _cosine_similarity(emb_expected, emb_actual)
        error = 1.0 - similarity
        return max(0.0, min(1.0, error))
    except Exception as e:
        logger.error(f"Prediction error failed: {e}", exc_info=True)
        return 0.5

def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)