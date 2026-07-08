from abc import ABC, abstractmethod

from atlas_backend.modules.ingestion.extractor.model import ParsedDocument


class DocumentExtractor(ABC):
    @abstractmethod
    async def extract(self, file_path: str) -> ParsedDocument:
        """Extract a document."""
