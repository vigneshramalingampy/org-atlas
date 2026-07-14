import json

from loguru import logger
from surrealdb import AsyncSurreal

from atlas_backend.provider.knowledge.vector_store.base import (
    SearchResult,
    VectorPoint,
    VectorStore,
)

COLLECTION = "chunks"


class SurrealDBVectorStore(VectorStore):
    def __init__(
        self,
        url: str,
        namespace: str,
        database: str,
        user: str = "root",
        password: str = "root",
    ) -> None:
        self._url = url
        self._namespace = namespace
        self._database = database
        self._user = user
        self._password = password
        self._client = AsyncSurreal(url)

    async def connect(self) -> None:
        await self._client.connect()
        await self._client.signin({"user": self._user, "pass": self._password})
        await self._client.use(self._namespace, self._database)
        logger.info("Connected to SurrealDB at {}", self._url)

    async def initialize(self, dimensions: int) -> None:
        await self._client.query(
            f"""
            DEFINE TABLE IF NOT EXISTS {COLLECTION} SCHEMAFULL;
            DEFINE FIELD IF NOT EXISTS chunk_id ON {COLLECTION} TYPE string;
            DEFINE FIELD IF NOT EXISTS text ON {COLLECTION} TYPE string;
            DEFINE FIELD IF NOT EXISTS index ON {COLLECTION} TYPE int;
            DEFINE FIELD IF NOT EXISTS parent_id ON {COLLECTION} TYPE option<string>;
            DEFINE FIELD IF NOT EXISTS child_ids ON {COLLECTION} TYPE option<array>;
            DEFINE FIELD IF NOT EXISTS source ON {COLLECTION} TYPE string;
            DEFINE FIELD IF NOT EXISTS page ON {COLLECTION} TYPE option<int>;
            DEFINE FIELD IF NOT EXISTS section ON {COLLECTION} TYPE option<string>;
            DEFINE FIELD IF NOT EXISTS file_type ON {COLLECTION} TYPE string;
            DEFINE FIELD IF NOT EXISTS char_count ON {COLLECTION} TYPE int;
            DEFINE FIELD IF NOT EXISTS token_count ON {COLLECTION} TYPE int;
            DEFINE FIELD IF NOT EXISTS embedding ON {COLLECTION} TYPE option<array<float>>;
            DEFINE FIELD IF NOT EXISTS document_id ON {COLLECTION} TYPE string;
            DEFINE INDEX IF NOT EXISTS idx_embedding ON {COLLECTION} FIELDS embedding
                HNSW DIMENSION {dimensions} DISTANCE cosine;
            """
        )
        logger.info("Initialized SurrealDB vector collection (dim={})", dimensions)

    async def upsert(self, points: list[VectorPoint]) -> None:
        if not points:
            return

        for point in points:
            await self._client.create(
                COLLECTION,
                {
                    "chunk_id": point.id,
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
        query_vec = json.dumps(query_vector)

        query = f"""
            SELECT id, chunk_id, vector::similarity::cosine(embedding, {query_vec}) AS score,
                   text, index, parent_id, child_ids, source, page, section,
                   file_type, char_count, token_count, document_id
            FROM {COLLECTION}
            WHERE embedding IS NOT NONE
   {" ".join(f"AND {k} = {json.dumps(v)}" for k, v in (filters or {}).items())}
            ORDER BY score DESC
            LIMIT {limit}
        """

        results = await self._client.query(query)

        if not results:
            return []

        search_results: list[SearchResult] = []
        for record in results:
            search_results.append(
                SearchResult(
                    id=str(record["id"]),
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
            await self._client.query(
                f"DELETE FROM {COLLECTION} WHERE chunk_id = '{vid}'",
            )

    async def delete_by_filter(self, filters: dict) -> None:
        where_clauses = " AND ".join(
            f"{k} = {json.dumps(v)}" for k, v in filters.items()
        )
        await self._client.query(f"DELETE FROM {COLLECTION} WHERE {where_clauses}")

    async def close(self) -> None:
        await self._client.close()
