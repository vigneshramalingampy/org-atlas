from abc import ABC, abstractmethod

from atlas_backend.modules.ingestion.extractor.model import ParsedDocument


class DocumentCleaner(ABC):
    @abstractmethod
    async def clean(self, document: ParsedDocument) -> ParsedDocument:
        """Clean a parsed document."""
