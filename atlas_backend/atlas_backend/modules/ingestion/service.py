from loguru import logger

from atlas_backend.modules.ingestion.chunker.config import ChunkingConfig
from atlas_backend.modules.ingestion.chunker.factory import ChunkingFactory
from atlas_backend.modules.ingestion.cleaner.factory import CleanerFactory
from atlas_backend.modules.ingestion.embedder.service import EmbeddingService
from atlas_backend.modules.ingestion.extractor.factory import ExtractorFactory
from atlas_backend.modules.ingestion.graph.base import GraphExtractor
from atlas_backend.modules.ingestion.model import IngestionJob, IngestionStatus
from atlas_backend.provider.embedding.base import EmbeddingProvider
from atlas_backend.provider.knowledge.graph_store.base import GraphStore
from atlas_backend.provider.knowledge.vector_store.base import VectorPoint, VectorStore
from atlas_backend.utils.enums import FileType


class IngestionService:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        chunking_config: ChunkingConfig | None = None,
        graph_extractor: GraphExtractor | None = None,
        graph_store: GraphStore | None = None,
    ) -> None:
        self._embedding_service = EmbeddingService(provider=embedding_provider)
        self._vector_store = vector_store
        self._chunking_config = chunking_config or ChunkingConfig()
        self._graph_extractor = graph_extractor
        self._graph_store = graph_store
        self._initialized = False
        self._graph_initialized = False

    async def _ensure_initialized(self, dimensions: int) -> None:
        if not self._initialized:
            await self._vector_store.initialize(dimensions)
            self._initialized = True

    async def _ensure_graph_initialized(self) -> None:
        if not self._graph_initialized and self._graph_store is not None:
            await self._graph_store.initialize()
            self._graph_initialized = True

    async def ingest(
        self, file_path: str, file_type: FileType, document_id: str
    ) -> IngestionJob:
        job = IngestionJob(
            id=document_id,
            filename=file_path.split("/")[-1].split("\\")[-1],
            file_type=file_type.value,
        )

        try:
            job.update_status(IngestionStatus.EXTRACTING)
            logger.info("[{}] Extracting {}", job.id, file_path)

            extractor = ExtractorFactory.create(file_type)
            parsed = await extractor.extract(file_path)

            job.update_status(IngestionStatus.CLEANING)
            logger.info("[{}] Cleaning document", job.id)

            cleaner = CleanerFactory.create("default")
            parsed = await cleaner.clean(parsed)

            job.update_status(IngestionStatus.CHUNKING)
            logger.info("[{}] Chunking document", job.id)

            chunker = ChunkingFactory.create(self._chunking_config.strategy)
            chunks = await chunker.chunk(parsed, self._chunking_config)

            micro_chunks = [c for c in chunks if c.parent_id is not None]
            logger.info(
                "[{}] Created {} micro chunks, {} macro chunks",
                job.id,
                len(micro_chunks),
                len(chunks) - len(micro_chunks),
            )

            job.update_status(IngestionStatus.EMBEDDING)
            logger.info("[{}] Embedding chunks", job.id)

            await self._ensure_initialized(self._embedding_service.dimensions)
            embedded_chunks = await self._embedding_service.embed_chunks(micro_chunks)

            job.update_status(IngestionStatus.STORING)
            logger.info("[{}] Storing vectors", job.id)

            points = [
                VectorPoint(
                    id=chunk.id,
                    vector=chunk.embedding,
                    payload={
                        "text": chunk.text,
                        "index": chunk.index,
                        "parent_id": chunk.parent_id,
                        "child_ids": chunk.child_ids,
                        "source": chunk.metadata.source,
                        "page": chunk.metadata.page,
                        "section": chunk.metadata.section,
                        "file_type": chunk.metadata.file_type,
                        "char_count": chunk.metadata.char_count,
                        "token_count": chunk.metadata.token_count,
                        "document_id": job.id,
                    },
                )
                for chunk in embedded_chunks
                if chunk.embedding is not None
            ]

            await self._vector_store.upsert(points)

            job.total_chunks = len(points)

            if self._graph_extractor and self._graph_store:
                job.update_status(IngestionStatus.GRAPH_EXTRACTING)
                logger.info("[{}] Extracting graph entities", job.id)

                await self._ensure_graph_initialized()
                await self._extract_and_store_graph(
                    embedded_chunks, job.id, parsed.text
                )

            job.update_status(IngestionStatus.COMPLETED)
            logger.info(
                "[{}] Ingestion complete — {} chunks stored", job.id, job.total_chunks
            )

        except Exception as exc:
            job.update_status(IngestionStatus.FAILED)
            job.error = str(exc)
            logger.exception("[{}] Ingestion failed: {}", job.id, exc)

        return job

    async def _extract_and_store_graph(
        self,
        chunks,
        document_id: str,
        full_text: str,
    ) -> None:
        all_entities = []
        all_relationships = []

        chunk_texts = [c.text for c in chunks]
        batch_size = 5

        for i in range(0, len(chunk_texts), batch_size):
            batch = chunk_texts[i : i + batch_size]
            batch_chunks = chunks[i : i + batch_size]

            for chunk_text, chunk in zip(batch, batch_chunks):
                try:
                    entities, relationships = await self._graph_extractor.extract(
                        text=chunk_text,
                        chunk_id=chunk.id,
                        document_id=document_id,
                    )
                    all_entities.extend(entities)
                    all_relationships.extend(relationships)
                except Exception as exc:
                    logger.warning(
                        "[{}] Graph extraction failed for chunk {}: {}",
                        document_id,
                        chunk.id,
                        exc,
                    )

        if all_entities:
            await self._graph_store.upsert_entities(all_entities, document_id)
            logger.info("[{}] Stored {} graph entities", document_id, len(all_entities))

        if all_relationships:
            await self._graph_store.upsert_relationships(all_relationships)
            logger.info(
                "[{}] Stored {} graph relationships",
                document_id,
                len(all_relationships),
            )
