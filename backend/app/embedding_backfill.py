from __future__ import annotations

import argparse
import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_database_engine
from app.services.embedding_generation import EmbeddingGenerationService
from app.services.embeddings import EmbeddingProviderError, GeminiEmbeddingProvider


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
    try:
        provider = GeminiEmbeddingProvider(settings=settings)
    except EmbeddingProviderError as exc:
        print(
            json.dumps(
                {
                    "processed": 0,
                    "skipped": 0,
                    "failed": 0,
                    "status": "provider_initialization_failed",
                    "failures": [_failure_payload(exc)],
                }
            )
        )
        return 1
    with Session(get_database_engine()) as session:
        result = EmbeddingGenerationService(session, provider, settings).run(
            document_id=args.document_id,
            batch_size=args.batch_size,
            force=args.force,
            limit=args.limit,
            dry_run=args.dry_run,
        )
    print(
        json.dumps(
            {
                "processed": result.processed,
                "skipped": result.skipped,
                "failed": result.failed,
                "status": result.status,
                "failures": [
                    {
                        "exception_type": failure.exception_type,
                        "message": failure.message,
                        "http_status": failure.http_status,
                        "retry_count": failure.retry_count,
                        "stage": failure.stage,
                    }
                    for failure in result.failures
                ],
            }
        )
    )
    return 1 if result.failed else 0


def _failure_payload(exc: EmbeddingProviderError) -> dict[str, str | int | None]:
    return {
        "exception_type": exc.exception_type,
        "message": str(exc),
        "http_status": exc.http_status,
        "retry_count": exc.retry_count,
        "stage": exc.stage,
    }


if __name__ == "__main__":
    raise SystemExit(main())
