# hari/engine/consolidation_worker.py
"""
Phase 6: Background Consolidation Manager.
Implements graceful shutdown pattern with asyncio.Event and proper cancellation handling.
Uses manual event loop management to avoid default SIGINT handling that would skip cleanup.
"""

import asyncio
import logging
import signal
import os
from typing import Optional

from engine.memory_consolidation import run_consolidation
from engine.curiosity_graph import get_graph_manager

logger = logging.getLogger(__name__)

CONSOLIDATION_INTERVAL_TURNS = int(os.getenv("CONSOLIDATION_INTERVAL_TURNS", "10"))
CONSOLIDATION_INTERVAL_SECONDS = int(os.getenv("CONSOLIDATION_INTERVAL_SECONDS", "60"))


class ConsolidationManager:
    """Manages background consolidation operations with explicit signal cleanup states."""

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._session_id: Optional[str] = None
        self._original_signal_handlers = {}

    async def start(self, session_id: str) -> None:
        """Start the background consolidation worker loop."""
        if self._task is not None and not self._task.done():
            logger.warning("Consolidation worker already running")
            return

        self._session_id = session_id
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())
        logger.info(f"🧹 Consolidation worker started for session {session_id}")

        # Signal handlers are set up in the main loop; they will call stop()
        self._setup_signal_handlers()

    async def _run(self) -> None:
        """Main loop executing granular operations and shielding cleanups from strict timeouts."""
        try:
            turn_counter = 0
            last_consolidation_turn = 0

            while not self._stop_event.is_set():
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=CONSOLIDATION_INTERVAL_SECONDS,
                    )
                    break
                except asyncio.TimeoutError:
                    pass

                turn_counter += CONSOLIDATION_INTERVAL_TURNS

                if turn_counter - last_consolidation_turn >= CONSOLIDATION_INTERVAL_TURNS:
                    logger.debug("Running consolidation cycle...")
                    try:
                        result = await run_consolidation(self._session_id, turn_counter)
                        if result.get("promoted_hypotheses", 0) > 0:
                            logger.info(f"📈 Promoted {result['promoted_hypotheses']} new hypotheses")
                        if result.get("archived_memories", 0) > 0:
                            logger.info(f"🗄️ Archived {result['archived_memories']} old memories")

                        graph_manager = await get_graph_manager()
                        await graph_manager.decay(decay_factor=0.99)


                        last_consolidation_turn = turn_counter
                    except Exception as e:
                        logger.error(f"❌ Consolidation cycle failed: {e}")

            logger.info("Consolidation worker stopping gracefully via explicit trigger.")

        except asyncio.CancelledError:
            logger.info("Consolidation worker cancellation requested. Preserving final application state...")
            # Shield the final DB writes from cancellation during loop shutdown
            try:
                await asyncio.shield(run_consolidation(self._session_id, 9999))
                graph_manager = await get_graph_manager()
                await asyncio.shield(graph_manager.decay(decay_factor=0.99))
            except RuntimeError as e:
                if "Event loop is closed" in str(e):
                    logger.warning(f"⚠️ Loop already closed; final consolidation skipped: {e}")
                else:
                    logger.error(f"❌ Final consolidation failed: {e}")
            except Exception as e:
                logger.error(f"❌ Final consolidation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Consolidation worker fatal error: {e}")
        finally:
            self._restore_signal_handlers()

    async def stop(self, timeout: float = 10.0) -> bool:
        """Gracefully request loop exit and clear references cleanly."""
        if self._task is None or self._task.done():
            return True

        logger.info("🛑 Stopping consolidation worker...")
        self._stop_event.set()

        try:
            # Use shield to protect the wait for task completion
            await asyncio.wait_for(asyncio.shield(self._task), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            logger.error(f"❌ Consolidation worker did not wind down inside {timeout}s window. Direct canceling.")
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            return False
        finally:
            self._task = None
            self._session_id = None

    def _setup_signal_handlers(self) -> None:
        """Bind shutdown triggers across supported active execution environments."""
        try:
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                self._original_signal_handlers[sig] = signal.getsignal(sig)
                # Signal handler sets the event; actual shutdown is driven by the main loop
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._handle_shutdown_signal(s))
                )
        except (RuntimeError, ValueError) as e:
            logger.debug(f"Signal integration bypassed: {e}")

    def _restore_signal_handlers(self) -> None:
        """Safely restore base environmental signals during teardowns."""
        try:
            loop = asyncio.get_running_loop()
            for sig, handler in self._original_signal_handlers.items():
                try:
                    loop.remove_signal_handler(sig)
                    signal.signal(sig, handler)
                except Exception as e:
                    logger.debug(f"Failed to reset event loop signal configuration for {sig}: {e}")
        except (RuntimeError, ValueError) as e:
            logger.debug(f"Signal teardown mapping bypassed: {e}")

    async def _handle_shutdown_signal(self, sig: signal.Signals) -> None:
        """Intercept hardware interrupts cleanly."""
        logger.info(f"Received terminating event via signal {sig.name}. Initializing runtime sequence shutdown...")
        await self.stop()


_manager: Optional[ConsolidationManager] = None


def get_manager() -> ConsolidationManager:
    """Singleton getter for active background synchronization execution blocks."""
    global _manager
    if _manager is None:
        _manager = ConsolidationManager()
    return _manager
