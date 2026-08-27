from typing import Protocol


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class EmbeddingProviderError(Exception):
    """Safe provider error that contains no request content or credentials."""


class EmbeddingTimeoutError(EmbeddingProviderError):
    pass


class EmbeddingQuotaError(EmbeddingProviderError):
    pass


class EmbeddingResponseError(EmbeddingProviderError):
    pass


class EmbeddingDimensionError(EmbeddingResponseError):
    pass
