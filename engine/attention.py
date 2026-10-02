"""
engine/attention.py — Cognitive Workspace & Attention System (Pressure‑Field Architecture)

Implements a Global Workspace Theory (GWT) selection–broadcast cycle using a
multi‑dimensional pressure field.

Each cognitive candidate (memory, hypothesis, curiosity, narrative, open thread)
is evaluated across four pressures:
  - Relevance Pressure   (semantic alignment with external event)
  - Novelty Pressure     (prediction error / surprise)
  - Curiosity Pressure   (knowledge gaps)
  - Completion Pressure  (momentum to finish ongoing thoughts)

The pressures are weighted by Hari’s current state (curiosity, completion,
dominance, etc.) and compete via a Softmax temperature‑controlled softmax
function. Temperature is driven by state.dominance (low T = stubborn /
focused; high T = fluid / creative).

Attentional inertia: winning items persist across turns with exponential decay.
"""

import asyncio
import json
import logging
import math
import os
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Literal
from concurrent.futures import ThreadPoolExecutor




from engine.memory import embed
from models.memory_event import MemoryEvent
from psyche.state import HariState
from engine.memory import increment_memory_usage
from datetime import datetime, timezone
from engine.attention_config import DEFAULT_ATTENTION_CONFIG, AttentionCalibration
from engine.attention_instrumentation import AttentionInstrumentation
from engine.generativity_estimator import get_estimator
from models.narrative import NarrativeThread

logger = logging.getLogger(__name__)


def _authority_weight(candidate: Dict[str, Any]) -> float:
    """Compute a structural provenance weight for a workspace candidate."""
    origin = str(candidate.get("origin") or "")
    source = str(candidate.get("source") or "")
    if origin.startswith("volition") or origin in ("internal_cognition", "curiosity_spreading"):
        return 1.0
    if source in ("volition", "volition_persistent", "internal_cognition", "curiosity_spreading"):
        return 1.0
    if origin in ("narrative", "self_belief", "perspective"):
        return 0.85
    if origin in ("memory", "hypothesis"):
        return 0.6
    return 0.4

_seeded_rng = None

def _rng():
    global _seeded_rng
    seed = os.getenv("EXPERIMENT_SEED", "").strip()
    if seed:
        if _seeded_rng is None:
            try:
                _seeded_rng = np.random.default_rng(int(seed))
            except ValueError:
                _seeded_rng = np.random.default_rng()
        return _seeded_rng
    return np.random.default_rng()

# -----------------------------------------------------------------------------
# Data Models – Container Pattern + Inertia Metrics
# -----------------------------------------------------------------------------

@dataclass
class ActivationMetrics:
    """Tracks workspace item persistence across turns."""
    activation: float = 1.0          # how strongly it's still active
    last_attended_turn: int = 0      # when it was last in workspace
    reentry_count: int = 0           # times it's re-entered workspace
    decay_rate: float = 0.15         # how fast activation decays


class WorkspaceItem:
    """Uniform envelope — different payloads, same container."""
    def __init__(
        self,
        id: str,
        item_type: Literal[
            "memory", "hypothesis", "curiosity_node", "narrative_thread",
            "open_thought", "minimal", "incoming_event",
        ],
        source: str,                   # where it came from (engine.memory, monologue, etc.)
        payload: Dict[str, Any],       # the actual content, unchanged
        attention_weight: float = 0.0,
        metrics: Optional[ActivationMetrics] = None
    ):
        self.id = id
        self.item_type = item_type
        self.source = source
        self.payload = payload
        self.attention_weight = attention_weight
        self.metrics = metrics or ActivationMetrics()

    # Convenience property for backward compatibility with generate.py
    @property
    def content(self) -> str:
        """Return the main text content from the payload."""
        return self.payload.get("content") or self.payload.get("statement") or str(self.payload)

    @property
    def activation(self) -> float:
        """Expose activation from metrics for easier access."""
        return self.metrics.activation

    @activation.setter
    def activation(self, value: float):
        self.metrics.activation = value

    @property
    def turn_loaded(self) -> int:
        """Last attended turn is stored in metrics."""
        return self.metrics.last_attended_turn

    @turn_loaded.setter
    def turn_loaded(self, value: int):
        self.metrics.last_attended_turn = value




