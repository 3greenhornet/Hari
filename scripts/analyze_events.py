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
    """Compute initiative score: fraction of turns with curiosity trigger."""
    curiosity_count = 0
    total_turns = 0
    for event in events:
        if event["event_type"] == "monologue_output":
            total_turns += 1
            if event["payload"].get("curiosity_trigger"):
                curiosity_count += 1
    return curiosity_count / max(1, total_turns)


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