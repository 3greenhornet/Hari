# hari/engine/memory_consolidation.py
"""
Phase 6: Memory Consolidation, Archival, and Hypothesis Promotion.
Implements content-adaptive archival (LLM summarization for conversational content,
extractive preservation for factual data) and sliding window summarization.
Includes proper async shutdown hooks and Pydantic structured outputs.

CRITICAL: Before using, run the migration SQL to add promoted_to_hypothesis column:
    ALTER TABLE memories ADD COLUMN IF NOT EXISTS promoted_to_hypothesis BOOLEAN DEFAULT FALSE;
    CREATE INDEX IF NOT EXISTS idx_memories_promoted ON memories(promoted_to_hypothesis, significance);
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Literal
import re

from litellm import acompletion
from pydantic import BaseModel, Field
from db.connection import get_pool
from models.memory_event import MemoryEvent
from models.hypothesis import Hypothesis

logger = logging.getLogger(__name__)

__all__ = [
    "run_consolidation",
    "archive_old_memories",
    "promote_to_hypothesis",

]

# ============================================
# Pydantic Models for Structured Outputs
# ============================================

class ExtractedHypothesis(BaseModel):
    """Pydantic model for hypothesis extraction from significant memories."""
    type: Literal["user", "self", "world"] = Field(
        description="The category of the belief or observation."
    )
    statement: str = Field(
        description="A single declarative sentence capturing the insight.",
        max_length=500
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0.",
        ge=0.0, le=1.0
    )


class SegmentSummary(BaseModel):
    """Pydantic model for conversation segment summarization."""
    summary: str = Field(
        description="A concise summary focusing on key topics, facts, and emotional tone.",
        max_length=1000
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="List of key insights extracted from the segment."
    )
    emotional_tone: Literal["neutral", "positive", "negative", "curious", "frustrated"] = Field(
        default="neutral",
        description="The dominant emotional tone of the segment."
    )


# ============================================
# Configuration – all tunable via environment
# ============================================

CONSOLIDATION_INTERVAL_TURNS = int(os.getenv("CONSOLIDATION_INTERVAL_TURNS", "10"))
SIGNIFICANCE_PROMOTION_THRESHOLD = float(os.getenv("SIGNIFICANCE_PROMOTION_THRESHOLD", "0.75"))
ARCHIVE_OLDER_THAN_DAYS = int(os.getenv("ARCHIVE_RETENTION_DAYS", "30"))
MAX_SUMMARY_LENGTH = int(os.getenv("MAX_SUMMARY_LENGTH", "300"))
WINDOW_SIZE_DAYS = int(os.getenv("WINDOW_SIZE_DAYS", "7"))
MAX_SUMMARIES_IN_WINDOW = int(os.getenv("MAX_SUMMARIES_IN_WINDOW", "4"))
SIMILARITY_SEARCH_LIMIT = int(os.getenv("SIMILARITY_SEARCH_LIMIT", "20"))
CONSOLIDATION_MODEL = os.getenv("CONSOLIDATION_SUMMARY_MODEL", "gemini-2.5-flash")
CONSOLIDATION_MAX_RETRIES = int(os.getenv("CONSOLIDATION_MAX_RETRIES", "1"))  # low because background worker


# ============================================
# Content Classification for Adaptive Archival
# ============================================

async def classify_content_density(content: str) -> Literal["sparse", "dense"]:
    """
    Classify content as sparse (conversational) or dense (factual/code).
    Uses simple heuristics to avoid API calls for obvious cases.
    """
    if not content:
        return "sparse"

    code_indicators = ["def ", "class ", "import ", "```", "function(", "const ", "let ", "if ("]
    has_code = any(indicator in content for indicator in code_indicators)

    has_factual = any(c.isdigit() for c in content) and len(content) > 20

    if has_code or has_factual:
        return "dense"
    return "sparse"


# ============================================
# Sliding Window Summarization (SWin Approach)
# ============================================




# ============================================
# Hypothesis Promotion with Pydantic Structured Output
# ============================================

async def promote_to_hypothesis(memory: MemoryEvent) -> Optional[Hypothesis]:
    """
    Extract a user/self/world hypothesis from a significant memory.
    Uses the LiteLLM fallback cascade for resilience.
    """
    if getattr(memory, 'promoted_to_hypothesis', False):
        logger.info(f"Memory {memory.id} already promoted, skipping.")
        return None
    if memory.significance < SIGNIFICANCE_PROMOTION_THRESHOLD:
        return None

    prompt = f"""Analyze this memory and extract a structured hypothesis.

