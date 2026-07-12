from datetime import datetime

from pydantic import BaseModel

from atlas_backend.modules.ingestion.model import IngestionStatus


class UploadResponse(BaseModel):
    job_id: str
    status: IngestionStatus
    filename: str
    file_type: str
    checksum: str


class IngestionJobProgress(BaseModel):
    stage: str
    total_chunks: int | None = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: IngestionStatus
    progress: IngestionJobProgress | None = None
    total_chunks: int | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
