from pathlib import Path

from docx import Document as DocxDocument

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


class DocxExtractor(DocumentExtractor):
    """Extract text from a .docx Word file.

    Uses python-docx to open the XML-based .docx format and iterate over
    paragraphs. Paragraph boundaries are preserved as double newlines so the
    downstream chunker can recognise logical breaks.

    NOTE: Tables are NOT extracted here. A future enhancement could call
    iter_cells() on each table and format the output as pipe-delimited rows.
    """

    async def extract(self, file_path: str) -> ParsedDocument:
        path = Path(file_path)
        if not path.exists():
            raise DocumentExtractionError(f"File not found: {file_path}")

        try:
            doc = DocxDocument(str(path))
        except Exception as exc:
            raise DocumentExtractionError(
                f"Failed to open DOCX {file_path}: {exc}"
            ) from exc

        # --- Collect paragraph text ----------------------------------------
        paragraphs: list[str] = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)

        # --- Also extract table text (flat, row-by-row) --------------------
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                line = " | ".join(cells)
                if line.strip():
                    paragraphs.append(line)

        if not paragraphs:
            raise DocumentExtractionError(
                f"No extractable text found in {file_path}"
            )

        text = "\n\n".join(paragraphs)

        metadata = DocumentMetadata(
            filename=path.name,
            total_pages=1,
            file_type=FileType.DOCX,
        )
        page = DocumentPage(page_number=0, text=text)

        return ParsedDocument(metadata=metadata, pages=[page])
