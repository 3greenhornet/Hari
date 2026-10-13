"""
CRITICAL ARCHITECTURAL GUARD (2026-08-21):
This module renders IdentityProjection into prompts. 
It MUST remain a set of CONSTITUTIONAL CONSTRAINTS and COMMITMENTS.
It MUST NOT become a behavioral script (e.g., "You are a curious being who loves...").
Rationale: Emergent behavior comes from the Workspace competition, not from persona prose.
Keep it crisp, factual, and principle-based.
"""

"""
Identity Projection Renderer
Converts IdentityProjection into consumer-specific formats.
"""
from typing import Dict, Any
from models.identity import IdentityProjection


def render_for_dialogue(projection: IdentityProjection) -> str:
    """Render only populated identity projection fields for dialogue."""
    parts = []
    if projection.self_narrative:
        parts.append(projection.self_narrative)
    if projection.core_commitments:
        parts.append("Commitments: " + "; ".join(projection.core_commitments))
    if projection.origin_summary:
        parts.append(projection.origin_summary)
    return "\n\n".join(parts) if parts else ""


def render_for_planning(projection: IdentityProjection) -> Dict[str, Any]:
    """Render identity projection as structured data for planning."""
    result = {}
    if projection.self_narrative:
        result["self_narrative"] = projection.self_narrative
    if projection.core_commitments:
        result["core_commitments"] = projection.core_commitments
    if projection.origin_summary:
        result["origin"] = projection.origin_summary
    if projection.active_self_questions:
        result["active_self_questions"] = projection.active_self_questions
    return result

def build_system_prompt_from_identity(identity_model=None, context="dialogue"):
    """Render only identity that has actually developed."""
    from models.identity import IdentityModel
    if identity_model is None:
        identity_model = IdentityModel()
    projection = identity_model.project(context=context)
    parts = []
    if projection.self_narrative:
        parts.append(projection.self_narrative)
    if projection.core_commitments:
        parts.append("Commitments: " + "; ".join(projection.core_commitments))
    if projection.origin_summary:
        parts.append(projection.origin_summary)
    return "\n\n".join(parts)