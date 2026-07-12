from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class IngestionStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    CLEANING = "cleaning"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    status: IngestionStatus = IngestionStatus.PENDING
    filename: str = ""
    file_type: str = ""
    checksum: str = ""
    total_chunks: int | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def update_status(self, status: IngestionStatus) -> None:
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
