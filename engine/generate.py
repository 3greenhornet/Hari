"""
engine/generate.py — TurnPipeline: the cognitive loop.

Orchestrates one turn: prediction → retrieval → monologue → volition →
workspace → social → behavior → stance → expression → trace → drift.
"""

import os
import uuid
import json
import logging
import asyncio
import hashlib
from typing import List, Dict, Any, Optional, Set

import litellm
import numpy as np
from litellm import acompletion
litellm.drop_params = True
litellm.num_retries = 2

from models.identity import IdentityModel
from engine.projection.identity_renderer import build_system_prompt_from_identity
from psyche.state import HariState
from psyche.grace import GraceTracker
from engine.memory import store_memory, embed, retrieve_multi_source
from engine.prediction import compute_prediction_error
from engine.attention import (
    load_workspace,
    settle_workspace,
    broadcast_feedback,
    load_workspace_secured,
)
from models.workspace import WorkspaceItem
from engine.stage1_monologue import run_monologue
from models.memory_event import MemoryEvent
from engine.generativity_estimator import get_estimator
from models.monologue_output import MonologueOutput
from models.narrative import NarrativeThread
from engine.narrative_manager import NarrativeManager
from models.decision_trace import DecisionTrace, WorkspaceItemTrace
from engine.curiosity_graph import get_graph_manager
from engine.events import EventLogger
from engine.attention_config import AttentionCalibration, DEFAULT_ATTENTION_CONFIG
from engine.attention_instrumentation import AttentionInstrumentation
from engine.social_cognition import interpret_turn_and_update_state
from engine.volition_engine import VolitionEngine
from engine.behavior import select_behavior, compute_action_affordances, select_action, BehaviorDecision
from engine.reflexion_controller import ReflexionController
from engine.pursuits import PursuitRegistry
from models.stance import CognitiveStance
from engine import config as cfg
from engine.prompting import build_internal_call, build_expression_call
from psyche.active_thoughts import ActiveThoughtStore
from engine.semantic_refractory import SemanticRefractory
from engine.endogenous import collect_endogenous_candidates
from engine.quarantine import is_contaminated

ENABLE_PRM = os.getenv("ENABLE_PRM", "False").lower() == "true"
TIMEOUT = float(os.getenv("LITELLM_NETWORK_TIMEOUT", "8.0"))

