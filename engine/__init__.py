# hari/engine/__init__.py
"""
Engine package for Hari cognitive architecture.

The runtime maintains a persistent TurnPipeline per session. Do not create
fresh pipelines per call — that loses all persistence.
"""

import asyncio
import uuid
from typing import Dict, Optional

from .generate import TurnPipeline, generate_lightweight_response

_pipelines: Dict[str, TurnPipeline] = {}
_pipeline_lock = asyncio.Lock()


async def get_or_create_pipeline(session_id: Optional[str] = None) -> TurnPipeline:
    """Return the persistent pipeline for this session, creating it once."""
    from psyche.state import HariState
    session_id = session_id or "default"
    async with _pipeline_lock:
        if session_id not in _pipelines:
            state = HariState()
            _pipelines[session_id] = TurnPipeline(session_id, state)
            try:
                from engine.tick import TickRunner
                runner = TickRunner(_pipelines[session_id])
                runner.start()
                _pipelines[session_id]._tick_runner = runner
            except Exception:
                pass
        return _pipelines[session_id]


async def shutdown_pipeline(session_id: str) -> None:
    async with _pipeline_lock:
        pipeline = _pipelines.pop(session_id, None)
        if pipeline is None:
            return
        runner = getattr(pipeline, "_tick_runner", None)
        if runner is not None:
            try:
                await runner.stop()
            except Exception:
                pass
        try:
            pipeline.shutdown()
        except Exception:
            pass


async def generate_hari_response(user_input: str, session_id: Optional[str] = None) -> dict:
    pipeline = await get_or_create_pipeline(session_id)
    turn_count = getattr(pipeline, "_turn_counter", 0) + 1
    pipeline._turn_counter = turn_count
    return await pipeline.execute(user_input, turn_count, trace_id=str(uuid.uuid4()))


__all__ = [
    "TurnPipeline",
    "generate_lightweight_response",
    "generate_hari_response",
    "get_or_create_pipeline",
    "shutdown_pipeline",
]