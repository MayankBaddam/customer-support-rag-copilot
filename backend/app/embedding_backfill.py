from __future__ import annotations

import argparse
import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_database_engine
from app.services.embedding_generation import EmbeddingGenerationService
from app.services.embeddings import GeminiEmbeddingProvider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate embeddings for completed document chunks.")
    parser.add_argument("--dry-run", action="store_true", help="Count eligible chunks without calling Gemini or writing embeddings.")
    parser.add_argument("--document-id", type=UUID, help="Limit the backfill to one document UUID.")
    parser.add_argument("--batch-size", type=int, help="Override EMBEDDING_BATCH_SIZE for this run.")
    parser.add_argument("--force", action="store_true", help="Explicitly replace existing embeddings.")
    parser.add_argument("--limit", type=int, help="Maximum number of eligible chunks to process.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    with Session(get_database_engine()) as session:
        result = EmbeddingGenerationService(
            session,
            GeminiEmbeddingProvider(settings=settings),
            settings,
        ).run(
            document_id=args.document_id,
            batch_size=args.batch_size,
            force=args.force,
            limit=args.limit,
            dry_run=args.dry_run,
        )
    print(json.dumps({"processed": result.processed, "skipped": result.skipped, "failed": result.failed, "status": result.status}))
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
