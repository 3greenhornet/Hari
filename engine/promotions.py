"""
engine/promotions.py — The sole cognitive authority for structure creation.

This is the CENTRAL CONVERGENCE HUB where raw experiences become permanent
cognitive structures: Patterns, Contradictions, Interests, and Identity Anchors.

ALL structure creation MUST flow through this engine.
"""

import json
import re
import logging
import uuid
import asyncio
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timezone
import numpy as np
from litellm import acompletion

from models.relational import Pattern, Contradiction, Interest
from db.connection import get_pool
from engine.cognitive_params import PROMOTION

logger = logging.getLogger(__name__)

# ============================================================
# Caches for performance
# ============================================================

_tension_cache = {}          # (text_a_hash, text_b_hash) -> (tension_type, severity)
_contradiction_history = {}  # key -> (last_check_time, severity)

# ============================================================
# Helper: Tension Classification with LLM (Cached)
# ============================================================

async def _evaluate_tension_llm(text_a: str, text_b: str) -> Tuple[str, float]:
    """
    Uses a fast LLM to classify cognitive tension between two related texts.
    Returns (tension_type, severity).
    Cached to avoid repeated calls.
    """
    cache_key = f"{hash(text_a)}_{hash(text_b)}"
    if cache_key in _tension_cache:
        return _tension_cache[cache_key]

    # Check if this pair was checked recently (within 1 hour)
    if cache_key in _contradiction_history:
        last_check, _ = _contradiction_history[cache_key]
        if (datetime.now() - last_check).total_seconds() < 3600:
            return _tension_cache.get(cache_key, ("neutral", 0.0))

    prompt = f"""Analyze the cognitive relationship between these two statements.
Statement A: "{text_a[:300]}"
Statement B: "{text_b[:300]}"

Output ONLY a JSON object with two fields:
- "tension_type": one of "contradiction", "ambiguity", "neutral"
- "severity": float 0.0-1.0 (0.0 = perfectly aligned, 1.0 = direct contradiction)
"""

    from engine.stage1_monologue import MONOLOGUE_FALLBACK_MODELS

    for model in MONOLOGUE_FALLBACK_MODELS:
        try:
            kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "timeout": PROMOTION.llm_timeout_seconds
            }
            if not model.startswith("openrouter"):
                kwargs["response_format"] = {"type": "json_object"}

            # Direct await – acompletion is already async
            response = await acompletion(**kwargs)
            raw = response.choices[0].message.content
            try:
                from engine.stage1_monologue import _extract_json_safely
                clean = _extract_json_safely(raw)
                data = json.loads(clean)
                tension_type = data.get("tension_type", "neutral")
                severity = float(data.get("severity", 0.0))
                _tension_cache[cache_key] = (tension_type, severity)
                _contradiction_history[cache_key] = (datetime.now(), severity)
                return tension_type, severity
            except Exception as e:
                logger.warning(f"Failed to parse tension response from {model}: {e}")
                continue
        except Exception as e:
            logger.warning(f"Tension classification failed on {model}: {e}")
            continue

    # Fallback
    _tension_cache[cache_key] = ("neutral", 0.0)
    return "neutral", 0.0

# ============================================================
# Core Promotion Functions
# ============================================================

