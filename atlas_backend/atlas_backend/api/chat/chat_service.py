from loguru import logger

from atlas_backend.modules.generation.prompt_builder import PromptBuilder
from atlas_backend.modules.retrival.retriver import Retriever
from atlas_backend.provider.llm.base import LLMProvider
from atlas_backend.schemas.chat import ChatRequest, ChatResponse, SourceRef


class ChatService:
    def __init__(
        self,
        retriever: Retriever,
        llm_provider: LLMProvider,
        prompt_builder: PromptBuilder | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        model: str = "",
    ) -> None:
        self._model = model
        self._retriever = retriever
        self._llm = llm_provider
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def chat(
        self,
        request: ChatRequest,
        model: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatResponse:
        logger.info("Chat request: query='{}'", request.query[:100])

        results = await self._retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            document_id=request.document_id,
        )

        messages = self._prompt_builder.build(request.query, results)

        answer = await self._llm.generate(
            messages=messages,
            model=model or self._model,
            temperature=temperature if temperature is not None else self._temperature,
            max_tokens=max_tokens or self._max_tokens,
        )

        sources = [
            SourceRef(
                chunk_id=r.id,
                source=r.payload.get("source", ""),
                page=r.payload.get("page"),
                score=r.score,
                text_preview=r.payload.get("text", "")[:200],
            )
            for r in results
        ]

        logger.info(
            "Chat response: answer={} chars, {} sources", len(answer), len(sources)
        )
        return ChatResponse(answer=answer, sources=sources)
