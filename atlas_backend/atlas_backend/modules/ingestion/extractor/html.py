from pathlib import Path

from bs4 import BeautifulSoup
from loguru import logger

from atlas_backend.modules.ingestion.extractor.base import DocumentExtractor
from atlas_backend.modules.ingestion.extractor.exceptions import (
    DocumentExtractionError,
)
from atlas_backend.modules.ingestion.extractor.model import (
    DocumentMetadata,
    DocumentPage,
    ParsedDocument,
)
from atlas_backend.utils.enums import FileType


class HtmlExtractor(DocumentExtractor):
    NOISE_TAGS = {
        "script",
        "style",
        "nav",
        "footer",
        "header",
        "aside",
        "form",
        "iframe",
        "noscript",
    }

    async def extract(self, file_path: str) -> ParsedDocument:
        logger.info("Extracting HTML: {}", file_path)

        path = Path(file_path)
        if not path.exists():
            logger.warning("HTML file not found: {}", file_path)
            raise DocumentExtractionError(f"File not found: {file_path}")

        try:
            raw_html = path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.error("Failed to read HTML {}: {}", file_path, exc)
            raise DocumentExtractionError(f"Failed to read {file_path}: {exc}") from exc

        try:
            soup = BeautifulSoup(raw_html, "lxml")
        except Exception as exc:
            logger.error("Failed to parse HTML {}: {}", file_path, exc)
            raise DocumentExtractionError(
                f"Failed to parse HTML {file_path}: {exc}"
            ) from exc

        for tag in self.NOISE_TAGS:
            for element in soup.find_all(tag):
                element.decompose()

        title_tag = soup.find("title")
        display_name = title_tag.get_text(strip=True) if title_tag else path.name

        body = soup.find("body")
        if body is None:
            body = soup

        text = body.get_text(separator="\n", strip=True)

        if not text:
            logger.warning("No extractable text found in HTML: {}", file_path)
            raise DocumentExtractionError(f"No extractable text found in {file_path}")

        char_count = len(text)
        logger.info("HTML extracted: {} chars from {}", char_count, display_name)

        metadata = DocumentMetadata(
            filename=display_name,
            total_pages=1,
            file_type=FileType.HTML,
        )
        page = DocumentPage(page_number=0, text=text)

        return ParsedDocument(metadata=metadata, pages=[page])
