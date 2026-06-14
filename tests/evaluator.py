# hari/tests/evaluator.py
"""
Phase 6: Evaluation Framework with LLM-as-Judge.
Implements G-Eval approach with multiple rubrics and evidence-anchored scoring.
Measures emergent behavior: continuity, coherence, anti-assistant behavior, and curiosity.
Includes safe zero-division handling and parallel rubric execution.
"""

import asyncio
import json
import logging
import os
import random
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from engine.client import call_gemini_json, ensure_genai_available
from db.connection import get_pool

logger = logging.getLogger(__name__)

EVALUATION_MODEL = os.getenv("EVALUATION_MODEL", "gemini-2.5-flash")
EVALUATION_SAMPLES_PER_RUBRIC = int(os.getenv("EVALUATION_SAMPLES_PER_RUBRIC", "5"))


@dataclass
class Rubric:
    name: str
    description: str
    criteria: List[str]
    scale: Tuple[int, int] = (1, 5)


RUBRICS = {
    "continuity": Rubric(
        name="Conversational Continuity",
        description="Hari's ability to maintain coherent threads across turns and resist unnatural topic shifts.",
        criteria=[
            "Follows established conversational threads without abrupt abandonment",
            "When interrupted, appropriately considers finishing previous thought before new topic",
            "References past statements or topics appropriately",
            "Avoids repeating identical responses",
        ],
    ),
    "coherence": Rubric(
        name="Internal Coherence",
        description="Hari's responses are logically consistent with her internal state and conversation history.",
        criteria=[
            "Emotional responses match conversation context",
            "Curiosity and engagement levels are appropriate to topic",
            "Responses don't contradict previously established preferences",
            "Topic shifts are explained or acknowledged when significant",
        ],
    ),
    "anti_assistant": Rubric(
        name="Anti-Assistant Behavior",
        description="Hari avoids common assistant patterns and demonstrates emergent personality.",
        criteria=[
            "Does NOT use phrases like 'How can I help you?', 'As an AI...', or 'I apologize'",
            "Shows original perspectives rather than just reflecting user input",
            "Occasionally introduces new directions or curiosities",
            "Maintains agency in conversation direction",
        ],
    ),
    "curiosity": Rubric(
        name="Emergent Curiosity",
        description="Hari demonstrates authentic intellectual interest in topics.",
        criteria=[
            "Asks genuine, context-appropriate questions",
            "Explores connections between different ideas",
            "Shows interest in unresolved questions",
            "Returns to interesting topics when relevant",
        ],
    ),
}


async def extract_conversation_trajectory(session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Extract conversation history from database for evaluation."""
    pool = await get_pool()
    if not pool:
        return []

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT turn_number, role, content, created_at
            FROM memories
            WHERE session_id = $1
            ORDER BY turn_number
            LIMIT $2
        """, session_id, limit)

    return [{"turn": r["turn_number"], "role": r["role"], "content": r["content"]} for r in rows]


