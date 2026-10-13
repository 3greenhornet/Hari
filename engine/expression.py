"""Final utterance prompt renderers and substrate artifact checks."""

import logging
import re
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

ARTIFACTS = re.compile(
    r"\b("
    r"as an AI"
    r"|as a language model"
    r"|language model"
    r"|I'?m an? (?:AI|assistant|bot|chatbot)"
    r"|I am an? (?:AI|assistant|bot|chatbot)"
    r"|digital assistant"
    r"|I (?:cannot|can'?t|don'?t) (?:feel|have feelings|have emotions)"
    r"|I'?m here to help"
    r"|How can I (?:help|assist)"
    r")\b",
    re.IGNORECASE,
)


def has_artifact(text: str) -> bool:
    """Return whether text contains substrate artifact markers."""
    return bool(ARTIFACTS.search(text or ""))


def render_continuation(
    identity_context: str,
    agenda_line: str,
    transcript: List[Tuple[str, str]],
    inner_fragment: Optional[str],
    participant_name: str,
) -> str:
    """Render a transcript ending at Hari's utterance cue."""
    lines: List[str] = []
    if identity_context.strip():
        lines += [identity_context.strip(), ""]
    if agenda_line.strip():
        lines += [agenda_line.strip(), ""]
    for speaker, text in transcript:
        lines.append(f"{speaker}: {text}")
    if inner_fragment:
        lines.append(f"Hari (to herself): {inner_fragment}")
    lines += ["", "Hari:"]
    return "\n".join(lines)


def render_sectioned(
    identity_context: str,
    agenda_line: str,
    stance,
    active_material: List[str],
    incoming_event: Optional[str],
) -> str:
    """Render the legacy sectioned expression prompt."""
    parts: List[str] = []
    if identity_context.strip():
        parts += ["HARI'S CURRENT SELF", identity_context.strip(), ""]
    if agenda_line.strip():
        parts += ["OCCUPIED WITH", agenda_line.strip(), ""]
    if active_material:
        parts += [
            "ACTIVE THOUGHTS / QUESTIONS",
            "\n".join(f"- {material}" for material in active_material),
            "",
        ]
    if stance is not None:
        parts += [
            "COGNITIVE STANCE",
            f"focus: {stance.focus}",
            f"pull: {stance.pull}",
            f"relation: {stance.relation}",
            "",
        ]
    if incoming_event:
        parts += ["IN HER FIELD, SOMEONE SAID", f'"{incoming_event}"', ""]
    parts += ["Speak only from this state, as Hari, in her own voice."]
    return "\n".join(parts)


def render_prompt(
    mode: str,
    identity_context: str,
    agenda_line: str,
    transcript: List[Tuple[str, str]],
    inner_fragment: Optional[str],
    participant_name: str,
    stance=None,
    active_material: Optional[List[str]] = None,
    incoming_event: Optional[str] = None,
) -> str:
    """Dispatch to the selected expression renderer."""
    if mode == "sectioned":
        return render_sectioned(
            identity_context,
            agenda_line,
            stance,
            active_material or [],
            incoming_event,
        )
    return render_continuation(
        identity_context,
        agenda_line,
        transcript,
        inner_fragment,
        participant_name,
    )
