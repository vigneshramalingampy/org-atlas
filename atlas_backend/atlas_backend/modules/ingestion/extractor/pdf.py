import fitz
from loguru import logger

from atlas_backend.modules.ingestion.extractor.base import DocumentExtractor
from atlas_backend.modules.ingestion.extractor.model import (
    ParsedDocument,
    DocumentPage,
    DocumentMetadata,
)
from atlas_backend.utils.enums import FileType


class PdfExtractor(DocumentExtractor):
    async def extract(self, file_path: str) -> ParsedDocument:
        logger.info("Extracting PDF: {}", file_path)

        file = fitz.open(file_path)

        pages: list[DocumentPage] = []

        for page_number in range(file.page_count):
            page = file.load_page(page_number)

            pages.append(DocumentPage(page_number=page_number, text=page.get_text()))

        pdf_metadata = DocumentMetadata(
            filename=file_path.split("/")[-1],
            total_pages=file.page_count,
            file_type=FileType.PDF,
        )

        char_count = sum(len(p.text) for p in pages)
        logger.info(
            "PDF extracted: {} pages, {} chars from {}",
            file.page_count,
            char_count,
            pdf_metadata.filename,
        )

        return ParsedDocument(metadata=pdf_metadata, pages=pages)
