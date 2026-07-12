from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class StoredFile:
    path: str
    bucket: str
    size_bytes: int


class StorageProvider(ABC):
    @abstractmethod
    async def upload(
        self, bucket: str, path: str, data: bytes, content_type: str
    ) -> StoredFile:
        """Upload a file to storage."""

    @abstractmethod
    async def download(self, bucket: str, path: str) -> bytes:
        """Download a file from storage."""

    @abstractmethod
    async def delete(self, bucket: str, path: str) -> None:
        """Delete a file from storage."""

    @abstractmethod
    async def exists(self, bucket: str, path: str) -> bool:
        """Check if a file exists in storage."""