# -----------------------------------------------------------------------------
# Pressure Field Computation
# -----------------------------------------------------------------------------
async def _compute_pressure_field(
    candidate: Dict[str, Any],
    state: HariState,
    event_embedding: Optional[np.ndarray],
    active_context_embedding: Optional[np.ndarray],
    prediction_error: float,
) -> Dict[str, float]:
    pressures: Dict[str, float] = {}

    if event_embedding is not None:
        event_affinity = 0.5
        candidate_embedding = candidate.get("embedding")
        if candidate_embedding is not None:
            try:
                candidate_emb = np.array(candidate_embedding, dtype=np.float32)
                event_norm = event_embedding / (np.linalg.norm(event_embedding) + 1e-8)
                cand_norm = candidate_emb / (np.linalg.norm(candidate_emb) + 1e-8)
                event_affinity = (float(np.dot(event_norm, cand_norm)) + 1) / 2
            except Exception:
                pass
        pressures["event_affinity"] = event_affinity

        novelty = 0.0
        if candidate_embedding is not None:
            try:
                cand_emb = np.array(candidate_embedding, dtype=np.float32)
                event_norm = event_embedding / (np.linalg.norm(event_embedding) + 1e-8)
                cand_norm = cand_emb / (np.linalg.norm(cand_emb) + 1e-8)
                similarity = float(np.dot(event_norm, cand_norm))
                similarity = max(0.0, min(1.0, similarity))
                novelty = prediction_error * (1.0 - similarity)
            except Exception:
                novelty = prediction_error * 0.25
        pressures["novelty"] = max(0.0, min(1.0, novelty))

    # endogenous_affinity — always present
    endogenous_affinity = 0.0
    if active_context_embedding is not None and candidate.get("embedding") is not None:
        try:
            candidate_emb = np.array(candidate["embedding"], dtype=np.float32)
            context_norm = active_context_embedding / (np.linalg.norm(active_context_embedding) + 1e-8)
            cand_norm = candidate_emb / (np.linalg.norm(candidate_emb) + 1e-8)
            endogenous_affinity = (float(np.dot(context_norm, cand_norm)) + 1) / 2
        except Exception:
            pass
    pressures["endogenous_affinity"] = endogenous_affinity

    # curiosity
    curiosity_boost = float(candidate.get("information_gap", 0.0))
    pressures["curiosity"] = min(1.0, state.curiosity * (1.0 + curiosity_boost))

    # completion
    completion_urgency = float(candidate.get("closure_pressure", 0.0))
    pressures["completion"] = min(1.0, state.completion * (1.0 + completion_urgency))

    # exploratory potential
    exploration_progress = float(candidate.get("exploration_progress", 0.0))
    novelty_for_exploratory = pressures.get("novelty", 0.0)
    exploratory_potential = (novelty_for_exploratory * 0.5) + (pressures["curiosity"] * 0.5)
    if candidate.get("item_type") == "curiosity_node":
        exploratory_potential *= (1.0 - exploration_progress)
    pressures["exploratory_potential"] = min(1.0, exploratory_potential)

    # shared significance
    try:
        from engine.shared_significance import compute_shared_significance
        pressures["shared_significance"] = min(1.0, compute_shared_significance(candidate, state))
    except ImportError:
        item_sig = float(candidate.get("significance", 0.5))
        pressures["shared_significance"] = min(1.0, item_sig * 0.5 + float(state.care) * 0.5)

    # coherence tension
    if candidate.get("item_type") in ("open_thought", "hypothesis"):
        pressures["coherence_tension"] = min(1.0, float(candidate.get("urgency", 0.0)))
    else:
        pressures["coherence_tension"] = 0.0

    # intrinsic relevance / persistence / internal activation
    intrinsic_relevance = float(candidate.get("intrinsic_relevance", 0.0))
    persistence = float(candidate.get("persistence", 0.0))
    internal_activation = float(candidate.get("internal_activation", 0.0))
    authority = _authority_weight(candidate)

    pressures["intrinsic_relevance"] = min(1.0, max(0.0, intrinsic_relevance))
    pressures["persistence"] = min(1.0, max(0.0, persistence))
    pressures["internal_activation"] = min(1.0, max(0.0, internal_activation))
    pressures["authority"] = authority

    # internal_standing as a small amplifier, not a compound of the above
    internal_standing = (
        max(intrinsic_relevance, persistence, internal_activation)
        * authority
    )
    pressures["internal_standing"] = min(1.0, max(0.0, internal_standing))

    return pressures


    # Legacy alias for engine/__init__.py (avoids refactoring downstream)
async def compute_salience(pressures: Dict[str, float], state: HariState) -> float:
    """Deprecated: use compute_total_salience directly."""
    return await compute_total_salience(pressures, state)

