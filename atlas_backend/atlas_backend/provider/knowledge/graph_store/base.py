from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(slots=True)
class Entity:
    id: str
    name: str
    entity_type: str
    properties: dict = field(default_factory=dict)


@dataclass(slots=True)
class Relationship:
    id: str
    source_id: str
    target_id: str
    relation_type: str
    properties: dict = field(default_factory=dict)


@dataclass(slots=True)
class Subgraph:
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)


class GraphStore(ABC):
    @abstractmethod
    async def add_entity(self, entity: Entity) -> str:
        """Add an entity to the graph store."""

    @abstractmethod
    async def add_relationship(self, relationship: Relationship) -> str:
        """Add a relationship to the graph store."""

    @abstractmethod
    async def traverse(
        self,
        start_id: str,
        depth: int = 2,
        relation_types: list[str] | None = None,
    ) -> Subgraph:
        """Traverse the graph from a starting entity."""

    @abstractmethod
    async def find_entity(
        self, name: str, entity_type: str | None = None
    ) -> list[Entity]:
        """Find entities by name and optional type."""
