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
        self._turn_event = asyncio.Event()
        self._session_id: Optional[str] = None
        self._current_turn: int = 0
        self._last_consolidation_turn: int = 0
        self._original_signal_handlers = {}

    def update_turn(self, turn_count: int) -> None:
        """Update the worker with the real conversation turn number.
        Wakes the worker if the consolidation interval is reached.
        """
        if turn_count < self._current_turn:
            logger.warning(
                "Ignoring non-monotonic turn update: %s < %s",
                turn_count,
                self._current_turn,
            )
            return

        self._current_turn = turn_count

        if (
            self._current_turn - self._last_consolidation_turn
            >= CONSOLIDATION_INTERVAL_TURNS
        ):
            self._turn_event.set()

    async def start(self, session_id: str) -> None:
        """Start the background consolidation worker loop."""
        if self._task is not None and not self._task.done():
            logger.warning("Consolidation worker already running")
            return

        self._session_id = session_id
        self._stop_event.clear()
        self._turn_event.clear()
        self._current_turn = 0
        self._last_consolidation_turn = 0
        self._task = asyncio.create_task(self._run())
        logger.info(f"🧹 Consolidation worker started for session {session_id}")

        self._setup_signal_handlers()

    async def _run(self) -> None:
        """Main loop: waits for turn events or stop signal."""
        try:
            while not self._stop_event.is_set():
                turn_wait = asyncio.create_task(self._turn_event.wait())
                stop_wait = asyncio.create_task(self._stop_event.wait())

                done, pending = await asyncio.wait(
                    {turn_wait, stop_wait},
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()

                if self._stop_event.is_set():
                    break

                self._turn_event.clear()

                current_turn = self._current_turn

                if (
                    current_turn - self._last_consolidation_turn
                    < CONSOLIDATION_INTERVAL_TURNS
                ):
                    continue

                await self._run_consolidation_cycle(current_turn)
                self._last_consolidation_turn = current_turn

        except asyncio.CancelledError:
            logger.info("Consolidation worker cancellation requested.")
            final_turn = self._current_turn
            try:
                await asyncio.shield(
                    run_consolidation(self._session_id, final_turn)
                )
                graph_manager = await get_graph_manager()
                await asyncio.shield(graph_manager.decay(decay_factor=0.99))
            except Exception as e:
                logger.error(f"Final consolidation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Consolidation worker fatal error: {e}")
        finally:
            self._restore_signal_handlers()

    async def _run_consolidation_cycle(self, turn_counter: int) -> None:
        """Run a single consolidation cycle with the given real turn."""
        logger.debug("Running consolidation cycle...")
        try:
            result = await run_consolidation(self._session_id, turn_counter)
            if result.get("promoted_hypotheses", 0) > 0:
                logger.info(f"📈 Promoted {result['promoted_hypotheses']} new hypotheses")
            if result.get("archived_memories", 0) > 0:
                logger.info(f"🗄️ Archived {result['archived_memories']} old memories")

            # ---- Process staging proposals (Promotion Engine) ----
            try:
                from engine.promotions import process_staging_proposals
                promo_results = await process_staging_proposals(self._session_id, turn_counter)
                if promo_results.get("accepted", 0) > 0:
                    logger.info(f"📈 Promoted {promo_results['accepted']} proposals from staging")
                if promo_results.get("contradictions_found", 0) > 0:
                    logger.info(f"🔍 Found {promo_results['contradictions_found']} contradictions during evaluation")
            except Exception as e:
                logger.error(f"Staging processing failed: {e}")

            # ---- Detect contradictions from recent memories ----
            try:
                from engine.promotions import detect_contradictions_from_memories
                contradictions = await detect_contradictions_from_memories(
                    self._session_id, turn_counter
                )
                if contradictions:
                    logger.info(f"🔍 Found {len(contradictions)} contradictions from memories")
            except Exception as e:
                logger.error(f"Contradiction detection failed: {e}")

            # ---- Archive inactive structures ----
            try:
                from engine.promotions import archive_inactive_structures
                archived = await archive_inactive_structures(turn_counter)
                if archived > 0:
                    logger.debug(f"🗄️ Archived {archived} inactive structures")
            except Exception as e:
                logger.error(f"Archival failed: {e}")

            graph_manager = await get_graph_manager()
            await graph_manager.decay(decay_factor=0.99)

        except Exception as e:
            logger.error(f"❌ Consolidation cycle failed: {e}")

    async def stop(self, timeout: float = 10.0) -> bool:
        """Gracefully request loop exit and clear references cleanly."""
        if self._task is None or self._task.done():
            return True

        logger.info("🛑 Stopping consolidation worker...")
        self._stop_event.set()

        try:
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