# hari/engine/generate.py
import os
import uuid
import json
import logging
from typing import List, Dict, Any, Optional

from psyche.state import HariState
from psyche.grace import GraceTracker
from engine.memory import retrieve_candidates, store_memory, get_genai_client, increment_memory_usage
from engine.prediction import compute_prediction_error
from engine.attention import load_workspace, broadcast_feedback, WorkspaceItem
from engine.stage1_monologue import run_monologue
from models.memory_event import MemoryEvent
from models.monologue_output import MonologueOutput
from models.narrative import NarrativeThread
from engine.narrative_manager import NarrativeManager
from google.genai import types

logger = logging.getLogger(__name__)

STAGE2_MODEL = os.getenv("STAGE2_MODEL", "gemini-2.5-flash")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    from groq import Groq
    groq_client = Groq(api_key=GROQ_API_KEY)
    GROQ_FALLBACK_MODEL = "llama-3.1-8b-instant"
else:
    groq_client = None


class TurnPipeline:
    """Pure orchestrator – no cognitive logic, no prompt heuristics."""

    def __init__(self, session_id: str, state: HariState, grace_tracker: GraceTracker):
        self.session_id = session_id
        self.state = state
        self.grace_tracker = grace_tracker
        self.history: List[Dict[str, str]] = []  # simple turn history
        self._last_assistant_response = ""

    async def execute(self, user_input: str, turn_count: int, trace_id: Optional[str] = None) -> Dict[str, Any]:
        # Step 1: Compute prediction error from last response vs current input
        surprise = await compute_prediction_error(self._last_assistant_response, user_input)

        # Step 2: Retrieve memory candidates (limit 25, lower threshold)
        candidates = await retrieve_candidates(user_input, self.session_id, limit=25)

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

        # Step 7: Generate dialogue response from workspace
        dialogue = await self._generate_dialogue(workspace_items, user_input, turn_count, surprise, trace_id)

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
        workspace_text = "=== ACTIVE ATTENTION WORKSPACE ===\n"
        for item in workspace_items:
            workspace_text += f"- [{item.item_type}] (weight {item.attention_weight:.2f}): {item.content}\n"

        prompt = f"""You are Hari. Current state:
{self.state.to_prompt_context()}

{workspace_text}

Prediction error (surprise): {surprise:.3f}
Turn: {turn_count}

Rules: no apologies, no assistant talk.

User: {user_input}
Hari:"""
        try:
            client = get_genai_client()
            response = await client.aio.models.generate_content(
                model=STAGE2_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.8)
            )
            dialogue = response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini error: {e}")
            if groq_client:
                try:
                    completion = groq_client.chat.completions.create(
                        model=GROQ_FALLBACK_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.8
                    )
                    dialogue = completion.choices[0].message.content.strip()
                except Exception as e2:
                    logger.error(f"Groq fallback failed: {e2}")
                    dialogue = "..."
            else:
                dialogue = "..."
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
        memory_event = MemoryEvent(
            id=str(uuid.uuid4()),
            session_id=self.session_id,
            turn_number=turn_count,
            role="assistant",
            content=dialogue,
            significance=0.5,
            meaning_summary=""
        )
        await store_memory(memory_event)


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