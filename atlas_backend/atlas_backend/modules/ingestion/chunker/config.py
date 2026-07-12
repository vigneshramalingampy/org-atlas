from dataclasses import dataclass, field


@dataclass
class ChunkingConfig:
    strategy: str = "recursive"
    max_chunk_size: int = 512
    min_chunk_size: int = 100
    parent_size: int = 1024
    overlap: int = 0
    separators: list[str] = field(default_factory=lambda: ["\n\n", "\n", ". ", " "])
    keep_tables_whole: bool = True
    keep_code_blocks_whole: bool = True
