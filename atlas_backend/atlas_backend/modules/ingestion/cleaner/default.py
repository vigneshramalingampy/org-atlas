import re
import unicodedata

from atlas_backend.modules.ingestion.cleaner.base import DocumentCleaner
from atlas_backend.modules.ingestion.extractor.model import (
    DocumentPage,
    ParsedDocument,
)


class DefaultCleaner(DocumentCleaner):
    async def clean(self, document: ParsedDocument) -> ParsedDocument:
        cleaned_pages: list[DocumentPage] = []

        for page in document.pages:
            text = page.text
            text = unicodedata.normalize("NFKC", text)
            text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = "\n".join(line.rstrip() for line in text.split("\n"))
            text = text.strip()

            cleaned_pages.append(DocumentPage(page_number=page.page_number, text=text))

        return ParsedDocument(
            metadata=document.metadata,
            pages=cleaned_pages,
        )
