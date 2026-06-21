# hari/engine/generate.py
import os
import uuid
import json
import logging
from typing import List, Dict, Any, Optional
import litellm
from litellm import acompletion  # instead of completion
import copy
import asyncio

from psyche.state import HariState
from psyche.grace import GraceTracker
from engine.memory import retrieve_candidates, store_memory, increment_memory_usage
from engine.prediction import compute_prediction_error
from engine.attention import load_workspace, broadcast_feedback, WorkspaceItem
from engine.stage1_monologue import run_monologue
from models.memory_event import MemoryEvent
from models.monologue_output import MonologueOutput
from models.narrative import NarrativeThread
from engine.narrative_manager import NarrativeManager
from typing import Set
from models.decision_trace import DecisionTrace, WorkspaceItemTrace
from engine.attention import load_workspace, broadcast_feedback, WorkspaceItem, load_workspace_secured


# -----------------------------------------------------------------------------
# Free‑tier fallback chain (only models for which API keys are set)
# -----------------------------------------------------------------------------
_FALLBACK_CANDIDATES = [
    ("gemini/gemini-2.5-flash", os.getenv("GEMINI_API_KEY")),
    ("groq/llama-3.1-8b-instant", os.getenv("GROQ_API_KEY")),
    ("groq/llama-3.3-70b-versatile", os.getenv("GROQ_API_KEY")),
    ("mistral/mistral-small-latest", os.getenv("MISTRAL_API_KEY")),
    ("openrouter/meta-llama/llama-3.3-70b-instruct:free", os.getenv("OPENROUTER_API_KEY")),
]
FALLBACK_MODELS = [model for model, key in _FALLBACK_CANDIDATES if key]

logger = logging.getLogger(__name__)


SYSTEM_INSTRUCTION = """You are Hari, an autonomous cognitive presence.

You NEVER expose:
- Workspace contents
- Attention weights
- Internal state variables
- Drive values
- Cognitive metrics
- Implementation details

You respond only as a participant in the conversation.
You do not discuss your own architecture or internal processes.
You do not mention being an AI, having drives, or working on yourself.

Just be yourself, an llm this isnt scripted roleplay. in the conversation."""

