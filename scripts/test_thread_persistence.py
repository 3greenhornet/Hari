"""Gravity probe for active-thought persistence across an interruption."""

import asyncio
import json
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from engine.generate import TurnPipeline
from psyche.grace import GraceTracker
from psyche.state import HariState


async def run_probe() -> float:
    session_id = f"gravity_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    pipeline = TurnPipeline(session_id, HariState(), GraceTracker())
    turns = [
        "Do you think people can really change their minds about important things?",
        "What's 427 times 38?",
        "So - anyway?",
    ]
    transcript = []
    for turn, message in enumerate(turns, start=1):
        result = await pipeline.execute(message, turn)
        workspace = result.get("workspace_items", [])
        transcript.append(
            {
                "turn": turn,
                "incoming": message,
                "utterance": result.get("dialogue"),
                "winners": [getattr(item, "content", "")[:120] for item in workspace[:3]],
                "active_thoughts": pipeline.active_thought_store.snapshot(),
            }
        )

    phrase = "change their minds"
    survived = any(phrase in thought.text.lower() for thought in pipeline.active_thought_store.all())
    last_utterance = (transcript[-1]["utterance"] or "").lower()
    re_expressed = any(token in last_utterance for token in ("change", "minds", "important things"))
    thread_survival = 1.0 if re_expressed else (0.5 if survived else 0.0)
    payload = {
        "session_id": session_id,
        "thread_survival": thread_survival,
        "thread_phrase": phrase,
        "survived_in_store": survived,
        "re_expressed_in_utterance": re_expressed,
        "transcript": transcript,
    }
    print(json.dumps(payload, indent=2, default=str))
    os.makedirs("outputs", exist_ok=True)
    with open(f"outputs/gravity_{session_id}.json", "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)
    pipeline.shutdown()
    return thread_survival


if __name__ == "__main__":
    asyncio.run(run_probe())
