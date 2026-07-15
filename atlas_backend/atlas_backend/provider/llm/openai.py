from openai import AsyncOpenAI
from loguru import logger

from atlas_backend.provider.llm.base import LLMProvider


class OpenaiProvider(LLMProvider):
    def __init__(self, api_key: str = "") -> None:
        self._client = AsyncOpenAI(api_key=api_key or None)

    async def generate(
        self,
        messages: list[dict],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        model = model or "gpt-4o-mini"

        logger.debug("OpenAI request: model={}, messages={}", model, len(messages))
        response = await self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or ""
        logger.debug("OpenAI response: {} chars", len(content))
        return content
