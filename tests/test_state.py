# hari/tests/test_state.py
import pytest
from psyche.state import HariState

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
