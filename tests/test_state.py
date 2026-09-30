# hari/tests/test_state.py
import pytest
from models.memory_event import MemoryEvent
from psyche.state import HariState
from engine.memory import (
    compute_actr_base_level_activation,
    compute_full_actr_activation,
    compute_somatic_bonus,
)


def test_memory_event_tracks_somatic_markers():
    event = MemoryEvent(
        session_id="s1",
        turn_number=1,
        role="user",
        content="example",
        valence=0.4,
        arousal=0.7,
    )
    assert event.valence == 0.4
    assert event.arousal == 0.7


def test_actr_helpers():
    base = compute_actr_base_level_activation(usage_count=3, turns_since_last_retrieval=2)
    assert base > -10.0

    class DummyMemory:
        turn_number = 10
        usage_count = 3
        embedding = [1.0, 0.0, 0.0]

    activation = compute_full_actr_activation(
        DummyMemory(),
        current_turn=12,
        query_embedding=[1.0, 0.0, 0.0],
    )
    assert activation is not None

    bonus = compute_somatic_bonus(0.5, 0.6, 0.5, 0.6)
    assert bonus >= 0.0


def test_asymptotic_update():
    s = HariState()
    # Test positive delta
    new = s.asymptotic_update(0.5, 0.2, (0,1))
    assert 0.5 < new < 0.55  # should increase but not overshoot
    # Test negative delta
    new2 = s.asymptotic_update(0.8, -0.2, (0,1))
    assert 0.75 < new2 < 0.8
    # Test bounds clamping
    new3 = s.asymptotic_update(0.99, 0.1, (0,1))
    assert new3 <= 1.0

def test_update_dict():
    s = HariState(care=0.5)
    s.update({"care": 0.3})
    assert s.care > 0.5  # positive delta from 0.5 should increase toward 1

def test_natural_drift():
    s = HariState(care=0.9, valence=0.8)
    s.natural_drift()
    assert s.care < 0.9
    assert s.valence < 0.8
