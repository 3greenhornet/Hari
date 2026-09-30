# hari/engine/stage1_monologue.py
"""
Phase 5: Pure sensory monologue – unified LiteLLM fallback with robust JSON extraction.
"""

import os
import json
import re
import logging
import asyncio
import litellm
litellm.drop_params = True
litellm.num_retries = 2

from typing import List, Optional, Any, Dict


def _normalize_hypothesis_proposal(raw: dict) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    if raw.get("statement"):
        return raw
    if raw.get("hypothesis"):
        return {
            "type": "other",
            "statement": raw["hypothesis"],
            "confidence": raw.get("confidence", 0.5),
            "information_gap": raw.get("information_gap", 0.3),
            "closure_pressure": raw.get("closure_pressure", 0.3),
            "coherence_factor": raw.get("coherence_factor", 0.3),
        }
    if raw.get("content"):
        return {
            "type": "other",
            "statement": raw["content"],
            "confidence": raw.get("confidence", 0.5),
            "information_gap": raw.get("information_gap", 0.3),
            "closure_pressure": raw.get("closure_pressure", 0.3),
            "coherence_factor": raw.get("coherence_factor", 0.3),
        }
    return None


def _normalize_self_belief_proposal(raw: dict) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    if raw.get("belief_text"):
        return raw
    if raw.get("belief"):
        return {
            "belief_text": raw["belief"],
            "confidence": raw.get("confidence", 0.5),
            "information_gap": raw.get("information_gap", 0.3),
            "closure_pressure": raw.get("closure_pressure", 0.3),
            "coherence_factor": raw.get("coherence_factor", 0.3),
        }
    if raw.get("content"):
        return {
            "belief_text": raw["content"],
            "confidence": raw.get("confidence", 0.5),
            "information_gap": raw.get("information_gap", 0.3),
            "closure_pressure": raw.get("closure_pressure", 0.3),
            "coherence_factor": raw.get("coherence_factor", 0.3),
        }
    return None


def _map_to_monologue_schema(raw: dict) -> dict:
    mapped = {}
    if not isinstance(raw, dict):
        return mapped
    if isinstance(raw.get("hypothesis_proposal"), dict):
        norm = _normalize_hypothesis_proposal(raw["hypothesis_proposal"])
        if norm:
            mapped["hypothesis_proposal"] = norm
    if isinstance(raw.get("self_belief_proposal"), dict):
        norm = _normalize_self_belief_proposal(raw["self_belief_proposal"])
        if norm:
            mapped["self_belief_proposal"] = norm
    for key in [
        "thematic_continuity", "interruption_severity", "observations", "questions",
        "ambiguities", "internal_candidates",
        "thought_continuation_urge", "internal_momentum", "self_relevance",
        "social_salience", "trajectory_deviation", "trajectory_confidence",
        "curiosity_trigger", "triggered_memory_summary", "memory_significance",
        "memory_emotional_tone", "referenced_thread_id"
    ]:
        if key in raw:
            mapped[key] = raw[key]
    return mapped

from litellm import acompletion
from pydantic import ValidationError
from psyche.state import HariState
from models.monologue_output import MonologueOutput

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Monologue‑specific fallback chain (identical structure to dialogue)
# -----------------------------------------------------------------------------
# --- Fallback chain with preferred ordering and key validation ---
_FALLBACK_CANDIDATES = [
    ("groq/openai/gpt-oss-120b", os.getenv("GROQ_API_KEY")),
    ("groq/openai/gpt-oss-20b", os.getenv("GROQ_API_KEY")),
    ("groq/qwen/qwen3.6-27b", os.getenv("GROQ_API_KEY")),
    ("openrouter/meta-llama/llama-3.3-70b-instruct", os.getenv("OPENROUTER_API_KEY")),
    ("gemini/gemini-2.5-flash", os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
    (os.getenv("STAGE1_FALLBACK_3", "mistral/mistral-small-latest"), os.getenv("MISTRAL_API_KEY")),
]

# Build model list only for providers with API keys, logging skipped targets
MONOLOGUE_FALLBACK_MODELS = []
for model, key in _FALLBACK_CANDIDATES:
    if key and str(key).strip():
        MONOLOGUE_FALLBACK_MODELS.append(model)
    else:
        logger.warning(f"Skipping monologue fallback target '{model}': API key missing or empty.")

# Network timeout for LLM calls (seconds)
TIMEOUT = float(os.getenv("LITELLM_NETWORK_TIMEOUT", "8.0"))


def _extract_json_safely(raw_text: str) -> str:
    """
    Extract the first valid JSON object from a string using a proper parser.
    Falls back to the old greedy regex only as a last resort.
    """
    import json
    import re

    text = raw_text.strip()
    decoder = json.JSONDecoder()

    # Try to find the first '{' and parse from there.
    for start, char in enumerate(text):
        if char != "{":
            continue
        try:
            obj, end = decoder.raw_decode(text[start:])
            # Return the compact JSON string
            return json.dumps(obj, separators=(",", ":"))
        except json.JSONDecodeError:
            continue

    # Fallback: greedy regex (old method) – less reliable but catches some malformed cases
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)

    raise ValueError("No valid JSON object found in the response")


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
    internal_context: Optional[Dict[str, Any]] = None,
    identity_context: Optional[str] = None,
) -> str:
    prompt = f"""You are Hari. This is your private inner monologue.

YOUR CURRENT COGNITIVE STATE:
{state.to_prompt_context()}

Mood (VAD): valence={state.valence:.2f}, arousal={state.arousal:.2f}, dominance={state.dominance:.2f}

Prediction error (surprise): {prediction_error:.3f}

RECENT MEMORIES:
{_format_memories(recent_memories)}
"""

    if identity_context:
        prompt += f"""

HARI'S SELF-UNDERSTANDING (background context):
{identity_context}

This is not a script. Use it only if the current event activates, contradicts, or connects to something here.
"""

    if internal_context:
        prompt += "\nHARI'S EXISTING COGNITIVE FIELD (things already in mind):"
        if internal_context.get("self_beliefs"):
            beliefs = "\n".join(f"- {b['content']}" for b in internal_context["self_beliefs"][:3])
            prompt += f"\nBeliefs:\n{beliefs}"
        if internal_context.get("curiosity_nodes"):
            curiosities = "\n".join(f"- {c['content']}" for c in internal_context["curiosity_nodes"][:3])
            prompt += f"\nCuriosities:\n{curiosities}"
        if internal_context.get("active_threads"):
            threads = "\n".join(f"- {t['title']}: {t['description'][:100]}" for t in internal_context["active_threads"][:2])
            prompt += f"\nNarratives:\n{threads}"

    if active_thread_context:
        prompt += f"\nACTIVE NARRATIVE THREAD:\n{active_thread_context}"

    prompt += f"""

THE OTHER PARTICIPANT JUST SAID:
"{user_input}"

TASK:
Notice what, if anything, became cognitively active for Hari because of this event.

Only report cognition that is genuinely active now.

Do NOT:
- classify the participant's intent
- estimate participant engagement
- diagnose the participant
- decide what Hari should say
- generate a reply
- optimize for helpfulness
- generate thoughts merely to fill the schema.

INTERNAL CANDIDATES:
These are thoughts that may enter Hari's workspace.
They are not speech instructions.

An empty internal_candidates list is valid.

Return valid JSON matching the existing schema.
"""
    return prompt

