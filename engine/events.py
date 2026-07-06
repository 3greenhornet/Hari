"""
Cognitive Event Logger – Immutable record of Hari's runtime.

This is the SINGLE source of truth for all cognitive events.
Events are immutable, timestamped, and write-once.

Principle: Store reality once, derive understanding many times.
"""

import json
import uuid
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EventType(Enum):
    """Types of cognitive events that can be logged."""
    # Input/Output
    USER_INPUT = "user_input"
    ASSISTANT_RESPONSE = "assistant_response"
    
    # Memory
    MEMORY_RETRIEVAL = "memory_retrieval"
    MEMORY_STORAGE = "memory_storage"
    
    # Workspace
    WORKSPACE_LOAD = "workspace_load"
    WORKSPACE_BROADCAST = "workspace_broadcast"
    
    # State
    STATE_SNAPSHOT = "state_snapshot"
    DRIVE_UPDATE = "drive_update"
    
    # Cognitive
    MONOLOGUE_OUTPUT = "monologue_output"
    CURIOSITY_TRIGGER = "curiosity_trigger"
    NARRATIVE_UPDATE = "narrative_update"
    HYPOTHESIS_UPDATE = "hypothesis_update"
    SELF_BELIEF_UPDATE = "self_belief_update"
    
    # Decisions
    DECISION_TRACE = "decision_trace"
    
    # Session
    SESSION_START = "session_start"
    SESSION_END = "session_end"


@dataclass
class CognitiveEvent:
    """
    A single immutable cognitive event.
    Events are write-once. They are never modified or deleted.
    """
    event_id: str
    session_id: str
    event_type: str
    timestamp: str  # ISO format
    turn_number: int
    payload: Dict[str, Any]
    trace_id: Optional[str] = None
    
    def to_jsonl(self) -> str:
        """Convert to JSONL format (one line per event)."""
        return json.dumps({
            "event_id": self.event_id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "turn_number": self.turn_number,
            "trace_id": self.trace_id,
            "payload": self.payload
        }) + "\n"


class EventLogger:
    """
    Write-only event logger.
    Events are written to JSONL files (one event per line).
    No querying, no filtering, no analytics. Just append.
    """
    
    def __init__(self, session_id: str, log_dir: str = "logs/events/"):
        self.session_id = session_id
        self.log_dir = log_dir
        self._turn_number = 0
        self._file_path = None
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        os.makedirs(self.log_dir, exist_ok=True)
    
    def _get_file_path(self) -> str:
        if self._file_path is None:
            self._file_path = os.path.join(
                self.log_dir,
                f"{self.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            )
        return self._file_path
    
    def _write_event(self, event: CognitiveEvent) -> None:
        """Write a single event to the log file."""
        with open(self._get_file_path(), "a", encoding="utf-8") as f:
            f.write(event.to_jsonl())
    
    def _create_event(self, event_type: EventType, payload: Dict[str, Any], trace_id: Optional[str] = None) -> CognitiveEvent:
        """Create a new event with default fields."""
        self._turn_number += 1
        return CognitiveEvent(
            event_id=str(uuid.uuid4()),
            session_id=self.session_id,
            event_type=event_type.value,
            timestamp=datetime.now().isoformat(),
            turn_number=self._turn_number,
            payload=payload,
            trace_id=trace_id
        )
    
    # ===== Public Logging Methods =====
    
    def log_session_start(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        event = self._create_event(
            EventType.SESSION_START,
            payload={"metadata": metadata or {}}
        )
        self._write_event(event)
    
    def log_session_end(self) -> None:
        event = self._create_event(
            EventType.SESSION_END,
            payload={"end_time": datetime.now().isoformat()}
        )
        self._write_event(event)
    
    def log_user_input(self, content: str) -> None:
        event = self._create_event(
            EventType.USER_INPUT,
            payload={"content": content, "length": len(content)}
        )
        self._write_event(event)
    
    def log_assistant_response(self, content: str, workspace_composition: Optional[List[Dict]] = None) -> None:
        payload = {
            "content": content,
            "length": len(content),
            "word_count": len(content.split())
        }
        if workspace_composition:
            payload["workspace_composition"] = workspace_composition
        event = self._create_event(
            EventType.ASSISTANT_RESPONSE,
            payload=payload
        )
        self._write_event(event)
    
    def log_state_snapshot(self, state: Any) -> None:
        payload = {}
        drive_keys = ["care", "curiosity", "maintenance", "completion", "coherence", "rest", "novelty"]
        vad_keys = ["valence", "arousal", "dominance"]
        conv_keys = ["momentum", "stability", "engagement"]
        meta_keys = ["uncertainty", "social_ambiguity", "cognitive_tension"]
        
        for key in drive_keys + vad_keys + conv_keys + meta_keys:
            if hasattr(state, key):
                payload[key] = getattr(state, key)
        
        event = self._create_event(
            EventType.STATE_SNAPSHOT,
            payload=payload
        )
        self._write_event(event)
    
    def log_memory_retrieval(self, query: str, count: int, top_memories: Optional[List[str]] = None) -> None:
        event = self._create_event(
            EventType.MEMORY_RETRIEVAL,
            payload={
                "query": query,
                "count": count,
                "top_memories": top_memories[:5] if top_memories else []
            }
        )
        self._write_event(event)
    
    def log_workspace_load(self, candidate_count: int, winner_count: int, winners: Optional[List[str]] = None) -> None:
        event = self._create_event(
            EventType.WORKSPACE_LOAD,
            payload={
                "candidate_count": candidate_count,
                "winner_count": winner_count,
                "winners": winners[:5] if winners else []
            }
        )
        self._write_event(event)
    
    def log_workspace_broadcast(self, composition: Dict[str, Any]) -> None:
        event = self._create_event(
            EventType.WORKSPACE_BROADCAST,
            payload=composition
        )
        self._write_event(event)
    
    def log_monologue_output(self, output: Any) -> None:
        payload = {}
        for key in ["perceived_user_intent", "intent_confidence", "thematic_continuity", 
                    "user_engagement_estimate", "interruption_severity", "memory_significance"]:
            if hasattr(output, key):
                payload[key] = getattr(output, key)
        
        if hasattr(output, "curiosity_trigger") and output.curiosity_trigger:
            payload["curiosity_trigger"] = output.curiosity_trigger
        if hasattr(output, "self_belief_update") and output.self_belief_update:
            payload["self_belief_update"] = output.self_belief_update
        if hasattr(output, "hypothesis_update") and output.hypothesis_update:
            payload["hypothesis_update"] = output.hypothesis_update
        
        event = self._create_event(
            EventType.MONOLOGUE_OUTPUT,
            payload=payload
        )
        self._write_event(event)
    
    def log_decision_trace(self, trace_id: str) -> None:
        event = self._create_event(
            EventType.DECISION_TRACE,
            payload={"trace_id": trace_id}
        )
        self._write_event(event)