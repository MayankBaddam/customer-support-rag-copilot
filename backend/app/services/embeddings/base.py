from typing import Protocol


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class EmbeddingProviderError(Exception):
    """Safe provider error that contains no request content or credentials."""

    def __init__(
        self,
        message: str,
        *,
        exception_type: str | None = None,
        http_status: int | None = None,
        stage: str = "during_provider_request",
    ) -> None:
        super().__init__(message)
        self.exception_type = exception_type or type(self).__name__
        self.http_status = http_status
        self.stage = stage
        self.retry_count = 0


class EmbeddingTimeoutError(EmbeddingProviderError):
    pass


class EmbeddingQuotaError(EmbeddingProviderError):
    pass


class EmbeddingResponseError(EmbeddingProviderError):
    pass


class EmbeddingDimensionError(EmbeddingResponseError):
    pass
