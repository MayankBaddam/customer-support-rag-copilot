import json
import logging
import sys
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request

REQUEST_LOG_FIELDS = (
    "event",
    "request_id",
    "request_method",
    "request_path",
    "status_code",
    "latency_ms",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in REQUEST_LOG_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload)


def register_request_logging(app: FastAPI) -> None:
    logger = logging.getLogger("app.requests")

    @app.middleware("http")
    async def log_request(request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        metadata = {
            "request_id": request_id,
            "request_method": request.method,
            "request_path": request.url.path,
        }
        logger.info("request_start", extra={"event": "request_start", **metadata})
        started_at = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.error(
                "request_failure",
                extra={
                    "event": "request_failure",
                    "status_code": 500,
                    "latency_ms": round((perf_counter() - started_at) * 1000, 3),
                    **metadata,
                },
            )
            raise

        latency_ms = round((perf_counter() - started_at) * 1000, 3)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_complete",
            extra={
                "event": "request_complete",
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                **metadata,
            },
        )
        if response.status_code >= 400:
            logger.warning(
                "request_failure",
                extra={
                    "event": "request_failure",
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    **metadata,
                },
            )
        return response


def configure_logging(environment: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG if environment == "development" else logging.INFO)
    for logger_name in ("httpcore", "httpx", "google"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)
