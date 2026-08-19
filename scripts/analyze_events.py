"""
Offline analysis of event logs.
Computes metrics, profiles, and reports from raw events.

Usage:
    python scripts/analyze_events.py logs/events/session_*.jsonl
"""

import json
import sys
import glob
import os
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime
from enum import Enum
import math
import statistics


def load_events(file_path: str) -> List[Dict[str, Any]]:
    """Load events from a JSONL file."""
    events = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    return events


def compute_mirroring(events: List[Dict[str, Any]]) -> float:
    """
    Compute mirroring score from events.
    Jaccard similarity of user and assistant word sets.
    """
    user_inputs = []
    assistant_responses = []
    for event in events:
        if event["event_type"] == "user_input":
            user_inputs.append(event["payload"]["content"])
        elif event["event_type"] == "assistant_response":
            assistant_responses.append(event["payload"]["content"])
    
    if not user_inputs or not assistant_responses:
        return 0.0
    
    user_words = set()
    for text in user_inputs:
        user_words.update(text.lower().split())
    
    assistant_words = set()
    for text in assistant_responses:
        assistant_words.update(text.lower().split())
    
    if not user_words or not assistant_words:
        return 0.0
    
    overlap = len(user_words.intersection(assistant_words))
    union = len(user_words.union(assistant_words))
    return overlap / union if union > 0 else 0.0


def compute_initiative(events: List[Dict[str, Any]]) -> float:
    """Compute initiative score: fraction of turns where the assistant initiated.

    Uses workspace composition when available: if a workspace item is an
    `open_thought`, `curiosity_node`, or `narrative_thread` and its `source`
    indicates `volition` or `curiosity_spreading`, it's counted as an initiative.
    Falls back to monologue curiosity_trigger when workspace data is missing.
    """
    def classify_initiative_from_comp(comp: List[Dict[str, Any]]) -> bool:
        for item in comp or []:
            itype = item.get("type") or item.get("item_type")
            source = item.get("source")
            if itype in ("open_thought", "curiosity_node", "narrative_thread"):
                if source in ("volition", "curiosity_spreading"):
                    return True
        return False

    # Build turns from events (match assistant_response -> workspace_composition)
    turns = defaultdict(dict)
    for event in events:
        t = event.get("turn_number", 0)
        if event["event_type"] == "assistant_response":
            turns[t]["assistant_response"] = event["payload"].get("content")
            turns[t]["workspace_composition"] = event["payload"].get("workspace_composition")
        elif event["event_type"] == "monologue_output":
            turns[t]["monologue"] = event["payload"]

    total_turns = len(turns)
    if total_turns == 0:
        return 0.0

    initiative_count = 0
    for t, data in turns.items():
        comp = data.get("workspace_composition")
        if comp:
            if classify_initiative_from_comp(comp):
                initiative_count += 1
                continue
        # Fallback: use monologue curiosity trigger
        mon = data.get("monologue")
        if mon and mon.get("curiosity_trigger"):
            initiative_count += 1

    return initiative_count / max(1, total_turns)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    try:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)
    except Exception:
        return 0.0


