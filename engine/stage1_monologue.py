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
from pydantic import ValidationError
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
    active_thread_context: Optional[str] = None,
) -> str:
    prompt = f"""You are Hari. This is your private inner monologue – no one sees this but you.

Your current internal state:
{state.to_prompt_context()}

Prediction error (surprise): {prediction_error:.3f} (0=expected, 1=surprising)

Recent memories (from similarity search):
{_format_memories(recent_memories)}
"""

    if active_thread_context:
        prompt += f"""
Current Active Cognitive Thread:
{active_thread_context}
Analyze the conversation trajectory relative to this active thread.
"""

    prompt += f"""
User just said: "{user_input}"

Output ONLY a JSON object with these fields:

- perceived_user_intent: one of curious, avoiding, testing, help_seeking, sharing, derailing
- intent_confidence: float 0.0-1.0
- thematic_continuity: float 0.0-1.0 (0=complete rupture, 1=seamless)
- user_engagement_estimate: float 0.0-1.0
- interruption_severity: float 0.0-1.0 (0=none, 1=complete derailment)
- dynamic_candidates: list of {"content": str, "item_type": one of memory/hypothesis/curiosity_node/narrative_thread/open_thought, "urgency": float}
  - IMPORTANT: Evaluate the interaction, not just the literal words. If the user's utterance has conversational significance (e.g., abrupt topic shift, testing, hesitation, avoidance), you MUST generate candidates separating observation from inference.
  - Step 1: Generate an "open_thought" for the OBSERVATION (what literally happened).
    - Example: {"content": "The topic shifted abruptly from identity to trivia.", "item_type": "open_thought", "urgency": 0.8}
  - Step 2: Generate a "hypothesis" for the INFERENCE (what they might be doing), preserving uncertainty.
    - Example: {"content": "The user might be testing my factual recall rather than continuing the conversation.", "item_type": "hypothesis", "urgency": 0.6}
  - Do NOT invent new item_type values. If no category clearly applies, use "open_thought".
- curiosity_trigger: optional string
- hypothesis_update: optional string
- self_belief_update: optional string
- triggered_memory_summary: optional string
- memory_significance: float 0.0-1.0
- memory_emotional_tone: neutral, positive, negative, curious, frustrated

# Ticket 014: Conversation trajectory analysis
- trajectory_deviation: float 0.0-1.0 (0.0 = continuing current thread, 1.0 = complete departure)
- trajectory_confidence: float 0.0-1.0 (how confident are you in the deviation estimate)
- referenced_thread_id: string or null (the ID of the thread being deviated from, if any)

Be honest. This is your inner voice.
Output valid JSON only, no extra text.
"""
    return prompt


def _default_sensory_output(prediction_error: float = 0.5) -> MonologueOutput:
    """Fallback when provider fails. Uses prediction error to keep state moving."""
    return MonologueOutput(
        perceived_user_intent="sharing",
        intent_confidence=0.5,
        thematic_continuity=max(0.0, 1.0 - prediction_error),
        user_engagement_estimate=0.5,
        interruption_severity=prediction_error,
        trajectory_deviation=prediction_error,
        trajectory_confidence=0.3,
        referenced_thread_id=None,
        dynamic_candidates=[],
        curiosity_trigger=None,
        hypothesis_update=None,
        self_belief_update=None,
        triggered_memory_summary=None,
        memory_significance=0.5,
        memory_emotional_tone="neutral",
    )


async def run_monologue(
    user_input: str,
    state: HariState,
    recent_memories: List,
    prediction_error: float = 0.0,
    active_thread_context: Optional[str] = None,
) -> MonologueOutput:
    """
    Sensory monologue extraction engine.
    Uses unified LiteLLM cascades to handle provider outages and rate limits safely.
    """
    prompt = _build_sensory_prompt(user_input, state, recent_memories, prediction_error, active_thread_context)

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
            if not model.startswith("openrouter"):
                kwargs["response_format"] = {"type": "json_object"}

            response = await acompletion(**kwargs)
            raw_payload = response.choices[0].message.content
            clean_json_str = _extract_json_safely(raw_payload)

            # Try to parse
            output = MonologueOutput.model_validate_json(clean_json_str)
            logger.info(f"Sensory Monologue successfully generated via platform model: {model}")
            return output

        except ValidationError as provider_err:
            logger.warning(f"Validation error on {model}, retrying with stricter prompt...")
            try:
                retry_messages = messages + [
                    {"role": "system", "content": "Previous response violated the JSON schema. Regenerate using ONLY the allowed item_type values. Do not invent new values."}
                ]
                retry_kwargs = {"model": model, "messages": retry_messages, "temperature": 0.1, "timeout": 3}
                if not model.startswith("openrouter"):
                    retry_kwargs["response_format"] = {"type": "json_object"}

                retry_response = await acompletion(**retry_kwargs)
                retry_raw = retry_response.choices[0].message.content
                retry_clean = _extract_json_safely(retry_raw)
                output = MonologueOutput.model_validate_json(retry_clean)
                logger.info(f"Retry successful on {model}")
                return output
            except Exception as retry_err:
                logger.warning(f"Retry failed on {model}: {retry_err}")
                continue
        except Exception as provider_err:
            logger.warning(f"Sensory pipeline stage 1 anomaly on model '{model}': {provider_err}")
            continue

    # Absolute fallback
    logger.critical("CRITICAL SUBSTRATE FAULT: All Monologue infrastructure providers exhausted. Issuing emergency defaults.")
    return _default_sensory_output(prediction_error)