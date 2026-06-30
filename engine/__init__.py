# hari/engine/__init__.py
"""
Engine package for Hari cognitive architecture.
External code should import TurnPipeline from .generate directly.
"""

from .generate import TurnPipeline, generate_lightweight_response
import uuid

async def generate_hari_response(user_input: str) -> dict:
    """Wrapper for Streamlit app to get a response in one turn."""
    from psyche.state import HariState
    from psyche.grace import GraceTracker
    session_id = str(uuid.uuid4())[:8]
    state = HariState()
    grace = GraceTracker()
    pipeline = TurnPipeline(session_id, state, grace)
    return await pipeline.execute(user_input, turn_count=1, trace_id=str(uuid.uuid4()))

__all__ = ["TurnPipeline", "generate_lightweight_response", "generate_hari_response"]