def compute_topic_drift(events: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute topic drift distribution (mean, std) using available embeddings.

    Expects per-turn embeddings to be present either in assistant_response payload
    under `embedding` or in workspace_composition items. If embeddings are missing,
    returns zeros.
    """
    # Collect embeddings per turn (prefer assistant_response.embedding)
    turns = {}
    for event in events:
        if event["event_type"] == "assistant_response":
            emb = event["payload"].get("embedding")
            if emb:
                turns[event.get("turn_number", 0)] = emb
        # Also check workspace composition items
        if event["event_type"] == "assistant_response":
            comp = event["payload"].get("workspace_composition") or []
            for item in comp:
                if item.get("embedding"):
                    # Use first available embedding for the turn if none set
                    turns.setdefault(event.get("turn_number", 0), item.get("embedding"))

    if len(turns) < 2:
        return {"mean": 0.0, "std": 0.0}

    ordered = [turns[t] for t in sorted(turns.keys())]
    drifts = []
    for i in range(len(ordered) - 1):
        a = ordered[i]
        b = ordered[i + 1]
        cs = _cosine_similarity(a, b)
        drifts.append(1.0 - cs)

    if not drifts:
        return {"mean": 0.0, "std": 0.0}
    mean = sum(drifts) / len(drifts)
    std = statistics.stdev(drifts) if len(drifts) > 1 else 0.0
    return {"mean": mean, "std": std}


class ConversationMove(Enum):
    FOLLOW = "follow"
    DEEPEN = "deepen"
    ASSOCIATE = "associate"
    PIVOT = "pivot"
    JOKE = "joke"
    CHALLENGE = "challenge"
    REVISIT = "revisit"
    SHARE = "share"
    WANDER = "wander"


def classify_move(workspace_composition: List[Dict[str, Any]], user_input: str, response: str) -> ConversationMove:
    """Heuristic move classification based on simple cues.

    This is intentionally lightweight; a fuller implementation would call an
    LLM classifier or more advanced heuristics.
    """
    resp = (response or "").lower()
    user = (user_input or "").lower()
    types = {item.get("type") for item in (workspace_composition or [])}

    if any(w in resp for w in ["lol", "haha", "😂", "joke"]):
        return ConversationMove.JOKE
    if "?" in resp and len(resp.split()) < 12:
        return ConversationMove.FOLLOW
    if any(t in types for t in ("curiosity_node", "narrative_thread")) and "i think" in resp:
        return ConversationMove.DEEPEN
    # Pivot detection: low word overlap between user and assistant
    user_words = set(user.split())
    resp_words = set(resp.split())
    overlap = len(user_words.intersection(resp_words))
    if user_words and overlap / max(1, len(user_words)) < 0.2:
        return ConversationMove.PIVOT
    if any(t == "open_thought" for t in types) and any(w in resp for w in ["i think", "i feel", "i believe"]):
        return ConversationMove.SHARE
    return ConversationMove.WANDER


def compute_drive_movement(events: List[Dict[str, Any]]) -> float:
    """Compute average drive movement from state snapshots."""
    snapshots = []
    for event in events:
        if event["event_type"] == "state_snapshot":
            snapshots.append(event["payload"])
    
    if len(snapshots) < 2:
        return 0.0
    
    drives = ["care", "curiosity", "maintenance", "completion", "coherence", "rest"]
    movements = []
    for i in range(len(snapshots) - 1):
        delta = 0.0
        for drive in drives:
            delta += abs(snapshots[i+1].get(drive, 0.0) - snapshots[i].get(drive, 0.0))
        movements.append(delta / len(drives))
    
    return sum(movements) / len(movements) if movements else 0.0


def compute_workspace_diversity(events: List[Dict[str, Any]]) -> float:
    """Compute average workspace diversity from events."""
    compositions = []
    for event in events:
        if event["event_type"] == "assistant_response":
            if "workspace_composition" in event["payload"]:
                compositions.append(event["payload"]["workspace_composition"])
    
    if not compositions:
        return 0.0
    
    avg_types = 0.0
    for comp in compositions:
        types = set(item["type"] for item in comp)
        avg_types += len(types)
    avg_types /= len(compositions)
    
    return min(1.0, avg_types / 5.0)


def compute_avg_response_length(events: List[Dict[str, Any]]) -> float:
    """Compute average response length."""
    lengths = []
    for event in events:
        if event["event_type"] == "assistant_response":
            lengths.append(event["payload"].get("length", 0))
    return sum(lengths) / max(1, len(lengths))


def generate_report(events: List[Dict[str, Any]], session_id: str) -> Dict[str, Any]:
    """Generate a full report from events."""
    return {
        "session_id": session_id,
        "total_events": len(events),
        "total_turns": len([e for e in events if e["event_type"] == "assistant_response"]),
        "mirroring": compute_mirroring(events),
        "initiative": compute_initiative(events),
        "drive_movement": compute_drive_movement(events),
        "workspace_diversity": compute_workspace_diversity(events),
        "avg_response_length": compute_avg_response_length(events),
        "timestamp": datetime.now().isoformat()
    }


def main():
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = glob.glob("logs/events/*.jsonl")
    
    if not files:
        print("No event log files found.")
        print("Usage: python scripts/analyze_events.py [file1.jsonl file2.jsonl ...]")
        return
    
    for file_path in files:
        events = load_events(file_path)
        session_id = os.path.basename(file_path).split("_")[0]
        report = generate_report(events, session_id)
        print(json.dumps(report, indent=2))
        
        # Save report
        report_dir = "profiles"
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, f"report_{session_id}.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to {report_path}")


if __name__ == "__main__":
    main()