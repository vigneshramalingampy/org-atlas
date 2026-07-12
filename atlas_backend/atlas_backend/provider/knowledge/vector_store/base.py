from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(slots=True)
class VectorPoint:
    id: str
    vector: list[float]
    payload: dict = field(default_factory=dict)


@dataclass(slots=True)
class SearchResult:
    id: str
    score: float
    payload: dict = field(default_factory=dict)


class VectorStore(ABC):
    @abstractmethod
    async def initialize(self, dimensions: int) -> None:
        """Initialize the collection with the given vector dimensions."""

    @abstractmethod
    async def upsert(self, points: list[VectorPoint]) -> None:
        """Insert or update vectors."""

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        """Search for similar vectors."""

    @abstractmethod
    async def delete(self, ids: list[str]) -> None:
        """Delete vectors by ID."""

    @abstractmethod
    async def delete_by_filter(self, filters: dict) -> None:
        """Delete vectors matching filters."""
