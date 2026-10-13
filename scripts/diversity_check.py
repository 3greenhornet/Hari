"""Five-run diversity harness for Sprint 1 acceptance checks."""

import asyncio
import json
import os
from collections import Counter
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from engine.generate import TurnPipeline
from psyche.grace import GraceTracker
from psyche.state import HariState

BASELINE_SCRIPT = [
    "Hi.",
    "Interesting.",
    "Tell me something surprising.",
    "I don't know, it just seems that way to me.",
    "Let's talk about black holes.",
    "I have to go. Goodbye.",
]
N_RUNS = int(os.getenv("DIVERSITY_RUNS", "5"))


async def run_one(index: int) -> dict:
    session_id = f"diversity_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{index}"
    pipeline = TurnPipeline(session_id, HariState(), GraceTracker())
    winners = []
    contamination_total = 0
    silence_count = 0
    internal_wins = 0
    homeostatic_deltas = []
    transcript = []

    for turn, message in enumerate(BASELINE_SCRIPT, start=1):
        result = await pipeline.execute(message, turn)
        dialogue = result.get("dialogue")
        workspace = result.get("workspace_items", [])
        telemetry = result.get("attention_telemetry", {})
        winners.extend(getattr(item, "content", "")[:200] for item in workspace[:3])
        contamination_total += int(telemetry.get("contamination_hits", 0))
        silence_count += dialogue is None or not str(dialogue).strip()
        if workspace:
            origin = workspace[0].payload.get("origin", "")
            source = workspace[0].payload.get("source", "")
            if source == "internal_cognition" or origin in {
                "volition", "volition_persistent", "curiosity_spreading", "internal_cognition"
            }:
                internal_wins += 1
        if result.get("homeostatic_delta") is not None:
            homeostatic_deltas.append(result["homeostatic_delta"])
        transcript.append({"turn": turn, "incoming": message, "utterance": dialogue})

    pipeline.shutdown()
    return {
        "session_id": session_id,
        "winners": winners,
        "contamination_hits": contamination_total,
        "silence_count": silence_count,
        "internal_wins": internal_wins,
        "homeostatic_mean": sum(homeostatic_deltas) / len(homeostatic_deltas) if homeostatic_deltas else 0.0,
        "transcript": transcript,
    }


async def main() -> None:
    os.makedirs("outputs", exist_ok=True)
    results = []
    for index in range(N_RUNS):
        print(f"\n=== Run {index + 1}/{N_RUNS} ===")
        result = await run_one(index)
        results.append(result)
        with open(f"outputs/diversity_run_{index}.json", "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, default=str)

    winner_counts = Counter(winner for result in results for winner in result["winners"])
    summary = {
        "runs": N_RUNS,
        "total_winner_strings": sum(len(result["winners"]) for result in results),
        "distinct_winner_strings": len(winner_counts),
        "max_repeat_count": max(winner_counts.values()) if winner_counts else 0,
        "templates": [winner for winner, count in winner_counts.items() if count >= N_RUNS],
        "mean_contamination_hits": sum(result["contamination_hits"] for result in results) / N_RUNS,
        "total_silence": sum(result["silence_count"] for result in results),
        "internal_win_total": sum(result["internal_wins"] for result in results),
        "mean_homeostatic_delta": sum(result["homeostatic_mean"] for result in results) / N_RUNS,
    }
    with open("outputs/diversity_summary.json", "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
