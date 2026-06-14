# hari/engine/client.py
"""
Shared Gemini client with robust rate limiting, retry logic, and connection testing.
All operations are thread-safe and async.
"""

import asyncio
import os
import time
import random
import logging
from functools import wraps
from typing import Any, Callable, Optional, List
from collections import deque
from contextlib import asynccontextmanager


from google import genai
from google.genai import types
from google.genai.errors import APIError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# Configuration – all tunable via environment
# ============================================

def get_env_int(name: str, default: int) -> int:
    """Safely read integer from environment."""
    try:
        return int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default

MAX_CONCURRENT = get_env_int("GEMINI_MAX_CONCURRENT", 2)
MAX_REQUESTS_PER_MINUTE = get_env_int("GEMINI_RPM", 12)
MAX_RETRIES = get_env_int("GEMINI_MAX_RETRIES", 3)
BASE_RETRY_DELAY = get_env_int("GEMINI_RETRY_BASE_DELAY", 1)
MAX_RETRY_DELAY = get_env_int("GEMINI_MAX_RETRY_DELAY", 15)

# ============================================
# Rate Limiter – Sliding Window with Proper Synchronization
# ============================================

class RateLimiter:
    """
    Sliding window rate limiter with proper async locking.
    Tracks request timestamps and enforces RPM limits.
    """
    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self.timestamps: List[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        """
        Wait if needed to respect rate limit.
        Returns the wait time (0 if no wait).
        """
        async with self._lock:
            now = time.time()
            # Remove timestamps older than 60 seconds
            window_start = now - 60.0
            self.timestamps = [t for t in self.timestamps if t > window_start]

            if len(self.timestamps) < self.requests_per_minute:
                self.timestamps.append(now)
                return 0.0

            # Calculate wait time until the oldest timestamp falls out
            oldest = min(self.timestamps)
            wait_seconds = max(0.0, (oldest + 60.0) - now)
            # Add jitter to prevent thundering herd
            wait_seconds += random.uniform(0.1, 0.5)

        if wait_seconds > 0:
            logger.debug(f"Rate limit: waiting {wait_seconds:.2f}s")
            await asyncio.sleep(wait_seconds)
            # Recursively acquire after wait
            return await self.acquire()

_rate_limiter: Optional[RateLimiter] = None

def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(MAX_REQUESTS_PER_MINUTE)
    return _rate_limiter

# ============================================
# Concurrency Semaphore
# ============================================

_semaphore: Optional[asyncio.Semaphore] = None

def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    return _semaphore

# ============================================
# Retry Helpers
# ============================================

def is_retryable(exception: Exception) -> bool:
    """Return True for transient errors that should be retried."""
    if isinstance(exception, APIError):
        # 429 Resource Exhausted (rate limit) – retry after appropriate delay
        if exception.code == 429:
            return True
        # 503 Service Unavailable – temporary overload
        if exception.code == 503:
            return True
        # 5xx server errors – retry
        if 500 <= exception.code <= 599:
            return True
    # Network / connection errors
    if isinstance(exception, (ConnectionError, TimeoutError)):
        return True
    return False

def extract_retry_delay(exception: Exception, attempt: int) -> float:
    """
    Extract retry delay from exception if available, otherwise use exponential backoff.
    Google's 429 responses often include a 'retry_delay' field.
    """
    # Try to extract from exception metadata
    if hasattr(exception, 'metadata') and exception.metadata:
        for item in exception.metadata:
            if item.key == 'retry_delay':
                try:
                    return float(item.value) + random.uniform(0, 0.5)
                except (ValueError, TypeError):
                    pass

    # Exponential backoff with jitter
    delay = min(MAX_RETRY_DELAY, BASE_RETRY_DELAY * (2 ** attempt))
    return delay + random.uniform(0, min(delay * 0.3, 2.0))

# ============================================
# Gemini Client
# ============================================

_genai_client: Optional[genai.Client] = None
_connection_healthy: bool = False

async def get_genai_client() -> Optional[genai.Client]:
    """Return configured Gemini client; tests connection on first use."""
    global _genai_client, _connection_healthy

    if _genai_client is not None:
        return _genai_client

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("❌ GEMINI_API_KEY not set")
        _connection_healthy = False
        return None

    try:
        _genai_client = genai.Client(api_key=api_key)
        # Quick test: list models (non‑rate‑limited)
        await _genai_client.aio.models.list()
        _connection_healthy = True
        logger.info("✅ Gemini client initialized and tested")
        return _genai_client
    except Exception as e:
        logger.error(f"❌ Gemini client init failed: {e}")
        _genai_client = None
        _connection_healthy = False
        return None

async def ensure_genai_available() -> bool:
    """Check if Gemini is available; return True if yes."""
    client = await get_genai_client()
    return client is not None

# ============================================
# Core API Call with Retry and Rate Limiting
# ============================================

async def call_gemini_json(
    model: str,
    prompt: str,
    schema: Any,
    temperature: float = 0.3,
) -> Optional[dict]:
    """
    Call Gemini with a JSON schema and return parsed response.
    Includes rate limiting, concurrency control, and retry logic.
    Returns None on failure (caller should fall back to defaults).
    """
    import time
    import json as json_module

    client = await get_genai_client()
    if not client:
        return None

    rate_limiter = get_rate_limiter()
    semaphore = get_semaphore()

    start_time = time.time()
    input_chars = len(prompt)
    retry_count = 0

    # Wait for rate limiter
    await rate_limiter.acquire()

    for attempt in range(MAX_RETRIES):
        try:
            async with semaphore:
                config = types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                    response_json_schema=schema.model_json_schema(),
                )
                response = await client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )

                # Access parsed response when available
                if hasattr(response, "parsed") and response.parsed:
                    result = response.parsed
                else:
                    import json
                    result = json.loads(response.text)

                # Success logging
                latency_ms = (time.time() - start_time) * 1000
                output_chars = len(response.text) if hasattr(response, 'text') else 0
                logger.info(json_module.dumps({
                    "event": "llm_call",
                    "provider": "gemini",
                    "model": model,
                    "success": True,
                    "latency_ms": round(latency_ms, 2),
                    "retry_count": retry_count,
                    "input_chars": input_chars,
                    "output_chars": output_chars,
                }))
                return result

        except Exception as e:
            retry_count = attempt + 1
            if not is_retryable(e):
                logger.error(f"❌ Non-retryable error: {e}")
                # Log failure
                latency_ms = (time.time() - start_time) * 1000
                logger.error(json_module.dumps({
                    "event": "llm_call",
                    "provider": "gemini",
                    "model": model,
                    "success": False,
                    "latency_ms": round(latency_ms, 2),
                    "retry_count": retry_count,
                    "input_chars": input_chars,
                    "output_chars": 0,
                }))
                return None

            if attempt == MAX_RETRIES - 1:
                logger.error(f"❌ All {MAX_RETRIES} retries exhausted: {e}")
                latency_ms = (time.time() - start_time) * 1000
                logger.error(json_module.dumps({
                    "event": "llm_call",
                    "provider": "gemini",
                    "model": model,
                    "success": False,
                    "latency_ms": round(latency_ms, 2),
                    "retry_count": retry_count,
                    "input_chars": input_chars,
                    "output_chars": 0,
                }))
                return None

            delay = extract_retry_delay(e, attempt)
            logger.warning(f"⚠️ API error: {e}. Retrying in {delay:.1f}s (attempt {attempt+1}/{MAX_RETRIES})")
            await asyncio.sleep(delay)

    return None

# ============================================
# Context Manager for Client Lifecycle
# ============================================

@asynccontextmanager
async def gemini_session():
    """Context manager for graceful client lifecycle."""
    try:
        yield
    finally:
        # Cleanup if needed
        pass