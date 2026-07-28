from abc import ABC, abstractmethod

from atlas_backend.provider.knowledge.graph_store.base import Entity, Relationship


class GraphExtractor(ABC):
    @abstractmethod
    async def extract(
        self,
        text: str,
        chunk_id: str,
        document_id: str,
    ) -> tuple[list[Entity], list[Relationship]]:
        """Extract entities and relationships from a text chunk."""
