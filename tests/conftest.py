"""
tests/conftest.py — Pytest fixtures for Hari Core tests.
Provides async event loop and mocked Gemini client.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def mock_gemini():
    """Mock the Gemini API calls to avoid real network requests."""
    with patch("engine.client.call_gemini_json", new_callable=AsyncMock) as mock_json:
        with patch("engine.client.call_gemini", new_callable=AsyncMock) as mock_text:
            # Default return values – tests can override
            mock_json.return_value = {"dialogue": "Mocked response"}
            mock_text.return_value = "Mocked response"
            yield {"json": mock_json, "text": mock_text}