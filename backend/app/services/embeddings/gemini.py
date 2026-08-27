from __future__ import annotations

import math
import re
from typing import Any

import httpx
from google import genai
from google.genai import errors, types

from app.core.config import Settings, get_settings
from app.services.embeddings.base import (
    EmbeddingDimensionError,
    EmbeddingProviderError,
    EmbeddingQuotaError,
    EmbeddingResponseError,
    EmbeddingTimeoutError,
)


class GeminiEmbeddingProvider:
    def __init__(self, client: Any | None = None, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client or self._build_client()

    def _build_client(self) -> genai.Client:
        if self._settings.gemini_api_key is None:
            raise EmbeddingProviderError(
                "The embedding provider is not configured.",
                stage="before_provider_request",
            )
        try:
            return genai.Client(
                api_key=self._settings.gemini_api_key.get_secret_value(),
                http_options=types.HttpOptions(
                    timeout=int(self._settings.embedding_api_timeout_seconds * 1000),
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
        except Exception as exc:
            raise EmbeddingProviderError(
                "The embedding provider client could not be initialized.",
                exception_type=type(exc).__name__,
                stage="before_provider_request",
            ) from exc

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise EmbeddingProviderError(
                "Embedding input must contain non-empty text.",
                stage="before_provider_request",
            )
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._settings.embedding_batch_size):
            vectors.extend(
                self._embed_batch(
                    texts[start : start + self._settings.embedding_batch_size],
                    "RETRIEVAL_DOCUMENT",
                )
            )
        return vectors

    def embed_query(self, text: str) -> list[float]:
        if not text.strip():
            raise EmbeddingProviderError(
                "The embedding query must not be empty.",
                stage="before_provider_request",
            )
        return self._embed_batch([text], "RETRIEVAL_QUERY")[0]

    def _embed_batch(self, texts: list[str], task_type: str) -> list[list[float]]:
        try:
            response = self._client.models.embed_content(
                model=self._settings.embedding_model.removeprefix("models/"),
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=self._settings.embedding_dimension,
                ),
            )
        except errors.APIError as exc:
            message = self._sanitize_provider_message(exc.message, texts)
            error_class = EmbeddingQuotaError if exc.code == 429 else EmbeddingProviderError
            raise error_class(
                message,
                exception_type=type(exc).__name__,
                http_status=exc.code,
            ) from exc
        except httpx.TimeoutException as exc:
            raise EmbeddingTimeoutError(
                "The embedding provider timed out.",
                exception_type=type(exc).__name__,
            ) from exc
        except httpx.HTTPError as exc:
            raise EmbeddingProviderError(
                "The embedding provider could not be reached.",
                exception_type=type(exc).__name__,
            ) from exc
        except Exception as exc:
            raise EmbeddingProviderError(
                "The embedding provider request failed.",
                exception_type=type(exc).__name__,
            ) from exc
        embeddings = response.embeddings
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise EmbeddingResponseError("The embedding provider returned an unexpected number of vectors.")
        vectors: list[list[float]] = []
        for embedding in embeddings:
            values = getattr(embedding, "values", None)
            if not isinstance(values, list) or not all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                for value in values
            ):
                raise EmbeddingResponseError("The embedding provider returned a malformed vector.")
            if len(values) != self._settings.embedding_dimension:
                raise EmbeddingDimensionError("The embedding provider returned a vector with the wrong dimension.")
            vectors.append([float(value) for value in values])
        return vectors

    def _sanitize_provider_message(self, message: str, texts: list[str]) -> str:
        safe = message or "The embedding provider request failed."
        if self._settings.gemini_api_key is not None:
            safe = safe.replace(self._settings.gemini_api_key.get_secret_value(), "[REDACTED]")
        for text in texts:
            safe = safe.replace(text, "[CONTENT REDACTED]")
        safe = re.sub(r"(?i)(postgres(?:ql)?://)[^\s]+", r"\1[REDACTED]", safe)
        safe = " ".join(safe.split())
        return safe[:500]
