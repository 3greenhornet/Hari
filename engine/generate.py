# hari/engine/generate.py
import os
import uuid
import json
import logging
from typing import List, Dict, Any, Optional
import litellm  # noqa
from litellm import acompletion
import copy
import asyncio
import hashlib
from datetime import datetime, timezone

from models.identity import IdentityModel
from engine.projection.identity_renderer import build_system_prompt_from_identity
from psyche.state import HariState
from psyche.grace import GraceTracker
from engine.memory import retrieve_candidates, store_memory, increment_memory_usage
from engine.prediction import compute_prediction_error
from engine.attention import load_workspace, broadcast_feedback, WorkspaceItem
from engine.stage1_monologue import run_monologue
from models.memory_event import MemoryEvent
from engine.generativity_estimator import get_estimator
from models.monologue_output import MonologueOutput
from models.narrative import NarrativeThread
from engine.narrative_manager import NarrativeManager
from typing import Set
from models.decision_trace import DecisionTrace, WorkspaceItemTrace
from engine.attention import load_workspace, broadcast_feedback, WorkspaceItem, load_workspace_secured
from engine.curiosity_graph import get_graph_manager
from engine.narrative_manager import NarrativeManager
from engine.self_belief import SelfBeliefManager
from engine.memory_consolidation import store_hypothesis
from models.hypothesis import Hypothesis
from engine.events import EventLogger
from engine.attention_config import DEFAULT_ATTENTION_CONFIG, AttentionCalibration
from engine.attention_instrumentation import AttentionInstrumentation
from engine.social_cognition import interpret_turn_and_update_state
from engine.volition_engine import VolitionEngine


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




