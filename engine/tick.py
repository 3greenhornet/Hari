"""Endogenous tick runner."""

import asyncio
import logging
from typing import Optional

from engine.generate import TurnPipeline

logger = logging.getLogger(__name__)


class TickRunner:
    def __init__(self, pipeline: TurnPipeline,
                 interval_seconds: float = 30.0,
                 min_pressure: float = 0.15):
        self.pipeline = pipeline
        self.interval_seconds = interval_seconds
        self.min_pressure = min_pressure
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._turn_offset = 0

    def _compute_internal_pressure(self) -> float:
        state = self.pipeline.state
        pressure = 0.0
        try:
            top = self.pipeline.active_thought_store.top(3)
            if top:
                pressure = max(pressure, max(t.activation for t in top))
        except Exception:
            pass
        try:
            active = self.pipeline.pursuit_registry.get_active()
            if active:
                pressure = max(pressure, max(p.strength for p in active))
        except Exception:
            pass
        try:
            if state.viability_zone_violated():
                pressure = max(pressure, 0.6)
        except Exception:
            pass
        if state.cognitive_tension > 0.5:
            pressure = max(pressure, state.cognitive_tension)
        if state.curiosity > 0.7:
            pressure = max(pressure, state.curiosity * 0.8)
        if state.completion > 0.7:
            pressure = max(pressure, state.completion * 0.75)
        # Narrative pressure: unfinished threads want attention
        try:
            if self.pipeline._active_threads:
                top_thread = self.pipeline._active_threads[0]
                closure = (1.0 - float(top_thread.completion_estimate)) * float(top_thread.emotional_investment)
                pressure = max(pressure, closure * 0.7)
        except Exception:
            pass
        # Curiosity graph importance (survives on fresh sessions if any nodes exist)
        try:
            nodes = self.pipeline._last_top_curiosity_nodes
            if nodes:
                pressure = max(pressure, float(nodes[0].get("importance", 0.0)) * 0.6)
        except Exception:
            pass
        return pressure

    async def _run(self) -> None:
        try:
            while not self._stop.is_set():
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self.interval_seconds)
                    break
                except asyncio.TimeoutError:
                    pass
                pressure = self._compute_internal_pressure()
                if pressure < self.min_pressure:
                    continue
                self._turn_offset += 1
                tick_turn = 100000 + self._turn_offset
                logger.info("Tick firing (pressure=%.2f, turn=%d)", pressure, tick_turn)
                try:
                    result = await self.pipeline.execute(
                        user_input=None,
                        turn_count=tick_turn,
                        seed="tick",
                    )
                    if result.get("dialogue"):
                        logger.info("Tick expression: %s", result["dialogue"][:200])
                except Exception as e:
                    logger.error("Tick execution failed: %s", e)
        except asyncio.CancelledError:
            raise

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run())
        logger.info("TickRunner started (interval=%.1fs, threshold=%.2f)",
                    self.interval_seconds, self.min_pressure)

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