# -----------------------------------------------------------------------------
# Salience Calculation (Tickets 010, 011, 012)
# -----------------------------------------------------------------------------

async def compute_total_salience(
    pressures: Dict[str, Any],
    state: HariState,
    config: AttentionCalibration = DEFAULT_ATTENTION_CONFIG,
    instrumentation: Optional[AttentionInstrumentation] = None,
    candidate_id: Optional[str] = None,
    candidate_type: Optional[str] = None,
    turn_number: Optional[int] = None,
    previous_engagement: Optional[float] = None,
) -> float:
    """
    Blends cognitive pressures with core state drives.
    Guarantees a clean, scalar float output between 0.0 and 1.0.
    
    Now uses configurable weights from AttentionCalibration.
    All new parameters have defaults, preserving backward compatibility.
    """
    # Get normalized weights from config
    weights = config.get_weights(state, previous_engagement)
    
    weighted_sum = 0.0
    total_weight = sum(weights.values())
    
    # Track contributions for instrumentation
    contributions = {}
    
    for name, raw_pressure in pressures.items():
        w = weights.get(name, 0.0)
        if w == 0.0:
            continue
        
        # Safely convert the pressure to a float scalar
        try:
            if isinstance(raw_pressure, np.ndarray):
                p = float(raw_pressure.item())
            else:
                p = float(raw_pressure)
        except (TypeError, ValueError) as cast_err:
            logger.error(f"Failed to convert pressure '{name}' value {raw_pressure} to float: {cast_err}")
            continue
        
        contribution = p * w
        weighted_sum += contribution
        contributions[name] = contribution
    
    # Calculate normalized score
    if total_weight > 0.0:
        salience = weighted_sum / total_weight
    else:
        salience = 0.5
    
    # Clamp
    salience = max(0.0, min(1.0, salience))
    
    # Log pressure contributions for calibration (if instrumentation provided)
    if instrumentation and candidate_id and turn_number is not None:
        instrumentation.record_pressure(
            turn_number=turn_number,
            candidate_id=candidate_id,
            candidate_type=candidate_type or "unknown",
            pressures=pressures,
            weights=weights,
            raw_score=weighted_sum,      # Proper raw score
            final_score=salience,
            was_selected=False  # Will be updated after selection
        )
    
    if isinstance(salience, np.ndarray):
        salience = float(salience.item())
    
    return max(0.0, min(1.0, salience))
# -----------------------------------------------------------------------------
# Softmax Competition (State‑Driven Temperature)
# -----------------------------------------------------------------------------

# In engine/attention.py, replace the existing _softmax_with_temperature with:

def _softmax(scores: List[float], temperature: float) -> List[float]:
    """Temperature-controlled softmax. Temperature <= 0 gives deterministic."""
    if temperature <= 0:
        max_idx = max(range(len(scores)), key=lambda i: scores[i])
        return [1.0 if i == max_idx else 0.0 for i in range(len(scores))]
    scaled = np.array(scores) / temperature
    exp_vals = np.exp(scaled - np.max(scaled))
    return (exp_vals / np.sum(exp_vals)).tolist()


def broadcast_feedback(elected: List[WorkspaceItem], state: HariState) -> Dict[str, float]:
    """Return workspace composition telemetry without modifying state."""
    if not elected:
        return {"curiosity_ratio": 0.0, "narrative_ratio": 0.0, "internal_ratio": 0.0, "n": 0}
    n = len(elected)
    return {
        "curiosity_ratio": sum(1 for item in elected if item.item_type == "curiosity_node") / n,
        "narrative_ratio": sum(1 for item in elected if item.item_type == "narrative_thread") / n,
        "internal_ratio": sum(1 for item in elected if item.payload.get("source") == "internal_cognition") / n,
        "n": n,
    }


# -----------------------------------------------------------------------------
# Main Workspace Loading (with Attentional Inertia)
# -----------------------------------------------------------------------------

