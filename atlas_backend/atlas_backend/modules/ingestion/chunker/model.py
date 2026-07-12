from dataclasses import dataclass, field


@dataclass(slots=True)
class ChunkMetadata:
    source: str
    page: int | None
    section: str | None
    file_type: str
    char_count: int
    token_count: int


@dataclass(slots=True)
class Chunk:
    id: str
    text: str
    index: int
    parent_id: str | None
    child_ids: list[str] = field(default_factory=list)
    metadata: ChunkMetadata | None = None
    embedding: list[float] | None = None
