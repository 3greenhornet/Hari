"""Endogenous cognition: candidates that arise from Hari's persistent internal state
without any incoming external event.

These are the thoughts she has when nobody is talking. They compete in the
same workspace as the participant's message. Neither is privileged.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def collect_endogenous_candidates(
    *,
    active_thought_store,
    curiosity_nodes: List[Dict[str, Any]],
    active_threads: List[Any],
    self_beliefs: List[Dict[str, Any]],
    pursuit_registry=None,
    contradictions: Optional[List[Dict[str, Any]]] = None,
    self_model: Any = None,
    monologue_candidates=None,
    current_turn: int = 0,
    max_per_source: int = 6,
) -> List[Dict[str, Any]]:
    """Collect internal candidates from all endogenous sources.

    Every candidate carries full provenance so the trace can record
    where it came from and why it competed.
    """
    candidates: List[Dict[str, Any]] = []

    # Active thoughts — highest priority internal source
    for thought in active_thought_store.top(max_per_source):
        text = (thought.text or "").strip()
        if not text:
            continue
        candidates.append({
            "id": f"endogenous_thought_{uuid.uuid4().hex[:8]}",
            "content": text,
            "item_type": "open_thought",
            "source": "internal_cognition",
            "internal_source": "active_thought",
            "internal_activation": float(thought.activation),
            "intrinsic_relevance": float(thought.activation) * 1.2,
            "persistence": 0.85,
            "origin": thought.origin or "internal",
            "activated_by": f"endogenous_turn_{current_turn}",
            "information_gap": 0.2,
            "closure_pressure": 0.3,
            "coherence_factor": 0.3,
        })

    # Active pursuits — persistent unresolved intentions
    if pursuit_registry is not None:
        try:
            for pursuit in pursuit_registry.get_active()[:max_per_source]:
                candidates.append({
                    "id": f"endogenous_pursuit_{pursuit.id}",
                    "content": pursuit.content,
                    "item_type": "open_thought",
                    "source": "volition_persistent",
                    "internal_source": "pursuit",
                    "internal_activation": float(pursuit.strength),
                    "intrinsic_relevance": float(pursuit.strength) * 1.2,
                    "persistence": 0.90,
                    "origin": "pursuit",
                    "activated_by": f"pursuit_{pursuit.id}",
                    "information_gap": 0.3 * pursuit.strength,
                    "closure_pressure": 0.5 * pursuit.strength,
                    "coherence_factor": 0.3 * pursuit.strength,
                })
        except Exception as e:
            logger.debug(f"Pursuit collection failed: {e}")

    # Curiosity nodes
    for node in curiosity_nodes[:max_per_source]:
        text = node.get("question") or node.get("content") or ""
        if not text.strip():
            continue
        importance = float(node.get("importance", 0.5))
        candidates.append({
            "id": f"endogenous_curiosity_{node.get('id', uuid.uuid4().hex[:8])}",
            "content": text,
            "item_type": "curiosity_node",
            "source": "internal_cognition",
            "internal_source": "curiosity",
            "internal_activation": importance,
            "intrinsic_relevance": importance,
            "persistence": 0.60,
            "origin": "curiosity",
            "activated_by": node.get("id", "curiosity_graph"),
            "information_gap": importance,
            "closure_pressure": 0.1 * importance,
            "coherence_factor": 0.2 * importance,
        })

    # Narratives
    for thread in active_threads[:max_per_source]:
        text = getattr(thread, "description", "") or getattr(thread, "title", "")
        if not text.strip():
            continue
        completion = float(getattr(thread, "completion_estimate", 0.5))
        investment = float(getattr(thread, "emotional_investment", 0.5))
        candidates.append({
            "id": f"endogenous_narrative_{getattr(thread, 'id', uuid.uuid4().hex[:8])}",
            "content": text,
            "item_type": "narrative_thread",
            "source": "internal_cognition",
            "internal_source": "narrative",
            "internal_activation": investment,
            "intrinsic_relevance": investment * 1.1,
            "persistence": 1.0 - completion,
            "origin": "narrative",
            "activated_by": getattr(thread, "id", "narrative_manager"),
            "information_gap": 0.1,
            "closure_pressure": (1.0 - completion) * investment,
            "coherence_factor": 0.1,
        })

    # Self-beliefs
    for belief in self_beliefs[:max_per_source]:
        text = belief.get("content") or belief.get("belief_text", "")
        if not text.strip():
            continue
        confidence = float(belief.get("confidence", 0.5))
        candidates.append({
            "id": f"endogenous_belief_{uuid.uuid4().hex[:8]}",
            "content": text,
            "item_type": "open_thought",
            "source": "internal_cognition",
            "internal_source": "self_belief",
            "internal_activation": confidence * 0.5,
            "intrinsic_relevance": confidence * 0.6,
            "persistence": 0.70,
            "origin": "self_belief",
            "activated_by": "self_beliefs",
            "information_gap": 0.2,
            "closure_pressure": 0.2,
            "coherence_factor": 0.4,
        })

    # Contradictions — high tension internal candidates
    if contradictions:
        for contradiction in contradictions[:max_per_source]:
            text = f"Tension: {(contradiction.get('belief_a') or '')[:100]} vs {(contradiction.get('belief_b') or '')[:100]}"
            if not text.strip():
                continue
            severity = float(contradiction.get("severity", 0.5))
            candidates.append({
                "id": f"endogenous_contradiction_{contradiction.get('contradiction_id', uuid.uuid4().hex[:8])}",
                "content": text,
                "item_type": "open_thought",
                "source": "internal_cognition",
                "internal_source": "contradiction",
                "internal_activation": severity * 0.9,
                "intrinsic_relevance": severity,
                "persistence": 0.85,
                "origin": "contradiction",
                "activated_by": contradiction.get("contradiction_id", "contradiction_store"),
                "information_gap": 0.7 * severity,
                "closure_pressure": 0.5 * severity,
                "coherence_factor": 0.5 * severity,
            })

    # Self-model questions
    if self_model is not None:
        for question in getattr(self_model, "active_self_questions", [])[:max_per_source]:
            if not question or not question.strip():
                continue
            candidates.append({
                "id": f"endogenous_self_question_{uuid.uuid4().hex[:8]}",
                "content": question,
                "item_type": "open_thought",
                "source": "internal_cognition",
                "internal_source": "self_question",
                "internal_activation": 0.4,
                "intrinsic_relevance": 0.5,
                "persistence": 0.80,
                "origin": "self_model",
                "activated_by": "identity_model",
                "information_gap": 0.4,
                "closure_pressure": 0.3,
                "coherence_factor": 0.4,
            })

    if monologue_candidates:
        for candidate in monologue_candidates[:max_per_source]:
            content = (getattr(candidate, "content", "") or "").strip()
            if not content:
                continue
            candidates.append({
                "id": f"endogenous_monologue_{uuid.uuid4().hex[:8]}",
                "content": content,
                "item_type": "open_thought",
                "source": "internal_cognition",
                "internal_source": getattr(candidate, "origin", "monologue"),
                "internal_activation": float(getattr(candidate, "urgency", 0.3)),
                "intrinsic_relevance": float(getattr(candidate, "intrinsic_relevance", 0.0)),
                "persistence": float(getattr(candidate, "persistence", 0.0)),
                "origin": "internal_cognition",
                "activated_by": f"monologue_turn_{current_turn}",
                "activation_reason": getattr(candidate, "activation_reason", None),
                "information_gap": 0.2,
                "closure_pressure": 0.3,
                "coherence_factor": 0.3,
            })
    return candidates
