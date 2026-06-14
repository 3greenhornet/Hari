from typing import Optional
from .base import BaseProvider
from .gemini import GeminiProvider

_provider: Optional[BaseProvider] = None

def get_provider() -> BaseProvider:
    global _provider
    if _provider is None:
        _provider = GeminiProvider()
    return _provider