from enum import Enum

from loguru import logger

from atlas_backend.provider.llm.base import LLMProvider


class RetrievalStrategy(str, Enum):
    VECTOR_ONLY = "vector_only"
    GRAPH_ONLY = "graph_only"
    HYBRID = "hybrid"


CLASSIFICATION_PROMPT = """You are a query classifier for a Retrieval-Augmented Generation system with both a vector store and a knowledge graph.

Given the user query, classify it into exactly ONE of these categories:

- **vector_only**: Simple factual lookups, definitions, "what is X", "when did Y happen", single-entity queries where semantic similarity search is sufficient.
- **graph_only**: Pure relationship/structural queries like "who works at Z", "what depends on X", "show me the hierarchy" — queries answerable purely by traversing entity relationships without needing document chunks.
- **hybrid**: Queries needing both semantic context AND relational knowledge — "how does X relate to Y", "explain the architecture", multi-entity comparison, causal reasoning, or anything that benefits from both document text and graph connections.

Return ONLY one word: vector_only, graph_only, or hybrid. Nothing else.

Query: {query}"""


class QueryRouter:
    def __init__(
        self,
        llm_provider: LLMProvider,
        model: str = "",
        graph_enabled: bool = True,
    ) -> None:
        self._llm = llm_provider
        self._model = model
        self._graph_enabled = graph_enabled

    async def classify(self, query: str) -> RetrievalStrategy:
        if not self._graph_enabled:
            return RetrievalStrategy.VECTOR_ONLY

        prompt = CLASSIFICATION_PROMPT.format(query=query)

        response = await self._llm.generate(
            messages=[{"role": "user", "content": prompt}],
            model=self._model,
            temperature=0.0,
            max_tokens=20,
        )

        strategy = self._parse_response(response)
        logger.info(
            "Query classified as '{}' for query='{}'",
            strategy.value,
            query[:80],
        )
        return strategy

    @staticmethod
    def _parse_response(response: str) -> RetrievalStrategy:
        raw = response.strip().lower().strip("\"'`.,;:!?")

        for strategy in RetrievalStrategy:
            if strategy.value in raw:
                return strategy

        logger.warning(
            "Unrecognized classification '{}', falling back to VECTOR_ONLY", raw
        )
        return RetrievalStrategy.VECTOR_ONLY
