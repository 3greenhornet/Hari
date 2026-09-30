"""
models/stance.py — Cognitive Stance (pre-verbal representation)
"""

from pydantic import BaseModel


class CognitiveStance(BaseModel):
    focus: str
    pull: str
    relation: str
    speech_impulse: str
    rationale: str = ""  # NEW: why this stance naturally arose
