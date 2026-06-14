"""
providers/base.py — Abstract provider interface.
All LLM calls must go through a concrete implementation of this class.
"""

from abc import ABC, abstractmethod
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseProvider(ABC):
    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        temperature: float = 0.3
    ) -> T:
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.8
    ) -> str:
        pass