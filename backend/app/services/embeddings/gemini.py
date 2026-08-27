from __future__ import annotations

import math

import httpx

from app.core.config import Settings, get_settings
from app.services.embeddings.base import (
    EmbeddingDimensionError,
    EmbeddingProviderError,
    EmbeddingQuotaError,
    EmbeddingResponseError,
    EmbeddingTimeoutError,
)


class GeminiEmbeddingProvider:
    api_base_url = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, client: httpx.Client | None = None, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client or httpx.Client(timeout=self._settings.embedding_api_timeout_seconds)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._settings.embedding_batch_size):
            vectors.extend(self._embed_batch(texts[start : start + self._settings.embedding_batch_size], "RETRIEVAL_DOCUMENT"))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        if not text.strip():
            raise EmbeddingProviderError("The embedding query must not be empty.")
        return self._embed_batch([text], "RETRIEVAL_QUERY")[0]

    def _embed_batch(self, texts: list[str], task_type: str) -> list[list[float]]:
        if self._settings.gemini_api_key is None:
            raise EmbeddingProviderError("The embedding provider is not configured.")
        model = self._settings.embedding_model.removeprefix("models/")
        model_resource = f"models/{model}"
        requests = [
            {
                "model": model_resource,
                "content": {"parts": [{"text": text}]},
                "embedContentConfig": {
                    "taskType": task_type,
                    "outputDimensionality": self._settings.embedding_dimension,
                },
            }
            for text in texts
        ]
        try:
            response = self._client.post(
                f"{self.api_base_url}/{model_resource}:batchEmbedContents",
                headers={"x-goog-api-key": self._settings.gemini_api_key.get_secret_value()},
                json={"requests": requests},
                timeout=self._settings.embedding_api_timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise EmbeddingTimeoutError("The embedding provider timed out.") from exc
        except httpx.HTTPError as exc:
            raise EmbeddingProviderError("The embedding provider could not be reached.") from exc
        if response.status_code == 429:
            raise EmbeddingQuotaError("The embedding provider quota was exceeded.")
        if response.status_code >= 300:
            raise EmbeddingProviderError("The embedding provider request failed.")
        try:
            payload = response.json()
            embeddings = payload["embeddings"]
        except (ValueError, KeyError, TypeError) as exc:
            raise EmbeddingResponseError("The embedding provider returned a malformed response.") from exc
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise EmbeddingResponseError("The embedding provider returned an unexpected number of vectors.")
        vectors: list[list[float]] = []
        for embedding in embeddings:
            values = embedding.get("values") if isinstance(embedding, dict) else None
            if not isinstance(values, list) or not all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) for value in values):
                raise EmbeddingResponseError("The embedding provider returned a malformed vector.")
            if len(values) != self._settings.embedding_dimension:
                raise EmbeddingDimensionError("The embedding provider returned a vector with the wrong dimension.")
            vectors.append([float(value) for value in values])
        return vectors
