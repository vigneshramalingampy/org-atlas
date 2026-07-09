from pathlib import Path

import mistune

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

    Why two hops (MD → HTML → text)?
    - mistune is the fastest Markdown→HTML renderer for Python.
    - BeautifulSoup already handles HTML→text perfectly (same pattern as HtmlExtractor).
    - This avoids writing a fragile Markdown AST walker ourselves.

    If you later need *structured* extraction (e.g., heading-aware sections),
    switch to a custom mistune renderer that collects the AST directly.
    """

    async def extract(self, file_path: str) -> ParsedDocument:
        path = Path(file_path)
        if not path.exists():
            raise DocumentExtractionError(f"File not found: {file_path}")

        try:
            raw_md = path.read_text(encoding="utf-8")
        except Exception as exc:
            raise DocumentExtractionError(
                f"Failed to read {file_path}: {exc}"
            ) from exc

        # --- Convert Markdown → HTML ---------------------------------------
        try:
            # mistune.create_markdown() returns a render function
            render = mistune.create_markdown()
            html = render(raw_md)
        except Exception as exc:
            raise DocumentExtractionError(
                f"Failed to parse Markdown {file_path}: {exc}"
            ) from exc

        # --- Strip HTML tags → plain text ----------------------------------
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        # Remove the same noise elements as HtmlExtractor
        for tag in {"script", "style", "nav", "footer", "header",
                     "aside", "form", "iframe", "noscript"}:
            for el in soup.find_all(tag):
                el.decompose()

        text = soup.get_text(separator="\n", strip=True)

        if not text:
            raise DocumentExtractionError(
                f"No extractable text found in {file_path}"
            )

        metadata = DocumentMetadata(
            filename=path.name,
            total_pages=1,
            file_type=FileType.MARKDOWN,
        )
        page = DocumentPage(page_number=0, text=text)

        return ParsedDocument(metadata=metadata, pages=[page])
