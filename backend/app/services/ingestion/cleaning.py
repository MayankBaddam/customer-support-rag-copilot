from __future__ import annotations

import re

from app.services.ingestion.extractors import ExtractedBlock, ExtractedDocument


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    lines = [line.strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def normalize_document(document: ExtractedDocument) -> ExtractedDocument:
    return ExtractedDocument(
        document.document_id,
        document.source_filename,
        tuple(
            ExtractedBlock(normalize_text(block.text), block.page_number, block.section_title)
            for block in document.blocks
            if normalize_text(block.text)
        ),
    )