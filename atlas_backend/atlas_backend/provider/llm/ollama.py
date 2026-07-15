import httpx
from loguru import logger

from atlas_backend.provider.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        self._base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def generate(
        self,
        messages: list[dict],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        if not self._client:
            self._client = httpx.AsyncClient(timeout=120.0)

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        logger.debug(
            "Ollama request: model={}, messages={}", payload["model"], len(messages)
        )
        resp = await self._client.post(f"{self._base_url}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["message"]["content"]
        logger.debug("Ollama response: {} chars", len(content))
        return content