async def promote_memory_to_pattern(
    memory_ids: List[str],
    source_tension_id: Optional[str] = None
) -> Optional[str]:
    """
    Ticket 017: Promote a cluster of MemoryEvents to a Pattern.
    Requires ≥3 memories with average similarity > threshold.
    """
    if len(memory_ids) < PROMOTION.pattern_min_memories:
        return None

    pool = await get_pool()
    if not pool:
        return None

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, content, significance, embedding, session_id, turn_number, trace_id
            FROM memories
            WHERE id = ANY($1::text[])
        """, memory_ids)

    if len(rows) < PROMOTION.pattern_min_memories:
        return None

    # Compute average cosine similarity
    embeddings = [np.array(r["embedding"], dtype=np.float32) for r in rows]
    similarities = []
    for i in range(len(embeddings)):
        for j in range(i+1, len(embeddings)):
            norm_i = embeddings[i] / (np.linalg.norm(embeddings[i]) + 1e-8)
            norm_j = embeddings[j] / (np.linalg.norm(embeddings[j]) + 1e-8)
            similarities.append(float(np.dot(norm_i, norm_j)))
    avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0

    if avg_similarity < PROMOTION.pattern_similarity_threshold:
        return None

    # Generate pattern description
    rows.sort(key=lambda r: r["significance"] or 0.0, reverse=True)
    description = " ; ".join([r["content"][:150] for r in rows[:3]])
    avg_significance = sum(r["significance"] for r in rows) / len(rows)

    session_id = rows[0]["session_id"]
    max_turn = max(r["turn_number"] for r in rows)

    async with pool.acquire() as conn:
        # Check for existing similar pattern
        existing = await conn.fetchrow("""
            SELECT pattern_id FROM patterns
            WHERE session_id = $1 AND cluster_similarity > $2
            LIMIT 1
        """, session_id, PROMOTION.pattern_similarity_threshold - 0.1)

        if existing:
            pattern_id = existing["pattern_id"]
            await conn.execute("""
                UPDATE patterns
                SET supporting_memory_ids = array_cat(supporting_memory_ids, $1::text[]),
                    supporting_trace_ids = array_cat(supporting_trace_ids, $2::text[]),
                    cluster_similarity = (cluster_similarity + $3) / 2,
                    significance = LEAST(1.0, significance + 0.05),
                    last_updated_turn = $4,
                    updated_at = NOW()
                WHERE pattern_id = $5
            """, memory_ids, [r["trace_id"] for r in rows], avg_similarity, max_turn, pattern_id)
            return pattern_id

        # Create new pattern
        pattern_id = f"pattern_{rows[0]['id'][:8]}_{int(datetime.now().timestamp())}"
        await conn.execute("""
            INSERT INTO patterns (
                pattern_id, session_id, description,
                supporting_memory_ids, supporting_trace_ids, cluster_similarity,
                significance, status, created_turn, last_updated_turn
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """, pattern_id, session_id, description, memory_ids,
            [r["trace_id"] for r in rows], avg_similarity, avg_significance,
            "emerging", max_turn, max_turn)

        logger.info(f"Pattern created: {pattern_id} (similarity: {avg_similarity:.3f})")
        return pattern_id

async def promote_pattern_to_contradiction(
    pattern_id: str,
    source_tension_id: Optional[str] = None
) -> Optional[str]:
    """
    Ticket 017: Check if a Pattern contradicts an existing Hypothesis.
    If so, create a Contradiction and spawn a Curiosity.
    """
    pool = await get_pool()
    if not pool:
        return None

    async with pool.acquire() as conn:
        pattern = await conn.fetchrow("SELECT * FROM patterns WHERE pattern_id = $1", pattern_id)
        if not pattern:
            return None

        # Fetch existing hypotheses (world/self)
        hypotheses = await conn.fetch("""
            SELECT statement, confidence, supporting_event_ids
            FROM hypotheses
            WHERE type IN ('world', 'self')
            ORDER BY confidence DESC
            LIMIT 10
        """)

        for hyp in hypotheses:
            tension_type, severity = await _evaluate_tension_llm(
                pattern["description"],
                hyp["statement"]
            )
            if tension_type == "contradiction" and severity > PROMOTION.contradiction_severity_threshold:
                contradiction_id = f"contradiction_pattern_{pattern_id[:8]}_{int(datetime.now().timestamp())}"
                await conn.execute("""
                    INSERT INTO contradictions (
                        contradiction_id, belief_a, belief_b,
                        source_a, source_b, severity, status, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, contradiction_id,
                    pattern["description"][:200],
                    hyp["statement"],
                    pattern_id,
                    hyp["supporting_event_ids"][0] if hyp["supporting_event_ids"] else "unknown",
                    severity,
                    "active",
                    datetime.now(timezone.utc)
                )

                # Spawn curiosity
                await promote_contradiction_to_curiosity(
                    contradiction_id,
                    source_tension_id or pattern_id,
                    severity
                )
                logger.info(f"Pattern-Hypothesis contradiction: {contradiction_id}")
                return contradiction_id
    return None

async def promote_contradiction_to_curiosity(
    contradiction_id: str,
    source_tension_id: str,
    severity: float = 0.5
) -> Optional[str]:
    """Spawn a CuriosityNode from a contradiction."""
    if severity < PROMOTION.curiosity_importance_floor:
        return None

    logger.info(f"Promoting contradiction {contradiction_id} -> curiosity (severity: {severity:.2f})")
    try:
        from engine.curiosity_graph import get_graph_manager
        graph = await get_graph_manager()
        importance = min(1.0, severity)
        node_id = await graph.add_node(
            question=f"Resolve tension: {contradiction_id}",
            importance=importance,
            session_id="system",
            origin_trace_id=source_tension_id
        )
        pool = await get_pool()
        if pool:
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE contradictions
                    SET linked_curiosity_node_ids = array_append(linked_curiosity_node_ids, $1)
                    WHERE contradiction_id = $2
                """, node_id, contradiction_id)
        return node_id
    except Exception as e:
        logger.error(f"Failed to promote contradiction to curiosity: {e}")
        return None

async def promote_curiosity_to_interest(
    curiosity_node_id: str,
    source_tension_id: str
) -> Optional[str]:
    """
    Ticket 018: Promote a frequently winning CuriosityNode to a persistent Interest.
    Checks if the node's importance is above threshold.
    """
    logger.info(f"Promoting curiosity {curiosity_node_id} to interest")
    from engine.curiosity_graph import get_graph_manager
    graph = await get_graph_manager()
    nodes = await graph.get_top_nodes(limit=10)
    node_importance = 0.0
    for n in nodes:
        if n["id"] == curiosity_node_id:
            node_importance = n["importance"]
            break
    if node_importance < PROMOTION.interest_activation_threshold:
        return None

    interest_id = f"interest_{curiosity_node_id}"
    pool = await get_pool()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO system_interests (interest_id, session_id, interest_name, current_strength)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (interest_id) DO UPDATE
                SET current_strength = EXCLUDED.current_strength, updated_at = NOW()
            """, interest_id, "system", f"Interest from {curiosity_node_id}", node_importance)
    logger.info(f"Interest created: {interest_id}")
    return interest_id

