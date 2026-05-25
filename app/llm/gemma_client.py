from openai import AsyncOpenAI, OpenAI
from openai.types.chat import ChatCompletion

from app.core.config import get_settings


class GemmaClient:
    def __init__(self):
        settings = get_settings()

        self.model = settings.gemma_model

        self.client = OpenAI(
            base_url=settings.gemma_base_url,
            api_key=settings.gemma_api_key,
        )

        self.async_client = AsyncOpenAI(
            base_url=settings.gemma_base_url,
            api_key=settings.gemma_api_key,
        )

    def generate(self, prompt: str) -> str:
        response = self.chat(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ]
        )

        content = response.choices[0].message.content
        return content or ""

    def chat(
        self,
        *,
        messages: list[dict],
        temperature: float = 0.2,
    ) -> ChatCompletion:
        payload = self._build_chat_payload(
            messages=messages,
            temperature=temperature,
        )

        return self.client.chat.completions.create(**payload)

    async def async_chat(
        self,
        *,
        messages: list[dict],
        temperature: float = 0.2,
    ) -> ChatCompletion:
        payload = self._build_chat_payload(
            messages=messages,
            temperature=temperature,
        )

        return await self.async_client.chat.completions.create(**payload)

    def _build_chat_payload(
        self,
        *,
        messages: list[dict],
        temperature: float,
    ) -> dict:
        return {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }