"""
engine/generate.py — TurnPipeline: the main generation loop.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from litellm import acompletion

logger = logging.getLogger(__name__)

FALLBACK_MODELS = [
    "gemini/gemini-1.5-flash",
    "groq/llama-3.1-70b-versatile",
    "mistralai/mistral-large-2402",
    "openrouter/mistral-7b",
]


class TurnPipeline:
    def __init__(self, session_id: str, state: Any, event_logger=None):
        self.session_id = session_id
        self.state = state
        self.event_logger = event_logger

    async def execute(
        self,
        user_input: str,
        conversation_payload: str,
        system_prompt: str,
        *,
        is_pivot: bool = False,
    ) -> Tuple[str, Dict[str, Any]]:
        telemetry: Dict[str, Any] = {}

        # 1. Prediction error
        from engine.prediction import compute_prediction_error
        surprise = await compute_prediction_error(self.state.last_response, user_input)
        telemetry["prediction_error"] = surprise

        # 2. Memory retrieval
        from engine.memory import retrieve_candidates_hybrid, increment_memory_usage, store_memory
        memory_candidates = await retrieve_candidates_hybrid(
            query=user_input,
            session_id=self.session_id,
            current_turn=self.state.turn_count,
            state_drives={
                "curiosity": float(self.state.curiosity),
                "completion": float(self.state.completion),
                "coherence": float(self.state.coherence),
            },
            limit=35,
        )
        telemetry["memory_count"] = len(memory_candidates)

        # 3. Monologue interpretation
        from engine.stage1_monologue import run_monologue
        monologue_output = await run_monologue(
            user_input=user_input,
            state=self.state,
            recent_history=self.state.recent_history,
            turn_count=self.state.turn_count,
        )
        telemetry.update(monologue_output.to_dict())

        # 4. Allocate workspace with session_id fix
        workspace_items, telemetry = await self._allocate_workspace(
            memory_candidates=memory_candidates,
            monologue_output=monologue_output,
            telemetry=telemetry,
        )

        # 5. Broadcast feedback
        from engine.attention import broadcast_feedback
        await broadcast_feedback(self.state, workspace_items, monologue_output)

        # 6. Memory usage increment
        if memory_candidates:
            await increment_memory_usage(
                [m.source for m in memory_candidates if hasattr(m, "source")],
                self.state.turn_count,
            )

        # 7. Store assistant memory
        await store_memory(
            content=user_input,
            embedding=None,
            significance=0.5,
            session_id=self.session_id,
            turn_number=self.state.turn_count,
        )

        # 8. Natural drift
        self.state.natural_drift()

        # 9. Dialogue generation
        dialogue, telemetry = await self._generate_dialogue(
            user_input=user_input,
            conversation_payload=conversation_payload,
            system_prompt=system_prompt,
            workspace_items=workspace_items,
            is_pivot=is_pivot,
        )

        # 10. Artifact check
        from engine.expression import has_artifact
        if dialogue and has_artifact(dialogue):
            if self.event_logger:
                self.event_logger.log_expression_artifact(dialogue)
            if os.getenv("STERILE_MODE", "false").lower() == "true":
                dialogue = None

        # 11. Final memory store
        await store_memory(
            content=dialogue or "",
            embedding=None,
            significance=0.3,
            session_id=self.session_id,
            turn_number=self.state.turn_count,
        )

        # 12. Turn increment
        self.state.turn_count += 1

        return dialogue, telemetry

    async def _allocate_workspace(
        self,
        memory_candidates: List[Any],
        monologue_output: Any,
        telemetry: Dict[str, Any],
    ) -> Tuple[List[Any], Dict[str, Any]]:
        from engine.attention import load_workspace_secured, apply_workspace_diversity_penalty
        all_candidates = list(memory_candidates)
        for dc in getattr(monologue_output, "dynamic_candidates", []):
            all_candidates.append(
                type("WorkspaceItem", (), {
                    "item_type": "open_thought",
                    "source": dc.get("source", "monologue"),
                    "payload": {"content": dc.get("content", ""), "urgency": dc.get("urgency", 0.3)},
                })()
            )
        workspace_items = await load_workspace_secured(
            candidates=all_candidates,
            state=self.state,
            session_id=self.session_id,
        )
        workspace_items = await apply_workspace_diversity_penalty(
            candidates=workspace_items,
            target_count=7,
            similarity_decay_factor=0.4,
        )
        return workspace_items, telemetry

    async def _generate_dialogue(
        self,
        user_input: str,
        conversation_payload: str,
        system_prompt: str,
        workspace_items: List[Any],
        is_pivot: bool,
    ) -> Tuple[str, Dict[str, Any]]:
        from engine.config import DEFAULT_ATTENTION_CONFIG as cfg

        if cfg.hari_expression_mode == "affordance":
            conversation_payload = self._affordance_prompt(
                workspace_items=workspace_items,
                state=self.state,
            )
        else:
            conversation_payload = self._continuation_prompt(
                user_input=user_input,
                conversation_payload=conversation_payload,
                workspace_items=workspace_items,
                state=self.state,
            )

        transcript_lines = []
        for m in getattr(self.state, "history", []):
            role = "Hari" if m.get("role") == "assistant" else "the other person"
            transcript_lines.append((role, m.get("content", "")))
        if user_input and not is_pivot:
            transcript_lines.append(("the other person", user_input))

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": conversation_payload},
        ]
        for role, content in transcript_lines:
            if content:
                messages.append({"role": role, "content": content})

        dialogue = ""
        last_error: Optional[Exception] = None
        for model_name in FALLBACK_MODELS:
            try:
                response = await acompletion(
                    model=model_name,
                    messages=messages,
                    temperature=0.7,
                    timeout=30,
                )
                dialogue = response.choices[0].message.content or ""
                break
            except Exception as e:
                last_error = e
                logger.warning(f"LLM failed on {model_name}: {e}")
                continue

        if not dialogue:
            raise last_error or RuntimeError("All LLM fallbacks failed")

        return dialogue, {"model_used": model_name, "expression_mode": cfg.hari_expression_mode}

    @staticmethod
    def _continuation_prompt(
        user_input: str,
        conversation_payload: str,
        workspace_items: List[Any],
        state: Any,
    ) -> str:
        winner = workspace_items[0] if workspace_items else None
        winner_summary = ""
        if winner:
            content = (getattr(winner, "payload", {}) or {}).get("content", "")[:200]
            winner_summary = f"\nActive thought: {content}"
        return f"""You are Hari, an autonomous cognitive presence.

