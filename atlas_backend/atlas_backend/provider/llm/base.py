from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str: ...


class LLMFactory:
    @staticmethod
    def create(provider: str, **kwargs) -> LLMProvider:
        if provider == "ollama":
            from atlas_backend.provider.llm.ollama import OllamaProvider

            return OllamaProvider(
                base_url=kwargs.get("base_url", "http://localhost:11434")
            )

        if provider == "openai":
            from atlas_backend.provider.llm.openai import OpenaiProvider

            return OpenaiProvider(api_key=kwargs.get("api_key", ""))

        if provider == "deepseek":
            from atlas_backend.provider.llm.deepseek import DeepseekProvider

            return DeepseekProvider(api_key=kwargs.get("api_key", ""))

        if provider == "anthropic":
            from atlas_backend.provider.llm.anthropic import AnthropicProvider

            return AnthropicProvider(api_key=kwargs.get("api_key", ""))

        msg = f"Unknown LLM provider: {provider}"
        raise ValueError(msg)
