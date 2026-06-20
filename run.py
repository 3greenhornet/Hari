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
from engine.generate import TurnPipeline   # <-- CHANGED: use the full pipeline
from engine.curiosity_graph import get_graph_manager
from db.connection import init_db, close_db
from engine.consolidation_worker import get_manager as get_consolidation_manager
from utils.async_input import ainput
from utils.logger import init_session_log, log_event

load_dotenv()

_ctx_state: ContextVar[HariState] = ContextVar("hari_state")

async def main():
    print("🧠 Hari Core – Phase 1 (Full Pipeline Mode)")
    print("Type 'exit' to quit.\n")

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

    # Feature flags – read from .env
    # NOTE: USE_WORKSPACE=False currently because attention.py has a signature bug.
    # After fixing engine/attention.py, set USE_WORKSPACE=True in .env.
    use_memory = os.getenv("USE_MEMORY", "True").lower() == "true"
    use_workspace = os.getenv("USE_WORKSPACE", "False").lower() == "true"
    use_monologue = os.getenv("USE_MONOLOGUE", "True").lower() == "true"
    print(f"Memory enabled: {use_memory}")
    print(f"Workspace enabled: {use_workspace} (will be True after attention.py fix)")
    print(f"Monologue enabled: {use_monologue}")

    # Graph manager sync worker
    graph = await get_graph_manager()
    try:
        await graph.start_sync_worker(interval=60)
        print("📡 Graph sync worker started (60s interval).")
    except Exception as e:
        print(f"⚠️ Failed to start graph sync worker: {e}")

    # Memory consolidation worker
    consolidation_manager = get_consolidation_manager()
    try:
        await consolidation_manager.start(session_id)
        print("🗄️ Background memory consolidation worker active.")
    except Exception as e:
        print(f"⚠️ Failed to start memory consolidation worker: {e}")

    # Periodic promotion archival (stub, but harmless)
    async def run_periodic_promotion():
        nonlocal _last_promotion_turn
        while True:
            await asyncio.sleep(1)
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
            trace_id = str(uuid.uuid4())

            # -----------------------------------------------------------------
            # REMOVED: hardcoded drive updates (len(user) < 10 ...)
            # State changes now come only from:
            #   - Stage1 monologue output
            #   - Deterministic cascades (below)
            #   - Natural drift (inside TurnPipeline)
            # -----------------------------------------------------------------

            # Apply deterministic cascades (these are fine – they model fatigue, sovereignty, etc.)
            apply_fatigue_cascade(state)
            apply_sovereignty_cascade(state)
            apply_coherence_cascade(state, contradiction_occurred=False)
            apply_completion_cascade(state, num_unresolved_questions=0)
            apply_session_horizon(state, turn)

            # Use the full TurnPipeline (bypasses the old lightweight generator)
            pipeline = TurnPipeline(session_id, state, grace)
            try:
                result = await pipeline.execute(
                    user_input=user,
                    turn_count=turn,
                    trace_id=trace_id
                )
                dialogue = result["dialogue"]
                print(f"Hari> {dialogue}\n")
                # Simple debug: show current drives (useful for tuning)
                print(f"[DEBUG turn {turn}] curiosity={state.curiosity:.2f}, completion={state.completion:.2f}, "
                      f"care={state.care:.2f}, rest={state.rest:.2f}")
            except Exception as e:
                print(f"⚠️ Error on turn {turn}: {e}")
                import traceback
                traceback.print_exc()
                continue   # go to next turn

    finally:
        print("\n🛑 Initiating graceful shutdown sequence...")
        try:
            await consolidation_manager.stop()
        except Exception as e:
            print(f"Error stopping consolidation manager: {e}")
        try:
            await graph.stop_sync_worker()
        except Exception as e:
            print(f"Error stopping graph worker: {e}")
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