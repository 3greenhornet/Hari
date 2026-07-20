"""
engine/shared_significance.py — Shared Significance Primitive

Ticket 012: Shared Significance is the estimated importance of a representation
because of its role in the evolving shared cognitive context between Hari
and another participant.
"""

from typing import Optional
from psyche.state import HariState

# Primitive coefficients (separate from attention weights)
SIGNIFICANCE_PROXY_WEIGHT = 0.6
CARE_PROXY_WEIGHT = 0.4


def compute_shared_significance(
    candidate: dict,
    state: HariState,
    relationship_model: Optional[dict] = None
) -> float:
    """
    V1 Proxy: candidate significance + care drive.
    
    This is a temporary proxy. When RelationshipModel exists,
    this function will be updated to use trust, familiarity,
    shared history, and other relational signals.
    
    The signature and return type remain unchanged.
    """
    item_significance = float(candidate.get("significance", 0.5))
    care = float(state.care)
    
    # V1 proxy with dedicated primitive coefficients
    shared_significance = (
        item_significance * SIGNIFICANCE_PROXY_WEIGHT
        + care * CARE_PROXY_WEIGHT
    )
    
    # FUTURE: When RelationshipModel is ready:
    # relationship_relevance = (
    #     state.care * 0.5
    #     + relationship_model.trust * 0.3
    #     + relationship_model.familiarity * 0.2
    # )
    # shared_significance = (item_significance * 0.6) + (relationship_relevance * 0.4)
    
    return min(1.0, max(0.0, shared_significance))