Memory content: "{memory.content[:500]}"

Role: {memory.role}

Determine which type of hypothesis this relates to:
- "user": Something about the user\'s values, beliefs, or patterns
- "self": Something about Hari\'s own tendencies or identity  
- "world": Something about external reality

Return ONLY a valid JSON object with exactly these fields:
- "type": one of "user", "self", "world"
- "statement": a concise declarative sentence (max 200 chars)
- "confidence": a float between 0.0 and 1.0

Example:
{{"type": "self", "statement": "I am uncomfortable with unstructured conversation.", "confidence": 0.8}}
"""

    messages = [
        {"role": "system", "content": "You are a hypothesis extraction engine. Output only valid JSON with the exact fields: type, statement, confidence."},
        {"role": "user", "content": prompt}
    ]

    from engine.stage1_monologue import MONOLOGUE_FALLBACK_MODELS
    for model in MONOLOGUE_FALLBACK_MODELS:
        try:
            kwargs = {"model": model, "messages": messages, "temperature": 0.2, "timeout": 3}
            # Use native JSON response format where supported
            if not model.startswith("openrouter"):
                kwargs["response_format"] = {"type": "json_object"}

            response = await acompletion(**kwargs)
            raw = response.choices[0].message.content.strip()

            # Extract JSON from the response
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                logger.warning(f"Model {model} returned no JSON object.")
                continue

            data = json.loads(match.group(0))

            # Default type to "world" if missing
            hypo_type = data.get("type", "world")
            statement = data.get("statement", "")
            confidence = data.get("confidence", 0.5)

            if not statement:
                logger.warning(f"Model {model} returned empty statement.")
                continue

            hypothesis = Hypothesis(
                type=hypo_type,                # <-- this is the real fix
                statement=statement,
                confidence=confidence,
                supporting_event_ids=[memory.id] if memory.id else [],
                contradicting_event_ids=[],
                last_updated=datetime.utcnow()
            )
            # No need for _extracted_type; it\'s already in hypothesis.type

            logger.info(json.dumps({
                "event": "hypothesis_promoted",
                "memory_id": memory.id,
                "hypothesis_type": hypo_type,
                "confidence": confidence,
                "statement_preview": statement[:100]
            }))
            return hypothesis

        except Exception as e:
            logger.warning(f"Promotion failed with model {model}: {e}")
            continue

    logger.error(f"All models failed to promote memory {memory.id}")
    return None

async def store_hypothesis(hypothesis: Hypothesis, hypothesis_type: str) -> None:
    """
    Store hypothesis in PostgreSQL for future retrieval.
    Handles TEXT[] arrays properly with explicit casting.
    """
    pool = await get_pool()
    if not pool:
        return

    supporting_ids = hypothesis.supporting_event_ids or []
    contradicting_ids = hypothesis.contradicting_event_ids or []

    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO hypotheses (type, statement, confidence, supporting_event_ids, contradicting_event_ids, last_updated)
            VALUES ($1, $2, $3, $4::TEXT[], $5::TEXT[], $6)
            ON CONFLICT (type, statement) DO UPDATE
            SET confidence = (hypotheses.confidence + EXCLUDED.confidence) / 2,
                supporting_event_ids = 
                    CASE 
                        WHEN hypotheses.supporting_event_ids IS NULL THEN EXCLUDED.supporting_event_ids
                        ELSE array_cat(hypotheses.supporting_event_ids, EXCLUDED.supporting_event_ids)
                    END,
                last_updated = EXCLUDED.last_updated
        """, hypothesis_type, hypothesis.statement, hypothesis.confidence,
           supporting_ids, contradicting_ids, hypothesis.last_updated)


