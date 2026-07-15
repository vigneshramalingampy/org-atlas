from anthropic import AsyncAnthropic
from loguru import logger

from atlas_backend.provider.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str = "") -> None:
        self._client = AsyncAnthropic(api_key=api_key)

    async def generate(
        self,
        messages: list[dict],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        model = model or "claude-3-5-haiku-latest"

        system_msg = None
        chat_messages = []
        for m in messages:
            if m.get("role") == "system":
                system_msg = m["content"]
            else:
                chat_messages.append({"role": m["role"], "content": m["content"]})

        logger.debug(
            "Anthropic request: model={}, messages={}", model, len(chat_messages)
        )

        kwargs = {}
        if system_msg:
            kwargs["system"] = system_msg

        response = await self._client.messages.create(
            model=model,
            messages=chat_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        content = response.content[0].text
        logger.debug("Anthropic response: {} chars", len(content))
        return content
