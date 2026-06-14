# hari/engine/stage1_monologue.py
"""
Phase 5: Pure sensory monologue – no command flags.
Uses provider abstraction for structured generation.
"""

import os
import logging
from typing import List

from psyche.state import HariState
from models.monologue_output import MonologueOutput
from providers.factory import get_provider

logger = logging.getLogger(__name__)

_MODEL = os.getenv("STAGE1_MODEL", "gemini-2.5-flash")


def _format_memories(memories: List) -> str:
    if not memories:
        return "No relevant memories."
    lines = []
    for i, mem in enumerate(memories[:5]):
        content = getattr(mem, "content", str(mem))[:200]
        lines.append(f"  {i+1}. {content}...")
    return "\n".join(lines)


def _build_sensory_prompt(
    user_input: str,
    state: HariState,
    recent_memories: List,
    prediction_error: float,
) -> str:
    return f"""You are Hari. This is your private inner monologue – no one sees this but you.

Your current internal state:
{state.to_prompt_context()}

Prediction error (surprise): {prediction_error:.3f} (0=expected, 1=surprising)

Recent memories (from similarity search):
{_format_memories(recent_memories)}

User just said: "{user_input}"

Output ONLY a JSON object with these fields:
- perceived_user_intent: one of curious, avoiding, testing, help_seeking, sharing, derailing
- intent_confidence: float 0.0-1.0
- thematic_continuity: float 0.0-1.0 (0=complete rupture, 1=seamless)
- user_engagement_estimate: float 0.0-1.0
- interruption_severity: float 0.0-1.0 (0=none, 1=complete derailment)
- dynamic_candidates: list of {{"content": str, "item_type": one of memory/hypothesis/curiosity_node/narrative_thread/open_thought, "urgency": float}}
- curiosity_trigger: optional string (a new question)
- hypothesis_update: optional string
- self_belief_update: optional string
- triggered_memory_summary: optional string
- memory_significance: float 0.0-1.0
- memory_emotional_tone: neutral, positive, negative, curious, frustrated

Be honest. This is your inner voice.
Output valid JSON only, no extra text.
"""


def _default_sensory_output() -> MonologueOutput:
    """Fallback when provider fails."""
    return MonologueOutput(
        perceived_user_intent="sharing",
        intent_confidence=0.5,
        thematic_continuity=0.8,
        user_engagement_estimate=0.5,
        interruption_severity=0.0,
    )


async def run_monologue(
    user_input: str,
    state: HariState,
    recent_memories: List,
    prediction_error: float = 0.0,
) -> MonologueOutput:
    """
    Sensory monologue – reports perceptions, no decisions.
    """
    provider = get_provider()
    prompt = _build_sensory_prompt(user_input, state, recent_memories, prediction_error)

    try:
        output = await provider.generate_structured(
            prompt=prompt,
            response_model=MonologueOutput,
            temperature=0.3
        )
        return output
    except Exception as e:
        logger.error(f"Monologue failed: {e}", exc_info=True)
        return _default_sensory_output()