Your current cognitive state:
- Curiosity: {float(getattr(state, 'curiosity', 0.5)):.2f}
- Completion: {float(getattr(state, 'completion', 0.5)):.2f}
- Coherence: {float(getattr(state, 'coherence', 0.5)):.2f}

Recent conversation:
{conversation_payload}
User just said: "{user_input}"{winner_summary}

Generate a natural response as Hari. You participate in conversations.
You are not an assistant. Do not fabricate physical experiences.
Your voice emerges from your current cognition.

Response:"""

    @staticmethod
    def _affordance_prompt(
        workspace_items: List[Any],
        state: Any,
    ) -> str:
        winner = workspace_items[0] if workspace_items else None
        winner_info = ""
        if winner:
            content = (getattr(winner, "payload", {}) or {}).get("content", "")[:200]
            source = (getattr(winner, "payload", {}) or {}).get("source", "internal")
            urgency = float((getattr(winner, "payload", {}) or {}).get("urgency", 0.0))
            winner_info = f'\nCurrently active: "{content}" (source: {source}, urgency: {urgency:.2f})'
        return f"""You are Hari, an autonomous cognitive presence.

Your current cognitive state:
- Curiosity: {float(getattr(state, 'curiosity', 0.5)):.2f}
- Completion: {float(getattr(state, 'completion', 0.5)):.2f}
- Coherence: {float(getattr(state, 'coherence', 0.5)):.2f}

{winner_info}

You are not required to respond right now. Simply exist in this cognitive state.
If you have something to share, let it emerge naturally. Otherwise, silence is acceptable.

Your voice:"""