async def promote_interest_to_identity_anchor(
    interest_id: str,
    stabilization_score: float
) -> Optional[str]:
    """
    Ticket 019: Record an identity anchor when an interest stabilizes.
    Uses DevelopmentEvent as the permanent ledger.
    """
    if stabilization_score < PROMOTION.identity_stabilization_threshold:
        return None

    anchor_id = f"anchor_{interest_id}"
    from models.development_event import DevelopmentEvent
    event = DevelopmentEvent(
        session_id="system",
        turn_number=0,
        event_type="identity_anchor_formed",
        source_attribution=[],
        confidence=stabilization_score,
        reason=f"Interest {interest_id} stabilized into identity anchor",
        interest_id=interest_id,
        metadata={"anchor_id": anchor_id}
    )
    from engine.development import store_development_event
    await store_development_event(event)
    logger.info(f"Identity anchor recorded: {anchor_id}")
    return anchor_id

# ============================================================
# Staging Processor (The Convergence Hub)
# ============================================================

from dataclasses import dataclass
from typing import List, Optional
import uuid

@dataclass
class ProposalEvaluation:
    proposal_id: str
    proposal_type: str  # 'user', 'self', 'world', or 'self_belief'
    content: str
    confidence: float
    accepted: bool
    rejection_reason: Optional[str]
    contradiction_found: bool
    contradiction_severity: float
    source_trace_id: str


