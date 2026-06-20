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
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Literal
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from engine.memory import embed
from models.memory_event import MemoryEvent
from psyche.state import HariState
from engine.memory import increment_memory_usage


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
        item_type: Literal["memory", "hypothesis", "curiosity_node", "narrative_thread", "open_thought"],
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


@dataclass
class NarrativeThread:
    """First‑class narrative thread for long‑running topics."""
    id: str
    goal_description: str
    current_status: str = "active"          # active, blocked, completed
    completion_estimate: float = 0.0        # 0.0 → 1.0
    activation: float = 0.5                 # current salience (decays over time)
    last_attended_turn: int = 0


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
    Returns a vector of four pressure values for a single candidate.
    """
    pressures = {}

    # 1. Relevance Pressure: cosine similarity with user input
    relevance = 0.5   # default neutral
    if user_embedding is not None and "embedding" in candidate:
        try:
            candidate_emb = np.array(candidate["embedding"], dtype=np.float32)
            # Normalise embeddings for cosine similarity
            user_norm = user_embedding / (np.linalg.norm(user_embedding) + 1e-8)
            cand_norm = candidate_emb / (np.linalg.norm(candidate_emb) + 1e-8)
            cos_sim = np.dot(user_norm, cand_norm)
            relevance = (cos_sim + 1) / 2   # map [-1,1] → [0,1]
        except Exception as e:
            logger.warning(f"Relevance pressure failed: {e}")
    pressures["relevance"] = relevance

    # 2. Novelty Pressure: driven by prediction error
    #    Clamp prediction error to [0,1] range
    novelty = min(1.0, max(0.0, prediction_error))
    pressures["novelty"] = novelty

    # 3. Curiosity Pressure: knowledge gap potential
    curiosity_pressure = state.curiosity
    if candidate.get("item_type") == "curiosity":
        curiosity_pressure *= 1.5   # boost for actual curiosity nodes
    pressures["curiosity"] = min(1.0, curiosity_pressure)

    # 4. Completion Pressure: finish ongoing thoughts
    completion_pressure = state.completion
    if candidate.get("item_type") in ("open_thread", "narrative"):
        # Open threads get an extra boost from their own urgency
        urgency = candidate.get("urgency", 0.5)
        completion_pressure = (completion_pressure + urgency) / 2
    pressures["completion"] = min(1.0, completion_pressure)

    return pressures


async def compute_total_salience(
    pressures: Dict[str, float],
    state: HariState,
) -> float:
    """
    Weight the pressure vector by Hari's current state drives.
    Returns a salience score between 0 and 1.
    """
    weights = {
        "relevance": 1.0,           # base weight – always matters
        "novelty": state.curiosity, # curious minds care about novelty
        "curiosity": state.curiosity,
        "completion": state.completion,
    }
    total = 0.0
    total_weight = 0.0
    for name, pressure in pressures.items():
        w = weights.get(name, 0.0)
        total += pressure * w
        total_weight += w
    # Normalise by total weight (avoid division by zero)
    if total_weight > 0:
        salience = total / total_weight
    else:
        salience = 0.5
    return min(1.0, max(0.0, salience))


    # Legacy alias for engine/__init__.py (avoids refactoring downstream)
async def compute_salience(pressures: Dict[str, float], state: HariState) -> float:
    """Deprecated: use compute_total_salience directly."""
    return await compute_total_salience(pressures, state)




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
    Update state drives based on workspace composition.
    Closes the cognitive loop.
    """
    if not elected:
        return
    # Curiosity: ratio of curiosity_nodes in workspace
    curiosity_ratio = sum(1 for item in elected if item.item_type == "curiosity_node") / len(elected)
    state.curiosity = min(1.0, state.curiosity + (curiosity_ratio * 0.05))
    # Coherence: if narrative threads dominate, boost coherence
    narrative_ratio = sum(1 for item in elected if item.item_type == "narrative_thread") / len(elected)
    state.coherence = min(1.0, state.coherence + (narrative_ratio * 0.03))
    # Engagement: if user input is highly attended (relevance pressure high), boost engagement slightly
    # This is optional; can be extended.


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
        add_candidate("memory", mem.id, {
            "content": mem.content,
            "embedding": getattr(mem, "embedding", None),
            "significance": getattr(mem, "significance", 0.5),
            "id": mem.id,
        })
    # Add hypotheses
    for hyp in hypotheses:
        add_candidate("hypothesis", hyp.get("id", "unknown"), {
            "content": hyp.get("statement", ""),
            "embedding": hyp.get("embedding"),
            "confidence": hyp.get("confidence", 0.5),
            "id": hyp.get("id"),
        })
    # Add curiosity nodes
    for node in curiosity_nodes:
        add_candidate("curiosity_node", node.get("id", "unknown"), {
            "content": node.get("question", ""),
            "embedding": node.get("embedding"),
            "importance": node.get("importance", 0.5),
            "id": node.get("id"),
        })
    # Add narrative threads
    for thread in narrative_threads:
        add_candidate("narrative_thread", thread.id, {
            "content": thread.goal_description,
            "completion_estimate": thread.completion_estimate,
            "activation": thread.activation,
            "id": thread.id,
        })
    # Add open threads
    for ot in open_threads:
        add_candidate("open_thought", ot.get("id", "unknown"), {
            "content": ot.get("content", ""),
            "urgency": ot.get("urgency", 0.5),
            "id": ot.get("id"),
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
    # Compute pressures and total salience for each candidate
    # Compute pressures and total salience for each candidate
    enriched_candidates = []
    for _, item_type, source_id, payload, _ in candidates:
        pressures = await _compute_pressure_field(payload, state, user_embedding, prediction_error)
        
        # Inertia boost
        if previous_workspace_items:
            for old in previous_workspace_items:
                if old.id == source_id:
                    pressures["relevance"] = (pressures["relevance"] + old.metrics.activation) / 2
                    break
        
        # Base salience from pressures
        base_salience = await compute_total_salience(pressures, state)
        
        # Memory fatigue and explanatory power
        usage_count = payload.get("usage_count", 0)
        explanatory_power = payload.get("explanatory_power", 0.5)
        surprise_contribution = prediction_error * explanatory_power
        fatigue_penalty = min(0.3, usage_count * 0.02)
        
        # Store fatigue_penalty in pressures so telemetry can see it
        pressures["fatigue_penalty"] = fatigue_penalty
        
        # Final salience
        total_salience = base_salience + surprise_contribution - fatigue_penalty
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
    probabilities = probabilities / np.sum(probabilities)   # force exact sum = 1.0hari


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

    return workspace_items, telemetry

# -----------------------------------------------------------------------------
# Helper to offload CPU‑bound ops to a thread pool
# -----------------------------------------------------------------------------

_executor = ThreadPoolExecutor(max_workers=2)

async def _run_in_executor(func, *args):
    """Run a CPU‑heavy function in a thread pool to avoid blocking the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, func, *args)