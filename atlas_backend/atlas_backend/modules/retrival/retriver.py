from loguru import logger

from atlas_backend.provider.embedding.base import EmbeddingProvider
from atlas_backend.provider.knowledge.graph_store.base import GraphStore, Subgraph
from atlas_backend.provider.knowledge.vector_store.base import (
    SearchResult,
    VectorStore,
)
from atlas_backend.modules.retrival.query_router import RetrievalStrategy


class Retriever:
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        graph_store: GraphStore | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
        graph_depth: int = 2,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider
        self._graph_store = graph_store
        self._top_k = top_k
        self._min_score = min_score
        self._graph_depth = graph_depth

    async def retrieve(
        self,
        query: str,
        strategy: RetrievalStrategy,
        top_k: int | None = None,
        document_id: str | None = None,
    ) -> tuple[list[SearchResult], Subgraph]:
        if strategy == RetrievalStrategy.GRAPH_ONLY:
            return [], await self._graph_retrieve(query, document_id)
        if strategy == RetrievalStrategy.HYBRID:
            return await self._vector_retrieve(
                query, top_k, document_id
            ), await self._graph_retrieve(query, document_id)
        return await self._vector_retrieve(query, top_k, document_id), Subgraph()

    async def _vector_retrieve(
        self,
        query: str,
        top_k: int | None = None,
        document_id: str | None = None,
    ) -> list[SearchResult]:
        logger.debug("Vector retrieve: query='{}' (top_k={})", query[:100], top_k)

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
            "Vector results: {} total, {} after min_score",
            len(results),
            len(filtered),
        )
        return filtered

    async def _graph_retrieve(
        self,
        query: str,
        document_id: str | None = None,
    ) -> Subgraph:
        logger.debug("Graph retrieve: query='{}'", query[:100])

        if not self._graph_store:
            return Subgraph()

        try:
            embeddings = await self._embedding_provider.embed([query])
            query_vector = embeddings[0]

            filters: dict = {}
            if document_id:
                filters["document_id"] = document_id

            vector_results = await self._vector_store.search(
                query_vector=query_vector,
                limit=5,
                filters=filters if filters else None,
            )

            entity_names = self._extract_entity_names(vector_results)
            if not entity_names:
                return Subgraph()

            all_entities = []
            seen_entity_ids: set[str] = set()

            for name in entity_names:
                entities = await self._graph_store.find_entity(name)
                for entity in entities:
                    if entity.id not in seen_entity_ids:
                        seen_entity_ids.add(entity.id)
                        all_entities.append(entity)

                        neighbors = await self._graph_store.find_neighbors(
                            entity.id,
                            depth=self._graph_depth,
                        )
                        for neighbor in neighbors:
                            if neighbor.id not in seen_entity_ids:
                                seen_entity_ids.add(neighbor.id)
                                all_entities.append(neighbor)

            subgraph = Subgraph(entities=all_entities) if all_entities else Subgraph()
            logger.debug("Graph context: {} entities", len(subgraph.entities))
            return subgraph

        except Exception as exc:
            logger.warning("Graph retrieval failed: {}", exc)
            return Subgraph()

    @staticmethod
    def _extract_entity_names(results: list[SearchResult]) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()

        for r in results:
            text = r.payload.get("text", "")
            for word in text.split():
                clean = word.strip(".,;:!?\"'()[]{}")
                if clean and clean[0].isupper() and len(clean) > 2:
                    lower = clean.lower()
                    if lower not in seen:
                        seen.add(lower)
                        names.append(clean)

        return names[:20]
