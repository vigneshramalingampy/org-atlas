from atlas_backend.modules.ingestion.chunker.base import TextChunker
from atlas_backend.modules.ingestion.chunker.recursive import RecursiveChunker


class ChunkingFactory:
    _registry: dict[str, type[TextChunker]] = {
        "recursive": RecursiveChunker,
    }

    @classmethod
    def create(cls, strategy: str = "recursive") -> TextChunker:
        chunker_cls = cls._registry.get(strategy)
        if chunker_cls is None:
            raise ValueError(f"Unsupported chunking strategy: {strategy}")
        return chunker_cls()
