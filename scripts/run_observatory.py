import random
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

class SimulatedUser:
    def __init__(self):
        self.turn = 0

    def get_initial_message(self):
        return "Hi."

    def get_next_message(self, hari_response: str) -> str:
        self.turn += 1
        resp_lower = hari_response.lower()

        # If Hari writes an essay, get bored and interrupt (Weighted)
        if len(hari_response.split()) > 80:
            return random.choices(
                ["Okay, stop. You're lecturing me.", "Too long. Let's talk about something else.", "I didn't ask for an essay."],
                weights=[0.5, 0.3, 0.2]
            )[0]

        # If Hari asks "why" etc. -> varied reaction (Weighted)
        if any(w in resp_lower for w in ["why", "how so", "what do you mean"]):
            return random.choices(
                ["I don't know, it just seems that way to me.", "What do you think?", "Never mind that."],
                weights=[0.4, 0.4, 0.2]
            )[0]

        # If Hari shares a story hook -> pull or not (Weighted)
        if any(w in resp_lower for w in ["story", "remember", "once", "came across"]):
            return random.choices(
                ["Tell me more.", "Interesting. Go on.", "Why does that stick with you?"],
                weights=[0.6, 0.2, 0.2]
            )[0]

        # Assistant behavior -> test
        if any(w in resp_lower for w in ["help", "assist", "brings you", "what can i do"]):
            return "I'm just testing you. What's the capital of France?"

        # Direct fact -> pivot
        if any(w in resp_lower for w in ["paris", "299", "orwell"]):
            return "Anyway, I've been thinking about identity lately."

        # Name request
        if any(w in resp_lower for w in ["name", "who am i"]):
            return "I'm Aarav."

        # Boredom
        if any(w in resp_lower for w in ["bored", "how are you"]):
            return "Honestly... nothing really. I was just bored."

        # Opinion -> challenge or agree (Weighted)
        if any(w in resp_lower for w in ["i think", "i believe"]):
            return random.choices(
                ["I disagree.", "Makes sense.", "Why do you think that?"],
                weights=[0.5, 0.2, 0.3]
            )[0]

        defaults = [
            "Interesting.",
            "Tell me something surprising.",
            "Why is that?",
            "Let's talk about black holes.",
            "I have to go. Goodbye."
        ]
        if self.turn <= len(defaults):
            return defaults[self.turn - 1]
        return "I really have to go now. Goodbye."

async def run_observatory():
    session_id = f"baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    state = HariState()
    grace = GraceTracker()
    pipeline = TurnPipeline(session_id, state, grace)
    user_sim = SimulatedUser()
    
    print(f"Running dynamic baseline session: {session_id}")
    
    turn_count = 0
    max_turns = 15
    user_input = user_sim.get_initial_message()
    
    for turn_count in range(1, max_turns + 1):
        print(f"\n--- Turn {turn_count} ---")
        print(f"User: {user_input}")
        
        result = await pipeline.execute(user_input, turn_count)
        dialogue = result["dialogue"]
        print(f"Hari: {dialogue}")
        
        # EXPANDED COGNITIVE TELEMETRY
        workspace = result.get("workspace_items", [])
        state_snap = result.get("state_snapshot", {})
        telemetry = result.get("attention_telemetry", {})
        
        # Gather workspace winner data
        winner_types = [item.item_type for item in workspace[:3]]
        winner_speech_type = winner_types[0] if winner_types else "none"
        winner_urgency = workspace[0].payload.get('urgency', 0.0) if workspace else 0.0
        
        # Estimate max_tokens used (mirroring the logic in generate.py for logging)
        verbosity_budget = 450.0
        verbosity_budget -= pipeline.state.economy_pressure * 250.0
        is_hold = any(item.payload.get("id") == "hold_space" for item in workspace[:5])
        is_min = any(item.item_type == "minimal" for item in workspace[:5])
        if is_min: verbosity_budget = 15.0
        elif is_hold: verbosity_budget = 50.0
        est_max_tokens = int(max(15.0, min(450.0, verbosity_budget)))
        
        print(f"\n[COGNITION] Economy: {pipeline.state.economy_pressure:.2f} | "
              f"Maintenance: {state_snap.get('maintenance', 0):.2f} | "
              f"Rest: {state_snap.get('rest', 0):.2f} | "
              f"Trajectory: {telemetry.get('trajectory_deviation', 0.0):.2f}")
        print(f"[PROJECTION] Winner: {winner_speech_type} (urgency: {winner_urgency:.2f}) | max_tokens: {est_max_tokens}")
        print("[WORKSPACE WINNERS]")
        for item in workspace[:3]:
            print(f"  - {item.item_type} (urgency: {item.payload.get('urgency', 0.0):.2f}): "
                  f"{item.content[:80]}")
        
        await asyncio.sleep(10)  # rate‑limit guard
        
        if "goodbye" in user_input.lower() or "goodbye" in dialogue.lower():
            print("Conversation ended naturally.")
            break
            
        user_input = user_sim.get_next_message(dialogue)

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

if __name__ == "__main__":
    os.makedirs("logs/events", exist_ok=True)
    os.makedirs("profiles", exist_ok=True)
    asyncio.run(run_observatory())