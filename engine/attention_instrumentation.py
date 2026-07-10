"""
engine/attention_instrumentation.py — Logging for attention calibration.

This module logs pressure contributions so you can empirically verify
that attention is working as expected.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import os

from engine.attention_config import AttentionCalibration

logger = logging.getLogger(__name__)


@dataclass
class PressureLogEntry:
    """A single pressure contribution log entry."""
    experiment_id: str
    turn_number: int
    candidate_id: str
    candidate_type: str
    pressures: Dict[str, float]
    weights: Dict[str, float]
    raw_score: float
    final_score: float
    was_selected: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "turn": self.turn_number,
            "candidate_id": self.candidate_id,
            "candidate_type": self.candidate_type,
            "pressures": self.pressures,
            "weights": self.weights,
            "raw_score": self.raw_score,
            "final_score": self.final_score,
            "was_selected": self.was_selected,
            "timestamp": self.timestamp
        }


class AttentionInstrumentation:
    """
    Logs pressure contributions for calibration and debugging.
    
    Use this to empirically verify that:
    1. Relevance doesn't dominate unreasonably
    2. State modulates weights as expected
    3. The feedback loop is stable
    """
    
    def __init__(self, config: AttentionCalibration, log_dir: str = "logs/attention/"):
        self.config = config
        self.log_dir = log_dir
        self._logs: List[PressureLogEntry] = []
        self._turn_counter = 0
        self._previous_engagement = None
        self._ensure_directory()
        
        # Generate experiment ID if not provided
        if not self.config.experiment_id:
            self.config.experiment_id = datetime.now().strftime("exp_%Y%m%d_%H%M%S")
    
    def _ensure_directory(self) -> None:
        os.makedirs(self.log_dir, exist_ok=True)
    
    def record_pressure(
        self,
        turn_number: int,
        candidate_id: str,
        candidate_type: str,
        pressures: Dict[str, float],
        weights: Dict[str, float],
        raw_score: float,
        final_score: float,
        was_selected: bool = False
    ) -> None:
        """
        Record a single pressure contribution.
        
        This is called for every candidate in the workspace competition.
        """
        if not self.config.log_pressure_contributions:
            return
        
        entry = PressureLogEntry(
            experiment_id=self.config.experiment_id,
            turn_number=turn_number,
            candidate_id=candidate_id,
            candidate_type=candidate_type,
            pressures=pressures,
            weights=weights,
            raw_score=raw_score,
            final_score=final_score,
            was_selected=was_selected
        )
        self._logs.append(entry)
        self._turn_counter += 1
        
        # Periodic logging to file
        if self._turn_counter % self.config.log_frequency == 0:
            self._flush_logs()
    
    def mark_selected(self, selected_ids: List[str]) -> None:
        """
        Mark which candidates were selected in the workspace competition.
        Called after load_workspace completes.
        """
        selected_set = set(selected_ids)
        for entry in self._logs:
            if entry.candidate_id in selected_set:
                entry.was_selected = True
        
        # Also flush logs immediately after selection marking
        self._flush_logs()
    
    def _flush_logs(self) -> None:
        """Write logs to file and clear buffer."""
        if not self._logs:
            return
        
        filename = os.path.join(
            self.log_dir,
            f"attention_log_{self.config.experiment_id}.jsonl"
        )
        
        with open(filename, "a") as f:
            for entry in self._logs:
                f.write(json.dumps(entry.to_dict()) + "\n")
        
        self._logs.clear()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the logged data."""
        if not self._logs and not os.path.exists(self.log_dir):
            return {"message": "No logs recorded yet"}
        
        # Load all logs for this experiment
        all_entries = []
        filename = os.path.join(self.log_dir, f"attention_log_{self.config.experiment_id}.jsonl")
        if os.path.exists(filename):
            with open(filename, "r") as f:
                for line in f:
                    if line.strip():
                        all_entries.append(json.loads(line))
        
        if not all_entries:
            return {"message": "No logs found"}
        
        total = len(all_entries)
        selected = sum(1 for e in all_entries if e.get("was_selected", False))
        
        # Calculate average pressure contributions by type
        pressure_sums: Dict[str, float] = {}
        for entry in all_entries:
            for key, value in entry.get("pressures", {}).items():
                pressure_sums[key] = pressure_sums.get(key, 0.0) + value
        
        avg_pressures = {k: v / total for k, v in pressure_sums.items()}
        
        # Calculate weight averages
        weight_sums: Dict[str, float] = {}
        for entry in all_entries:
            for key, value in entry.get("weights", {}).items():
                weight_sums[key] = weight_sums.get(key, 0.0) + value
        
        avg_weights = {k: v / total for k, v in weight_sums.items()}
        
        return {
            "experiment_id": self.config.experiment_id,
            "total_entries": total,
            "selected_count": selected,
            "selection_rate": selected / total if total > 0 else 0.0,
            "average_pressures": avg_pressures,
            "average_weights": avg_weights,
            "latest_turn": all_entries[-1]["turn"] if all_entries else 0,
            "config": {
                "relevance_base": self.config.relevance_base,
                "curiosity_modulation": self.config.curiosity_modulation,
                "max_engagement_influence": self.config.max_engagement_influence,
            }
        }
    
    def compare_experiments(self, other_experiment_id: str) -> Dict[str, Any]:
        """Compare this experiment with another."""
        # Load other experiment logs
        other_filename = os.path.join(self.log_dir, f"attention_log_{other_experiment_id}.jsonl")
        if not os.path.exists(other_filename):
            return {"error": f"Experiment {other_experiment_id} not found"}
        
        self_summary = self.get_summary()
        # Load other summary
        other_entries = []
        with open(other_filename, "r") as f:
            for line in f:
                if line.strip():
                    other_entries.append(json.loads(line))
        
        other_total = len(other_entries)
        other_selected = sum(1 for e in other_entries if e.get("was_selected", False))
        
        return {
            "experiment_a": self.config.experiment_id,
            "experiment_b": other_experiment_id,
            "selection_rate_a": self_summary.get("selection_rate", 0),
            "selection_rate_b": other_selected / other_total if other_total > 0 else 0,
            "selection_rate_delta": (self_summary.get("selection_rate", 0) - 
                                    (other_selected / other_total if other_total > 0 else 0)),
            "turn_count_a": self_summary.get("total_entries", 0),
            "turn_count_b": other_total,
        }
    
    def close(self) -> None:
        """Flush remaining logs and cleanup."""
        self._flush_logs()