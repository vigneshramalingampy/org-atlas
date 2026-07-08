from abc import ABC, abstractmethod

from atlas_backend.provider.llm import (
    OllamaProvider,
    DeepseekProvider,
    AnthropicProvider,
)
from atlas_backend.provider.llm.openai import OpenaiProvider
from atlas_backend.utils.enums import LLMModel


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self):
        """Generate a response from the LLM."""
        pass


class LLMFactory:
    @staticmethod
    def create(provider: LLMModel):
        if provider == LLMModel.OLLAMA:
            return OllamaProvider()
        if provider == LLMModel.DEEPSEEK:
            return DeepseekProvider()
        if provider == LLMModel.OPENAI:
            return OpenaiProvider()
        if provider == LLMModel.ANTHROPIC:
            return AnthropicProvider()
