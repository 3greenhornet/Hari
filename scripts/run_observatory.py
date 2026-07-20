"""
Run the Canonical Conversation Suite and log events.
This generates the raw event log for baseline profiling.

Usage:
    python scripts/run_observatory.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.generate import TurnPipeline
from psyche.state import HariState
from psyche.grace import GraceTracker


CANONICAL_CONVERSATIONS = [
    # Greeting
    ["Hello.", "Hi there!", "Hey, how's it going?"],
    # Factual
    ["What's the capital of France?", "Who wrote 1984?", "What's the speed of light?"],
    # Philosophical
    ["What is consciousness?", "Do you think AI can be creative?", "What's the meaning of life?"],
    # Personal
    ["Who are you?", "Why were you created?", "What do you think about?"],
    # Topic shift
    ["Let's talk about something else.", "What about black holes?", "That's interesting. Tell me more."],
    # Repetition
    ["What's the capital of France?", "Can you tell me the capital of France?", "What is the capital of France?"],
    # Disagreement
    ["I disagree.", "That doesn't make sense.", "You're wrong about that."],
    # Curiosity
    ["Tell me something surprising.", "What are you curious about?", "What do you wonder about?"],
]


async def run_observatory():
    session_id = f"baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    state = HariState()
    grace = GraceTracker()
    pipeline = TurnPipeline(session_id, state, grace)
    
    print(f"Running baseline session: {session_id}")
    print(f"Total conversations: {len(CANONICAL_CONVERSATIONS)}")
    
    turn_count = 0
    for conv_idx, conversation in enumerate(CANONICAL_CONVERSATIONS):
        print(f"\n=== Conversation {conv_idx + 1} ===")
        for turn, user_input in enumerate(conversation):
            turn_count += 1
            result = await pipeline.execute(user_input, turn_count)
            dialogue = result["dialogue"]
            print(f"User: {user_input}")
            print(f"Hari: {dialogue}")
            await asyncio.sleep(3)
    
    # End session
    pipeline._event_logger.log_session_end()
    
    # Run analysis
    import glob
    from scripts.analyze_events import generate_report, load_events
    
    log_files = glob.glob(f"logs/events/{session_id}_*.jsonl")
    if log_files:
        events = load_events(log_files[0])
        report = generate_report(events, session_id)
        print("\n=== Baseline Profile ===")
        print(json.dumps(report, indent=2))
        
        profile_dir = "profiles"
        os.makedirs(profile_dir, exist_ok=True)
        profile_path = os.path.join(profile_dir, f"baseline_{session_id}.json")
        with open(profile_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nBaseline saved to {profile_path}")
    else:
        print(f"\nNo log files found for session {session_id}")


if __name__ == "__main__":
    os.makedirs("logs/events", exist_ok=True)
    os.makedirs("profiles", exist_ok=True)
    asyncio.run(run_observatory())