async def load_workspace(
    memories: List[MemoryEvent],
    hypotheses: List[Dict[str, Any]],
    curiosity_nodes: List[Dict[str, Any]],
    narrative_threads: List[NarrativeThread],
    open_threads: List[Dict[str, Any]],
    state: HariState,
    external_event: str,
    prediction_error: float,
    current_turn: int,
    workspace_size: int = 5,
    previous_workspace_items: Optional[List[WorkspaceItem]] = None,
    thought_persistence_urge: float = 0.0,
    instrumentation: Optional[AttentionInstrumentation] = None,   # NEW
    active_thought_texts: Optional[List[str]] = None,
    refractory: Optional[Any] = None,
) -> Tuple[List[WorkspaceItem], Dict[str, Any]]:
    """
    Loads the cognitive workspace using pressure fields + softmax competition.

    Args:
        previous_workspace_items: Items from previous turn (for inertia).

    Returns:
        workspace_items: Top items selected for this turn (as WorkspaceItem objects).
        telemetry: Detailed log of pressures, scores, and selection probabilities.
    """
    # 1. Compute event and active-context embeddings once per turn.
    external_event_embedding = None
    if external_event:
        try:
            external_event_embedding = np.array(await embed(external_event), dtype=np.float32)
        except Exception as e:
            logger.warning(f"Failed to compute event embedding: {e}")

    active_context_embedding = None
    if active_thought_texts:
        try:
            embeddings = [
                await embed(text)
                for text in active_thought_texts[:5]
                if text and text.strip()
            ]
            if embeddings:
                active_context_embedding = np.mean(
                    np.array(embeddings, dtype=np.float32), axis=0
                )
        except Exception as e:
            logger.debug(f"Failed to compute active context embedding: {e}")

    # 2. Build candidate pool (new items + inertia items)
    candidates = []  # each: (salience, item_type, original_dict, pressures)

    # Helper to add a candidate from any source
    def add_candidate(item_type: str, source_id: str, payload: Dict[str, Any]):
        nonlocal candidates
        pressures = None  # will compute later to avoid repeated calls
        candidates.append((0.0, item_type, source_id, payload, pressures))

    # Add memories
    for mem in memories:
        significance = getattr(mem, "significance", 0.5)
        
        # Base payload
        payload = {
            "content": mem.content,
            "embedding": getattr(mem, "embedding", None),
            "significance": significance,
            "id": mem.id,
            # Ecology Signals
            "information_gap": 0.0,
            "closure_pressure": 0.0,
            "coherence_factor": 0.1 * significance,
            "valence_delta": 0.0 # Ensure valence is present
        }
        
        # Hook logic: If memory is highly significant and not explicitly requested, only inject the hook
        if significance > 0.7 and not getattr(mem, 'explicitly_requested', False):
            hook_text = f"I remember a story about {getattr(mem, 'meaning_summary', 'something relevant')[:50]}..."
            payload["is_hook"] = True
            payload["hook_memory_id"] = mem.id
            payload["content"] = hook_text
        
        add_candidate("memory", mem.id, payload)
    # Add hypotheses
    for hyp in hypotheses:
        extracted_text = (hyp.get("content") or hyp.get("statement") or "").strip()
        if not extracted_text:
            continue
        confidence = float(hyp.get("confidence") or hyp.get("urgency") or 0.5)
        add_candidate("hypothesis", hyp.get("id", "unknown"), {
            "content": extracted_text,
            "urgency": confidence,
            "id": hyp.get("id"),
            # Ecology Signals (Ticket 013)
            "information_gap": 0.2 * confidence,  # V1: Hypotheses resolve uncertainty
            "closure_pressure": 0.3 * confidence,  # V1: Hypotheses need validation
            "coherence_factor": 0.3 * confidence,  # V1: Confidence affects coherence
        })
    # Add curiosity nodes
    for node in curiosity_nodes:
        importance = float(node.get("importance", 0.5))
        add_candidate("curiosity_node", node.get("id", "unknown"), {
            "content": node.get("question", ""),
            "embedding": node.get("embedding"),
            "importance": importance,
            "exploration_progress": node.get("exploration_progress", 0.0),
            "id": node.get("id"),
            # Ecology Signals (Ticket 013)
            "information_gap": importance,  # V1: Curiosity = information gap
            "closure_pressure": 0.1 * importance,  # V1: Curiosity has low closure pressure
            "coherence_factor": 0.2 * importance,  # V1: Curiosity challenges coherence
        })
    # Add narrative threads
    for thread in narrative_threads:
        # V1 Proxy: Unfinished threads demand closure
        closure_urgency = (1.0 - thread.completion_estimate) * thread.emotional_investment
        add_candidate("narrative_thread", thread.id, {
            "content": thread.description,
            "completion_estimate": thread.completion_estimate,
            "activation": thread.emotional_investment,
            "id": thread.id,
            # Ecology Signals (Ticket 013)
            "information_gap": 0.1,  # V1: Narratives create some uncertainty
            "closure_pressure": closure_urgency,  # V1: Unfinished threads demand closure
            "coherence_factor": 0.1,  # V1: Narratives support coherence
        })
    # Add open threads
    for ot in open_threads:
        urgency = float(ot.get("urgency", 0.5))
        item_type = ot.get("item_type", "open_thought")
        coherence_factor = urgency * 0.6

        payload = {
            "content": ot.get("content", ""),
            "urgency": urgency,
            "id": ot.get("id"),
            "information_gap": float(ot.get("information_gap", 0.1)),
            "closure_pressure": float(ot.get("closure_pressure", urgency)),
            "coherence_factor": float(ot.get("coherence_factor", coherence_factor)),
        }

        # PRESERVE INTERNAL METADATA
        for key in [
            "source", "internal_source", "internal_activation", "intrinsic_relevance",
            "persistence", "activation_reason", "origin", "activated_by"
        ]:
            if key in ot:
                payload[key] = ot[key]

        add_candidate(item_type, ot.get("id", "unknown"), payload)
    

    # 3. Add previous workspace items with decayed activation (attentional inertia)
    if previous_workspace_items:
        for old_item in previous_workspace_items:
            base_decay = 1.0 - (float(state.rest) * 0.4)
            tension_retention = float(state.cognitive_tension) * 0.5
            decay_multiplier = min(1.0, base_decay + tension_retention)
            old_item.metrics.activation *= decay_multiplier
            if old_item.metrics.activation < 0.05:
                continue
            # Convert back to candidate dict and preserve internal metadata for inertia
            cand_dict = {
                "item_type": old_item.item_type,
                "content": old_item.content,
                "embedding": old_item.payload.get("embedding"),
                "urgency": old_item.payload.get("urgency", 0.5),
                "id": old_item.id,
                # Preserve internal metadata
                "source": old_item.payload.get("source"),
                "internal_source": old_item.payload.get("internal_source"),
                "internal_activation": float(old_item.payload.get("internal_activation", 0.0)),
                "intrinsic_relevance": float(old_item.payload.get("intrinsic_relevance", 0.0)),
                "persistence": float(old_item.payload.get("persistence", 0.0)),
                "activation_reason": old_item.payload.get("activation_reason"),
                "origin": old_item.payload.get("origin"),
                "activated_by": old_item.payload.get("activated_by"),
                "information_gap": float(old_item.payload.get("information_gap", 0.0)),
                "closure_pressure": float(old_item.payload.get("closure_pressure", 0.0)),
                "coherence_factor": float(old_item.payload.get("coherence_factor", 0.0)),
            }
            add_candidate(old_item.item_type, old_item.id, cand_dict)

    if not candidates:
        return [], {"no_candidates": True}

    # Compute pressures and total salience for each candidate
    enriched_candidates = []
    for _, item_type, source_id, payload, _ in candidates:
        pressures = await _compute_pressure_field(
            payload,
            state,
            external_event_embedding,
            active_context_embedding,
            prediction_error,
        )

        # === Observational: Log generativity estimates (Ticket 011) ===
        # This does NOT influence cognition. It only logs estimates for validation.
        try:
            estimator = get_estimator()
            gen_est = await estimator.estimate(payload, state, {"turn": current_turn})
            estimator.log_estimate(source_id, gen_est)
        except Exception as e:
            logger.debug(f"Generativity logging failed: {e}")
        
        # Inertia boost
        if previous_workspace_items:
            for old in previous_workspace_items:
                if old.source == source_id:
                    pressures["event_affinity"] = (
                        pressures.get("event_affinity", 0.5) + old.metrics.activation
                    ) / 2
                    break
        
        # Base salience from pressures (NOW with instrumentation and all parameters)
        total_salience = await compute_total_salience(
            pressures, 
            state,
            config=DEFAULT_ATTENTION_CONFIG,
            instrumentation=instrumentation,
            candidate_id=source_id,
            candidate_type=item_type,
            turn_number=current_turn,
            previous_engagement=state.engagement
        )

        # Repetition Suppression Field
        if hasattr(state, '_last_assistant_response') and state._last_assistant_response:
            resp_words = set(state._last_assistant_response.lower().split())
            cand_words = set(payload.get("content", "").lower().split())
            overlap = len(resp_words.intersection(cand_words)) / max(len(resp_words), 1)
            if overlap > 0.4:          # >40% word overlap with last response
                total_salience *= 0.2   # 80% penalty

        if refractory is not None:
            penalty = refractory.apply_penalty(
                candidate_id=source_id,
                candidate_embedding=payload.get("embedding"),
                current_turn=current_turn,
            )
            pressures["refractory_penalty"] = penalty
            if os.getenv("ENABLE_SEMANTIC_REFRACTORY", "false").lower() == "true" and penalty < 1.0:
                total_salience *= penalty
        
        # Memory fatigue and explanatory power
        usage_count = payload.get("usage_count", 0)
        explanatory_power = payload.get("explanatory_power", 0.5)
        fatigue_penalty = min(0.3, usage_count * 0.02)
        
        # Store fatigue_penalty in pressures so telemetry can see it
        pressures["fatigue_penalty"] = fatigue_penalty
        
        # Remove the global surprise bonus – only candidate-specific novelty remains.
        total_salience = total_salience - fatigue_penalty
        total_salience = max(0.0, total_salience)
        
        # Boost for open_thought
        if item_type == "open_thought" and thought_persistence_urge > 0:
            total_salience *= (1 + thought_persistence_urge)
        
        enriched_candidates.append((total_salience, item_type, source_id, payload, pressures))


    # ------------------------------------------------------------------
    # 5. Determine the cognitive winner.
    #
    # The workspace is not just a random bag of salient items.
    # One candidate becomes the current focus; additional candidates
    # become supporting context.
    # ------------------------------------------------------------------

    # Determine softmax temperature and probabilities for telemetry.
    scores_all = [enriched_candidates[i][0] for i in range(len(enriched_candidates))]
    # Temperature driven by dominance (low dominance -> higher temp) and coherence
    temperature = max(
        0.05,
        min(
            1.0,
            0.4 + (1.0 - getattr(state, "dominance", 0.5)) * 0.3 + (1.0 - getattr(state, "coherence", 0.5)) * 0.3,
        ),
    )
    try:
        probabilities = _softmax(scores_all, temperature)
    except Exception:
        probabilities = [1.0 / len(scores_all)] * len(scores_all)

    # Rank all candidates by salience descending.
    ranked_indices = sorted(
        range(len(enriched_candidates)),
        key=lambda i: enriched_candidates[i][0],
        reverse=True,
    )

    # The top candidate is the cognitive winner.
    winner_index = ranked_indices[0]

    # The remaining candidates are eligible for supporting slots.
    remaining_indices = ranked_indices[1:]

    # How many supporting items do we need?
    num_supporting = min(
        max(0, workspace_size - 1),   # workspace_size is the total number of slots
        len(remaining_indices),
    )

    if num_supporting > 0:
        # Extract salience scores of the remaining candidates.
        support_scores = np.array(
            [enriched_candidates[i][0] for i in remaining_indices],
            dtype=np.float64,
        )

        # Temperature for supporting selection – lower than main softmax
        # to make it more focused, but still stochastic.
        # Derive from coherence: high coherence => more focused (lower temp),
        # low coherence => more exploratory (higher temp).
        support_temperature = max(
            0.15,
            min(
                0.6,
                0.5 - (state.coherence * 0.3)
            )
        )

        support_probabilities = _softmax(
            support_scores.tolist(),
            support_temperature,
        )

        supporting_indices = np.random.choice(
            remaining_indices,
            size=num_supporting,
            replace=False,
            p=support_probabilities,
        ).tolist()
    else:
        supporting_indices = []

    # Combine winner and supporters.
    selected_indices = [winner_index] + supporting_indices

    # Build the final list of candidates in the order: winner then supporters.
    selected_candidates = [
        enriched_candidates[i]
        for i in selected_indices
    ]

    # 6. Build WorkspaceItem objects with attention weights (normalised salience)
    workspace_items = []
    total_salience_selected = sum(c[0] for c in selected_candidates) or 1.0
    for salience, item_type, source_id, payload, pressures in selected_candidates:
        attention_weight = salience / total_salience_selected
        ws_id = f"{item_type}_{source_id}_{current_turn}"
        item = WorkspaceItem(
            id=ws_id,
            item_type=item_type,
            source=source_id,
            payload=payload,
            attention_weight=attention_weight,
            metrics=ActivationMetrics(activation=1.0, last_attended_turn=current_turn, reentry_count=0, decay_rate=0.15)
        )
        item.payload["_pressure_scores"] = pressures
        item.payload["_total_salience"] = salience
        workspace_items.append(item)

    # 7. Build telemetry for debugging
    telemetry = {
        "temperature": temperature,
        "candidate_scores": [
            {
                "type": c[1],
                "source_id": c[2],
                "salience": c[0],
                "relevance": c[4].get("relevance", 0),
                "novelty": c[4].get("novelty", 0),
                "curiosity": c[4].get("curiosity", 0),
                "completion": c[4].get("completion", 0),
                "fatigue_penalty": c[4].get("fatigue_penalty", 0),
            }
            for c in enriched_candidates
        ],
        "probabilities": probabilities.tolist() if isinstance(probabilities, np.ndarray) else probabilities,
        "selected_indices": selected_indices,
    }

    # --- Increment usage count for selected memory items (memory fatigue) ---
    memory_ids = [item.payload.get("id") for item in workspace_items if item.item_type == "memory"]
    if memory_ids:
        await increment_memory_usage(memory_ids, current_turn)

    # --- Mark selections in instrumentation (NEW) ---
    if instrumentation:
        selected_ids = [item.source for item in workspace_items]
        instrumentation.mark_selected(selected_ids)

    return workspace_items, telemetry