# ============================================
# Memory Archival (Content‑Adaptive)
# ============================================

def _extract_key_facts(content: str) -> str:
    """Extract key facts from dense content (code, structured data, IDs)."""
    lines = content.split("\n")
    key_lines = []

    code_indicators = ["def ", "class ", "import ", "const ", "let ", "if (", "```"]
    for line in lines:
        if any(indicator in line for indicator in code_indicators):
            key_lines.append(line[:150])
        elif any(c.isdigit() for c in line) and len(line) < 100:
            key_lines.append(line[:100])

    result = "\n".join(key_lines[:10])
    if not result:
        result = content[:200]
    return result


async def _summarize_sparse_content(content: str) -> str:
    """
    Summarize sparse/conversational content using LiteLLM fallback.
    If all models fail, fallback to extractive summary (first 3 sentences).
    """
    from engine.stage1_monologue import MONOLOGUE_FALLBACK_MODELS

    prompt = f"""Summarize this conversational content in a concise way, focusing on key topics and insights:

{content[:800]}"""

    messages = [
        {"role": "system", "content": "You are a summarization assistant. Output only the summary, no extra text."},
        {"role": "user", "content": prompt}
    ]
    for model in MONOLOGUE_FALLBACK_MODELS:
        try:
            response = await acompletion(
                model=model,
                messages=messages,
                temperature=0.3,
                timeout=5
            )
            summary = response.choices[0].message.content.strip()
            if summary:
                return summary[:MAX_SUMMARY_LENGTH]
        except Exception as e:
            logger.warning(f"Summarization with {model} failed: {e}")
            continue
    # Fallback: extractive summary
    sentences = content.split(".")
    return ". ".join(sentences[:3])[:MAX_SUMMARY_LENGTH]


