from loguru import logger

from atlas_backend.provider.embedding.base import EmbeddingProvider
from atlas_backend.provider.knowledge.vector_store.base import (
    SearchResult,
    VectorStore,
)


class Retriever:
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider
        self._top_k = top_k
        self._min_score = min_score

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        document_id: str | None = None,
    ) -> list[SearchResult]:
        logger.debug("Retrieving for query='{}' (top_k={})", query[:100], top_k)

        embeddings = await self._embedding_provider.embed([query])
        query_vector = embeddings[0]

        filters: dict = {}
        if document_id:
            filters["document_id"] = document_id

        results = await self._vector_store.search(
            query_vector=query_vector,
            limit=top_k or self._top_k,
            filters=filters if filters else None,
        )

        filtered = [r for r in results if r.score >= self._min_score]
        logger.debug(
            "Retrieved {} results ({} after min_score filter)",
            len(results),
            len(filtered),
        )
        return filtered