# -----------------------------------------------------------------------------
# Helper to offload CPU‑bound ops to a thread pool
# -----------------------------------------------------------------------------

_executor = ThreadPoolExecutor(max_workers=2)

async def _run_in_executor(func, *args):
    """Run a CPU‑heavy function in a thread pool to avoid blocking the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, func, *args)



def apply_workspace_diversity_penalty(
    candidates: List[MemoryEvent],
    target_count: int = 15,
    similarity_decay_factor: float = 0.4
) -> List[MemoryEvent]:
    """
    Iteratively selects candidates using a diversity penalty filter.
    Guarantees the workspace contains a balanced mixture of thematic context.
    """
    if not candidates:
        return []

    selected_items: List[MemoryEvent] = []
    remaining_pool = list(candidates)
    observed_tags: Dict[str, int] = {}

    while len(selected_items) < target_count and remaining_pool:
        for item in remaining_pool:
            penalty = 0.0
            for tag in item.thematic_tags or []:
                if tag in observed_tags:
                    penalty += observed_tags[tag] * similarity_decay_factor
            item.computed_score -= penalty

        remaining_pool.sort(key=lambda x: x.computed_score, reverse=True)
        winner = remaining_pool.pop(0)
        selected_items.append(winner)

        for tag in winner.thematic_tags or []:
            observed_tags[tag] = observed_tags.get(tag, 0) + 1

    return selected_items


async def load_workspace_secured(
    external_event: str,
    session_id: str,
    current_turn: int,
    state: HariState,
    previous_workspace_items: Optional[List[WorkspaceItem]] = None,
    limit: int = 35
) -> List[MemoryEvent]:
    """
    Ensures cognition never collapses to zero by falling back through a structured chain.
    """
    from engine.memory import retrieve_candidates_hybrid

    state_drives = {
        "curiosity": state.curiosity,
        "completion": state.completion,
        "coherence": state.coherence,
        "care": state.care
    }

    # Layer 1: Primary hybrid retrieval
    candidates = await retrieve_candidates_hybrid(
        query=external_event,
        session_id=session_id,
        current_turn=current_turn,
        state_drives=state_drives,
        limit=limit
    )

    # Layer 2: Fallback if candidates < 5
    if len(candidates) < 5:
        logger.warning(f"Turn {current_turn}: Primary retrieval returned {len(candidates)} candidates. Triggering fallback.")
        from db.connection import get_pool
        pool = await get_pool()
        if pool:
            async with pool.acquire() as conn:
                fallback_rows = await conn.fetch("""
                    SELECT id, session_id, turn_number, role, content, event_type,
                           thematic_tags, significance, meaning_summary,
                           usage_count, last_retrieved_turn, explanatory_power, created_at
                    FROM memories
                    WHERE session_id = $1
                    ORDER BY turn_number DESC
                    LIMIT 15
                """, session_id)

                for row in fallback_rows:
                    if not any(c.id == row["id"] for c in candidates):
                        mem = MemoryEvent(
                            id=row["id"],
                            session_id=row["session_id"],
                            turn_number=row["turn_number"],
                            role=row["role"],
                            content=row["content"],
                            event_type=row["event_type"],
                            thematic_tags=row["thematic_tags"] or [],
                            significance=row["significance"],
                            meaning_summary=row["meaning_summary"],
                            created_at=row["created_at"],
                            usage_count=row["usage_count"],
                            last_retrieved_turn=row["last_retrieved_turn"],
                            explanatory_power=row["explanatory_power"]
                        )
                        mem.computed_score = 0.5
                        candidates.append(mem)

    # Apply diversity penalty
    diversified = apply_workspace_diversity_penalty(candidates, target_count=15)
    return diversified

async def settle_workspace(
    *,
    session_id: str,
    memories: List[MemoryEvent],
    hypotheses: List[Dict[str, Any]],
    curiosity_nodes: List[Dict[str, Any]],
    narrative_threads: List[NarrativeThread],
    open_threads: List[Dict[str, Any]],
    state: HariState,
    external_event: str,
    prediction_error: float,
    current_turn: int,
    graph_manager,
    workspace_size: int = 5,
    previous_workspace_items: Optional[List[WorkspaceItem]] = None,
    thought_persistence_urge: float = 0.0,
    instrumentation: Optional[AttentionInstrumentation] = None,
    active_thought_texts: Optional[List[str]] = None,
    refractory: Optional[Any] = None,
    attention_config: Optional[AttentionCalibration] = None,
    max_rounds: int = 3,
) -> Tuple[List[WorkspaceItem], Dict[str, Any]]:
    """Bounded recurrent settling. Winner of each round seeds next round."""

    all_candidates = list(open_threads or [])
    winner_history: List[str] = []
    final_winner: Optional[WorkspaceItem] = None
    final_supporters: List[WorkspaceItem] = []
    round_count = 0

    for round_idx in range(max_rounds):
        round_count = round_idx + 1

        workspace_items, telemetry = await load_workspace(
            memories=memories,
            hypotheses=hypotheses,
            curiosity_nodes=curiosity_nodes,
            narrative_threads=narrative_threads,
            open_threads=all_candidates,
            state=state,
            external_event=external_event,
            prediction_error=prediction_error,
            current_turn=current_turn + round_idx,
            workspace_size=workspace_size,
            previous_workspace_items=previous_workspace_items if round_idx == 0 else None,
            thought_persistence_urge=thought_persistence_urge,
            instrumentation=instrumentation,
            active_thought_texts=active_thought_texts,
            refractory=refractory,
            attention_config=attention_config,
        )

        if not workspace_items:
            break

        winner = workspace_items[0]
        winner_content = winner.content
        winner_history.append(winner_content)

        # Convergence: same winner two rounds in a row
        if len(winner_history) >= 2 and winner_history[-1] == winner_history[-2]:
            final_winner = winner
            final_supporters = workspace_items[1:]
            break

        final_winner = winner
        final_supporters = workspace_items[1:]

        # Last round: don't need to seed
        if round_idx == max_rounds - 1:
            break

        # Seed spreading activation from winner
        if graph_manager is not None:
            try:
                graph_manager.seed_from_text(winner_content, weight=1.0)
                new_activated = graph_manager.step_activation()
                for node in new_activated:
                    all_candidates.append({
                        "id": f"spread_{node['id']}_r{round_idx}",
                        "content": node["question"],
                        "urgency": float(node["activation"]),
                        "item_type": "curiosity_node",
                        "source": "curiosity_spreading",
                        "internal_source": "spread_activation",
                        "internal_activation": float(node["activation"]),
                        "intrinsic_relevance": float(node["activation"]) * 1.2,
                        "persistence": 0.7 if node.get("is_primed") else 0.4,
                        "origin": "curiosity_spreading",
                        "activated_by": f"winner_round_{round_idx}",
                        "information_gap": float(node["activation"]),
                        "closure_pressure": 0.15 * float(node["activation"]),
                        "coherence_factor": 0.25 * float(node["activation"]),
                    })
            except Exception as e:
                logger.debug("Spread activation failed: %s", e)

        # Also retrieve memories similar to winner
        try:
            from engine.memory import embed, retrieve_candidates_hybrid
            winner_emb = await embed(winner_content)
            spread_memories = await retrieve_candidates_hybrid(
                query=winner_content,
                session_id=session_id,
                current_turn=current_turn + round_idx,
                state_drives={"curiosity": state.curiosity,
                              "completion": state.completion,
                              "coherence": state.coherence,
                              "care": state.care},
                limit=5,
            )
            memories = list(memories) + [m for m in spread_memories
                                          if m.id not in {mm.id for mm in memories}]
        except Exception as e:
            logger.debug("Spread memory retrieval failed: %s", e)

    if final_winner is None and winner_history:
        # fallback: use last winner
        pass

    return [final_winner] + final_supporters if final_winner else [], {
        "rounds": round_count,
        "winner_history": winner_history,
    }
