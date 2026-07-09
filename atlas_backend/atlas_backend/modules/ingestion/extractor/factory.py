from atlas_backend.modules.ingestion.extractor.base import DocumentExtractor
from atlas_backend.modules.ingestion.extractor.docx import DocxExtractor
from atlas_backend.modules.ingestion.extractor.html import HtmlExtractor
from atlas_backend.modules.ingestion.extractor.markdown import MarkdownExtractor
from atlas_backend.modules.ingestion.extractor.pdf import PdfExtractor
from atlas_backend.utils.enums import FileType


class ExtractorFactory:
    """Maps a FileType enum to its corresponding DocumentExtractor class.

    Usage:
        extractor = ExtractorFactory.create(FileType.PDF)
        doc = await extractor.extract("report.pdf")

    Adding a new format:
        1. Create a new extractor class (e.g., RtfExtractor).
        2. Import it here.
        3. Add the mapping below.
        That's it — call sites never change.
    """

    _registry: dict[FileType, type[DocumentExtractor]] = {
        FileType.PDF: PdfExtractor,
        FileType.HTML: HtmlExtractor,
        FileType.MARKDOWN: MarkdownExtractor,
        FileType.DOCX: DocxExtractor,
    }

    @classmethod
    def create(cls, file_type: FileType) -> DocumentExtractor:
        """Return an extractor instance suitable for *file_type*."""
        extractor_cls = cls._registry.get(file_type)
        if extractor_cls is None:
            raise ValueError(f"Unsupported file type: {file_type}")
        return extractor_cls()
