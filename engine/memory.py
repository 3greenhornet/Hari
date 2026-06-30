# hari/engine/memory.py
import os
import uuid
from typing import List, Optional, Dict
from datetime import datetime
import numpy as np
from google import genai
from models.memory_event import MemoryEvent
import math

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_genai_client = None

def get_genai_client():
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(api_key=GEMINI_API_KEY)
    return _genai_client

async def embed(text: str) -> List[float]:
    client = get_genai_client()
    response = await client.aio.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text
    )
    return response.embeddings[0].values

async def store_memory(event: MemoryEvent) -> None:
    from db.connection import get_pool
    pool = await get_pool()
    if pool is None:
        return
    # Compute embedding from content (not from event.embedding which may be None)
    embedding = await embed(event.content)
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO memories (id, session_id, turn_number, role, content, event_type,
                                thematic_tags, significance, meaning_summary, embedding, created_at,
                                usage_count, last_retrieved_turn, explanatory_power)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        """, event.id, event.session_id, event.turn_number,
            event.role, event.content, event.event_type,
            event.thematic_tags, event.significance,
            event.meaning_summary, embedding,
            event.created_at,
            event.usage_count, event.last_retrieved_turn, event.explanatory_power)

async def retrieve_similar(
    query: str,
    session_id: str,
    limit: int = 5,
    threshold: float = 0.65,
    recency_weight: float = 0.2,
    significance_weight: float = 0.2
) -> List[MemoryEvent]:
    from db.connection import get_pool
    pool = await get_pool()
    if pool is None:
        return []
        # Guard: empty or whitespace-only queries cannot be embedded
    if not query or not query.strip():
        return []
    
    query_emb = await embed(query)
    max_turn = await pool.fetchval(
        "SELECT COALESCE(MAX(turn_number),0) FROM memories WHERE session_id=$1", session_id
    ) or 1
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, session_id, turn_number, role, content, event_type,
                   thematic_tags, significance, meaning_summary, created_at,usage_count, last_retrieved_turn, explanatory_power ,
                   1 - (embedding <=> $1) AS similarity
            FROM memories
            WHERE session_id = $2
              AND 1 - (embedding <=> $1) > $3
            ORDER BY similarity DESC
            LIMIT $4
            """, query_emb, session_id, threshold, limit*2)
    scored = []
    for r in rows:
        similarity = r["similarity"]
        recency_norm = (max_turn - r["turn_number"]) / max_turn
        recency_score = 1 - recency_norm
        significance = r["significance"]
        final_score = (similarity * (1 - recency_weight - significance_weight) +
                       recency_score * recency_weight +
                       significance * significance_weight)
        scored.append((final_score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]
    results = []
    for _, r in top:
        emb_value = r.get("embedding")

        results.append(MemoryEvent(
            id=r["id"], session_id=r["session_id"], turn_number=r["turn_number"],
            role=r["role"], content=r["content"], event_type=r["event_type"],
            thematic_tags=r["thematic_tags"], significance=r["significance"],
            meaning_summary=r["meaning_summary"], created_at=r["created_at"],
            embedding=emb_value   # will be None if not present
        ))
    return results

# Inside engine/memory.py, add or replace retrieve_candidates:

async def retrieve_candidates(
    query: str,
    session_id: str,
    limit: int = 25,
    similarity_threshold: float = 0.6
) -> List[MemoryEvent]:
    """
    Retrieve memory candidates for workspace competition.
    Uses pgvector cosine similarity, returns up to `limit` results.
    """
    from db.connection import get_pool
    pool = await get_pool()
    if pool is None:
        return []
    query_embedding = await embed(query)

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, session_id, turn_number, role, content, event_type,
                   thematic_tags, significance, meaning_summary, embedding,
                   created_at, usage_count, last_retrieved_turn, explanatory_power,
                   1 - (embedding <=> $1) AS similarity
            FROM memories
            WHERE session_id = $2 AND embedding IS NOT NULL
              AND 1 - (embedding <=> $1) > $3
            ORDER BY similarity DESC
            LIMIT $4
            """, query_embedding, session_id, similarity_threshold, limit)
    memories = []
    for row in rows:
        embedding_value = row["embedding"]

        mem = MemoryEvent(
            id=row["id"],
            session_id=row["session_id"],
            turn_number=row["turn_number"],
            role=row["role"],
            content=row["content"],
            event_type=row["event_type"],
            thematic_tags=row["thematic_tags"],
            significance=row["significance"],
            meaning_summary=row["meaning_summary"],
            embedding=embedding_value,  # now a list or None
            created_at=row["created_at"],
            usage_count=row.get("usage_count", 0),
            last_retrieved_turn=row.get("last_retrieved_turn", 0),
            explanatory_power=row.get("explanatory_power", 0.5),
        )
        memories.append(mem)
    return memories

async def increment_memory_usage(memory_ids: List[str], current_turn: int) -> None:
    from db.connection import get_pool
    if not memory_ids:
        return
    pool = await get_pool()
    if pool is None:
        return
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE memories
            SET usage_count = usage_count + 1,
                last_retrieved_turn = $2,
                significance = LEAST(1.0, significance + 0.005)
            WHERE id = ANY($1::text[])
        """, memory_ids, current_turn)

