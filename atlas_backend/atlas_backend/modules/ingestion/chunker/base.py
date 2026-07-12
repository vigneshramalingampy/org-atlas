from abc import ABC, abstractmethod

from atlas_backend.modules.ingestion.chunker.config import ChunkingConfig
from atlas_backend.modules.ingestion.chunker.model import Chunk
from atlas_backend.modules.ingestion.extractor.model import ParsedDocument


class TextChunker(ABC):
    @abstractmethod
    async def chunk(
        self, document: ParsedDocument, config: ChunkingConfig
    ) -> list[Chunk]:
        """Chunk a parsed document into smaller pieces."""