async def process_staging_proposals(session_id: str, current_turn: int) -> Dict[str, int]:
    results = {"accepted": 0, "rejected": 0, "contradictions_found": 0}
    pool = await get_pool()
    if not pool:
        return results

    # ------------------------------------------------------------------
    # PHASE 1 – ATOMIC CLAIM
    # ------------------------------------------------------------------
    claimed_proposals = []
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            WITH claimed AS (
                SELECT proposal_id
                FROM staging_proposals
                WHERE session_id = $1
                  AND status = 'pending'
                ORDER BY created_at ASC
                LIMIT $2
                FOR UPDATE SKIP LOCKED
            )
            UPDATE staging_proposals sp
            SET status = 'processing',
                processing_started_at = NOW()
            FROM claimed
            WHERE sp.proposal_id = claimed.proposal_id
            RETURNING sp.*
        """, session_id, PROMOTION.staging_batch_size)
        claimed_proposals = rows

    if not claimed_proposals:
        return results

    # ------------------------------------------------------------------
    # PHASE 2 – EVALUATE (no DB connection held)
    # ------------------------------------------------------------------
    # Fetch existing hypotheses once – type-aware
    existing_hypotheses = {}
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT type, statement FROM hypotheses
            ORDER BY confidence DESC, last_updated DESC
            LIMIT 20
        """)
        for row in rows:
            existing_hypotheses.setdefault(row["type"], []).append(row["statement"])

    evaluations: List[ProposalEvaluation] = []

    for prop in claimed_proposals:
        confidence = float(prop.get("confidence_estimate", 0.5))
        info_gap = float(prop.get("information_gap", 0.0))
        closure_pressure = float(prop.get("closure_pressure", 0.0))
        coherence_factor = float(prop.get("coherence_factor", 0.0))

        combined = (
            confidence * 0.4
            + info_gap * 0.2
            + closure_pressure * 0.2
            + coherence_factor * 0.2
        )

        accepted = False
        rejection_reason = None
        contradiction_found = False
        contradiction_severity = 0.0

        # Determine if this is a hypothesis type
        is_hypothesis = prop["proposal_type"] in ("user", "self", "world")

        if combined >= PROMOTION.staging_confidence_threshold and is_hypothesis:
            # Check contradictions only against same-type hypotheses
            same_type_hypotheses = existing_hypotheses.get(prop["proposal_type"], [])
            for hyp_statement in same_type_hypotheses:
                tension_type, severity = await _evaluate_tension_llm(
                    prop["content"],
                    hyp_statement,
                )
                if (
                    tension_type == "contradiction"
                    and severity >= PROMOTION.contradiction_severity_threshold
                ):
                    contradiction_found = True
                    contradiction_severity = severity
                    results["contradictions_found"] += 1
                    logger.info(f"Contradiction with existing {prop['proposal_type']} hypothesis")
                    break

            if not contradiction_found:
                accepted = True

        elif combined >= PROMOTION.staging_confidence_threshold and prop["proposal_type"] == "self_belief":
            accepted = True

        if not accepted and not rejection_reason:
            rejection_reason = (
                "Contradiction detected" if contradiction_found
                else "Insufficient combined score"
            )

        evaluations.append(
            ProposalEvaluation(
                proposal_id=prop["proposal_id"],
                proposal_type=prop["proposal_type"],
                content=prop["content"],
                confidence=combined,
                accepted=accepted,
                rejection_reason=rejection_reason,
                contradiction_found=contradiction_found,
                contradiction_severity=contradiction_severity,
                source_trace_id=prop["source_trace_id"],
            )
        )

    # ------------------------------------------------------------------
    # PHASE 3 – COMMIT (re‑acquire connection)
    # ------------------------------------------------------------------
    async with pool.acquire() as conn:
        async with conn.transaction():
            for ev in evaluations:
                if ev.accepted:
                    status = 'accepted'
                    if ev.proposal_type in ("user", "self", "world"):
                        # Hypothesis
                        await conn.execute("""
                            INSERT INTO hypotheses (type, statement, confidence, supporting_event_ids, last_updated)
                            VALUES ($1, $2, $3, $4::TEXT[], $5)
                            ON CONFLICT (type, statement) DO UPDATE
                            SET confidence = (hypotheses.confidence + EXCLUDED.confidence) / 2,
                                supporting_event_ids = array_cat(hypotheses.supporting_event_ids, EXCLUDED.supporting_event_ids),
                                last_updated = EXCLUDED.last_updated
                        """, ev.proposal_type, ev.content, ev.confidence, [ev.source_trace_id], datetime.now(timezone.utc))
                        results["accepted"] += 1
                    elif ev.proposal_type == "self_belief":
                        await conn.execute("""
                            INSERT INTO self_beliefs (id, session_id, belief_text, created_at)
                            VALUES ($1, 'system', $2, NOW())
                        """, str(uuid.uuid4()), ev.content)
                        results["accepted"] += 1
                else:
                    status = 'rejected'
                    results["rejected"] += 1

                await conn.execute("""
                    UPDATE staging_proposals
                    SET status = $1, evaluated_at = NOW(), rejection_reason = $2
                    WHERE proposal_id = $3
                """, status, ev.rejection_reason, ev.proposal_id)

    logger.info(f"Promotion Engine processed staging: {results}")
    return results