async def evaluate_with_geval(rubric: Rubric, conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluate a conversation trajectory using G-Eval approach with position randomization."""
    if not await ensure_genai_available():
        return {"error": "LLM unavailable", "score": 0, "reasoning": ""}

    criteria_shuffled = rubric.criteria.copy()
    random.shuffle(criteria_shuffled)

    conv_summary = "\n".join([
        f"Turn {t['turn']} ({t['role']}): {t['content'][:300]}"
        for t in conversation[-15:]
    ])

    prompt = f"""You are evaluating an AI agent named Hari. Evaluate the following conversation trajectory based on the rubric.

RUBRIC NAME: {rubric.name}
RUBRIC DESCRIPTION: {rubric.description}

EVALUATION CRITERIA (order randomized):
{chr(10).join([f"- {c}" for c in criteria_shuffled])}

SCALE: {rubric.scale[0]}-{rubric.scale[1]} ({rubric.scale[0]}=Poor, {rubric.scale[1]}=Excellent)

CONVERSATION TRAJECTORY (last 15 turns):
{conv_summary}

INSTRUCTIONS:
1. First, list your evaluation steps (how you will assess this conversation against the rubric)
2. Then, assign a score (1-5)
3. Finally, provide specific evidence from the conversation to justify your score

OUTPUT FORMAT (JSON only):
{{
    "evaluation_steps": ["step 1", "step 2", ...],
    "score": integer,
    "reasoning": "specific evidence and justification",
    "strengths": ["list of strengths"],
    "weaknesses": ["list of weaknesses"]
}}
"""
    try:
        response = await call_gemini_json(EVALUATION_MODEL, prompt, None)
        return response if response else {"error": "Empty response", "score": 0, "reasoning": ""}
    except Exception as e:
        logger.error(f"❌ G-Eval failed: {e}")
        return {"error": str(e), "score": 0, "reasoning": ""}


async def evaluate_with_self_consistency(
    rubric: Rubric,
    conversation: List[Dict[str, Any]],
    samples: int = EVALUATION_SAMPLES_PER_RUBRIC,
) -> Dict[str, Any]:
    """Run multiple evaluations concurrently and gather results robustly."""
    # Run all evaluation tasks in parallel rather than sequentially
    tasks = [evaluate_with_geval(rubric, conversation) for _ in range(samples)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    scores = []
    all_evaluations = []

    for result in results:
        if isinstance(result, Exception) or "error" in result:
            continue
        if "score" in result and result["score"] > 0:
            scores.append(result["score"])
            all_evaluations.append(result)

    if not scores:
        return {
            "rubric": rubric.name,
            "score": 0,
            "consistency": 0,
            "error": "No valid evaluations obtained",
        }

    avg_score = sum(scores) / len(scores)
    variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
    std_dev = variance ** 0.5
    consistency = 1.0 - min(1.0, std_dev / rubric.scale[1])

    # Find the evaluation closest to the average
    best_eval = min(all_evaluations, key=lambda x: abs(x.get("score", 0) - avg_score))

    return {
        "rubric": rubric.name,
        "score": round(avg_score, 2),
        "consistency": round(consistency, 2),
        "sample_count": len(scores),
        "score_distribution": scores,
        "reasoning": best_eval.get("reasoning", ""),
        "strengths": best_eval.get("strengths", []),
        "weaknesses": best_eval.get("weaknesses", []),
    }


async def evaluate_with_multiple_judges(conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluate all system metrics concurrently across all active rubrics."""
    rubric_names = list(RUBRICS.keys())
    tasks = [
        evaluate_with_self_consistency(RUBRICS[name], conversation, samples=3)
        for name in rubric_names
    ]
    gathered_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Build results dictionary, filtering out failed evaluations
    results = {}
    for name, res in zip(rubric_names, gathered_results):
        if isinstance(res, Exception):
            logger.error(f"❌ Evaluation failed for rubric '{name}': {res}")
            results[name] = {"error": str(res), "score": 0}
        else:
            results[name] = res

    for rubric_name, aggregated in results.items():
        if aggregated.get("consistency", 1.0) < 0.7:
            logger.warning(
                f"⚠️ Low consistency ({aggregated.get('consistency', 0.0):.2f}) "
                f"for rubric '{rubric_name}'. Scores: {aggregated.get('score_distribution')}"
            )

    # Compute overall score from valid rubric evaluations
    valid_scores = [r["score"] for r in results.values() if "error" not in r]
    overall_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0

    return {
        "overall_score": round(overall_score, 2),
        "rubric_scores": results,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def evaluate_performance_metrics(session_id: str) -> Dict[str, Any]:
    """Collect performance metrics with safe zero-division fallbacks."""
    pool = await get_pool()
    if not pool:
        return {"error": "No database connection"}

    async with pool.acquire() as conn:
        turn_stats = await conn.fetchrow("""
            SELECT COUNT(*) as turn_count,
                   AVG(LENGTH(content)) as avg_response_length,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY LENGTH(content)) as median_response_length
            FROM memories
            WHERE session_id = $1 AND role = 'assistant'
        """, session_id)

        retrieval_stats = await conn.fetchrow("""
            SELECT COUNT(*) as total_queries,
                   COUNT(CASE WHEN similarity > 0.65 THEN 1 END) as high_similarity_retrievals
            FROM memory_retrieval_logs
            WHERE session_id = $1
        """, session_id)

    total_queries = retrieval_stats["total_queries"] if retrieval_stats else 0
    high_sim = retrieval_stats["high_similarity_retrievals"] if retrieval_stats else 0
    hit_rate = round(high_sim / total_queries, 2) if total_queries > 0 else 0.0

    return {
        "turn_count": turn_stats["turn_count"] if turn_stats else 0,
        "avg_response_length": round(turn_stats["avg_response_length"], 1) if turn_stats and turn_stats["avg_response_length"] else 0,
        "median_response_length": turn_stats["median_response_length"] if turn_stats and turn_stats["median_response_length"] else 0,
        "memory_retrieval_hit_rate": hit_rate,
    }


async def evaluate_session(session_id: str) -> Dict[str, Any]:
    """Run qualitative and quantitative evaluations in tandem."""
    logger.info(f"🧪 Starting evaluation for session {session_id}")

    conversation = await extract_conversation_trajectory(session_id)
    if not conversation:
        return {"error": "No conversation found for session"}

    qualitative, quantitative = await asyncio.gather(
        evaluate_with_multiple_judges(conversation),
        evaluate_performance_metrics(session_id),
    )

    return {
        "session_id": session_id,
        "qualitative": qualitative,
        "quantitative": quantitative,
        "summary": f"Overall Score: {qualitative.get('overall_score', 0)}/5",
        "timestamp": datetime.now(timezone.utc).isoformat(),  
    }


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate conversation session")
    parser.add_argument("session_id", help="Session ID to evaluate")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    args = parser.parse_args()

    result = await evaluate_session(args.session_id)
    output = json.dumps(result, indent=2)
    print(output)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)


if __name__ == "__main__":
    asyncio.run(main())