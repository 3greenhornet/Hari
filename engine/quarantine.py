"""
engine/quarantine.py - Contamination detector for internal cognition.

Temporary scaffolding. Default behavior is log-only; sterile mode filters hits.
"""

import logging
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

BANNED = re.compile(
    r"("
    r"\buser\b"
    r"|\busers\b"
    r"|user[_ ]?(intent|engagement|satisfaction|response|state|model)"
    r"|engagement (level|estimate|trajectory|score)"
    r"|conversation(al)? strategy"
    r"|response strategy"
    r"|respond appropriately"
    r"|respond helpfully"
    r"|test of (conversational )?symmetry"
    r"|participant[- ]role"
    r"|social (frame|expectation) mismatch"
    r"|interaction success"
    r"|response plan(ning)?"
    r"|intent confidence"
    r"|\bsatisf(y|ying) the\b"
    r"|\bhelp(ing)? the (user|participant)\b"
    r"|\bassistant\b"
    r"|digital assistant"
    r"|conversational partner"
    r")",
    re.IGNORECASE,
)


def is_contaminated(text: str) -> Tuple[bool, List[str]]:
    """Return whether text contains banned markers and the matching markers."""
    if not text:
        return False, []
    matches = [match.group(0) for match in BANNED.finditer(text)]
    return bool(matches), matches


def quarantine(
    candidates: List[Dict],
    trace_id: str = "?",
    session_id: str = "?",
    sterile: bool = False,
) -> Tuple[List[Dict], int]:
    """Inspect candidates, log hits, and optionally filter contaminated items."""
    kept: List[Dict] = []
    hits = 0
    for candidate in candidates:
        content = candidate.get("content", "")
        contaminated, matches = is_contaminated(content)
        if contaminated:
            hits += 1
            logger.warning(
                "QUARANTINE [%s/%s]: %r matches=%s",
                session_id,
                trace_id,
                content[:120],
                matches,
            )
            candidate["contamination"] = True
            candidate["contamination_matches"] = matches
            if not sterile:
                kept.append(candidate)
        else:
            candidate["contamination"] = False
            kept.append(candidate)
    return kept, hits
