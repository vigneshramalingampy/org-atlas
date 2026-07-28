from abc import ABC, abstractmethod

from atlas_backend.modules.ingestion.model import IngestionJob


class JobStore(ABC):
    @abstractmethod
    async def save(self, job: IngestionJob) -> None:
        """Persist an ingestion job (create or update)."""

    @abstractmethod
    async def get(self, job_id: str) -> IngestionJob | None:
        """Retrieve a job by ID."""

    @abstractmethod
    async def initialize(self) -> None:
        """Create the jobs table if it doesn't exist."""
