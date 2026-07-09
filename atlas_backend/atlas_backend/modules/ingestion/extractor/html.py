from pathlib import Path

from bs4 import BeautifulSoup

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
    """Extract clean readable text from an HTML file.

    Uses BeautifulSoup with the lxml parser (fast, lenient with broken HTML).
    Strips non-content elements (script, style, nav, etc.) so the RAG pipeline
    doesn't index navigation menus, ads, or JavaScript.
    """

    # Tags whose contents are never useful for text extraction
    NOISE_TAGS = {"script", "style", "nav", "footer", "header", "aside", "form",
                  "iframe", "noscript"}

    async def extract(self, file_path: str) -> ParsedDocument:
        path = Path(file_path)
        if not path.exists():
            raise DocumentExtractionError(f"File not found: {file_path}")

        try:
            raw_html = path.read_text(encoding="utf-8")
        except Exception as exc:
            raise DocumentExtractionError(
                f"Failed to read {file_path}: {exc}"
            ) from exc

        try:
            soup = BeautifulSoup(raw_html, "lxml")
        except Exception as exc:
            raise DocumentExtractionError(
                f"Failed to parse HTML {file_path}: {exc}"
            ) from exc

        # --- Strip noise ---------------------------------------------------
        for tag in self.NOISE_TAGS:
            for element in soup.find_all(tag):
                element.decompose()  # removes tag AND its children

        # --- Extract title (for metadata / display) ------------------------
        title_tag = soup.find("title")
        display_name = title_tag.get_text(strip=True) if title_tag else path.name

        # --- Extract body text ----------------------------------------------
        body = soup.find("body")
        if body is None:
            # Some documents only have body content implicitly
            body = soup

        text = body.get_text(separator="\n", strip=True)

        if not text:
            raise DocumentExtractionError(
                f"No extractable text found in {file_path}"
            )

        metadata = DocumentMetadata(
            filename=display_name,
            total_pages=1,
            file_type=FileType.HTML,
        )
        page = DocumentPage(page_number=0, text=text)

        return ParsedDocument(metadata=metadata, pages=[page])