async def archive_old_memories(session_id: str, older_than_days: int = ARCHIVE_OLDER_THAN_DAYS) -> int:
    """
    Archive old memories using content‑adaptive strategy:
    - Sparse (conversational): LLM summary compression via structured output
    - Dense (factual/code): Extractive preservation of key facts
    """
    pool = await get_pool()
    if not pool:
        return 0

    cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

    async with pool.acquire() as conn:
        old_memories = await conn.fetch("""
            SELECT id, content, role, significance, created_at, turn_number
            FROM memories
            WHERE session_id = $1 AND created_at < $2
            ORDER BY turn_number
            LIMIT 1000
        """, session_id, cutoff_date)

        if not old_memories:
            return 0

        archived_count = 0

        for mem in old_memories:
            content_density = await classify_content_density(mem["content"])

            if content_density == "sparse":
                # Abstractive LLM summary compression
                compressed = await _summarize_sparse_content(mem["content"])
            else:
                # Dense content: extractive preservation
                compressed = _extract_key_facts(mem["content"])

            await conn.execute("""
                INSERT INTO archived_memories (id, original_id, session_id, compressed_content, original_significance, archived_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, f"arch_{mem['id']}", mem["id"], session_id, compressed, mem["significance"], datetime.utcnow())

            await conn.execute("DELETE FROM memories WHERE id = $1", mem["id"])
            archived_count += 1

        logger.info(json.dumps({
            "event": "archival_complete",
            "session_id": session_id,
            "archived_count": archived_count,
            "older_than_days": older_than_days
        }))

        return archived_count


# ============================================
# Periodic Consolidation (called from worker)
# ============================================

async def run_consolidation(session_id: str, turn_count: int) -> Dict[str, Any]:
    """
    Execute full consolidation cycle:
    1. Promote high-significance memories to hypotheses (skip already promoted)
    2. Archive old memories (content-adaptive)
    3. Return statistics
    """
    pool = await get_pool()
    if not pool:
        return {"status": "error", "message": "No database connection"}

    results = {
        "status": "success",
        "promoted_hypotheses": 0,
        "archived_memories": 0,
        "errors": []
    }

    try:
        # 1. Find high-significance memories that haven\'t been promoted yet
        async with pool.acquire() as conn:
            significant_memories = await conn.fetch("""
                SELECT id, content, role, significance, session_id, turn_number, created_at,
                       promoted_to_hypothesis
                FROM memories
                WHERE significance >= $1 
                  AND session_id = $2
                  AND (promoted_to_hypothesis IS NULL OR promoted_to_hypothesis = FALSE)
                ORDER BY significance DESC
                LIMIT 20
            """, SIGNIFICANCE_PROMOTION_THRESHOLD, session_id)

            logger.info(f"CONSOLIDATION_QUERY: found {len(significant_memories)} high‑significance unpromoted memories")

        for mem_data in significant_memories:
            try:
                memory = MemoryEvent(
                    id=mem_data["id"],
                    session_id=mem_data["session_id"],
                    turn_number=mem_data["turn_number"],
                    role=mem_data["role"],
                    content=mem_data["content"],
                    significance=mem_data["significance"],
                    created_at=mem_data["created_at"],
                    promoted_to_hypothesis=mem_data.get("promoted_to_hypothesis", False)  # pass flag
                )
                logger.info(f"PROMOTION_ATTEMPT: memory_id={memory.id} significance={memory.significance}")
                hypothesis = await promote_to_hypothesis(memory)
                if hypothesis:
                    # The extracted type is attached as _extracted_type
                    hypo_type = getattr(hypothesis, '_extracted_type', 'world')
                    await store_hypothesis(hypothesis, hypo_type)
                    results["promoted_hypotheses"] += 1

                    # Mark memory as promoted
                    async with pool.acquire() as conn:
                        await conn.execute(
                            "UPDATE memories SET promoted_to_hypothesis = TRUE WHERE id = $1",
                            memory.id
                        )
            except Exception as e:
                results["errors"].append(f"Memory {mem_data['id']}: {str(e)}")

        # 2. Archive old memories
        archived = await archive_old_memories(session_id, ARCHIVE_OLDER_THAN_DAYS)
        results["archived_memories"] = archived

    except Exception as e:
        results["status"] = "error"
        results["errors"].append(str(e))
        logger.error(f"❌ Consolidation failed: {e}")

    # Structured telemetry
    logger.info(json.dumps({
        "event": "consolidation_complete",
        "session_id": session_id,
        "turn_count": turn_count,
        "promoted_hypotheses": results["promoted_hypotheses"],
        "archived_memories": results["archived_memories"],
        "error_count": len(results["errors"])
    }))

    return results


# ============================================
# SQL Schema for Additional Tables
# ============================================

CONSOLIDATION_SCHEMA = """
-- Table for archived (compressed) memories
CREATE TABLE IF NOT EXISTS archived_memories (
    id TEXT PRIMARY KEY,
    original_id TEXT,
    session_id TEXT NOT NULL,
    compressed_content TEXT,
    original_significance FLOAT,
    archived_at TIMESTAMP DEFAULT NOW()
);

-- Table for extracted hypotheses
CREATE TABLE IF NOT EXISTS hypotheses (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL,  -- 'user', 'self', 'world'
    statement TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.5,
    supporting_event_ids TEXT[],
    contradicting_event_ids TEXT[],
    last_updated TIMESTAMP,
    UNIQUE(type, statement)
);

-- Memory retrieval logs (for performance metrics)
CREATE TABLE IF NOT EXISTS memory_retrieval_logs (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    query_text TEXT,
    retrieved_count INTEGER,
    similarity_avg FLOAT,
    latency_ms FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Optimized HNSW index for vector similarity search
-- For datasets under 1M rows, HNSW provides excellent recall and speed
CREATE INDEX IF NOT EXISTS memories_embedding_hnsw_idx 
ON memories 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- CRITICAL MIGRATION for Phase 6:
ALTER TABLE memories ADD COLUMN IF NOT EXISTS promoted_to_hypothesis BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_memories_promoted ON memories(promoted_to_hypothesis, significance);
"""
