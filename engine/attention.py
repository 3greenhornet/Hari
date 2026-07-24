"""
engine/attention.py — Cognitive Workspace & Attention System (Pressure‑Field Architecture)

Implements a Global Workspace Theory (GWT) selection–broadcast cycle using a
multi‑dimensional pressure field.

Each cognitive candidate (memory, hypothesis, curiosity, narrative, open thread)
is evaluated across four pressures:
  - Relevance Pressure   (semantic alignment with user input)
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
import logging
import math
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Literal
from concurrent.futures import ThreadPoolExecutor




from engine.memory import embed
from models.memory_event import MemoryEvent
from psyche.state import HariState
from engine.memory import increment_memory_usage
from datetime import datetime
from engine.attention_config import DEFAULT_ATTENTION_CONFIG, AttentionCalibration
from engine.attention_instrumentation import AttentionInstrumentation
from engine.generativity_estimator import get_estimator
from models.narrative import NarrativeThread

logger = logging.getLogger(__name__)

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
        item_type: Literal["memory", "hypothesis", "curiosity_node", "narrative_thread", "open_thought","minimal"],
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
    user_embedding: Optional[np.ndarray],
    prediction_error: float,
) -> Dict[str, float]:
    """
    Returns a vector of pressure values for a single candidate.
    """
    pressures = {}

    # 1. Relevance Pressure: cosine similarity with user input
    relevance = 0.5   # default neutral
    candidate_embedding = candidate.get("embedding")
    if user_embedding is not None and candidate_embedding is not None:
        try:
            candidate_emb = np.array(candidate_embedding, dtype=np.float32)
            user_norm = user_embedding / (np.linalg.norm(user_embedding) + 1e-8)
            cand_norm = candidate_emb / (np.linalg.norm(candidate_emb) + 1e-8)
            cos_sim = np.dot(user_norm, cand_norm)
            relevance = (cos_sim + 1) / 2
        except Exception as e:
            logger.warning(f"Relevance pressure failed: {e}")
    pressures["relevance"] = relevance

    # 2. Novelty Pressure: driven by prediction error
    novelty = min(1.0, max(0.0, prediction_error))
    pressures["novelty"] = novelty

    # 3. Curiosity Pressure (Ecology Signals Contract: no item-type logic)
    curiosity_boost = float(candidate.get("information_gap", 0.0))
    curiosity_pressure = min(1.0, state.curiosity * (1.0 + curiosity_boost))
    pressures["curiosity"] = curiosity_pressure

    # 4. Completion Pressure (Ecology Signals Contract: no item-type logic)
    completion_urgency = float(candidate.get("closure_pressure", 0.0))
    completion_pressure = min(1.0, state.completion * (1.0 + completion_urgency))
    pressures["completion"] = completion_pressure

    # 5. Exploratory Potential (Ticket 011)
    exploration_progress = float(candidate.get("exploration_progress", 0.0))
    exploratory_potential = (novelty * 0.5) + (curiosity_pressure * 0.5)
    if candidate.get("item_type") == "curiosity_node":
        exploratory_potential *= (1.0 - exploration_progress)
    pressures["exploratory_potential"] = min(1.0, exploratory_potential)

    # 6. Shared Significance (Ticket 012)
    # Uses the shared_significance module (or you can inline as fallback)
    try:
        from engine.shared_significance import compute_shared_significance
        shared_significance = compute_shared_significance(candidate, state)
    except ImportError:
        # Fallback inline computation if module missing
        item_significance = float(candidate.get("significance", 0.5))
        shared_significance = (item_significance * 0.5) + (float(state.care) * 0.5)
    pressures["shared_significance"] = min(1.0, shared_significance)

    # === Interruption / Coherence Tension Pressure ===
    # If this candidate is an open_thought (e.g., "trajectory deviation detected"),
    # its urgency becomes a pressure field that can override factual relevance.
    if candidate.get("item_type") == "open_thought":
        coherence_tension = float(candidate.get("urgency", 0.0))
        pressures["coherence_tension"] = min(1.0, coherence_tension)
        # When the deviation is severe, boost relevance so this thought can win
        if coherence_tension > 0.5:
            pressures["relevance"] = max(pressures["relevance"], coherence_tension)
    else:
        pressures["coherence_tension"] = 0.0

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


def broadcast_feedback(elected: List[WorkspaceItem], state: HariState) -> None:
    """
    Ticket 013: Strengthened feedback using asymptotic updates.
    
    Ecology Signals Contract:
    - information_gap: How much uncertainty this candidate resolves
    - closure_pressure: How urgently this candidate needs resolution
    - coherence_factor: How well this candidate integrates with current cognition
    
    All signals are optional. Missing signals default to 0.0.
    Coefficients are calibrated and documented in ATTENTION_COEFFICIENTS.md.
    """
    if not elected:
        return
    n = len(elected)

    # Aggregate ecology signals from payloads (optional, default 0.0)
    curiosity_signal = sum(item.payload.get("information_gap", 0.0) for item in elected) / n
    completion_signal = sum(item.payload.get("closure_pressure", 0.0) for item in elected) / n
    coherence_signal = sum(item.payload.get("coherence_factor", 0.0) for item in elected) / n
    
    diversity_signal = len({item.item_type for item in elected}) / max(n, 1)

    # V1 Coefficients (Ticket 013 calibration)
    # curiosity: 0.15  | completion: 0.15  | coherence: 0.10  | arousal: 0.05
    state.update({
        "curiosity": curiosity_signal * 0.15,
        "completion": completion_signal * 0.15,
        "coherence": coherence_signal * 0.10,
        "arousal": diversity_signal * 0.05,
    }, source="BROADCAST", reason="workspace_feedback")

    # Debug validation (only in development)
    if __debug__:
        for item in elected:
            has_signal = any(
                key in item.payload 
                for key in ["information_gap", "closure_pressure", "coherence_factor"]
            )
            if not has_signal:
                logger.debug(
                    f"Candidate {item.id} ({item.item_type}) has no ecology signals. "
                    f"This contributes 0.0 to broadcast_feedback."
                )


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
    user_input: str,
    prediction_error: float,
    current_turn: int,
    workspace_size: int = 5,
    previous_workspace_items: Optional[List[WorkspaceItem]] = None,
    thought_persistence_urge: float = 0.0,
    instrumentation: Optional[AttentionInstrumentation] = None,   # NEW
) -> Tuple[List[WorkspaceItem], Dict[str, Any]]:
    """
    Loads the cognitive workspace using pressure fields + softmax competition.

    Args:
        previous_workspace_items: Items from previous turn (for inertia).

    Returns:
        workspace_items: Top items selected for this turn (as WorkspaceItem objects).
        telemetry: Detailed log of pressures, scores, and selection probabilities.
    """
    # 1. Compute user embedding once for the whole turn
    user_embedding = None
    if user_input:
        try:
            user_embedding = await embed(user_input)
            user_embedding = np.array(user_embedding, dtype=np.float32)
        except Exception as e:
            logger.warning(f"Failed to compute user embedding: {e}")

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
        urgency = ot.get("urgency", 0.5)
        add_candidate("open_thought", ot.get("id", "unknown"), {
            "content": ot.get("content", ""),
            "urgency": urgency,
            "id": ot.get("id"),
            # Ecology Signals (Ticket 013)
            "information_gap": 0.1,  # V1: Open thoughts create some uncertainty
            "closure_pressure": urgency,  # V1: Urgency = closure pressure
            "coherence_factor": 0.1 * urgency,  # V1: Urgency affects coherence
        })

    # 3. Add previous workspace items with decayed activation (attentional inertia)
    if previous_workspace_items:
        for old_item in previous_workspace_items:
            # Decay activation by 0.85 per turn (exponential)
            old_item.metrics.activation *= 0.85
            if old_item.metrics.activation < 0.05:
                continue
            # Convert back to candidate dict
            cand_dict = {
                "item_type": old_item.item_type,
                "content": old_item.content,
                "embedding": old_item.payload.get("embedding"),
                "urgency": old_item.payload.get("urgency", 0.5),
                "id": old_item.id,
            }
            add_candidate(old_item.item_type, old_item.id, cand_dict)

    if not candidates:
        return [], {"no_candidates": True}

    # Compute pressures and total salience for each candidate
    enriched_candidates = []
    for _, item_type, source_id, payload, _ in candidates:
        pressures = await _compute_pressure_field(payload, state, user_embedding, prediction_error)

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
                if old.id == source_id:
                    pressures["relevance"] = (pressures["relevance"] + old.metrics.activation) / 2
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
        
        # Memory fatigue and explanatory power
        usage_count = payload.get("usage_count", 0)
        explanatory_power = payload.get("explanatory_power", 0.5)
        surprise_contribution = prediction_error * explanatory_power
        fatigue_penalty = min(0.3, usage_count * 0.02)
        
        # Store fatigue_penalty in pressures so telemetry can see it
        pressures["fatigue_penalty"] = fatigue_penalty
        
        # Final salience
        total_salience = total_salience + surprise_contribution - fatigue_penalty
        total_salience = max(0.0, total_salience)
        
        # Boost for open_thought
        if item_type == "open_thought" and thought_persistence_urge > 0:
            total_salience *= (1 + thought_persistence_urge)
        
        enriched_candidates.append((total_salience, item_type, source_id, payload, pressures))


    # 4. Extract scores and apply Softmax with state‑driven temperature
    scores = [c[0] for c in enriched_candidates]
    temperature = 0.2 + (1.0 - state.dominance) * 0.8   # maps 0.0 → 1.0
    if state.coherence > 0.7:
        temperature *= 0.8
    probabilities = _softmax(scores, temperature)
    probabilities = np.array(probabilities)
    prob_sum = np.sum(probabilities)
    if prob_sum <= 0 or np.isnan(prob_sum):
        # Fallback to uniform distribution if all scores are zero/NaN
        probabilities = np.ones(len(probabilities))
        prob_sum = len(probabilities)
    probabilities = probabilities / prob_sum


    # 5. Select top items (stochastic sampling according to probabilities)
    num_selected = min(workspace_size, len(enriched_candidates))
    indices = list(range(len(enriched_candidates)))
    selected_indices = np.random.choice(indices, size=num_selected, replace=False, p=probabilities)
    selected_candidates = [enriched_candidates[i] for i in selected_indices]

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
    user_input: str,
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
        query=user_input,
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

    # Layer 3: Inertia – inject previous workspace items
    if len(candidates) < 3 and previous_workspace_items:
        logger.warning(f"Turn {current_turn}: Injecting previous workspace items for inertia.")
        for old_item in previous_workspace_items:
            if not any(c.id == old_item.id for c in candidates):
                mem = MemoryEvent(
                    id=old_item.id,
                    session_id=session_id,
                    turn_number=current_turn - 1,
                    role="assistant",
                    content=old_item.content,
                    event_type="workspace_inertia",
                    thematic_tags=[],
                    significance=0.4,
                    meaning_summary=old_item.content[:100],
                    created_at=datetime.now(),
                    usage_count=0,
                    last_retrieved_turn=current_turn - 1,
                    explanatory_power=0.3
                )
                mem.computed_score = 0.4
                candidates.append(mem)

    # Apply diversity penalty
    diversified = apply_workspace_diversity_penalty(candidates, target_count=15)
    return diversified