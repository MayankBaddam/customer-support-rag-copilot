from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas.health import HealthResponse, ReadinessResponse

root_router = APIRouter(tags=["system"])
api_router = APIRouter(tags=["system"])
ReadinessCheck = Callable[[], Awaitable[dict[str, str]]]


@root_router.get("/health", response_model=HealthResponse)
@api_router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="customer-support-rag-backend")


@root_router.get("/ready", response_model=ReadinessResponse)
@api_router.get("/ready", response_model=ReadinessResponse)
async def readiness(request: Request) -> ReadinessResponse | JSONResponse:
    try:
        checks = await request.app.state.readiness_check()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "DEPENDENCY_UNAVAILABLE",
                    "message": "A required dependency is unavailable.",
                }
            },
        )
    return ReadinessResponse(status="ready", checks=checks)