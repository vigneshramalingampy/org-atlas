import json
import logging

from surrealdb import Surreal

from atlas_backend.provider.knowledge.vector_store.base import (
    SearchResult,
    VectorPoint,
    VectorStore,
)

logger = logging.getLogger(__name__)

COLLECTION = "chunks"


class SurrealDBVectorStore(VectorStore):
    def __init__(self, url: str, namespace: str, database: str) -> None:
        self._url = url
        self._namespace = namespace
        self._database = database
        self._client = Surreal(url)

    async def connect(self) -> None:
        await self._client.connect()
        await self._client.use_namespace(self._namespace)
        await self._client.use_database(self._database)
        logger.info("Connected to SurrealDB at %s", self._url)

    async def initialize(self, dimensions: int) -> None:
        await self._client.query(
            f"""
            DEFINE TABLE {COLLECTION} SCHEMAFULL;
            DEFINE FIELD text ON {COLLECTION} TYPE string;
            DEFINE FIELD index ON {COLLECTION} TYPE int;
            DEFINE FIELD parent_id ON {COLLECTION} TYPE option<string>;
            DEFINE FIELD child_ids ON {COLLECTION} TYPE array;
            DEFINE FIELD source ON {COLLECTION} TYPE string;
            DEFINE FIELD page ON {COLLECTION} TYPE option<int>;
            DEFINE FIELD section ON {COLLECTION} TYPE option<string>;
            DEFINE FIELD file_type ON {COLLECTION} TYPE string;
            DEFINE FIELD char_count ON {COLLECTION} TYPE int;
            DEFINE FIELD token_count ON {COLLECTION} TYPE int;
            DEFINE FIELD embedding ON {COLLECTION} TYPE option<array<float>>;
            DEFINE FIELD document_id ON {COLLECTION} TYPE string;
            DEFINE INDEX idx_embedding ON {COLLECTION} FIELDS embedding HNSW options {{
                dimensions: {dimensions},
                distance: cosine
            }};
            """
        )
        logger.info("Initialized SurrealDB vector collection (dim=%d)", dimensions)

    async def upsert(self, points: list[VectorPoint]) -> None:
        if not points:
            return

        for point in points:
            await self._client.merge(
                COLLECTION,
                {
                    "id": point.id,
                    "embedding": point.vector,
                    **point.payload,
                },
            )

    async def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        query = f"""
            SELECT id, vector::similarity::cosine(embedding, $query) AS score,
                   text, index, parent_id, child_ids, source, page, section,
                   file_type, char_count, token_count, document_id
            FROM {COLLECTION}
            WHERE embedding IS NOT NONE
            ORDER BY vector::similarity::cosine(embedding, $query) DESC
            LIMIT $limit
        """

        results = await self._client.query(
            query, {"query": query_vector, "limit": limit}
        )

        if not results:
            return []

        search_results: list[SearchResult] = []
        for record in results[0]["result"]:
            search_results.append(
                SearchResult(
                    id=record["id"],
                    score=record.get("score", 0.0),
                    payload={
                        "text": record.get("text", ""),
                        "source": record.get("source", ""),
                        "page": record.get("page"),
                        "section": record.get("section"),
                        "file_type": record.get("file_type", ""),
                        "document_id": record.get("document_id", ""),
                    },
                )
            )

        return search_results

    async def delete(self, ids: list[str]) -> None:
        for vid in ids:
            await self._client.delete(COLLECTION, vid)

    async def delete_by_filter(self, filters: dict) -> None:
        where_clauses = " AND ".join(
            f"{k} = {json.dumps(v)}" for k, v in filters.items()
        )
        await self._client.query(f"DELETE FROM {COLLECTION} WHERE {where_clauses}")

    async def close(self) -> None:
        await self._client.close()
