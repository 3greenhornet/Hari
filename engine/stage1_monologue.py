# hari/engine/stage1_monologue.py
"""
Phase 5: Pure sensory monologue – unified LiteLLM fallback with robust JSON extraction.
"""

import os
import json
import re
import logging
from typing import List, Optional, Any

from litellm import acompletion
from psyche.state import HariState
from models.monologue_output import MonologueOutput

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Monologue‑specific fallback chain (identical structure to dialogue)
# -----------------------------------------------------------------------------
_FALLBACK_CANDIDATES = [
    ("gemini/gemini-2.5-flash", os.getenv("GEMINI_API_KEY")),
    ("groq/llama-3.1-8b-instant", os.getenv("GROQ_API_KEY")),
    ("groq/llama-3.3-70b-versatile", os.getenv("GROQ_API_KEY")),
    ("mistral/mistral-small-latest", os.getenv("MISTRAL_API_KEY")),
    ("openrouter/meta-llama/llama-3.3-70b-instruct:free", os.getenv("OPENROUTER_API_KEY")),
]
MONOLOGUE_FALLBACK_MODELS = [model for model, key in _FALLBACK_CANDIDATES if key]


def _extract_json_safely(raw_text: str) -> str:
    """
    Robust regex utility to extract nested JSON objects from raw text payloads.
    Guarantees parsing safety even if models return conversational prefixes.
    """
    text = raw_text.strip()
    # Locate the first structural brace and matching closing brace
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text


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
Dynamic candidates are NOT abstract topics or discussion points.
They are **conversational actions** Hari can perform right now.

Bad examples:
- "Explore the concept of self-introduction"
- "Discuss casual conversation"

Good examples:
- "Introduce yourself to Anand"
- "Keep the tone casual and friendly"
- "Notice the sudden topic change and react naturally"
- "Stop explaining and just react"
- "Tell a random observation"

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
    Sensory monologue extraction engine.
    Uses unified LiteLLM cascades to handle provider outages and rate limits safely.
    """
    prompt = _build_sensory_prompt(user_input, state, recent_memories, prediction_error)

    messages = [
        {
            "role": "system",
            "content": (
                "You are Hari's internal monologue. Analyse input context deeply. "
                "You MUST respond exclusively with a valid JSON object matching the requested schema fields. "
                "Do not include conversational preamble or explanation text outside the JSON structure."
            )
        },
        {"role": "user", "content": prompt}
    ]

    for model in MONOLOGUE_FALLBACK_MODELS:
        try:
            # Base parameters
            kwargs = {"model": model, "messages": messages, "temperature": 0.2, "timeout": 3}

            # Use native JSON response format where supported (skip for OpenRouter free)
            if not model.startswith("openrouter"):
                kwargs["response_format"] = {"type": "json_object"}

            response = await acompletion(**kwargs)
            raw_payload = response.choices[0].message.content

            # Clean conversational text drift away from the JSON object structural targets
            clean_json_str = _extract_json_safely(raw_payload)

            # Validate output data structures natively using your Pydantic architecture
            output = MonologueOutput.model_validate_json(clean_json_str)
            logger.info(f"Sensory Monologue successfully generated via platform model: {model}")
            return output

        except Exception as provider_err:
            logger.warning(f"Sensory pipeline stage 1 anomaly on model '{model}': {provider_err}")
            continue  # Try next model in cascade

    # Absolute fallback boundary logic protecting the pipeline execution clock
    logger.critical("CRITICAL SUBSTRATE FAULT: All Monologue infrastructure providers exhausted. Issuing emergency defaults.")
    return _default_sensory_output()