from dataclasses import dataclass, field


@dataclass(slots=True)
class DocumentMetadata:
    filename: str
    total_pages: int
    file_type: str


@dataclass(slots=True)
class DocumentPage:
    page_number: int
    text: str


@dataclass(slots=True)
class ParsedDocument:
    metadata: DocumentMetadata
    pages: list[DocumentPage] = field(default_factory=list)