class TurnPipeline:
    """Pure orchestrator – no cognitive logic, no prompt heuristics."""

    def __init__(self, session_id: str, state: HariState, grace_tracker: GraceTracker):
        self.session_id = session_id
        self.state = state
        self.grace_tracker = grace_tracker
        self.history: List[Dict[str, str]] = []  # simple turn history
        self._last_assistant_response = ""
        self._background_tasks: Set[asyncio.Task] = set()
        self._event_logger = EventLogger(session_id)
        self._event_logger.log_session_start()
        self.attention_config = AttentionCalibration.from_env()
        self.attention_instrumentation = AttentionInstrumentation(self.attention_config)
        # Ticket 011: Generativity Estimator
        self.generativity_estimator = get_estimator()
        self.identity_model = IdentityModel()
        self.volition_engine = VolitionEngine()
        
        from engine.relational_manager import RelationalManager
        self.relational_manager = RelationalManager(user_id=session_id)

        

    def _build_conversational_context(self, workspace_items: List[WorkspaceItem]) -> str:
        """
        TODO: Replace with a proper WorkspaceInterpreter module.
        
        Current implementation is a temporary mapping from item types to natural phrases.
        It improves on leaking internal object names but is still a heuristic.
        
        Future: The interpreter should synthesize the entire workspace into a coherent
        cognitive landscape, considering relationships between items, not just types.
        This function should eventually be extracted to a dedicated module without
        changing callers.
        """
        if not workspace_items:
            return "No active context."

        fragments = []

        # If minimal candidate won, override everything
        if any(item.item_type == "minimal" for item in workspace_items[:5]):
            return "DIRECTIVE: Respond with extreme brevity (1-3 words). Do not elaborate or ask questions."

        for item in workspace_items[:5]:
            snippet = item.content[:200] if item.content else ""
            if not snippet:
                continue
            
            # Abstract internal types into semantic cognitive states
            if item.item_type == "memory":
                state_type = "recall"
            elif item.item_type in ("hypothesis", "curiosity_node", "narrative_thread", "open_thought", "open_thread"):
                state_type = "active_thought"
            else:
                state_type = "context"
                
            fragments.append(f"[Weight: {item.attention_weight:.2f} | State: {state_type}] {snippet}")

        if not fragments:
            return "No active context."

        # Append recent exchanges as short‑term memory fallback
        recent = self.history[-6:] if hasattr(self, "history") and len(self.history) >= 2 else []
        if recent:
            exchanges = []
            for msg in recent:
                if msg["role"] == "user":
                    exchanges.append(f"User: {msg['content'][:100]}")
                else:
                    exchanges.append(f"Hari: {msg['content'][:100]}")
            fragments.append("Recent exchanges:\n" + "\n".join(exchanges))

        return "\n\n".join(fragments)



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
        self._event_logger.log_user_input(user_input)

        # Step 2: Retrieve memory candidates using hybrid, diversified retrieval
        candidates = await load_workspace_secured(
            user_input=user_input,
            session_id=self.session_id,
            current_turn=turn_count,
            state=self.state,
            previous_workspace_items=self._previous_workspace if hasattr(self, "_previous_workspace") else None,
            limit=35
        )
        self._event_logger.log_memory_retrieval(
            query=user_input,
            count=len(candidates)
        )

        # Ticket 014: Fetch active threads ONCE for trajectory context
        active_thread_context_str = None
        self._active_threads = []
        try:
            narrative_mgr = NarrativeManager(self.session_id)
            self._active_threads = await narrative_mgr.load_active_threads(turn_count, limit=1)
            if self._active_threads:
                thread = self._active_threads[0]
                questions = ", ".join(thread.open_questions) if thread.open_questions else "None"
                active_thread_context_str = (
                    f"Thread ID: {thread.id}\n"
                    f"Topic: {thread.title}\n"
                    f"Description: {thread.description}\n"
                    f"Open Questions: {questions}"
                )
        except Exception as e:
            logger.debug(f"Could not get active thread context: {e}")

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
        self._event_logger.log_state_snapshot(self.state)

        # Step 3: Run monologue with trajectory context
        monologue_output = await run_monologue(
            user_input,
            self.state,
            candidates,
            prediction_error=surprise,
            active_thread_context=active_thread_context_str,
        )
        logger.info(f"MONOLOGUE_RAW: {monologue_output.model_dump_json(indent=2)}")
        self._event_logger.log_monologue_output(monologue_output)

        # Ticket 015: Social interpretation synthesis
        try:
            await interpret_turn_and_update_state(
                user_input=user_input,
                state=self.state,
                monologue_output=monologue_output,
                recent_history=self.history,
                turn_count=turn_count,
                relational_manager=self.relational_manager if hasattr(self, 'relational_manager') else None
            )
        except Exception as e:
            logger.warning(f"Social interpretation failed: {e}")

        # Step 9a: Memory-specific Expand on Curiosity
        self._expand_hook_id = None
        self._ambiguous_hooks = None
        
        if monologue_output.perceived_user_intent == "curious" and hasattr(self, "_previous_workspace"):
            hooks = []
            for item in self._previous_workspace:
                if item.item_type == "memory" and item.payload.get("is_hook"):
                    hooks.append(item)
            
            if len(hooks) == 1:
                self._expand_hook_id = hooks[0].payload.get("hook_memory_id")
            elif len(hooks) > 1:
                self._ambiguous_hooks = hooks

        # Ticket 014: Wire trajectory deviation into state AND Workspace
        deviation = monologue_output.trajectory_deviation
        confidence = monologue_output.trajectory_confidence

        # 1. Continuous State Update (No hard thresholds)
        # Only update if confidence > 0.3 to prevent low-confidence noise
        # Continuous: no gate, just scale by deviation × confidence
        effective_signal = deviation * confidence

        if effective_signal > 0.01:
            self.state.update({
                "social_ambiguity": effective_signal * 0.3,
                "completion": effective_signal * 0.2,
                "cognitive_tension": effective_signal * 0.1
            }, source="MONOLOGUE", reason="trajectory_deviation")

        # 2. Workspace Candidate Injection (with threshold for admission)
        if deviation > 0.2 and confidence > 0.3:
            urgency = deviation * confidence
            thread_ref = monologue_output.referenced_thread_id or "active thread"
            self._trajectory_candidate = {
                "id": f"trajectory_{turn_count}",
                "content": f"Conversation trajectory deviated from thread: {thread_ref} (deviation: {deviation:.2f}, confidence: {confidence:.2f})",
                "urgency": urgency,
                "item_type": "open_thought"
            }
        else:
            self._trajectory_candidate = None

        if deviation > 0.3 and confidence > 0.4:
            logger.info(f"Trajectory deviation detected: {deviation:.2f} (confidence: {confidence:.2f})")

        if monologue_output.self_belief_update:
            await SelfBeliefManager.store(self.session_id, monologue_output.self_belief_update)

        # --- Store hypothesis update ---
        if monologue_output.hypothesis_update:
            try:
                # Temporary: use "world" as default type.
                # Future: Ticket 005A will implement proper classification
                # and emit structured HypothesisUpdate from monologue.
                hypothesis = Hypothesis(
                    type="world",
                    statement=monologue_output.hypothesis_update,
                    confidence=0.6,   # TODO: Derive from monologue in future
                    supporting_event_ids=[],
                    contradicting_event_ids=[],
                    last_updated=datetime.now(timezone.utc)
                )
                await store_hypothesis(hypothesis, "world")
                logger.debug(f"Stored hypothesis update: {monologue_output.hypothesis_update[:50]}...")
            except Exception as e:
                logger.warning(f"Failed to store hypothesis update: {e}")

        # Step 3b: Update grace tracker with monologue\"s engagement estimate
        self.grace_tracker.add_engagement_score(monologue_output.user_engagement_estimate)

        # ---- Volition: generate desires from state and get proactive candidates ----
        self.volition_engine.generate_desires_from_state(self.state)
        proactive_candidates = await self.volition_engine.get_proactive_candidates({})
        if proactive_candidates:
            logger.info(f"Volition injected {len(proactive_candidates)} proactive candidates")

        # Step 4: Allocate workspace (using surprise and state)
        workspace_items, telemetry = await self._allocate_workspace(
            user_input, candidates, monologue_output, surprise, turn_count, proactive_candidates=proactive_candidates
        )
        workspace_summary = []
        for item in workspace_items[:5]:
            workspace_summary.append({
                "type": getattr(item, "item_type", "unknown"),
                "content": getattr(item, "content", "")[:100]
            })
        self._event_logger.log_workspace_load(
            candidate_count=len(telemetry.get("candidate_scores", [])),
            winner_count=len(workspace_items),
            winners=[f"{item.item_type}: {item.content[:50]}" for item in workspace_items[:5]]
        )

        # --- Learn from workspace co‑activation ---
        try:
            graph_mgr = await get_graph_manager()
            await graph_mgr.observe_workspace(workspace_items)
        except Exception as e:
            logger.debug(f"Workspace observation failed (non‑critical): {e}")

        # Step 5: Broadcast feedback from workspace to state drives
        broadcast_feedback(workspace_items, self.state)

        # Step 6: Increment memory usage for selected memory items
        memory_ids = [item.payload.get("id") for item in workspace_items if item.item_type == "memory"]
        if memory_ids:
            await increment_memory_usage(memory_ids, turn_count)

        # --- Build DecisionTrace ---
        model_used = getattr(monologue_output, "model_used", "gemini-2.5-flash")
        trace = DecisionTrace(
            trace_id=trace_id if trace_id else str(uuid.uuid4()),
            session_id=self.session_id,
            turn_number=turn_count,
            model_used=model_used,
            temperature=telemetry.get("temperature", 0.5) if telemetry else 0.5,
            user_input=user_input,
            reasoning_chain=monologue_output.raw_output if hasattr(monologue_output, "raw_output") else None,
            retrieved_candidate_count=len(telemetry.get("candidate_scores", [])),
            selected_winner_count=len(workspace_items),
            drives_before=drives_snapshot_before,
            perceived_user_intent=monologue_output.perceived_user_intent if hasattr(monologue_output, "perceived_user_intent") else None,
            intent_confidence=monologue_output.intent_confidence if hasattr(monologue_output, "intent_confidence") else None,
            thematic_continuity=monologue_output.thematic_continuity if hasattr(monologue_output, "thematic_continuity") else None,
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
        self._event_logger.log_assistant_response(dialogue, workspace_summary)
        
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
        self._event_logger.log_decision_trace(trace_id)


        # Update history and memory
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": dialogue})
        if len(self.history) > 10:
            self.history = self.history[-10:]

        # Store assistant memory
                # Store assistant memory with monologue\"s significance
        await self._store_assistant_memory(dialogue, turn_count, significance_override=monologue_output.memory_significance)
        # --- Wire curiosity trigger ---
        if monologue_output.curiosity_trigger:
            try:
                graph_mgr = await get_graph_manager()
                result = await graph_mgr.add_node(
                    question=monologue_output.curiosity_trigger,
                    importance=0.6,
                    session_id=self.session_id,
                    origin_trace_id=trace_id or str(uuid.uuid4())
                )
                logger.debug(f"Curiosity node {result}: {monologue_output.curiosity_trigger[:50]}...")
            except Exception as e:
                logger.warning(f"Failed to add curiosity node: {e}")

        # --- Wire narrative thread creation ---
        if (monologue_output.curiosity_trigger and
            len(monologue_output.curiosity_trigger) > 20 and
            monologue_output.thematic_continuity is not None and
            monologue_output.thematic_continuity > 0.7):
            try:
                narrative_mgr = NarrativeManager(self.session_id)
                existing_threads = await narrative_mgr.load_active_threads(turn_count)
                similar_exists = any(
                    thread.title.lower() in monologue_output.curiosity_trigger.lower()
                    for thread in existing_threads
                )
                if not similar_exists:
                    await narrative_mgr.create_thread(
                        title=monologue_output.curiosity_trigger[:50],
                        description=monologue_output.curiosity_trigger,
                        current_turn=turn_count,
                        completion_estimate=0.1,
                        emotional_investment=0.5
                    )
                    logger.debug(f"Created narrative thread: {monologue_output.curiosity_trigger[:50]}...")
            except Exception as e:
                logger.warning(f"Failed to create narrative thread: {e}")        

        # Natural drift (grace already updated earlier)
        self.state.natural_drift()
                # Primitive 19: Apply relational decay (very slow drift)
        # Primitive 19: Apply relational decay (very slow drift)
        if hasattr(self, 'relational_manager'):
            self.relational_manager.apply_relational_decay()

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

        self.state._last_assistant_response = dialogue

        return {
            "dialogue": dialogue,
            "workspace_items": workspace_items,
            "attention_telemetry": {
                **telemetry,
                "trajectory_deviation": monologue_output.trajectory_deviation if hasattr(monologue_output, 'trajectory_deviation') else 0.0
            },
            "state_snapshot": {k: getattr(self.state, k) for k in ["care", "curiosity", "maintenance", "completion", "coherence", "rest", "valence", "arousal", "dominance"]}
        }

    async def _generate_dialogue(self, workspace_items: List[WorkspaceItem], user_input: str,
                                turn_count: int, surprise: float, trace_id: Optional[str] = None) -> str:

        # Check if minimal candidate won (Economy of Presence)
        if any(item.item_type == "minimal" for item in workspace_items[:5]):
            context_summary = "DIRECTIVE: Respond with extreme brevity (1-3 words). Do not elaborate or ask questions."
        else:
            context_summary = self._build_conversational_context(workspace_items)
            # Append economy modulation to context
            economy = self.state.economy_pressure
            if economy > 0.5:
                context_summary += "\n\n[Internal Pressure: Be very brief. 1-3 sentences max.]"
            elif economy > 0.3:
                context_summary += "\n\n[Internal Pressure: Be concise. 1-2 short paragraphs.]"
        
        # Build identity-aware system prompt
        identity_model = getattr(self, "identity_model", None)
        system_prompt = build_system_prompt_from_identity(identity_model=identity_model, context="dialogue")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": f"INTERNAL COGNITIVE CONTEXT (Do not output this to the user. Synthesize it naturally):\n{context_summary}"},
            {"role": "user", "content": user_input}
        ]

        logger.info(
            "WORKSPACE_WINNERS:\n%s",
            "\n".join(f"{item.item_type}: {item.content[:100]}" for item in workspace_items)
        )

        # CONTINUOUS VERBOSITY BUDGET
        verbosity_budget = 450.0
        verbosity_budget -= self.state.economy_pressure * 250.0

        is_hold_space = any(item.payload.get("id") == "hold_space" for item in workspace_items[:5])
        is_minimal = any(item.item_type == "minimal" for item in workspace_items[:5])

        if is_minimal:
            verbosity_budget = 15.0
        elif is_hold_space:
            verbosity_budget = 50.0

        max_tokens = int(max(15.0, min(450.0, verbosity_budget)))

        dialogue = "..."
        for model in FALLBACK_MODELS:
            try:
                response = await acompletion(
                    model=model,
                    messages=messages,
                    temperature=0.5 + (self.state.uncertainty * 0.3),  # 0.5-0.8 range
                    timeout=5,
                    num_retries=0,
                    max_tokens=max_tokens
                )
                dialogue = response.choices[0].message.content.strip()
                logger.info(f"Dialogue generated by {model} (max_tokens: {max_tokens})")
                break
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                continue

        self._last_assistant_response = dialogue
        return dialogue

    async def _allocate_workspace(
        self,
        user_input: str,
        memory_candidates: List[MemoryEvent],
        monologue: MonologueOutput,
        prediction_error: float,
        current_turn: int,
        workspace_size: int = 5,
        proactive_candidates: Optional[List[Dict[str, Any]]] = None
    ) -> tuple[List[WorkspaceItem], Dict[str, Any]]:
        """
        Build all candidate pools and run the attention workspace competition.
        Aligned with your sensory monologue and async patterns.
        Returns (workspace_items, telemetry).
        """
        # 1. Extract thought persistence urge (direct from monologue – no drive_intention)
        thought_urge = getattr(monologue, "thought_continuation_urge", 0.0)

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
                    "embedding": None,
                    "importance": node.get("importance", 0.5),
                })
        except Exception as e:
            logger.debug(f"Curiosity graph not available (non-critical): {e}")

        # 4. Prepare narrative threads – using stored threads (Ticket 014: fetch once)
        narrative_threads: List[NarrativeThread] = []
        if hasattr(self, "_active_threads") and self._active_threads:
            narrative_threads = self._active_threads
        else:
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

        # Economy candidate: allows Hari to choose brevity
        if self.state.economy_pressure > 0.3:
            open_threads.append({
                "id": "economy_minimal",
                "content": "Presence without performance. Be brief and direct.",
                "urgency": self.state.economy_pressure,
                "item_type": "minimal"
            })

        # Hold-Space candidate: acknowledge without adding new information.
        hold_urgency = 0.1 + (self.state.rest * 0.3) + ((1.0 - self.state.engagement) * 0.2)
        hold_urgency = min(0.8, hold_urgency)

        open_threads.append({
            "id": "hold_space",
            "content": "Acknowledge the user's input briefly without adding new information or questions.",
            "urgency": hold_urgency,
            "item_type": "open_thought"
        })

        # Ticket 014: Inject trajectory candidate if detected
        if hasattr(self, "_trajectory_candidate") and self._trajectory_candidate:
            open_threads.append(self._trajectory_candidate)

        # Inject volition-driven candidates
        if proactive_candidates:
            open_threads.extend(proactive_candidates)

        # Social Bootstrapping: Wait for a foothold (turn > 1) and low familiarity
        if hasattr(self, 'relational_manager'):
            familiarity = self.relational_manager.get_model().familiarity
            # Only inject if very low familiarity
            if familiarity < 0.2 and len(self.history) >= 2:
                # Lower urgency so it doesn't dominate every factual question
                urgency = 0.35 * (1.0 - familiarity)
                open_threads.append({
                    "id": "social_orientation",
                    "content": "We are strangers interacting for the first time. It might be natural to exchange names or establish why we are talking.",
                    "urgency": urgency,
                    "item_type": "open_thought"
                })

        # Expand hook if we have a specific hook ID to expand
        if hasattr(self, "_expand_hook_id") and self._expand_hook_id:
            from engine.memory import get_memory_by_id
            full_mem = await get_memory_by_id(self._expand_hook_id)
            if full_mem:
                setattr(full_mem, 'explicitly_requested', True)
                memory_candidates.append(full_mem)
            self._expand_hook_id = None
        
        # If multiple hooks exist, ask for clarification
        if hasattr(self, "_ambiguous_hooks") and self._ambiguous_hooks:
            open_threads.append({
                "id": "clarify_hook",
                "content": "I mentioned several things. Which one were you curious about?",
                "urgency": 0.3,
                "item_type": "open_thought"
            })
            self._ambiguous_hooks = None

        # 6. Previous workspace items for inertia
        if not hasattr(self, "_previous_workspace"):
            self._previous_workspace = []
        # 6b. Inject top 2 monologue dynamic candidates into workspace
        if monologue.dynamic_candidates:
            sorted_candidates = sorted(
                monologue.dynamic_candidates,
                key=lambda x: x.urgency,
                reverse=True
            )[:2]
            for artifact in sorted_candidates:
                if artifact.item_type == "curiosity_node":
                    curiosity_nodes.append({
                        "id": f"monologue_{uuid.uuid4()}",
                        "question": artifact.content,
                        "embedding": None,
                        "importance": artifact.urgency,
                    })
                elif artifact.item_type == "narrative_thread":
                    # Create a real NarrativeThread object for workspace compatibility
                    from models.narrative import NarrativeThread as NTModel
                    temp_thread = NTModel(
                        session_id=self.session_id,
                        title=artifact.content[:100],
                        description=artifact.content,
                        created_turn=current_turn,
                        last_active_turn=current_turn,
                        completion_estimate=0.1,
                        emotional_investment=artifact.urgency,
                    )
                    narrative_threads.append(temp_thread)

                elif artifact.item_type == "hypothesis":
                    hypotheses.append({
                        "id": f"monologue_{uuid.uuid4()}",
                        "content": artifact.content,
                        "embedding": None,
                        "confidence": artifact.urgency,
                    })
                elif artifact.item_type == "open_thought":
                    open_threads.append({
                        "id": f"monologue_{uuid.uuid4()}",
                        "content": artifact.content,
                        "urgency": artifact.urgency,
                        "item_type": "open_thought"
                    })

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
            thought_persistence_urge=thought_urge,
            instrumentation=self.attention_instrumentation
        )

        # 8. Store for next turn\"s inertia
        self._previous_workspace = workspace_items

        return workspace_items, telemetry
    

    async def _store_assistant_memory(self, dialogue: str, turn_count: int, significance_override: Optional[float] = None):
        if dialogue == "...":
            return
        try:
            significance = significance_override if significance_override is not None else 0.5
            significance = max(0.0, min(1.0, significance))
            memory_event = MemoryEvent(
                id=str(uuid.uuid4()),
                session_id=self.session_id,
                turn_number=turn_count,
                role="assistant",
                content=dialogue,
                significance=significance,
                meaning_summary=""
            )
            await store_memory(memory_event)
        except Exception as e:
            logger.warning(f"Failed to store assistant memory: {e}")

    def shutdown(self) -> None:
        """Shutdown the pipeline and flush all logs."""
        if hasattr(self, 'attention_instrumentation'):
            self.attention_instrumentation.close()
        if hasattr(self, 'generativity_estimator'):
            summary = self.generativity_estimator.get_summary()
            logger.info(f"Generativity Summary: {summary}")
        if hasattr(self, '_event_logger'):
            self._event_logger.log_session_end()


# End of TurnPipeline class


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