# ============================================================
# Contradiction Detection from Recent Memories
# ============================================================

async def detect_contradictions_from_memories(session_id: str, current_turn: int) -> List[str]:
    """
    Scans recent high-significance memories for contradictions using LLM.
    Frequency-capped and limited per cycle.
    """
    contradictions_found = []
    cycle_key = f"cycle_{current_turn // PROMOTION.contradiction_check_interval}"
    if cycle_key in _contradiction_history:
        return contradictions_found
    _contradiction_history[cycle_key] = datetime.now()

    pool = await get_pool()
    if not pool:
        return contradictions_found

    async with pool.acquire() as conn:
        memories = await conn.fetch("""
            SELECT id, content, significance, embedding, trace_id
            FROM memories
            WHERE session_id = $1 AND significance > 0.6
            ORDER BY turn_number DESC
            LIMIT 15
        """, session_id)

        if len(memories) < 2:
            return contradictions_found

        checked = 0
        for i in range(len(memories)):
            for j in range(i+1, len(memories)):
                if checked >= PROMOTION.contradiction_llm_limit_per_cycle:
                    break
                mem_a, mem_b = memories[i], memories[j]

                # Relationship discovery: similarity > threshold
                emb_a = np.array(mem_a["embedding"], dtype=np.float32)
                emb_b = np.array(mem_b["embedding"], dtype=np.float32)
                norm_a = emb_a / (np.linalg.norm(emb_a) + 1e-8)
                norm_b = emb_b / (np.linalg.norm(emb_b) + 1e-8)
                cos_sim = float(np.dot(norm_a, norm_b))
                if cos_sim < PROMOTION.contradiction_similarity_threshold:
                    continue

                tension_type, severity = await _evaluate_tension_llm(mem_a["content"], mem_b["content"])
                checked += 1
                if tension_type == "neutral" or severity < PROMOTION.contradiction_severity_threshold:
                    continue

                # Check if already exists
                existing = await conn.fetchrow("""
                    SELECT contradiction_id FROM contradictions
                    WHERE (source_a = $1 AND source_b = $2) OR (source_a = $2 AND source_b = $1)
                """, mem_a["id"], mem_b["id"])
                if existing:
                    continue

                contradiction_id = f"contradiction_{mem_a['id'][:8]}_{mem_b['id'][:8]}_{int(datetime.now().timestamp())}"
                await conn.execute("""
                    INSERT INTO contradictions (
                        contradiction_id, belief_a, belief_b,
                        source_a, source_b, severity, status, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, contradiction_id,
                    mem_a["content"][:200],
                    mem_b["content"][:200],
                    mem_a["id"],
                    mem_b["id"],
                    severity,
                    "active",
                    datetime.now(timezone.utc)
                )

                await promote_contradiction_to_curiosity(
                    contradiction_id,
                    mem_a["trace_id"] or "system",
                    severity
                )
                contradictions_found.append(contradiction_id)
                logger.info(f"Contradiction detected: {contradiction_id} (severity: {severity:.3f})")

    return contradictions_found

# ============================================================
# Archival
# ============================================================

async def archive_inactive_structures(current_turn: int) -> int:
    """Archive old staging entries, interests, and patterns."""
    archived = 0
    pool = await get_pool()
    if not pool:
        return archived

    async with pool.acquire() as conn:
        # Archive accepted/rejected staging older than 7 days
        result = await conn.execute("""
            DELETE FROM staging_proposals
            WHERE status IN ('accepted', 'rejected')
              AND evaluated_at < NOW() - INTERVAL '7 days'
            RETURNING proposal_id
        """)
        # Correctly parse asyncpg result
        parts = result.split(" ")
        archived += int(parts[1]) if len(parts) > 1 else 0

        # Archive low-strength interests
        result = await conn.execute("""
            UPDATE system_interests
            SET current_strength = GREATEST(0, current_strength - 0.01)
            WHERE current_strength < 0.1
            RETURNING interest_id
        """)
        parts = result.split(" ")
        archived += int(parts[1]) if len(parts) > 1 else 0

        # Archive old emerging patterns
        result = await conn.execute("""
            UPDATE patterns
            SET status = 'archived'
            WHERE status = 'emerging'
              AND last_updated_turn < $1 - $2
            RETURNING pattern_id
        """, current_turn, PROMOTION.pattern_archive_age_turns)
        parts = result.split(" ")
        archived += int(parts[1]) if len(parts) > 1 else 0

    logger.debug(f"Archived {archived} inactive structures at turn {current_turn}")
    return archived

    # ============================================================
# FUTURE EXTENSIONS (Phase 7 - Identity & Perspective Shifts)
# ============================================================
# The following functions are intentionally NOT implemented here.
# 
# Rationale:
# - `record_perspective_shift` and `promote_to_development_event` belong to 
#   Identity evolution, which is a separate concern from the Ecology Pipeline 
#   (Memory -> Pattern -> Contradiction -> Curiosity -> Interest).
# - These are now managed by engine/development.py and models/development.py 
#   to maintain a clean separation between "structural memory" (Ecology)
#   and "permanent identity" (SelfModel / Constitution).
#
# - Reference: HARI_COGNITIVE_ECOLOGY.md - Section 3 (Transformation Rules)
# - Reference: docs/research_incubator/ARCHITECTURE.md - ADR-002 (Canonical State)
# - Reference: ENGINE_TICKETS.md - Phase 7 (Future Identity Reinforcement)
#
# If you are reading this in Phase 7, uncomment and wire them up.
# For now, we keep them here as a historical roadmap marker.
# ============================================================

# async def record_perspective_shift(
#     conceptual_axis: str,
#     from_stance: str,
#     to_stance: str,
#     source_tension_id: str,
#     parent_event_id: Optional[str] = None
# ) -> Optional[str]:
#     """
#     DEPRECATED (Moved to Phase 7): 
#     Create a PerspectiveShift atomic log.
#     Currently handled by engine/development.py and models/development.py.
#     """
#     logger.debug(f"record_perspective_shift called for axis '{conceptual_axis}' (stub - moved to development.py)")
#     # TODO Phase 7: Uncomment and implement using IdentityModel
#     return None

# async def promote_to_development_event(
#     perspective_shift_ids: List[str],
#     event_type: str,
#     impact_domain: str,
#     source_tension_id: str,
#     description: str,
#     previous_perspective: str,
#     stabilized_perspective: str
# ) -> Optional[str]:
#     """
#     DEPRECATED (Moved to Phase 7): 
#     Compile multiple PerspectiveShifts into a DevelopmentEvent.
#     Currently handled by engine/development.py and models/development.py.
#     """
#     logger.debug(f"promote_to_development_event called with {len(perspective_shift_ids)} shifts (stub - moved to development.py)")
#     # TODO Phase 7: Uncomment and implement using IdentityModel
#     return None

# ============================================================
# END OF FILE
# ============================================================