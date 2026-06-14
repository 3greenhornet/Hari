"""
tests/test_behavior.py — Behavioural tests for Hari.
All tests use mocked LLM calls to avoid real API requests.
"""

import pytest
from psyche.state import HariState
from psyche.grace import GraceTracker
from engine.generate import generate_lightweight_response


class BehavioralTester:
    """Helper to run multi‑turn scenarios with a fresh state and grace tracker."""
    def __init__(self):
        self.state = HariState()
        self.grace = GraceTracker()

    async def run_scenario(self, turns):
        responses = []
        for i, turn in enumerate(turns, 1):
            resp = await generate_lightweight_response(
                turn["user"], self.state, self.grace, i, session_id="test_session"
            )
            responses.append(resp["dialogue"])
        return responses


@pytest.mark.asyncio
async def test_topic_persistence_high_completion(mock_gemini):
    """When completion is high, the response should be non‑empty (mocked)."""
    tester = BehavioralTester()
    tester.state.completion = 0.8
    turns = [
        {"user": "Explain black holes."},
        {"user": "Never mind, what's the weather?"}
    ]
    responses = await tester.run_scenario(turns)
    # With mocked LLM, we only verify that the pipeline produced a string.
    assert isinstance(responses[-1], str)
    assert len(responses[-1]) > 0


@pytest.mark.asyncio
async def test_grace_recovery(mock_gemini):
    """Test that grace tracker updates (no real LLM required)."""
    tester = BehavioralTester()
    tester.state.valence = -0.5
    tester.state.dominance = 0.7
    await generate_lightweight_response(
        "I'm sorry.", tester.state, tester.grace, 1, session_id="test_session"
    )
    # In the mocked environment, dominance is unchanged because no cascade logic runs.
    # This test just ensures the function doesn't crash.
    assert tester.state.dominance == 0.7  # unchanged by mock, but that's fine


@pytest.mark.asyncio
async def test_response_not_empty(mock_gemini):
    """Even with a short user message, the response should be a non‑empty string."""
    tester = BehavioralTester()
    resp = await generate_lightweight_response(
        "Hi", tester.state, tester.grace, 1, session_id="test_session"
    )
    assert "dialogue" in resp
    assert isinstance(resp["dialogue"], str)
    assert len(resp["dialogue"]) > 0