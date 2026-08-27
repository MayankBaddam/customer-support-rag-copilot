from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from re import match
from uuid import UUID

from pypdf import PdfReader

from app.models.enums import DocumentFileType


@dataclass(frozen=True, slots=True)
class ExtractedBlock:
    text: str
    page_number: int | None = None
    section_title: str | None = None


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    document_id: UUID
    source_filename: str
    blocks: tuple[ExtractedBlock, ...]

    @property
    def text(self) -> str:
        return "\n\n".join(block.text for block in self.blocks if block.text)


class PlainTextExtractor:
    def extract(self, content: bytes, *, document_id: UUID, source_filename: str) -> ExtractedDocument:
        return ExtractedDocument(
            document_id,
            source_filename,
            (ExtractedBlock(content.decode("utf-8-sig", errors="replace")),),
        )


class MarkdownExtractor(PlainTextExtractor):
    def extract(self, content: bytes, *, document_id: UUID, source_filename: str) -> ExtractedDocument:
        text = content.decode("utf-8-sig", errors="replace")
        blocks: list[ExtractedBlock] = []
        current_section: str | None = None
        current_lines: list[str] = []

        def flush() -> None:
            if current_lines:
                blocks.append(ExtractedBlock("\n".join(current_lines), section_title=current_section))
                current_lines.clear()

        for line in text.splitlines():
            heading = match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
            if heading:
                flush()
                current_section = heading.group(1).strip()
                blocks.append(ExtractedBlock(line.strip(), section_title=current_section))
            elif not line.strip():
                flush()
            else:
                current_lines.append(line)
        flush()
        return ExtractedDocument(document_id, source_filename, tuple(blocks))


class PdfExtractor:
    def extract(self, content: bytes, *, document_id: UUID, source_filename: str) -> ExtractedDocument:
        reader = PdfReader(BytesIO(content))
        blocks = tuple(
            ExtractedBlock(page.extract_text() or "", page_number=page_number)
            for page_number, page in enumerate(reader.pages, start=1)
        )
        return ExtractedDocument(document_id, source_filename, blocks)


def extractor_for_file_type(file_type: DocumentFileType):
    return {
        DocumentFileType.PDF: PdfExtractor,
        DocumentFileType.MARKDOWN: MarkdownExtractor,
        DocumentFileType.TEXT: PlainTextExtractor,
    }[file_type]()