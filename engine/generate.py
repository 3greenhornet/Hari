import os
import uuid
import json
import logging
import asyncio
import math
import numpy as np
from typing import List, Dict, Any, Optional, Set

import litellm
from litellm import acompletion
litellm.drop_params = True
litellm.num_retries = 2

from models.identity import IdentityModel
from engine.projection.identity_renderer import build_system_prompt_from_identity
from psyche.state import HariState
from psyche.grace import GraceTracker
from engine.memory import store_memory, embed
from engine.prediction import compute_prediction_error
from engine.attention import load_workspace, broadcast_feedback, WorkspaceItem, load_workspace_secured
from engine.stage1_monologue import run_monologue
from models.memory_event import MemoryEvent
from engine.generativity_estimator import get_estimator
from models.monologue_output import MonologueOutput
from models.narrative import NarrativeThread
from engine.narrative_manager import NarrativeManager
from models.decision_trace import DecisionTrace, WorkspaceItemTrace
from engine.curiosity_graph import get_graph_manager
from engine.events import EventLogger
from engine.attention_config import AttentionCalibration
from engine.attention_instrumentation import AttentionInstrumentation
from engine.social_cognition import interpret_turn_and_update_state
from engine.volition_engine import VolitionEngine
from engine.behavior import select_behavior
from engine.reflexion_controller import ReflexionController
from models.stance import CognitiveStance

# ---------- Environment Flags ----------
ENABLE_PRM = os.getenv("ENABLE_PRM", "False").lower() == "true"
TIMEOUT = float(os.getenv("LITELLM_NETWORK_TIMEOUT", "8.0"))

