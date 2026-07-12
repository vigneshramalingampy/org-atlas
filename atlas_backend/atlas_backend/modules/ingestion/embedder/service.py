import logging

from atlas_backend.modules.ingestion.chunker.model import Chunk
from atlas_backend.provider.embedding.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(
        self,
        provider: EmbeddingProvider,
        batch_size: int = 64,
    ) -> None:
        self._provider = provider
        self._batch_size = batch_size

    @property
    def dimensions(self) -> int:
        return self._provider.dimensions

    @property
    def model_name(self) -> str:
        return self._provider.model_name

    async def embed_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        if not chunks:
            return []

        logger.info(
            "Embedding %d chunks with model %s (batch_size=%d)",
            len(chunks),
            self.model_name,
            self._batch_size,
        )

        chunks_with_text = [c for c in chunks if c.text.strip()]
        if not chunks_with_text:
            return chunks

        texts = [c.text for c in chunks_with_text]

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            batch_embeddings = await self._provider.embed(batch)
            all_embeddings.extend(batch_embeddings)

        for chunk, embedding in zip(chunks_with_text, all_embeddings):
            chunk.embedding = embedding

        return chunks