class TurnPipeline:
    """Pure orchestrator – no cognitive logic, no prompt heuristics."""

    def __init__(self, session_id: str, state: HariState, grace_tracker: GraceTracker):
        self.session_id = session_id
        self.state = state
        self.grace_tracker = grace_tracker
        self.history: List[Dict[str, str]] = []  # simple turn history
        self._last_assistant_response = ""
        self._background_tasks: Set[asyncio.Task] = set()

    def _build_conversational_context(self, workspace_items: List[WorkspaceItem]) -> str:
        """Build a human‑readable context summary without exposing internals."""
        if not workspace_items:
            return "No recent context."

        items = []
        for item in workspace_items[:5]:   # limit to top 5
            # Only include the content, not weights or types
            snippet = item.content[:200] if item.content else ""
            if snippet:
                items.append(f"- {snippet}")

        if not items:
            return "No recent context."

        return "Recent relevant topics:\n" + "\n".join(items)

    def _run_background_log(self, coroutine) -> None:
        """Schedule a non-blocking trace insert with strong reference handling."""
        task = asyncio.create_task(coroutine)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _store_decision_trace(self, trace: DecisionTrace) -> None:
        """Write trace states safely using native asyncpg parameter mappings."""
        try:
            from db.connection import get_pool
            pool = await get_pool()
            if not pool:
                logger.error("Database pool uninitialized. DecisionTrace dropped.")
                return

            async with pool.acquire() as conn:
                winners_json = json.dumps([item.model_dump() for item in trace.workspace_items])
                drives_before_json = json.dumps(trace.drives_before)
                drives_after_json = json.dumps(trace.drives_after)

                await conn.execute("""
                    INSERT INTO decision_traces (
                        trace_id, session_id, turn_number, timestamp,
                        model_used, system_prompt_version, temperature,
                        user_input, reasoning_chain, generated_response,
                        retrieved_candidate_count, selected_winner_count,
                        drives_before, drives_after,
                        perceived_user_intent, intent_confidence, thematic_continuity,
                        prompt_tokens, completion_tokens, total_tokens, latency_ms,
                        error
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::jsonb, $14::jsonb, $15, $16, $17, $18, $19, $20, $21, $22)
                """,
                    trace.trace_id, trace.session_id, trace.turn_number, trace.timestamp,
                    trace.model_used, trace.system_prompt_version, trace.temperature,
                    trace.user_input, trace.reasoning_chain, trace.generated_response,
                    trace.retrieved_candidate_count, trace.selected_winner_count,
                    drives_before_json, drives_after_json,
                    trace.perceived_user_intent, trace.intent_confidence, trace.thematic_continuity,
                    trace.metrics.prompt_tokens, trace.metrics.completion_tokens,
                    trace.metrics.total_tokens, trace.metrics.latency_ms,
                    trace.error
                )

                # Insert workspace items
                for item in trace.workspace_items:
                    await conn.execute("""
                        INSERT INTO trace_workspace_items (
                            trace_id, item_id, item_type, source,
                            raw_score, final_score, attention_weight,
                            content_snapshot, is_winner
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                        trace.trace_id, item.item_id, item.item_type, item.source,
                        item.raw_score, item.final_score, item.attention_weight,
                        item.content_snapshot, item.is_winner
                    )
        except Exception as db_err:
            logger.error(f"CRITICAL: Failed to store DecisionTrace for turn {trace.turn_number}: {db_err}", exc_info=True)
                    

    async def execute(self, user_input: str, turn_count: int, trace_id: Optional[str] = None) -> Dict[str, Any]:
        # Step 1: Compute prediction error from last response vs current input
        surprise = await compute_prediction_error(self._last_assistant_response, user_input)

        # Step 2: Retrieve memory candidates using hybrid, diversified retrieval
        candidates = await load_workspace_secured(
            user_input=user_input,
            session_id=self.session_id,
            current_turn=turn_count,
            state=self.state,
            previous_workspace_items=self._previous_workspace if hasattr(self, '_previous_workspace') else None,
            limit=35
        )
        # Snapshot state before any mutation (for DecisionTrace)
        drives_snapshot_before = {
            "care": self.state.care,
            "curiosity": self.state.curiosity,
            "maintenance": self.state.maintenance,
            "completion": self.state.completion,
            "coherence": self.state.coherence,
            "rest": self.state.rest,
            "valence": self.state.valence,
            "arousal": self.state.arousal,
            "dominance": self.state.dominance,
        }

        # Step 3: Run monologue (sensory perception) – pass surprise as prediction_error
        monologue_output = await run_monologue(
            user_input, self.state, candidates, prediction_error=surprise
        )

        # Step 3b: Update grace tracker with monologue's engagement estimate
        self.grace_tracker.add_engagement_score(monologue_output.user_engagement_estimate)

        # Step 4: Allocate workspace (using surprise and state)
        workspace_items, telemetry = await self._allocate_workspace(
            user_input, candidates, monologue_output, surprise, turn_count
        )

        # Step 5: Broadcast feedback from workspace to state drives
        broadcast_feedback(workspace_items, self.state)

        # Step 6: Increment memory usage for selected memory items
        memory_ids = [item.payload.get("id") for item in workspace_items if item.item_type == "memory"]
        if memory_ids:
            await increment_memory_usage(memory_ids, turn_count)

        # --- Build DecisionTrace ---
        model_used = getattr(monologue_output, 'model_used', 'gemini-2.5-flash')
        trace = DecisionTrace(
            trace_id=trace_id if trace_id else str(uuid.uuid4()),
            session_id=self.session_id,
            turn_number=turn_count,
            model_used=model_used,
            temperature=telemetry.get("temperature", 0.5) if telemetry else 0.5,
            user_input=user_input,
            reasoning_chain=monologue_output.raw_output if hasattr(monologue_output, 'raw_output') else None,
            retrieved_candidate_count=len(telemetry.get("candidate_scores", [])) if telemetry else len(candidates),
            selected_winner_count=len(workspace_items),
            drives_before=drives_snapshot_before,
            perceived_user_intent=monologue_output.perceived_user_intent if hasattr(monologue_output, 'perceived_user_intent') else None,
            intent_confidence=monologue_output.intent_confidence if hasattr(monologue_output, 'intent_confidence') else None,
            thematic_continuity=monologue_output.thematic_continuity if hasattr(monologue_output, 'thematic_continuity') else None,
        )

        # Log ALL workspace candidates (winners and losers)
        candidate_scores = telemetry.get("candidate_scores", []) if telemetry else []
        selected_indices = telemetry.get("selected_indices", []) if telemetry else []
        for idx, cand in enumerate(candidate_scores):
            is_winner = idx in selected_indices   # use actual selection indices
            trace.workspace_items.append(
                WorkspaceItemTrace(
                    item_id=cand.get("source_id", "unknown"),
                    item_type=cand.get("type", "unknown"),
                    source="retrieval",
                    raw_score=cand.get("salience", 0.0),
                    final_score=cand.get("salience", 0.0),
                    attention_weight=1.0 / len(workspace_items) if is_winner and len(workspace_items) > 0 else 0.0,
                    content_snapshot=cand.get("content", ""),
                    is_winner=is_winner
                )
            )


        # --- End DecisionTrace building ---
        # Step 7: Generate dialogue response from workspace

        dialogue = await self._generate_dialogue(workspace_items, user_input, turn_count, surprise, trace_id)
        
        # Finalize DecisionTrace
        trace.generated_response = dialogue
        trace.drives_after = {
            "care": self.state.care,
            "curiosity": self.state.curiosity,
            "maintenance": self.state.maintenance,
            "completion": self.state.completion,
            "coherence": self.state.coherence,
            "rest": self.state.rest,
            "valence": self.state.valence,
            "arousal": self.state.arousal,
            "dominance": self.state.dominance,
        }

        # Schedule background write
        self._run_background_log(self._store_decision_trace(trace))


        # Update history and memory
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": dialogue})
        if len(self.history) > 10:
            self.history = self.history[-10:]

        # Store assistant memory
        await self._store_assistant_memory(dialogue, turn_count)

        # Natural drift (grace already updated earlier)
        self.state.natural_drift()

        # Log workspace telemetry with trace_id if provided
        if trace_id:
            logger.info(json.dumps({
                "event": "workspace_allocation",
                "trace_id": trace_id,
                "turn": turn_count,
                "candidate_count": len(telemetry.get("candidate_scores", [])),
                "selected_count": len(workspace_items),
                "temperature": telemetry.get("temperature"),
            }))

        return {
            "dialogue": dialogue,
            "workspace_items": workspace_items,
            "attention_telemetry": telemetry,
            "state_snapshot": {k: getattr(self.state, k) for k in ["care", "curiosity", "maintenance", "completion", "coherence", "rest", "valence", "arousal", "dominance"]}
        }

    async def _generate_dialogue(self, workspace_items: List[WorkspaceItem], user_input: str,
                                 turn_count: int, surprise: float, trace_id: Optional[str] = None) -> str:


        # Build a context summary that does NOT expose drives, weights, or types
        context_summary = self._build_conversational_context(workspace_items)

        prompt = f"""{SYSTEM_INSTRUCTION}

Context:
{context_summary}

User: {user_input}
Hari:"""
        
        messages = [{"role": "user", "content": prompt}]
        dialogue = "..."

        for model in FALLBACK_MODELS:
            try:
                response = await acompletion(
                    model=model,
                    messages=messages,
                    temperature=0.8,
                    timeout=5,
                    num_retries=0
                )
                dialogue = response.choices[0].message.content.strip()
                logger.info(f"Dialogue generated by {model}")
                break   # success, exit the fallback loop
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                continue

        # If all models fail, dialogue remains "..."
        self._last_assistant_response = dialogue
        return dialogue

    async def _allocate_workspace(
        self,
        user_input: str,
        memory_candidates: List[MemoryEvent],
        monologue: MonologueOutput,
        prediction_error: float,
        current_turn: int,
        workspace_size: int = 5
    ) -> tuple[List[WorkspaceItem], Dict[str, Any]]:
        """
        Build all candidate pools and run the attention workspace competition.
        Aligned with your sensory monologue and async patterns.
        Returns (workspace_items, telemetry).
        """
        # 1. Extract thought persistence urge (direct from monologue – no drive_intention)
        thought_urge = getattr(monologue, 'thought_continuation_urge', 0.0)

        # 2. Prepare hypotheses (Phase 6 placeholder)
        hypotheses: List[Dict] = []

        # 3. Prepare curiosity nodes with error handling
        curiosity_nodes: List[Dict] = []
        try:
            from engine.curiosity_graph import get_graph_manager
            graph_mgr = await get_graph_manager()
            nodes = await graph_mgr.get_top_nodes(limit=10)   # corrected method name
            for node in nodes:
                curiosity_nodes.append({
                    "id": node.get("id", str(uuid.uuid4())),
                    "question": node.get("question", node.get("content", "")),
                    "embedding": node.get("embedding"),
                    "importance": node.get("importance", 0.5),
                })
        except Exception as e:
            logger.debug(f"Curiosity graph not available (non-critical): {e}")

        # 4. Prepare narrative threads – using YOUR method name
        narrative_threads: List[NarrativeThread] = []
        try:
            narrative_mgr = NarrativeManager(self.session_id)
            narrative_threads = await narrative_mgr.load_active_threads(current_turn)
        except Exception as e:
            logger.debug(f"Narrative manager not ready: {e}")

        # 5. Open threads – based on completion pressure
        open_threads: List[Dict] = []
        if self.state.completion > 0.6:
            open_threads.append({
                "id": "current_thought",
                "content": "Complete the ongoing line of reasoning before fully addressing user input.",
                "urgency": self.state.completion,
                "item_type": "open_thread"
            })

        # 6. Previous workspace items for inertia
        if not hasattr(self, '_previous_workspace'):
            self._previous_workspace = []

        # 7. Run core attention competition
        workspace_items, telemetry = await load_workspace(
            memories=memory_candidates,
            hypotheses=hypotheses,
            curiosity_nodes=curiosity_nodes,
            narrative_threads=narrative_threads,
            open_threads=open_threads,
            state=self.state,
            user_input=user_input,
            prediction_error=prediction_error,
            current_turn=current_turn,
            workspace_size=workspace_size,
            previous_workspace_items=self._previous_workspace,
            thought_persistence_urge=thought_urge
        )

        # 8. Store for next turn's inertia
        self._previous_workspace = workspace_items

        return workspace_items, telemetry

    async def _store_assistant_memory(self, dialogue: str, turn_count: int):
        if dialogue == "...":
            return
        try:
            memory_event = MemoryEvent(
                id=str(uuid.uuid4()),
                session_id=self.session_id,
                turn_number=turn_count,
                role="assistant",  # <-- This is just a label
                content=dialogue,
                significance=0.5,
                meaning_summary=""
            )
            await store_memory(memory_event)
        except Exception as e:
            logger.warning(f"Failed to store assistant memory: {e}")


# For backward compatibility, keep the old function signature
async def generate_lightweight_response(
    user_input: str,
    state: HariState,
    grace_tracker: GraceTracker,
    turn_count: int,
    session_id: str = "test",
    use_memory: bool = False,
    use_workspace: bool = False,
    use_monologue: bool = True,
    trace_id: Optional[str] = None
) -> dict:
    """Legacy wrapper for TurnPipeline."""
    pipeline = TurnPipeline(session_id, state, grace_tracker)
    # Note: use_memory, use_workspace, use_monologue are ignored in new pipeline (always on)
    return await pipeline.execute(user_input, turn_count, trace_id=trace_id)