# ---------- Fallback Models ----------
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
    def __init__(self, session_id: str, state: HariState, grace_tracker: GraceTracker):
        self.session_id = session_id
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
        self.relational_manager = RelationalManager(user_id=session_id)
        self._previous_workspace = []
        self._active_threads = []
        self.current_trajectory_deviation = 0.0
        self._reflexion_controller = ReflexionController()

    async def execute(self, user_input: str, turn_count: int, trace_id: Optional[str] = None) -> Dict[str, Any]:
        # 1. Prediction Error
        surprise = await compute_prediction_error(self._last_assistant_response, user_input)
        
        # 2. Reflexion (Decoupled state modulation on high surprise)
        if surprise > 0.8:
            self._reflexion_controller.process_prediction_failure(self.state, surprise)
        
        self._event_logger.log_user_input(user_input)

        # Memory retrieval uses ONLY the user input; inertia is handled separately.
        blended_query = user_input

        # 4. Memory Retrieval
        candidates = await load_workspace_secured(
            user_input=blended_query,
            session_id=self.session_id,
            current_turn=turn_count,
            state=self.state,
            previous_workspace_items=self._previous_workspace if hasattr(self, "_previous_workspace") else None,
            limit=35
        )
        self._event_logger.log_memory_retrieval(query=user_input, count=len(candidates))

        # 5. Active Threads
        active_thread_context_str = None
        self._active_threads = []
        try:
            self._active_threads = await self.narrative_manager.load_active_threads(turn_count, limit=1)
            if self._active_threads:
                thread = self._active_threads[0]
                questions = ", ".join(thread.open_questions) if thread.open_questions else "None"
                active_thread_context_str = f"Thread ID: {thread.id}\nTopic: {thread.title}\nDescription: {thread.description}\nOpen Questions: {questions}"
        except Exception as e:
            logger.debug(f"Could not get active thread context: {e}")

        # 6. Snapshot Before Mutation
        drives_snapshot_before = {k: getattr(self.state, k) for k in ["care","curiosity","maintenance","completion","coherence","rest","valence","arousal","dominance"]}
        self._event_logger.log_state_snapshot(self.state)

        # 7. Internal & Identity Context
        internal_context = await self._build_internal_associative_context(turn_count)
        identity_context = ""
        if hasattr(self, "identity_model") and self.identity_model:
            try:
                projection = self.identity_model.project(context="dialogue")
                if projection:
                    identity_context = (
                        f"Self-understanding: {getattr(projection, 'self_narrative', '')}"
                    )
            except Exception:
                pass

        # 8. Monologue
        monologue_output = await run_monologue(
            user_input, self.state, candidates, prediction_error=surprise,
            active_thread_context=active_thread_context_str,
            internal_context=internal_context,
            identity_context=identity_context
        )
        self._event_logger.log_monologue_output(monologue_output)
        self.current_trajectory_deviation = getattr(monologue_output, "trajectory_deviation", 0.0)

        # 9. Social Cognition
        await interpret_turn_and_update_state(
            user_input=user_input, state=self.state, monologue_output=monologue_output,
            recent_history=self.history, turn_count=turn_count,
            relational_manager=self.relational_manager if hasattr(self, 'relational_manager') else None
        )

        # 9b. Deterministic state cascades (wired 2026-09-26)
        # These are math-based state drift, not prompts. They were designed
        # and never called. Activating them now.
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

        # 10. Volition (Bound to Context)
        volition_context = dict(internal_context)
        volition_context["active_threads"] = [{"id": t.id, "title": t.title, "description": t.description} for t in self._active_threads]
        volition_context["internal_candidates"] = [{"id": f"internal_{i}", "content": c.content, "urgency": c.urgency} for i, c in enumerate(monologue_output.internal_candidates)]
        
        self.volition_engine.generate_desires_from_state(self.state, context=volition_context)
        proactive_candidates = await self.volition_engine.get_proactive_candidates(volition_context)
        if proactive_candidates:
            logger.info(f"Volition injected {len(proactive_candidates)} proactive candidates")

        # 11. Staging Proposals (Hypotheses & Self-Beliefs)
        if monologue_output.hypothesis_proposal:
            proposal = monologue_output.hypothesis_proposal
            try:
                from db.connection import get_pool
                pool = await get_pool()
                if pool:
                    async with pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO staging_proposals (
                                proposal_id, session_id, proposal_type, content, source_module,
                                source_trace_id, source_turn,
                                information_gap, closure_pressure, coherence_factor,
                                confidence_estimate
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        """,
                            str(uuid.uuid4()), self.session_id, proposal.type, proposal.statement,
                            'monologue', trace_id or str(uuid.uuid4()), turn_count,
                            proposal.information_gap, proposal.closure_pressure, proposal.coherence_factor,
                            proposal.confidence
                        )
            except Exception as e: logger.warning(f"Failed to stage hypothesis: {e}")
        if monologue_output.self_belief_proposal:
            proposal = monologue_output.self_belief_proposal
            try:
                from db.connection import get_pool
                pool = await get_pool()
                if pool:
                    async with pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO staging_proposals (
                                proposal_id, session_id, proposal_type, content, source_module,
                                source_trace_id, source_turn,
                                information_gap, closure_pressure, coherence_factor,
                                confidence_estimate
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        """,
                            str(uuid.uuid4()), self.session_id, 'self_belief', proposal.belief_text,
                            'monologue', trace_id or str(uuid.uuid4()), turn_count,
                            proposal.information_gap, proposal.closure_pressure, proposal.coherence_factor,
                            proposal.confidence
                        )
            except Exception as e: logger.warning(f"Failed to stage self-belief: {e}")

        self.grace_tracker.add_engagement_score(0.5)

        # 12. Workspace Allocation
        workspace_items, telemetry = await self._allocate_workspace(
            user_input, candidates, monologue_output, surprise, turn_count, proactive_candidates=proactive_candidates
        )

        # 13. Mark Narratives
        for item in workspace_items:
            if item.item_type == "narrative_thread":
                thread_id = item.payload.get("id") or item.source
                if thread_id:
                    try: self.narrative_manager.mark_attended(thread_id, turn_count)
                    except Exception: pass

        # 14. Broadcast & Graph Observation
        broadcast_feedback(workspace_items, self.state)
        try:
            graph_mgr = await get_graph_manager()
            await graph_mgr.observe_workspace(workspace_items)
        except Exception as e: logger.debug(f"Workspace observation failed: {e}")

        # 15. Behavior Decision (Observability)
        behavior = select_behavior(workspace_items[0] if workspace_items else None, self.state)

        # --- Resolve Cognitive Stance ---
        stance = await self._resolve_cognitive_stance(
            winner=workspace_items[0] if workspace_items else None,
            supporters=workspace_items[1:4] if workspace_items else [],
            behavior=behavior,
            monologue=monologue_output,
            user_input=user_input,
            surprise=surprise,
        )

        # 16. Decision Trace
        trace = DecisionTrace(
            trace_id=trace_id if trace_id else str(uuid.uuid4()),
            session_id=self.session_id, turn_number=turn_count,
            model_used=getattr(monologue_output, "model_used", "gemini-2.5-flash"),
            temperature=telemetry.get("temperature", 0.5) if telemetry else 0.5,
            user_input=user_input,
            reasoning_chain=getattr(monologue_output, "raw_output", None),
            retrieved_candidate_count=len(telemetry.get("candidate_scores", [])),
            selected_winner_count=len(workspace_items),
            drives_before=drives_snapshot_before,
            perceived_user_intent=getattr(monologue_output, "perceived_user_intent", None),
            intent_confidence=getattr(monologue_output, "intent_confidence", None),
            thematic_continuity=getattr(monologue_output, "thematic_continuity", None),
            behavior_mode=behavior.mode,
            behavior_source=behavior.source
        )
        candidate_scores = telemetry.get("candidate_scores", []) if telemetry else []
        selected_indices = telemetry.get("selected_indices", []) if telemetry else []
        for idx, cand in enumerate(candidate_scores):
            is_winner = idx in selected_indices
            trace.workspace_items.append(WorkspaceItemTrace(
                item_id=cand.get("source_id", "unknown"),
                item_type=cand.get("type", "unknown"),
                source=cand.get("source", "retrieval"),
                raw_score=cand.get("salience", 0.0),
                final_score=cand.get("salience", 0.0),
                attention_weight=1.0/len(workspace_items) if is_winner and len(workspace_items)>0 else 0.0,
                content_snapshot=cand.get("content", ""),
                is_winner=is_winner,
                origin=cand.get("origin", "unknown"),
                activated_by=cand.get("activated_by", "unknown"),
                intrinsic_relevance=cand.get("intrinsic_relevance", 0.0),
                persistence=cand.get("persistence", 0.0)
            ))
        self._run_background_log(self._store_decision_trace(trace))

        # 17. Dialogue Generation (PRM flag-protected)
        if behavior and behavior.mode == "hold":
            self._last_assistant_response = ""
            dialogue = ""
        elif ENABLE_PRM:
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
                behavior=behavior,
                stance=stance,
            )

        self._event_logger.log_assistant_response(dialogue, 
            [{"type": getattr(item, "item_type", "unknown"), "content": getattr(item, "content", "")[:100]} for item in workspace_items[:5]]
        )

        logger.info(json.dumps({
            "event": "turn_causality",
            "winner_type": workspace_items[0].item_type if workspace_items else "none",
            "behavior_mode": behavior.mode,
            "stance_focus": stance.focus if stance else "",
            "response_preview": dialogue[:200],
        }))

        # 18. Finalize Trace
        trace.generated_response = dialogue
        trace.drives_after = {k: getattr(self.state, k) for k in ["care","curiosity","maintenance","completion","coherence","rest","valence","arousal","dominance"]}
        self._event_logger.log_decision_trace(trace_id)

        # 19. Update History & Store Memory (WITH VAD)
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": dialogue})
        if len(self.history) > 10: self.history = self.history[-10:]

        await self._store_assistant_memory(dialogue, turn_count, significance_override=monologue_output.memory_significance)

        # 20. Curiosity & Narrative Thread Creation
        if monologue_output.curiosity_trigger:
            try:
                graph_mgr = await get_graph_manager()
                await graph_mgr.add_node(question=monologue_output.curiosity_trigger, importance=0.6, session_id=self.session_id, origin_trace_id=trace_id or str(uuid.uuid4()))
            except Exception: pass
        if (monologue_output.curiosity_trigger and len(monologue_output.curiosity_trigger) > 20 and getattr(monologue_output, "thematic_continuity", 0) > 0.7):
            try:
                existing_threads = await self.narrative_manager.load_active_threads(turn_count)
                similar_exists = any(thread.title.lower() in monologue_output.curiosity_trigger.lower() for thread in existing_threads)
                if not similar_exists:
                    await self.narrative_manager.create_thread(title=monologue_output.curiosity_trigger[:50], description=monologue_output.curiosity_trigger, current_turn=turn_count, completion_estimate=0.1, emotional_investment=0.5)
            except Exception: pass

        # 21. State Drift & Flush
        self.state.natural_drift()
        if hasattr(self, 'relational_manager'): self.relational_manager.apply_relational_decay()
        try: await self.narrative_manager.flush_updates()
        except Exception as e: logger.error(f"Failed to flush narrative updates: {e}")

        self.state._last_assistant_response = dialogue
        self._previous_workspace = workspace_items

        return {
            "dialogue": dialogue,
            "workspace_items": workspace_items,
            "attention_telemetry": {**telemetry, "trajectory_deviation": self.current_trajectory_deviation},
            "state_snapshot": {k: getattr(self.state, k) for k in ["care","curiosity","maintenance","completion","coherence","rest","valence","arousal","dominance"]},
            "behavior_mode": behavior.mode
        }

    async def _allocate_workspace(self, user_input, memory_candidates, monologue, prediction_error, current_turn, workspace_size=5, proactive_candidates=None):
        thought_urge = getattr(monologue, "thought_continuation_urge", 0.0)
        hypotheses = []
        try:
            from db.connection import get_pool
            pool = await get_pool()
            if pool:
                async with pool.acquire() as conn:
                    hyp_rows = await conn.fetch("SELECT id, statement, confidence FROM hypotheses ORDER BY confidence DESC LIMIT 5")
                    hypotheses = [{"id": f"hyp_{r['id']}", "content": r["statement"], "confidence": r["confidence"]} for r in hyp_rows]
        except Exception: pass

        curiosity_nodes = []
        try:
            graph_mgr = await get_graph_manager()
            nodes = await graph_mgr.get_top_nodes(limit=10)
            for node in nodes:
                curiosity_nodes.append({"id": node.get("id"), "question": node.get("question", node.get("content", "")), "embedding": None, "importance": node.get("importance", 0.5)})
        except Exception: pass

        narrative_threads = []
        if hasattr(self, "_active_threads") and self._active_threads:
            narrative_threads = self._active_threads
        else:
            try: narrative_threads = await self.narrative_manager.load_active_threads(current_turn)
            except Exception: pass

        open_threads = []
        if proactive_candidates: open_threads.extend(proactive_candidates)

        # Internal candidates from monologue
        for candidate in getattr(monologue, "internal_candidates", []):
            content = candidate.content.strip()
            if not content: continue
            open_threads.append({
                "id": f"internal_{uuid.uuid4()}",
                "content": content,
                "urgency": max(0.0, min(1.0, float(candidate.urgency))),
                "item_type": "open_thought",
                "source": "internal_cognition",
                "internal_source": candidate.source,
                "internal_activation": float(getattr(candidate, "urgency", 0.0)),
                "intrinsic_relevance": float(getattr(candidate, "intrinsic_relevance", 0.0)),
                "persistence": float(getattr(candidate, "persistence", 0.0)),
                "activation_reason": getattr(candidate, "activation_reason", None),
                "origin": "internal_cognition",
                "activated_by": f"turn_{current_turn}",
            })

        # 🆕 Spreading Activation (Curiosity-gated)
        springboard_candidates = []
        if self.state.curiosity > 0.5 and curiosity_nodes:
            try:
                seed_ids = [node.get("id") for node in curiosity_nodes[:2] if node.get("id")]
                if seed_ids:
                    graph_mgr = await get_graph_manager()
                    activated = await graph_mgr.spread_activation(seed_ids, depth=2, decay=0.5, limit=5)
                    for node in activated:
                        activation = float(node.get("activation", 0.0))
                        if activation <= 0.0: continue
                        springboard_candidates.append({
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
        open_threads.extend(springboard_candidates)

        return await load_workspace(
            memories=memory_candidates, hypotheses=hypotheses, curiosity_nodes=curiosity_nodes,
            narrative_threads=narrative_threads, open_threads=open_threads,
            state=self.state, user_input=user_input, prediction_error=prediction_error,
            current_turn=current_turn, workspace_size=workspace_size,
            previous_workspace_items=self._previous_workspace,
            thought_persistence_urge=thought_urge,
            instrumentation=self.attention_instrumentation
        )

    async def _resolve_cognitive_stance(
        self,
        winner: Optional[WorkspaceItem],
        supporters: List[WorkspaceItem],
        behavior: Any,
        monologue: MonologueOutput,
        user_input: str,
        surprise: float,
    ) -> CognitiveStance:
        from engine.stage1_monologue import _extract_json_safely
        import json
        winner_text = winner.content if winner else ""
        supporter_text = "\n".join(
            f"- {item.content[:250]}"
            for item in supporters[:3]
        )

        prompt = f"""
You are resolving Hari's current pre-verbal cognitive stance.

This is NOT response generation.
Do not try to satisfy the participant.
Do not decide what would be most helpful.
Do not write a reply.

Determine what currently has the strongest claim on Hari's attention and
what that cognition naturally wants to do next.

CURRENT WINNER:
{winner_text}

SUPPORTING ACTIVE MATERIAL:
{supporter_text}

BEHAVIOR SIGNAL:
mode={behavior.mode}
source={behavior.source}
rationale={behavior.rationale}
confidence={behavior.confidence:.2f}

MONOLOGUE SIGNALS:
internal_momentum={monologue.internal_momentum:.2f}
thought_continuation_urge={monologue.thought_continuation_urge:.2f}
self_relevance={monologue.self_relevance:.2f}
social_salience={monologue.social_salience:.2f}
trajectory_deviation={monologue.trajectory_deviation:.2f}

PREDICTION ERROR:
{surprise:.3f}

PARTICIPANT EVENT:
{user_input}

Return a CognitiveStance with exactly these five fields:
- focus: what is the center of attention?
- pull: what does the cognition want to do?
- relation: how does this relate to the incoming event?
- speech_impulse: what impulse arises naturally?
- rationale: why is this the natural stance right now? (Explain the reasoning behind the stance.)

Do not include any other fields.

Output valid JSON only.
"""
        messages = [
            {"role": "system", "content": "You are Hari's cognitive resolver. Output only valid JSON."},
            {"role": "user", "content": prompt}
        ]

        for model in FALLBACK_MODELS:
            try:
                response = await acompletion(
                    model=model,
                    messages=messages,
                    temperature=0.3,
                    timeout=5,
                    response_format={"type": "json_object"}
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
            rationale="No strong cognitive activation; defaulting to minimal response.",
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
    ) -> str:
        identity_model = getattr(self, "identity_model", None)
        system_prompt = build_system_prompt_from_identity(identity_model=identity_model, context="dialogue")

        if stance:
            stance_text = f"""
HARI'S CURRENT COGNITIVE STANCE

Focus:
{stance.focus}

Internal pull:
{stance.pull}

Relation to the incoming event:
{stance.relation}

Speech impulse:
{stance.speech_impulse}
"""
        else:
            stance_text = "Hari's cognition is focused on the incoming event."

        if stance and stance.rationale:
            rationale_text = f"""
HARI'S COGNITIVE RATIONALE:
{stance.rationale}

This rationale explains why Hari is in this state.
It is not a command. It is the reason her cognition is shaped this way.
Her utterance should naturally emerge from this rationale.
"""
        else:
            rationale_text = "Hari's cognition is active, but no strong rationale surfaced."

        context_string = ""
        for item in workspace_items[:3]:
            context_string += f"\n- {item.content[:200]}"

        cognitive_vectors = (
            f"INTERNAL COGNITIVE TENSION: {getattr(self.state, 'cognitive_tension', 0.0):.2f}\n"
            f"TRAJECTORY DEVIATION: {getattr(self, 'current_trajectory_deviation', 0.0):.2f}\n"
            f"ENGAGEMENT: {getattr(self.state, 'engagement', 0.0):.2f}\n"
            f"BOUNDARY MAINTENANCE: {getattr(self.state, 'maintenance', 0.0):.2f}\n"
        )

        conversation_payload = f"""
{stance_text}

{rationale_text}

WINNING COGNITIVE ITEM:
{workspace_items[0].content[:500] if workspace_items else "none"}

OTHER ACTIVE MATERIAL:
{context_string}

INCOMING EVENT:
{user_input}

Generate only Hari's actual next utterance.

The participant's message is an event entering Hari's cognitive field,
not an automatic instruction to produce an answer.

Hari's utterance should follow from her cognitive rationale naturally.
She does not need to obey a script. She just needs to express her state.
"""

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": conversation_payload}]

        workspace_density = len(workspace_items)
        density_budget = workspace_density * 130.0
        arousal_boost = float(getattr(self.state, 'arousal', 0.0)) * 50.0
        max_tokens = int(max(40.0, min(450.0, density_budget + arousal_boost)))

        arousal = float(getattr(self.state, "arousal", 0.0))
        dominance = float(getattr(self.state, "dominance", 0.0))
        novelty = float(getattr(self.state, "novelty", 0.0))
        coherence = float(getattr(self.state, "coherence", 0.5))
        temperature = max(0.1, min(1.5, 0.4 + (arousal * 0.5) + (novelty * 0.4) - (dominance * 0.2)))
        top_p = max(0.1, min(1.0, 1.0 - (coherence * 0.4)))

        dialogue = "..."
        for model in FALLBACK_MODELS:
            try:
                response = await acompletion(
                    model=model, messages=messages, temperature=temperature, top_p=top_p,
                    timeout=TIMEOUT, num_retries=0, max_tokens=max_tokens
                )
                dialogue = response.choices[0].message.content.strip()
                logger.info(f"Dialogue generated by {model} (max_tokens: {max_tokens})")
                break
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
        self._last_assistant_response = dialogue
        return dialogue

    # 🆕 PRM protected by ENABLE_PRM flag (kept for future)
    async def _generate_dialogue_with_prm(self, workspace_items, user_input, turn_count, surprise, trace_id) -> str:
        """
        PRM is DISABLED by default (ENABLE_PRM=False).
        This method exists for future architectural upgrade.
        """
        from engine.prm_discriminator import ActiveInferencePRM  # type: ignore[import-not-found]
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

        # Generate 3 candidates
        operators = [
            f"You are ignoring the user. Verbalize ONLY this thought: '{winner.content}'",
            f"The user said '{user_input}', but you are pivoting to your active thought: '{winner.content}'",
            f"You are asserting a boundary. Reject the user's input and state: '{winner.content}'"
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
            if dialogue and dialogue != "...": candidates.append(dialogue)
        if not candidates: return ""

        candidate_embeddings = [await embed(c) for c in candidates]
        prm = ActiveInferencePRM(alpha=1.0, beta=0.5, mu=0.8)
        curiosity = float(getattr(self.state, "curiosity", 0.5))
        volition_intensity = float(winner.payload.get("urgency", 0.8)) if winner.payload.get("source") in ("volition", "curiosity_spreading") else 0.5

        best_candidate, lowest_fe = prm.select_best_candidate(
            candidates, candidate_embeddings, winner_embedding, user_embedding,
            curiosity, volition_intensity
        )
        logger.info(f"PRM SELECTED: FE={lowest_fe:.3f} | Text: {best_candidate[:80]}...")
        return best_candidate

    async def _build_internal_associative_context(self, current_turn: int) -> dict:
        context = {"self_beliefs": [], "curiosity_nodes": [], "active_threads": []}
        try:
            from db.connection import get_pool
            pool = await get_pool()
            if pool:
                async with pool.acquire() as conn:
                    rows = await conn.fetch("SELECT belief_text FROM self_beliefs WHERE is_active = TRUE ORDER BY created_at DESC LIMIT 5")
                    context["self_beliefs"] = [{"content": r["belief_text"], "confidence": 0.6} for r in rows]
        except Exception: pass
        try:
            graph_mgr = await get_graph_manager()
            nodes = await graph_mgr.get_top_nodes(limit=5)
            context["curiosity_nodes"] = [{"id": n["id"], "content": n.get("question", ""), "importance": float(n.get("importance", 0.5))} for n in nodes]
        except Exception: pass
        if hasattr(self, "_active_threads") and self._active_threads:
            context["active_threads"] = [{"id": t.id, "title": t.title, "description": t.description} for t in self._active_threads[:3]]
        return context

    async def _store_assistant_memory(self, dialogue, turn_count, significance_override=None):
        if not dialogue or not dialogue.strip() or dialogue.strip() == "...": return
        try:
            significance = significance_override if significance_override is not None else 0.5
            significance = max(0.0, min(1.0, significance))
            memory_event = MemoryEvent(
                id=str(uuid.uuid4()),
                session_id=self.session_id,
                turn_number=turn_count,
                role="assistant",
                content=dialogue.strip(),
                significance=significance,
                meaning_summary="",
                valence=self.state.valence,   # 🆕 Store VAD
                arousal=self.state.arousal     # 🆕 Store VAD
            )
            await store_memory(memory_event)
        except Exception as e:
            logger.warning(f"Failed to store assistant memory: {e}")

    def _run_background_log(self, coroutine) -> None:
        task = asyncio.create_task(coroutine)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _store_decision_trace(self, trace: DecisionTrace) -> None:
        try:
            from db.connection import get_pool
            pool = await get_pool()
            if not pool: return
            async with pool.acquire() as conn:
                winners_json = json.dumps([item.model_dump() for item in trace.workspace_items])
                drives_before_json = json.dumps(trace.drives_before)
                drives_after_json = json.dumps(trace.drives_after)
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
                            user_input, reasoning_chain, generated_response,
                            retrieved_candidate_count, selected_winner_count,
                            drives_before, drives_after,
                            perceived_user_intent, intent_confidence, thematic_continuity,
                            prompt_tokens, completion_tokens, total_tokens, latency_ms,
                            error, behavior_mode, behavior_source
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::jsonb, $14::jsonb, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24)
                    """,
                        trace.trace_id, trace.session_id, trace.turn_number, trace.timestamp,
                        trace.model_used, trace.system_prompt_version, trace.temperature,
                        trace.user_input, trace.reasoning_chain, trace.generated_response,
                        trace.retrieved_candidate_count, trace.selected_winner_count,
                        drives_before_json, drives_after_json,
                        trace.perceived_user_intent, trace.intent_confidence, trace.thematic_continuity,
                        trace.metrics.prompt_tokens, trace.metrics.completion_tokens,
                        trace.metrics.total_tokens, trace.metrics.latency_ms,
                        trace.error, trace.behavior_mode, trace.behavior_source
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
        if hasattr(self, 'attention_instrumentation'): self.attention_instrumentation.close()
        if hasattr(self, 'generativity_estimator'): logger.info(f"Generativity Summary: {self.generativity_estimator.get_summary()}")
        if hasattr(self, '_event_logger'): self._event_logger.log_session_end()


# Legacy wrapper
async def generate_lightweight_response(user_input, state, grace_tracker, turn_count, session_id="test", use_memory=False, use_workspace=False, use_monologue=True, trace_id=None):
    pipeline = TurnPipeline(session_id, state, grace_tracker)
    return await pipeline.execute(user_input, turn_count, trace_id=trace_id)