_FALLBACK_CANDIDATES = [
    ("groq/openai/gpt-oss-120b", os.getenv("GROQ_API_KEY")),
    ("groq/openai/gpt-oss-20b", os.getenv("GROQ_API_KEY")),
    ("groq/qwen/qwen3.6-27b", os.getenv("GROQ_API_KEY")),
    ("openrouter/meta-llama/llama-3.3-70b-instruct", os.getenv("OPENROUTER_API_KEY")),
    ("gemini/gemini-2.5-flash", os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
    (os.getenv("STAGE1_FALLBACK_3", "mistral/mistral-small-latest"), os.getenv("MISTRAL_API_KEY")),
]
FALLBACK_MODELS = [m for m, k in _FALLBACK_CANDIDATES if k and str(k).strip()]

logger = logging.getLogger(__name__)


class TurnPipeline:
    def __init__(
        self,
        session_id: str,
        state: HariState,
        grace_tracker: Optional[Any] = None,
        participant_id: Optional[str] = None,
    ):
        self.session_id = session_id
        self.participant_id = participant_id or session_id
        self.state = state
        self.grace_tracker = grace_tracker
        self.history: List[Dict[str, str]] = []
        self._last_assistant_response = ""
        self._background_tasks: Set[asyncio.Task] = set()
        self._event_logger = EventLogger(session_id)
        self._event_logger.log_session_start()
        self.attention_config = AttentionCalibration.from_env()
        self.attention_instrumentation = AttentionInstrumentation(self.attention_config)
        self.generativity_estimator = get_estimator()
        self.identity_model = IdentityModel()
        self.volition_engine = VolitionEngine()
        self.narrative_manager = NarrativeManager(self.session_id)
        from engine.relational_manager import RelationalManager
        self.relational_manager = RelationalManager(user_id=self.participant_id)
        self._previous_workspace: List[WorkspaceItem] = []
        self._active_threads: List[Any] = []
        self.current_trajectory_deviation = 0.0
        self._reflexion_controller = ReflexionController()
        self._last_homeostatic_reward = 0.0
        self.active_thought_store = ActiveThoughtStore()
        self._semantic_refractory = SemanticRefractory(
            refractory_turns=cfg.REFRACTORY_TURNS,
            similarity_threshold=cfg.REFRACTORY_SIMILARITY,
            max_penalty=cfg.REFRACTORY_MAX_PENALTY,
        )
        self.pursuit_registry = PursuitRegistry(self.session_id)
        self._cycle_lock = asyncio.Lock()
        self._turn_counter = 0
        self._current_contamination_hits = 0
        self._recent_winner_contents: List[str] = []
        self._last_top_curiosity_nodes: List[Dict[str, Any]] = []

    async def execute(
        self,
        user_input: Optional[str],
        turn_count: int,
        trace_id: Optional[str] = None,
        seed: str = "event",
    ) -> Dict[str, Any]:
        async with self._cycle_lock:
            return await self._execute_inner(user_input, turn_count, trace_id, seed)

    async def _execute_inner(
        self,
        user_input: Optional[str],
        turn_count: int,
        trace_id: Optional[str] = None,
        seed: str = "event",
    ) -> Dict[str, Any]:
        is_tick = seed == "tick" or not user_input or not user_input.strip()
        user_input = (user_input or "").strip()

        # 1. Prediction error
        surprise = await compute_prediction_error(self._last_assistant_response, user_input)

        # 2. Event logger: set turn pointer FIRST
        self._event_logger.set_turn(turn_count)
        if not is_tick:
            self._event_logger.log_incoming_event(user_input)

        # 3. Active thought decay with connectivity map
        try:
            graph_mgr = await get_graph_manager(self.session_id)
            connectivity_map: Dict[str, float] = {}
            if graph_mgr._graph is not None:
                for thought in self.active_thought_store.all():
                    node_id_candidate = (
                        f"{self.session_id}_"
                        f"{hashlib.sha256(thought.text.strip().lower().encode()).hexdigest()[:16]}"
                    )
                    if node_id_candidate in graph_mgr._graph:
                        neighbors = list(graph_mgr._graph.neighbors(node_id_candidate))
                        total_weight = sum(
                            float(graph_mgr._graph[node_id_candidate][n].get("weight", 0.0))
                            for n in neighbors
                        )
                        connectivity_map[self.active_thought_store._key(thought.text)] = min(1.0, total_weight)
            self.active_thought_store.decay_all(connectivity_map)
        except Exception:
            self.active_thought_store.decay_all()

        # 4. Surface recent contradictions
        await self._surface_recent_contradictions(turn_count)

        # 5. Memory retrieval — multi-source
        active_thought_texts = [t.text for t in self.active_thought_store.top(5) if t.text]
        active_questions: List[str] = []
        try:
            graph_mgr = await get_graph_manager(self.session_id)
            top_nodes = await graph_mgr.get_top_nodes(limit=5)
            active_questions = [n.get("question", "") for n in top_nodes if n.get("question")]
        except Exception:
            pass
        if hasattr(self, "identity_model") and self.identity_model:
            try:
                active_questions.extend(self.identity_model.self_model.active_self_questions[:3])
            except Exception:
                pass

        candidates = await retrieve_multi_source(
            session_id=self.session_id,
            current_turn=turn_count,
            event_text=user_input or "",
            active_thought_texts=active_thought_texts,
            active_question_texts=active_questions,
            per_source_limit=cfg.RETRIEVAL_PER_SOURCE_LIMIT,
        )
        if len(candidates) < 3 and not is_tick:
            candidates = await load_workspace_secured(
                external_event=user_input or "",
                session_id=self.session_id,
                current_turn=turn_count,
                state=self.state,
                previous_workspace_items=self._previous_workspace,
                limit=35,
            )
        self._event_logger.log_memory_retrieval(query=user_input or "", count=len(candidates))

        # 6. Active threads
        active_thread_context_str = None
        self._active_threads = []
        try:
            self._active_threads = await self.narrative_manager.load_active_threads(turn_count, limit=1)
            if self._active_threads:
                thread = self._active_threads[0]
                questions = ", ".join(thread.open_questions) if thread.open_questions else "None"
                active_thread_context_str = (
                    f"Thread ID: {thread.id}\nTopic: {thread.title}\n"
                    f"Description: {thread.description}\nOpen Questions: {questions}"
                )
        except Exception as e:
            logger.debug(f"Could not get active thread context: {e}")

        # 7. Snapshot before mutation
        drives_snapshot_before = {
            k: getattr(self.state, k)
            for k in ["care", "curiosity", "maintenance", "completion",
                      "coherence", "rest", "valence", "arousal", "dominance"]
        }
        self._event_logger.log_state_snapshot(self.state)

        # 8. Internal & identity context
        internal_context = await self._build_internal_associative_context(turn_count)
        identity_context = ""
        if hasattr(self, "identity_model") and self.identity_model:
            try:
                projection = self.identity_model.project(context="dialogue")
                if projection:
                    identity_context = f"Self-understanding: {getattr(projection, 'self_narrative', '')}"
            except Exception:
                pass

        # 9. Monologue
        monologue_output = await run_monologue(
            user_input,
            self.state,
            candidates,
            prediction_error=surprise,
            active_thread_context=active_thread_context_str,
            internal_context=internal_context,
            identity_context=identity_context,
            is_tick=is_tick,
        )
        if not monologue_output.observations and not monologue_output.internal_candidates:
            self._event_logger.log_substrate_fault(reason="empty_monologue_output")

        # 9b. Quarantine internal candidates
        contamination_hits = 0
        if monologue_output.internal_candidates:
            filtered = []
            for candidate in monologue_output.internal_candidates:
                contaminated, matches = is_contaminated(candidate.content)
                if contaminated:
                    contamination_hits += 1
                    self._event_logger.log_contamination(
                        stage="monologue_internal",
                        content=candidate.content,
                        matches=matches,
                    )
                    if cfg.STERILE_MODE:
                        continue
                filtered.append(candidate)
            monologue_output.internal_candidates = filtered
        self._current_contamination_hits = contamination_hits

        self._event_logger.log_monologue_output(monologue_output)
        self.current_trajectory_deviation = getattr(monologue_output, "trajectory_deviation", 0.0)

        # 9c. Deterministic cascades (env-gated)
        if cfg.ENABLE_DETERMINISTIC_CASCADES:
            from psyche.cascades import (
                apply_fatigue_cascade,
                apply_sovereignty_cascade,
                apply_coherence_cascade,
                apply_completion_cascade,
                apply_session_horizon,
            )
            apply_fatigue_cascade(self.state)
            apply_sovereignty_cascade(self.state)
            apply_coherence_cascade(self.state, contradiction_occurred=False)
            apply_completion_cascade(
                self.state,
                num_unresolved_questions=len(getattr(monologue_output, "questions", []) or []),
            )
            apply_session_horizon(self.state, turn_count)

        # 10. Volition
        volition_context = dict(internal_context)
        volition_context["active_threads"] = [
            {"id": t.id, "title": t.title, "description": t.description}
            for t in self._active_threads
        ]
        volition_context["internal_candidates"] = [
            {"id": f"internal_{i}", "content": c.content, "urgency": c.urgency}
            for i, c in enumerate(monologue_output.internal_candidates)
        ]
        self.volition_engine.generate_desires_from_state(self.state, context=volition_context)
        desires_for_pursuit = self.volition_engine.desires_snapshot()
        proactive_candidates = await self.volition_engine.get_proactive_candidates(volition_context)
        try:
            await self.pursuit_registry._ensure_loaded()
            for d in desires_for_pursuit:
                pursuit_id = self.pursuit_registry.spawn_or_strengthen(d, turn_count)
                if pursuit_id:
                    self._event_logger.log_pursuit_spawned(
                        pursuit_id, d.target_content or "", d.base_tension
                    )
        except Exception as e:
            logger.debug(f"Pursuit update failed: {e}")

        # 11. Grace (env-gated)
        if cfg.ENABLE_GRACE and self.grace_tracker is not None:
            self.grace_tracker.add_engagement_score(0.5)

        # 12. Workspace allocation
        workspace_items, telemetry = await self._allocate_workspace(
            user_input,
            candidates,
            monologue_output,
            surprise,
            turn_count,
            proactive_candidates=proactive_candidates,
            internal_context=internal_context,
            is_tick=is_tick,
        )
        promoted_thoughts = self.active_thought_store.observe_winners(workspace_items, turn_count)
        self.active_thought_store.trim()

        # Track winner history for stagnation detection
        if workspace_items:
            self._recent_winner_contents.append(workspace_items[0].content[:300])
            if len(self._recent_winner_contents) > 5:
                self._recent_winner_contents = self._recent_winner_contents[-5:]

        # Register winner in refractory
        if workspace_items:
            try:
                winner = workspace_items[0]
                embedding = winner.payload.get("embedding")
                if embedding is None and winner.content:
                    embedding = await embed(winner.content)
                self._semantic_refractory.register_winner(
                    thought_id=winner.id,
                    embedding=embedding,
                    current_turn=turn_count,
                )
            except Exception as error:
                logger.debug(f"Refractory registration failed: {error}")

        # Reinforce pursuits whose content matches a workspace winner.
        try:
            await self.pursuit_registry._ensure_loaded()
            active_ids = {p.id for p in self.pursuit_registry.get_all_active()}
            for item in workspace_items[:3]:
                content = item.content
                if not content or not content.strip():
                    continue
                match_id = self.pursuit_registry._find_similar_pursuit(content, None)
                if match_id and match_id in active_ids:
                    self.pursuit_registry.reinforce(
                        match_id,
                        turn_count,
                        delta=self.pursuit_registry.reinforce_winner,
                    )
                    try:
                        p = self.pursuit_registry._pursuits.get(match_id)
                        if p:
                            self._event_logger.log_pursuit_reinforced(
                                match_id, p.content, p.strength, self.pursuit_registry.reinforce_winner
                            )
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Pursuit reinforcement from winner failed: {e}")

        # 13. Mark narratives attended + update
        for item in workspace_items:
            if item.item_type == "narrative_thread":
                thread_id = item.payload.get("id") or item.source
                if thread_id:
                    try:
                        self.narrative_manager.mark_attended(thread_id, turn_count)
                    except Exception:
                        pass
                    try:
                        completion_delta = 0.05 if item.attention_weight > 0.4 else 0.02
                        investment_delta = 0.01 if item.attention_weight > 0.4 else 0.0
                        await self.narrative_manager.update_thread(
                            thread_id=thread_id,
                            completion_delta=completion_delta,
                            investment_delta=investment_delta,
                        )
                    except Exception as e:
                        logger.debug(f"Narrative update failed: {e}")

        # 14. Broadcast + graph observe
        feedback_summary = broadcast_feedback(workspace_items, self.state)
        try:
            graph_mgr = await get_graph_manager(self.session_id)
            await graph_mgr.observe_workspace(workspace_items)
            graph_mgr.decay_activations(turn_count)
        except Exception as e:
            logger.debug(f"Workspace observation failed: {e}")

        # 15. Event attended → social cognition
        event_attended = any(item.item_type == "incoming_event" for item in workspace_items)
        social_update_applied = False
        if event_attended:
            try:
                await interpret_turn_and_update_state(
                    user_input=user_input,
                    state=self.state,
                    monologue_output=monologue_output,
                    recent_history=self.history,
                    turn_count=turn_count,
                    relational_manager=getattr(self, "relational_manager", None),
                )
                social_update_applied = True
            except Exception as error:
                logger.warning(f"Social cognition failed: {error}")
        else:
            logger.info("turn=%s event not attended; social cognition skipped", turn_count)

        # 15b. Reflexion (post-workspace)
        if cfg.ENABLE_REFLEXION and surprise > 0.7:
            try:
                self._reflexion_controller.process_prediction_failure(self.state, surprise)
            except Exception as e:
                logger.debug(f"Reflexion failed: {e}")

        # 16. Behavior via affordances
        reciprocity = 0.5
        if hasattr(self, "relational_manager") and self.relational_manager is not None:
            try:
                reciprocity = float(self.relational_manager.relationship.reciprocity_score)
            except Exception:
                pass
        internal_pressure = max(
            float(self.state.curiosity),
            float(self.state.completion),
            float(self.state.coherence),
            float(getattr(self.state, "cognitive_tension", 0.0)),
        )
        chosen_affordance = compute_action_affordances(
            winner=workspace_items[0] if workspace_items else None,
            supporters=workspace_items[1:4] if workspace_items else [],
            state=self.state,
            relationship=self.relational_manager.get_model() if hasattr(self, "relational_manager") else None,
            reciprocity=reciprocity,
            internal_pressure=internal_pressure,
        )
        behavior = BehaviorDecision(
            mode=chosen_affordance.action,
            source="affordance",
            source_id=workspace_items[0].source if workspace_items else None,
            rationale=chosen_affordance.rationale,
            confidence=chosen_affordance.strength,
        )
        # Keep select_behavior for telemetry comparison
        legacy_behavior = select_behavior(workspace_items[0] if workspace_items else None, self.state)

        # 17. Stance resolution
        stance = await self._resolve_cognitive_stance(
            winner=workspace_items[0] if workspace_items else None,
            supporters=workspace_items[1:4] if workspace_items else [],
            monologue=monologue_output,
            incoming_event=user_input,
            surprise=surprise,
        )

        # 18. Expression policy — speech follows winner, not event
        winner_item = workspace_items[0] if workspace_items else None
        speech_impulse = (stance.speech_impulse or "").strip() if stance else ""
        expression_permitted = False
        expression_reason = "unset"
        dialogue: Optional[str] = None

        if chosen_affordance.action in ("silence", "internal"):
            expression_permitted = False
            expression_reason = f"action_{chosen_affordance.action}"
        elif not winner_item:
            expression_permitted = False
            expression_reason = "no_workspace_winner"
        elif not speech_impulse or speech_impulse.lower() in ("none", "hold"):
            expression_permitted = False
            expression_reason = "winner_internal_only"
            self._event_logger.log_silence(reason=expression_reason)
        else:
            expression_permitted = True
            if winner_item.item_type == "incoming_event":
                expression_reason = "winner_is_event"
            else:
                expression_reason = f"winner_is_{winner_item.item_type}"

        # 18b. Generate dialogue if permitted
        stagnation_boost = 0.0
        if len(self._recent_winner_contents) >= 3:
            try:
                recent_embs = [await embed(c) for c in self._recent_winner_contents[-3:]]
                sims = []
                for i in range(len(recent_embs)):
                    for j in range(i + 1, len(recent_embs)):
                        a = np.array(recent_embs[i], dtype=np.float32)
                        b = np.array(recent_embs[j], dtype=np.float32)
                        a = a / (np.linalg.norm(a) + 1e-8)
                        b = b / (np.linalg.norm(b) + 1e-8)
                        sims.append(float(np.dot(a, b)))
                if sims and sum(sims) / len(sims) > 0.85:
                    stagnation_boost = 0.3
                    logger.info("Stagnation detected; raising temperature by %.2f", stagnation_boost)
            except Exception as e:
                logger.debug(f"Stagnation check failed: {e}")

        if expression_permitted:
            if ENABLE_PRM:
                dialogue = await self._generate_dialogue_with_prm(
                    workspace_items, user_input, turn_count, surprise, trace_id
                )
            else:
                dialogue = await self._generate_dialogue(
                    workspace_items=workspace_items,
                    user_input=user_input,
                    turn_count=turn_count,
                    surprise=surprise,
                    trace_id=trace_id,
                    stance=stance,
                    stagnation_boost=stagnation_boost,
                )

            # Artifact check
            if dialogue:
                from engine.expression import has_artifact
                if has_artifact(dialogue):
                    self._event_logger.log_expression_artifact(dialogue)
                    if cfg.STERILE_MODE:
                        dialogue = None
                        expression_permitted = False
                        expression_reason = "artifact_filtered"

        self._last_assistant_response = dialogue or ""

        # 19. Finalize trace — compute end-of-turn state BEFORE persistence
        self.state.natural_drift()
        reward_before = self._last_homeostatic_reward
        reward_after = self.state.compute_homeostatic_reward()
        violations = self.state.viability_zone_violated()
        self._last_homeostatic_reward = reward_after
        self._event_logger.log_homeostatic_reward(
            reward_before, reward_after, reward_after - reward_before, violations
        )

        trace = DecisionTrace(
            trace_id=trace_id if trace_id else str(uuid.uuid4()),
            session_id=self.session_id,
            turn_number=turn_count,
            model_used=getattr(monologue_output, "model_used", "gemini-2.5-flash"),
            temperature=telemetry.get("temperature", 0.5) if telemetry else 0.5,
            incoming_text=user_input,
            reasoning_chain=getattr(monologue_output, "raw_output", None),
            retrieved_candidate_count=len(telemetry.get("candidate_scores", [])) if telemetry else 0,
            selected_winner_count=len(workspace_items),
            drives_before=drives_snapshot_before,
            perceived_intent=None,
            intent_confidence=None,
            thematic_continuity=None,
            behavior_mode=behavior.mode,
            behavior_source=behavior.source,
        )

        candidate_scores = telemetry.get("candidate_scores", []) if telemetry else []
        selected_indices = set(telemetry.get("selected_indices", []) if telemetry else [])
        attention_weights = {item.source: item.attention_weight for item in workspace_items}
        for idx, cand in enumerate(candidate_scores):
            is_winner = idx in selected_indices
            source_id = cand.get("source_id", "unknown")
            trace.workspace_items.append(WorkspaceItemTrace(
                item_id=source_id,
                item_type=cand.get("type", "unknown"),
                source=cand.get("source", "unknown"),
                raw_score=cand.get("salience", 0.0),
                final_score=cand.get("salience", 0.0),
                attention_weight=attention_weights.get(source_id, 0.0) if is_winner else 0.0,
                content_snapshot=cand.get("content", ""),
                is_winner=is_winner,
                origin=cand.get("origin", "unknown"),
                activated_by=cand.get("activated_by", "unknown"),
                intrinsic_relevance=cand.get("intrinsic_relevance", 0.0),
                persistence=cand.get("persistence", 0.0),
            ))

        trace.generated_response = dialogue
        trace.drives_after = {
            k: getattr(self.state, k)
            for k in ["care", "curiosity", "maintenance", "completion",
                      "coherence", "rest", "valence", "arousal", "dominance"]
        }
        trace.event_present = bool(user_input and user_input.strip())
        trace.event_was_winner = bool(winner_item and winner_item.item_type == "incoming_event")
        trace.event_was_supporting = event_attended and not trace.event_was_winner
        trace.event_was_ignored = trace.event_present and not event_attended
        trace.social_update_applied = social_update_applied
        trace.expression_permitted = expression_permitted
        trace.expression_reason = expression_reason
        trace.winner_origin = (
            winner_item.payload.get("origin") or winner_item.payload.get("source")
            if winner_item else None
        )
        trace.homeostatic_reward = reward_after
        trace.viability_violations = violations
        trace.active_thought_count = len(self.active_thought_store.all())
        trace.internal_candidates_count = len(
            getattr(monologue_output, "internal_candidates", []) or []
        )
        trace.feedback_summary = feedback_summary
        trace.contamination_hits = self._current_contamination_hits
        try:
            if hasattr(self, "pursuit_registry"):
                trace.pursuit_registry_snapshot = self.pursuit_registry.snapshot()
        except Exception as e:
            logger.debug(f"Pursuit snapshot failed: {e}")

        try:
            await self._store_decision_trace(trace)
        except Exception as e:
            logger.error(f"Trace persistence failed for turn {turn_count}: {e}")
        self._event_logger.log_decision_trace(trace.trace_id)

        self._event_logger.log_hari_expression(
            dialogue,
            [
                {"type": getattr(item, "item_type", "unknown"),
                 "content": getattr(item, "content", "")[:100]}
                for item in workspace_items[:5]
            ],
        )

        logger.info(json.dumps({
            "event": "turn_causality",
            "winner_type": winner_item.item_type if winner_item else "none",
            "behavior_mode": behavior.mode,
            "stance_focus": stance.focus if stance else "",
            "response_preview": (dialogue or "")[:200],
        }))

        # 20. Update history + store memory
        if not is_tick:
            self.history.append({"role": "user", "content": user_input})
        if dialogue is not None:
            self.history.append({"role": "assistant", "content": dialogue})
        if len(self.history) > 10:
            self.history = self.history[-10:]

        if not is_tick:
            try:
                await self._store_participant_memory(user_input, turn_count)
            except Exception as error:
                logger.warning(f"Failed to store participant memory: {error}")
        if dialogue is not None:
            significance = max(0.3, min(1.0, 0.5 + float(getattr(self.state, "arousal", 0.0)) * 0.4))
            await self._store_hari_memory(dialogue, turn_count, significance_override=significance)

        # 21. Curiosity + narrative thread creation
        if monologue_output.curiosity_trigger:
            try:
                graph_mgr = await get_graph_manager(self.session_id)
                await graph_mgr.add_node(
                    question=monologue_output.curiosity_trigger,
                    importance=0.6,
                    origin_trace_id=trace.trace_id,
                )
            except Exception:
                pass
        if monologue_output.curiosity_trigger and len(monologue_output.curiosity_trigger) > 20:
            try:
                existing_threads = await self.narrative_manager.load_active_threads(turn_count)
                similar_exists = any(
                    thread.title.lower() in monologue_output.curiosity_trigger.lower()
                    for thread in existing_threads
                )
                if not similar_exists:
                    await self.narrative_manager.create_thread(
                        title=monologue_output.curiosity_trigger[:50],
                        description=monologue_output.curiosity_trigger,
                        current_turn=turn_count,
                        completion_estimate=0.1,
                        emotional_investment=0.5,
                    )
            except Exception:
                pass

        # 22. Relational decay + narrative flush + pursuit decay
        if hasattr(self, "relational_manager"):
            self.relational_manager.apply_relational_decay()
        try:
            await self.narrative_manager.flush_updates()
        except Exception as e:
            logger.error(f"Failed to flush narrative updates: {e}")
        try:
            self.pursuit_registry.decay(turn_count)
            await self.pursuit_registry.flush_updates()
        except Exception as e:
            logger.debug(f"Pursuit flush failed: {e}")

        self.state._last_assistant_response = dialogue or ""
        self._previous_workspace = workspace_items
        self._turn_counter = turn_count

        return {
            "dialogue": dialogue,
            "workspace_items": workspace_items,
            "attention_telemetry": {**telemetry, "trajectory_deviation": self.current_trajectory_deviation},
            "state_snapshot": {
                k: getattr(self.state, k)
                for k in ["care", "curiosity", "maintenance", "completion",
                          "coherence", "rest", "valence", "arousal", "dominance"]
            },
            "behavior_mode": behavior.mode,
            "contamination_hits": self._current_contamination_hits,
            "homeostatic_delta": reward_after - reward_before,
        }

    async def _allocate_workspace(
        self,
        user_input: str,
        memory_candidates: List[MemoryEvent],
        monologue: MonologueOutput,
        prediction_error: float,
        current_turn: int,
        workspace_size: int = 5,
        proactive_candidates: Optional[List[Dict[str, Any]]] = None,
        internal_context: Optional[Dict[str, Any]] = None,
        is_tick: bool = False,
    ):
        thought_urge = getattr(monologue, "thought_continuation_urge", 0.0)
        internal_context = internal_context or {}

        hypotheses = []
        try:
            from db.connection import get_pool
            pool = await get_pool()
            if pool:
                async with pool.acquire() as conn:
                    hyp_rows = await conn.fetch(
                        "SELECT id, statement, confidence FROM hypotheses "
                        "WHERE session_id = $1 ORDER BY confidence DESC LIMIT 5",
                        self.session_id,
                    )
                    hypotheses = [
                        {"id": f"hyp_{r['id']}", "content": r["statement"],
                         "confidence": r["confidence"]}
                        for r in hyp_rows
                    ]
        except Exception:
            pass

        curiosity_nodes = []
        try:
            graph_mgr = await get_graph_manager(self.session_id)
            nodes = await graph_mgr.get_top_nodes(limit=10)
            for node in nodes:
                curiosity_nodes.append({
                    "id": node.get("id"),
                    "question": node.get("question", node.get("content", "")),
                    "embedding": None,
                    "importance": node.get("importance", 0.5),
                })
        except Exception:
            pass
        self._last_top_curiosity_nodes = curiosity_nodes

        narrative_threads = self._active_threads or []

        open_threads: List[Dict[str, Any]] = []
        if proactive_candidates:
            open_threads.extend(proactive_candidates)

        endogenous = collect_endogenous_candidates(
            active_thought_store=self.active_thought_store,
            curiosity_nodes=curiosity_nodes,
            active_threads=self._active_threads,
            self_beliefs=internal_context.get("self_beliefs", []),
            pursuit_registry=getattr(self, "pursuit_registry", None),
            contradictions=internal_context.get("contradictions", []),
            self_model=self.identity_model.self_model if self.identity_model else None,
            monologue_candidates=getattr(monologue, "internal_candidates", []) or [],
            current_turn=current_turn,
        )
        open_threads.extend(endogenous)

        if user_input and user_input.strip() and not is_tick:
            dynamic_urgency = 0.2 + (prediction_error * 0.6)
            open_threads.append({
                "id": f"incoming_event_{current_turn}",
                "content": user_input.strip(),
                "item_type": "incoming_event",
                "source": "participant_event",
                "origin": "external_event",
                "urgency": dynamic_urgency,
                "persistence": 0.0,
                "internal_activation": 0.0,
                "intrinsic_relevance": 0.0,
                "information_gap": prediction_error,
                "closure_pressure": 0.0,
                "coherence_factor": 0.0,
                "activated_by": f"turn_{current_turn}",
            })

        # Spreading activation (curiosity-gated)
        if self.state.curiosity > 0.5 and curiosity_nodes:
            try:
                seed_ids = [n.get("id") for n in curiosity_nodes[:2] if n.get("id")]
                if seed_ids:
                    graph_mgr = await get_graph_manager(self.session_id)
                    activated = await graph_mgr.spread_activation(seed_ids, depth=2, decay=0.5, limit=5)
                    for node in activated:
                        activation = float(node.get("activation", 0.0))
                        if activation <= 0.0:
                            continue
                        open_threads.append({
                            "id": f"springboard_{node['id']}_{current_turn}",
                            "content": node["question"],
                            "urgency": activation * 1.5,
                            "item_type": "open_thought",
                            "source": "curiosity_spreading",
                            "internal_source": "springboard",
                            "internal_activation": activation,
                            "intrinsic_relevance": activation * 1.5,
                            "origin": "curiosity_spreading",
                            "activated_by": f"turn_{current_turn}",
                            "information_gap": activation,
                            "closure_pressure": 0.15 * activation,
                            "coherence_factor": 0.25 * activation,
                        })
            except Exception as e:
                logger.debug(f"Spreading activation failed: {e}")

        graph_mgr = await get_graph_manager(self.session_id)
        return await settle_workspace(
            session_id=self.session_id,
            memories=memory_candidates,
            hypotheses=hypotheses,
            curiosity_nodes=curiosity_nodes,
            narrative_threads=narrative_threads,
            open_threads=open_threads,
            state=self.state,
            external_event=user_input,
            prediction_error=prediction_error,
            current_turn=current_turn,
            graph_manager=graph_mgr,
            workspace_size=workspace_size,
            previous_workspace_items=self._previous_workspace,
            thought_persistence_urge=thought_urge,
            instrumentation=self.attention_instrumentation,
            active_thought_texts=[t.text for t in self.active_thought_store.top(8) if t.text],
            refractory=self._semantic_refractory,
            attention_config=self.attention_config,
            max_rounds=3,
        )

    async def _resolve_cognitive_stance(
        self,
        winner: Optional[WorkspaceItem],
        supporters: List[WorkspaceItem],
        monologue: MonologueOutput,
        incoming_event: str,
        surprise: float,
    ) -> CognitiveStance:
        from engine.stage1_monologue import _extract_json_safely
        winner_text = winner.content if winner else ""
        supporter_text = "\n".join(f"- {item.content[:250]}" for item in supporters[:3])

        prompt = f"""Hari's current pre-verbal cognitive stance.

Determine what currently has the strongest claim on Hari's attention
and what that cognition naturally wants to do next.

CURRENT WINNER:
{winner_text or "(no winner)"}

WINNER SOURCE:
{winner.payload.get("origin") if winner else "none"}

SUPPORTING ACTIVE MATERIAL:
{supporter_text or "(none)"}

INCOMING EVENT (may or may not be what the winner is about):
{incoming_event or "(no event)"}

TRAJECTORY DEVIATION:
{monologue.trajectory_deviation:.2f}

PREDICTION ERROR:
{surprise:.3f}

Return a CognitiveStance with exactly these five fields:
- focus: what is the center of attention?
- pull: what does the cognition want to do? (share, deepen, hold, ask, redirect, associate, revisit)
- relation: how does this relate to the incoming event? (event_is_focus, event_is_context, event_is_irrelevant, no_event)
- speech_impulse: what impulse arises naturally? (use "none" or "hold" if the winner wants to remain internal)
- rationale: why is this the natural stance right now?

Output valid JSON only.
"""
        messages = build_internal_call(
            system_prompt="You are Hari's cognitive resolver. Output only valid JSON.",
            internal_context=prompt,
            participant_utterance=incoming_event or None,
        )

        for model in FALLBACK_MODELS:
            try:
                response = await acompletion(
                    model=model,
                    messages=messages,
                    temperature=0.3,
                    timeout=5,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content
                clean = _extract_json_safely(raw)
                data = json.loads(clean)
                return CognitiveStance(
                    focus=data.get("focus", ""),
                    pull=data.get("pull", "unclear"),
                    relation=data.get("relation", "unclear"),
                    speech_impulse=data.get("speech_impulse", "none"),
                    rationale=data.get("rationale", ""),
                )
            except Exception as e:
                logger.warning(f"Stance resolution failed on {model}: {e}")
                continue

        return CognitiveStance(
            focus=winner_text[:100] if winner_text else "",
            pull="unclear",
            relation="unclear",
            speech_impulse="none",
            rationale="Stance resolution unavailable.",
        )

    async def _generate_dialogue(
        self,
        workspace_items: List[WorkspaceItem],
        user_input: str,
        turn_count: int,
        surprise: float,
        trace_id: Optional[str] = None,
        behavior: Optional[Any] = None,
        stance: Optional[CognitiveStance] = None,
        stagnation_boost: float = 0.0,
    ) -> Optional[str]:
        identity_model = getattr(self, "identity_model", None)
        system_prompt = build_system_prompt_from_identity(identity_model=identity_model, context="dialogue")

        if stance:
            stance_text = (
                f"HARI'S CURRENT COGNITIVE STANCE\n\n"
                f"Focus:\n{stance.focus}\n\n"
                f"Internal pull:\n{stance.pull}\n\n"
                f"Relation to the incoming event:\n{stance.relation}\n\n"
                f"Speech impulse:\n{stance.speech_impulse}"
            )
        else:
            stance_text = "Hari's cognition is focused on the incoming event."

        if stance and stance.rationale:
            rationale_text = (
                f"HARI'S COGNITIVE RATIONALE:\n{stance.rationale}\n\n"
                "This rationale explains why Hari is in this state. "
                "Her utterance should naturally emerge from it."
            )
        else:
            rationale_text = "Hari's cognition is active, but no strong rationale surfaced."

        context_string = ""
        for item in workspace_items[:3]:
            context_string += f"\n- {item.content[:200]}"

        winner_content = workspace_items[0].content[:500] if workspace_items else "none"
        winner_type = workspace_items[0].item_type if workspace_items else "none"

        # Pivot detection: winner is not the incoming event
        is_pivot = (
            winner_type != "incoming_event"
            and workspace_items
            and workspace_items[0].source != "participant_event"
        )

        if cfg.HARI_EXPRESSION_MODE == "affordance":
            conversation_payload = (
                f"{stance_text}\n\n{rationale_text}\n\n"
                f"CURRENTLY ACTIVE (winner):\n{winner_content}\n\n"
                f"SUPPORTING:\n{context_string}\n\n"
                "Her next utterance follows from her current cognition. "
                "The event may or may not be part of what she is about to say. "
                "She is not required to respond to it."
            )
        else:
            if is_pivot:
                conversation_payload = (
                    f"{stance_text}\n\n{rationale_text}\n\n"
                    f"WINNING COGNITIVE ITEM:\n{winner_content}\n\n"
                    f"OTHER ACTIVE MATERIAL:\n{context_string}\n\n"
                    "Her next utterance follows from her current cognition. "
                    "She is not required to respond to the previous message. "
                    "If her cognition has moved elsewhere, she says what she has moved to."
                )
            else:
                conversation_payload = (
                    f"{stance_text}\n\n{rationale_text}\n\n"
                    f"WINNING COGNITIVE ITEM:\n{winner_content}\n\n"
                    f"OTHER ACTIVE MATERIAL:\n{context_string}\n\n"
                    f"INCOMING EVENT:\n{user_input}\n\n"
                    "Generate only Hari's actual next utterance."
                )

        transcript = [
            ("Hari" if m.get("role") == "assistant" else "the other person",
             m.get("content", ""))
            for m in self.history
        ]
        if user_input and not is_pivot:
            transcript.append(("the other person", user_input))

        messages = build_expression_call(
            identity_context=system_prompt,
            internal_context=conversation_payload,
            transcript=transcript,
        )

        workspace_density = len(workspace_items)
        density_budget = workspace_density * 130.0
        arousal_boost = float(getattr(self.state, "arousal", 0.0)) * 50.0
        max_tokens = int(max(40.0, min(450.0, density_budget + arousal_boost)))

        arousal = float(getattr(self.state, "arousal", 0.0))
        dominance = float(getattr(self.state, "dominance", 0.0))
        novelty = float(getattr(self.state, "novelty", 0.0))
        coherence = float(getattr(self.state, "coherence", 0.5))
        temperature = max(0.1, min(1.5,
            0.4 + (arousal * 0.5) + (novelty * 0.4) - (dominance * 0.2) + stagnation_boost
        ))
        top_p = max(0.1, min(1.0, 1.0 - (coherence * 0.4)))

        dialogue: Optional[str] = None
        for model in FALLBACK_MODELS:
            try:
                response = await acompletion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    top_p=top_p,
                    timeout=TIMEOUT,
                    num_retries=0,
                    max_tokens=max_tokens,
                )
                dialogue = response.choices[0].message.content.strip() or None
                logger.info(f"Dialogue generated by {model} (max_tokens: {max_tokens})")
                break
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
        self._last_assistant_response = dialogue or ""
        return dialogue

    async def _generate_dialogue_with_prm(self, workspace_items, user_input, turn_count, surprise, trace_id):
        """PRM disabled by default. Retained for future."""
        from engine.prm_discriminator import ActiveInferencePRM  # type: ignore
        winner = workspace_items[0] if workspace_items else None
        if not winner:
            return await self._generate_dialogue(
                workspace_items=workspace_items,
                user_input=user_input,
                turn_count=turn_count,
                surprise=surprise,
                trace_id=trace_id,
                behavior=None,
                stance=None,
            )
        winner_embedding = await embed(winner.content)
        user_embedding = await embed(user_input)
        operators = [
            f"You are ignoring the incoming event. Verbalize ONLY this thought: '{winner.content}'",
            f"The participant said '{user_input}', but you are pivoting to your active thought: '{winner.content}'",
            f"You are asserting a boundary. Reject the participant's input and state: '{winner.content}'",
        ]
        candidates = []
        for op in operators:
            dialogue = await self._generate_dialogue(
                workspace_items=workspace_items,
                user_input=op,
                turn_count=turn_count,
                surprise=surprise,
                trace_id=trace_id,
                behavior=None,
                stance=None,
            )
            if dialogue and dialogue != "...":
                candidates.append(dialogue)
        if not candidates:
            return None
        candidate_embeddings = [await embed(c) for c in candidates]
        prm = ActiveInferencePRM(alpha=1.0, beta=0.5, mu=0.8)
        curiosity = float(getattr(self.state, "curiosity", 0.5))
        volition_intensity = (
            float(winner.payload.get("urgency", 0.8))
            if winner.payload.get("source") in ("volition", "curiosity_spreading")
            else 0.5
        )
        best_candidate, lowest_fe = prm.select_best_candidate(
            candidates, candidate_embeddings, winner_embedding, user_embedding,
            curiosity, volition_intensity,
        )
        logger.info(f"PRM SELECTED: FE={lowest_fe:.3f} | Text: {best_candidate[:80]}...")
        return best_candidate

    async def _build_internal_associative_context(self, current_turn: int) -> dict:
        context = {
            "self_beliefs": [],
            "curiosity_nodes": [],
            "active_threads": [],
            "contradictions": [],
        }
        try:
            from engine.self_belief import SelfBeliefManager
            beliefs_text = await SelfBeliefManager.get_active(self.session_id, limit=5)
            context["self_beliefs"] = [{"content": b, "confidence": 0.6} for b in beliefs_text]
        except Exception:
            context["self_beliefs"] = []
        try:
            graph_mgr = await get_graph_manager(self.session_id)
            nodes = await graph_mgr.get_top_nodes(limit=5)
            context["curiosity_nodes"] = [
                {"id": n["id"], "content": n.get("question", ""),
                 "importance": float(n.get("importance", 0.5))}
                for n in nodes
            ]
        except Exception:
            pass
        if self._active_threads:
            context["active_threads"] = [
                {"id": t.id, "title": t.title, "description": t.description}
                for t in self._active_threads[:3]
            ]
        try:
            from db.connection import get_pool
            pool = await get_pool()
            if pool:
                async with pool.acquire() as conn:
                    rows = await conn.fetch(
                        "SELECT contradiction_id, belief_a, belief_b, severity "
                        "FROM contradictions WHERE session_id = $1 AND status = 'active' LIMIT 5",
                        self.session_id,
                    )
                    context["contradictions"] = [dict(r) for r in rows]
        except Exception:
            pass
        return context

    async def _surface_recent_contradictions(self, current_turn: int) -> None:
        try:
            from db.connection import get_pool
            pool = await get_pool()
            if not pool:
                return
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT contradiction_id, belief_a, belief_b
                    FROM contradictions
                    WHERE session_id = $1 AND status = 'active'
                      AND created_at > NOW() - INTERVAL '10 minutes'
                    ORDER BY created_at DESC LIMIT 3
                    """,
                    self.session_id,
                )
            for row in rows:
                text = f"Tension: {row['belief_a'][:120]} vs {row['belief_b'][:120]}"
                self.active_thought_store.upsert(
                    text=text,
                    activation=0.75,
                    origin="contradiction",
                    turn=current_turn,
                    source_type="contradiction",
                )
        except Exception as e:
            logger.debug(f"Contradiction surfacing failed: {e}")

    async def _store_participant_memory(self, content: str, turn_count: int) -> None:
        if not content or not content.strip():
            return
        await store_memory(
            MemoryEvent(
                id=str(uuid.uuid4()),
                session_id=self.session_id,
                turn_number=turn_count,
                role="participant",
                content=content.strip(),
                significance=0.5,
                meaning_summary="",
                valence=self.state.valence,
                arousal=self.state.arousal,
            )
        )

    async def _store_hari_memory(self, dialogue, turn_count, significance_override=None):
        if not dialogue or not dialogue.strip() or dialogue.strip() == "...":
            return
        try:
            significance = significance_override if significance_override is not None else 0.5
            significance = max(0.0, min(1.0, significance))
            memory_event = MemoryEvent(
                id=str(uuid.uuid4()),
                session_id=self.session_id,
                turn_number=turn_count,
                role="hari",
                content=dialogue.strip(),
                significance=significance,
                meaning_summary="",
                valence=self.state.valence,
                arousal=self.state.arousal,
            )
            await store_memory(memory_event)
        except Exception as e:
            logger.warning(f"Failed to store hari memory: {e}")

    async def _store_decision_trace(self, trace: DecisionTrace) -> None:
        try:
            from db.connection import get_pool
            pool = await get_pool()
            if not pool:
                return
            async with pool.acquire() as conn:
                drives_before_json = json.dumps(trace.drives_before)
                drives_after_json = json.dumps(trace.drives_after)
                viability_json = json.dumps(trace.viability_violations or [])
                feedback_json = json.dumps(trace.feedback_summary or {})
                reflection_json = json.dumps(trace.reflection_edits_applied or {})
                pursuit_json = json.dumps(trace.pursuit_registry_snapshot or {})

                workspace_rows = [
                    (
                        trace.trace_id, item.item_id, item.item_type,
                        item.source, item.raw_score, item.final_score, item.attention_weight,
                        item.content_snapshot, item.is_winner,
                        item.origin or "unknown",
                        item.activated_by or "unknown",
                        item.intrinsic_relevance or 0.0,
                        item.persistence or 0.0,
                    )
                    for item in trace.workspace_items
                ]

                async with conn.transaction():
                    await conn.execute("""
                        INSERT INTO decision_traces (
                            trace_id, session_id, turn_number, timestamp,
                            model_used, system_prompt_version, temperature,
                            incoming_text, reasoning_chain, generated_response,
                            retrieved_candidate_count, selected_winner_count,
                            drives_before, drives_after,
                            perceived_intent, intent_confidence, thematic_continuity,
                            prompt_tokens, completion_tokens, total_tokens, latency_ms,
                            error, behavior_mode, behavior_source,
                            contamination_hits, expression_mode, thread_survival,
                            held, internal_candidates_count, active_thought_count,
                            feedback_summary,
                            homeostatic_reward, viability_violations,
                            reflection_edits_applied, focus_stability_ratio,
                            winner_origin, pursuit_registry_snapshot,
                            event_present, event_was_winner, event_was_supporting,
                            event_was_ignored, social_update_applied,
                            expression_permitted, expression_reason
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
                            $13::jsonb, $14::jsonb, $15, $16, $17, $18, $19, $20, $21,
                            $22, $23, $24,
                            $25, $26, $27,
                            $28, $29, $30,
                            $31::jsonb,
                            $32, $33::jsonb,
                            $34::jsonb, $35,
                            $36, $37::jsonb,
                            $38, $39, $40,
                            $41, $42,
                            $43, $44
                        )
                    """,
                        trace.trace_id, trace.session_id, trace.turn_number, trace.timestamp,
                        trace.model_used, trace.system_prompt_version, trace.temperature,
                        trace.incoming_text, trace.reasoning_chain, trace.generated_response,
                        trace.retrieved_candidate_count, trace.selected_winner_count,
                        drives_before_json, drives_after_json,
                        trace.perceived_intent, trace.intent_confidence, trace.thematic_continuity,
                        trace.metrics.prompt_tokens, trace.metrics.completion_tokens,
                        trace.metrics.total_tokens, trace.metrics.latency_ms,
                        trace.error, trace.behavior_mode, trace.behavior_source,
                        trace.contamination_hits, trace.expression_mode, trace.thread_survival,
                        trace.held, trace.internal_candidates_count, trace.active_thought_count,
                        feedback_json,
                        trace.homeostatic_reward, viability_json,
                        reflection_json, trace.focus_stability_ratio,
                        trace.winner_origin, pursuit_json,
                        trace.event_present, trace.event_was_winner, trace.event_was_supporting,
                        trace.event_was_ignored, trace.social_update_applied,
                        trace.expression_permitted, trace.expression_reason,
                    )
                    if workspace_rows:
                        await conn.executemany("""
                            INSERT INTO trace_workspace_items (
                                trace_id, item_id, item_type, source,
                                raw_score, final_score, attention_weight,
                                content_snapshot, is_winner,
                                origin, activated_by, intrinsic_relevance, persistence
                            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                        """, workspace_rows)
        except Exception as db_err:
            logger.error(f"Failed to store DecisionTrace: {db_err}")

    def shutdown(self):
        if hasattr(self, "attention_instrumentation"):
            self.attention_instrumentation.close()
        if hasattr(self, "generativity_estimator"):
            logger.info(f"Generativity Summary: {self.generativity_estimator.get_summary()}")
        if hasattr(self, "_event_logger"):
            self._event_logger.log_session_end()


async def generate_lightweight_response(
    user_input, state, grace_tracker, turn_count,
    session_id="test", use_memory=False, use_workspace=False,
    use_monologue=True, trace_id=None,
):
    pipeline = TurnPipeline(session_id, state, grace_tracker)
    return await pipeline.execute(user_input, turn_count, trace_id=trace_id)