async def retrieve_candidates_hybrid(
    query: str,
    session_id: str,
    current_turn: int,
    state_drives: Dict[str, float],
    limit: int = 35,
    vector_weight: float = 0.5,
    keyword_weight: float = 0.3,
    recency_weight: float = 0.2
) -> List[MemoryEvent]:
    """
    Executes a unified vector + BM25 keyword + recency candidate search.
    Returns up to `limit` candidates with computed scores.
    """
    if not query or not query.strip():
        return []    
    from db.connection import get_pool
    pool = await get_pool()
    if pool is None:
        return []

    query_embedding = await embed(query)

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, session_id, turn_number, role, content, event_type,
                   thematic_tags, significance, meaning_summary,
                   usage_count, last_retrieved_turn, explanatory_power, created_at,
                   (1 - (embedding <=> $1)) AS vector_similarity,
                   ts_rank_cd(text_search_vector, plainto_tsquery('english', $2)) AS keyword_score
            FROM memories
            WHERE session_id = $3 AND embedding IS NOT NULL
              AND (
                1 - (embedding <=> $1) > 0.3
                OR text_search_vector @@ plainto_tsquery('english', $2)
              )
            ORDER BY vector_similarity DESC
            LIMIT $4
        """, query_embedding, query, session_id, limit)

    candidates: List[MemoryEvent] = []

    for row in rows:
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
            embedding=None,
            created_at=row["created_at"],
            usage_count=row["usage_count"],
            last_retrieved_turn=row["last_retrieved_turn"],
            explanatory_power=row["explanatory_power"]
        )

        v_sim_raw = row["vector_similarity"]
        if isinstance(v_sim_raw, np.ndarray):
            v_sim = float(v_sim_raw.item())
        else:
            v_sim = float(v_sim_raw or 0.0)
        v_sim = max(0.0, v_sim)
        k_score = min(1.0, (row["keyword_score"] or 0.0) / 10.0)

        turn_delta = max(0, current_turn - mem.turn_number)
        recency_score = math.exp(-0.015 * turn_delta)

        base_score = (
            (v_sim * vector_weight) +
            (k_score * keyword_weight) +
            (recency_score * recency_weight)
        )

        drive_boost = 0.0
        if state_drives.get("curiosity", 0.0) > 0.7 and mem.usage_count == 0:
            drive_boost += 0.15
        if state_drives.get("completion", 0.0) > 0.7 and mem.event_type in ("open_thread", "tension"):
            drive_boost += 0.20

        mem.computed_score = base_score + drive_boost
        candidates.append(mem)

    candidates.sort(key=lambda x: x.computed_score, reverse=True)
    return candidates



async def ensure_memories_table():
    """Table already created manually – do nothing."""
    pass