"""Centralized message construction for internal and expression calls."""

from typing import Dict, List, Optional


def build_internal_call(
    system_prompt: str,
    internal_context: str,
    participant_utterance: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Build messages for an internal cognitive call."""
    system_content = f"{system_prompt}\n\n{internal_context}"
    if participant_utterance:
        system_content += f"\n\nINCOMING FROM PARTICIPANT:\n{participant_utterance}"
        user_content = participant_utterance
    else:
        system_content += "\n\n[Internal cognition task — no external speaker this turn]"
        user_content = "[internal cognition task]"

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def build_expression_call(
    identity_context: str,
    internal_context: str,
    transcript: list,
) -> List[Dict[str, str]]:
    """Build a continuation document for final expression generation.

    The name-attributed transcript is intentionally carried in the user role;
    explicit speaker prefixes distinguish self from participant in continuation mode.
    """
    system_content = "\n\n".join(
        part for part in (identity_context.strip(), internal_context.strip()) if part
    )
    lines = [f"{speaker}: {text}" for speaker, text in transcript]
    lines.append("Hari:")

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": "\n".join(lines)},
    ]
