from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.services.ingestion.extractors import ExtractedBlock, ExtractedDocument
from app.services.ingestion.tokenizing import count_tokens, tokenize


@dataclass(frozen=True, slots=True)
class ChunkConfig:
    target_tokens: int = 500
    overlap_tokens: int = 75

    def __post_init__(self) -> None:
        if self.target_tokens <= 0:
            raise ValueError("target_tokens must be greater than zero")
        if self.overlap_tokens < 0 or self.overlap_tokens >= self.target_tokens:
            raise ValueError("overlap_tokens must be less than target_tokens")


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    chunk_index: int
    content: str
    token_count: int
    page_number: int | None
    section_title: str | None
    metadata: dict


def _split_block(block: ExtractedBlock, config: ChunkConfig) -> list[ExtractedBlock]:
    words = tokenize(block.text)
    if len(words) <= config.target_tokens:
        return [block]
    step = config.target_tokens - config.overlap_tokens
    return [
        ExtractedBlock(" ".join(words[start : start + config.target_tokens]), block.page_number, block.section_title)
        for start in range(0, len(words), step)
        if words[start : start + config.target_tokens]
    ]


def create_chunks(document: ExtractedDocument, config: ChunkConfig | None = None) -> list[ChunkDraft]:
    config = config or ChunkConfig()
    blocks = [block for source in document.blocks for block in _split_block(source, config) if source.text.strip()]
    chunks: list[ChunkDraft] = []
    current: list[ExtractedBlock] = []
    current_tokens = 0

    def emit(items: list[ExtractedBlock]) -> None:
        content = "\n\n".join(item.text.strip() for item in items if item.text.strip())
        if content:
            first = items[0]
            chunks.append(
                ChunkDraft(
                    len(chunks), content, count_tokens(content), first.page_number, first.section_title,
                    {"document_id": str(document.document_id), "source_filename": document.source_filename},
                )
            )

    for block in blocks:
        block_tokens = count_tokens(block.text)
        if current and current_tokens + block_tokens > config.target_tokens:
            emit(current)
            overlap: list[ExtractedBlock] = []
            overlap_count = 0
            for item in reversed(current):
                if overlap_count + count_tokens(item.text) > config.overlap_tokens:
                    break
                overlap.insert(0, item)
                overlap_count += count_tokens(item.text)
            current = overlap
            current_tokens = overlap_count
        current.append(block)
        current_tokens += block_tokens
    emit(current)
    return chunks