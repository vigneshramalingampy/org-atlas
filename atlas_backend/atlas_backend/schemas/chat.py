from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str
    top_k: int = 5
    document_id: str | None = None


class SourceRef(BaseModel):
    chunk_id: str
    source: str
    page: int | None = None
    score: float
    text_preview: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceRef]
