import os
import logging
from google import genai
from google.genai import types
from pydantic import BaseModel
from .base import BaseProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = os.getenv("STAGE2_MODEL", "gemini-2.5-flash")

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[BaseModel],
        temperature: float = 0.3
    ) -> BaseModel:
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=response_model,
            )
        )
        if hasattr(response, "parsed") and response.parsed:
            return response.parsed
        # Fallback: parse JSON text
        return response_model.model_validate_json(response.text)

    async def generate_text(self, prompt: str, temperature: float = 0.8) -> str:
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=temperature)
        )
        return response.text.strip()