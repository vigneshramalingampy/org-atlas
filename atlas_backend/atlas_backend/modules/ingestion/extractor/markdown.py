from pathlib import Path

import mistune
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


class MarkdownExtractor(DocumentExtractor):
    """Extract text from a Markdown file.

    Strategy: convert the Markdown to HTML via mistune, then use BeautifulSoup
    to strip the HTML tags and recover plain text.
    """

    async def extract(self, file_path: str) -> ParsedDocument:
        logger.info("Extracting Markdown: {}", file_path)

        path = Path(file_path)
        if not path.exists():
            logger.warning("Markdown file not found: {}", file_path)
            raise DocumentExtractionError(f"File not found: {file_path}")

        try:
            raw_md = path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.error("Failed to read Markdown {}: {}", file_path, exc)
            raise DocumentExtractionError(f"Failed to read {file_path}: {exc}") from exc

        try:
            render = mistune.create_markdown()
            html = render(raw_md)
        except Exception as exc:
            logger.error("Failed to parse Markdown {}: {}", file_path, exc)
            raise DocumentExtractionError(
                f"Failed to parse Markdown {file_path}: {exc}"
            ) from exc

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        for tag in {
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "form",
            "iframe",
            "noscript",
        }:
            for el in soup.find_all(tag):
                el.decompose()

        text = soup.get_text(separator="\n", strip=True)

        if not text:
            logger.warning("No extractable text found in Markdown: {}", file_path)
            raise DocumentExtractionError(f"No extractable text found in {file_path}")

        char_count = len(text)
        logger.info("Markdown extracted: {} chars from {}", char_count, path.name)

        metadata = DocumentMetadata(
            filename=path.name,
            total_pages=1,
            file_type=FileType.MARKDOWN,
        )
        page = DocumentPage(page_number=0, text=text)

        return ParsedDocument(metadata=metadata, pages=[page])