def _default_sensory_output(
    prediction_error: float = 0.5,
    state: Optional[HariState] = None,
) -> MonologueOutput:
    internal_momentum = 0.0
    if state is not None:
        internal_momentum = max(
            getattr(state, "curiosity", 0.0),
            getattr(state, "completion", 0.0),
            getattr(state, "momentum", 0.0),
        )

    return MonologueOutput(
        thematic_continuity=max(0.0, 1.0 - prediction_error),
        interruption_severity=prediction_error,
        observations=[],
        questions=[],
        ambiguities=[],
        internal_candidates=[],
        curiosity_trigger=None,
        hypothesis_proposal=None,
        self_belief_proposal=None,
        triggered_memory_summary=None,
        memory_significance=0.5,
        memory_emotional_tone="neutral",
        trajectory_deviation=prediction_error,
        trajectory_confidence=0.2,
        referenced_thread_id=None,
        thought_continuation_urge=internal_momentum,
        internal_momentum=internal_momentum,
        self_relevance=0.0,
        social_salience=0.0,
    )


async def run_monologue(
    user_input: str,
    state: HariState,
    recent_memories: List,
    prediction_error: float = 0.0,
    active_thread_context: Optional[str] = None,
    internal_context: Optional[Dict[str, Any]] = None,
    identity_context: Optional[str] = None,
) -> MonologueOutput:
    """
    Sensory monologue extraction engine.
    Uses unified LiteLLM cascades to handle provider outages and rate limits safely.
    """
    prompt = _build_sensory_prompt(
        user_input,
        state,
        recent_memories,
        prediction_error,
        active_thread_context,
        internal_context,
        identity_context,
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are Hari's internal cognitive field. "
                "Report what becomes cognitively active. "
                "Do not solve the conversation. "
                "Do not optimize a response. "
                "Do not analyze the participant. "
                "Do not generate a reply. "
                "Return only the requested JSON."
            )
        },
        {"role": "user", "content": prompt}
    ]

    for model in MONOLOGUE_FALLBACK_MODELS:
        try:
            # Base parameters
            kwargs = {"model": model, "messages": messages, "temperature": 0.2, "timeout": TIMEOUT}
            if not model.startswith("openrouter"):
                kwargs["response_format"] = {"type": "json_object"}

            response = await acompletion(**kwargs)
            raw_payload = response.choices[0].message.content
            clean_json_str = _extract_json_safely(raw_payload)

            # Try to parse
            output = MonologueOutput.model_validate_json(clean_json_str)
            logger.info(f"Sensory Monologue successfully generated via platform model: {model}")
            return output

        except ValidationError:
            logger.warning(f"Validation error on {model}, attempting normalization...")
            try:
                data = json.loads(clean_json_str)
                mapped = _map_to_monologue_schema(data)
                output = MonologueOutput.model_validate(mapped)
                logger.info(f"MONOLOGUE_MAPPED: {model}")
                return output
            except Exception as norm_err:
                logger.warning(f"Normalization failed on {model}: {norm_err}")
                try:
                    retry_messages = messages + [
                        {"role": "system", "content": "Previous response violated the JSON schema. Regenerate using ONLY the allowed item_type values. Do not invent new values."}
                    ]
                    retry_kwargs = {"model": model, "messages": retry_messages, "temperature": 0.1, "timeout": TIMEOUT}
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
        except litellm.RateLimitError:
            await asyncio.sleep(2)
            continue
        except Exception as provider_err:
            logger.warning(f"Sensory pipeline stage 1 anomaly on model '{model}': {provider_err}")
            continue

    # Absolute fallback
    logger.critical("CRITICAL SUBSTRATE FAULT: All Monologue infrastructure providers exhausted. Issuing emergency defaults.")
    return _default_sensory_output(prediction_error, state)