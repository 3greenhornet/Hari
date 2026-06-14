# hari/run.py
import asyncio
import os
import uuid
from dotenv import load_dotenv
from contextvars import ContextVar

from psyche.state import HariState
from psyche.grace import GraceTracker
from psyche.cascades import (
    apply_fatigue_cascade,
    apply_sovereignty_cascade,
    apply_coherence_cascade,
    apply_completion_cascade,
    apply_session_horizon,
)
from engine.generate import generate_lightweight_response as generate_hari_response
from engine.curiosity_graph import get_graph_manager
from db.connection import init_db, close_db
from engine.consolidation_worker import get_manager as get_consolidation_manager
from utils.async_input import ainput
from utils.logger import init_session_log, log_event

load_dotenv()

_ctx_state: ContextVar[HariState] = ContextVar("hari_state")

async def main():
    print("🧠 Hari Core – Phase 1 (Lightweight Mode)")
    print("Type 'exit' to quit.\n")

    # Initialize database and session
    await init_db()
    session_id = str(uuid.uuid4())[:8]
    init_session_log(session_id)
    log_event({"event": "session_start", "session_id": session_id})

    state = HariState()
    _ctx_state.set(state)
    grace = GraceTracker()
    turn = 0

    # Promotion engine background task control
    _promotion_task = None
    _last_promotion_turn = 0
    PROMOTION_INTERVAL_TURNS = 50

    use_memory = os.getenv("USE_MEMORY", "False").lower() == "true"
    use_workspace = os.getenv("USE_WORKSPACE", "False").lower() == "true"
    print(f"Memory enabled: {use_memory}")
    print(f"Workspace enabled: {use_workspace}")

    # Initialize and start the Graph Manager sync worker
    graph = await get_graph_manager()
    try:
        await graph.start_sync_worker(interval=60)
        print("📡 Graph sync worker started (60s interval).")
    except Exception as e:
        print(f"⚠️ Failed to start graph sync worker: {e}")
        # Proceed anyway, but log the issue
# Initialize and start Phase 6 Background Memory Consolidation

    consolidation_manager = get_consolidation_manager()
    try:
        await consolidation_manager.start(session_id)
        print("扫 Background memory consolidation worker active.")
    except Exception as e:
        print(f"⚠️ Failed to start memory consolidation worker: {e}")

    # Background promotion task (calls archive_inactive_structures periodically)
    async def run_periodic_promotion():
        nonlocal _last_promotion_turn
        while True:
            await asyncio.sleep(1)  # Check every second
            if turn - _last_promotion_turn >= PROMOTION_INTERVAL_TURNS and turn > 0:
                from engine.promotions import archive_inactive_structures
                archived = await archive_inactive_structures(turn)
                if archived > 0:
                    print(f"📦 Promotion engine archived {archived} inactive structures")
                _last_promotion_turn = turn

    _promotion_task = asyncio.create_task(run_periodic_promotion())
    
            
    try:
        while True:
            try:
                user = await ainput("You> ")
            except (KeyboardInterrupt, asyncio.CancelledError):
                print("\nAborting...")
                break
            if user.lower() in ("exit", "quit"):
                break

            turn += 1
            # Generate a unique trace ID for this turn
            trace_id = str(uuid.uuid4())

            # Simple deterministic drive changes (demo)
            if len(user) < 10:
                state.update({"curiosity": -0.05, "rest": 0.03})
            else:
                state.update({"curiosity": 0.05, "care": 0.03})

            # Apply cascades
            apply_fatigue_cascade(state)
            apply_sovereignty_cascade(state)
            apply_coherence_cascade(state, contradiction_occurred=False)
            apply_completion_cascade(state, num_unresolved_questions=0)
            apply_session_horizon(state, turn)

            # Generate response – pass trace_id
            result = await generate_hari_response(
                user, state, grace, turn, session_id, use_memory, use_workspace,
                trace_id=trace_id
            )
            dialogue = result["dialogue"]
            print(f"Hari> {dialogue}\n")
            print(f"[DEBUG turn {turn}] curiosity={state.curiosity:.2f}, completion={state.completion:.2f}, rest={state.rest:.2f}")

    finally:
        print("\n🛑 Initiating graceful shutdown sequence...")

        # 1. Stop the memory consolidation worker first
        print("🗄️ Stopping memory consolidation worker...")
        try:
            await consolidation_manager.stop()
        except Exception as e:
            print(f"Error winding down consolidation manager: {e}")

        # 2. Always stop the graph worker before closing DB
        print("🛑 Stopping graph sync worker...")
        try:
            await graph.stop_sync_worker()
        except Exception as e:
            print(f"Error stopping graph worker: {e}")

        # 3. Cancel the promotion background task
        if _promotion_task:
            _promotion_task.cancel()
            try:
                await _promotion_task
            except asyncio.CancelledError:
                pass

        await close_db()
        log_event({"event": "session_end", "turn_count": turn})
        print("Goodbye.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass