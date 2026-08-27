from uuid import uuid4

import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject

from app.services.ingestion import (
    ChunkConfig,
    ExtractedBlock,
    ExtractedDocument,
    MarkdownExtractor,
    PdfExtractor,
    PlainTextExtractor,
    count_tokens,
    create_chunks,
    normalize_document,
)


def pdf_fixture() -> bytes:
    writer = PdfWriter()
    for page_number in range(2):
        page = writer.add_blank_page(width=200, height=200)
        font = NameObject("/F1")
        font_dictionary = DictionaryObject()
        font_dictionary[font] = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): font_dictionary})
        stream = StreamObject()
        stream._data = f"BT /F1 12 Tf 20 100 Td (Page {page_number + 1} text) Tj ET".encode()
        page[NameObject("/Contents")] = writer._add_object(stream)
    import io

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_pdf_extraction_preserves_text_and_pages():
    document = PdfExtractor().extract(pdf_fixture(), document_id=uuid4(), source_filename="guide.pdf")

    assert [block.page_number for block in document.blocks] == [1, 2]
    assert [block.text.strip() for block in document.blocks] == ["Page 1 text", "Page 2 text"]
    assert document.source_filename == "guide.pdf"


def test_markdown_extraction_preserves_headings_and_sections():
    document = MarkdownExtractor().extract(
        b"# Refunds\n\nUse error code E-42.\n\n- Keep this list\n- And punctuation!",
        document_id=uuid4(),
        source_filename="guide.md",
    )

    assert document.blocks[0].text == "# Refunds"
    assert document.blocks[1].section_title == "Refunds"
    assert any("- Keep this list" in block.text for block in document.blocks)


def test_plain_text_extraction_and_normalization():
    document = PlainTextExtractor().extract(
        b"  first\r\n\r\n\r\nsecond\x00  ", document_id=uuid4(), source_filename="notes.txt"
    )

    normalized = normalize_document(document)
    assert normalized.text == "first\n\nsecond"


def test_empty_extracted_text_has_no_blocks():
    document = normalize_document(
        PlainTextExtractor().extract(b"\x00 \r\n", document_id=uuid4(), source_filename="empty.txt")
    )
    assert document.blocks == ()


def test_chunks_are_deterministic_and_have_metadata_and_counts():
    document = ExtractedDocument(
        uuid4(), "guide.md", (ExtractedBlock("Heading\n\nerror E-42.", page_number=2, section_title="Heading"),)
    )

    first = create_chunks(document, ChunkConfig(target_tokens=3, overlap_tokens=1))
    second = create_chunks(document, ChunkConfig(target_tokens=3, overlap_tokens=1))

    assert first == second
    assert first[0].chunk_index == 0
    assert first[0].token_count == count_tokens(first[0].content)
    assert first[0].page_number == 2
    assert first[0].metadata == {"document_id": str(document.document_id), "source_filename": "guide.md"}
    assert all(chunk.content for chunk in first)


def test_chunk_overlap_and_oversized_paragraph_handling():
    document = ExtractedDocument(uuid4(), "notes.txt", (ExtractedBlock("one two three four five six"),))
    chunks = create_chunks(document, ChunkConfig(target_tokens=4, overlap_tokens=2))

    assert chunks[0].content == "one two three four"
    assert chunks[1].content.startswith("three four")
    assert all(chunk.content for chunk in chunks)


def test_invalid_chunk_configuration_is_rejected():
    with pytest.raises(ValueError, match="less than"):
        ChunkConfig(target_tokens=10, overlap_tokens=10)

    with pytest.raises(ValueError):
        ChunkConfig(target_tokens=0, overlap_tokens=0)