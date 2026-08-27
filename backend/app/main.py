from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.api.v1.system import root_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, register_request_logging
from app.services.readiness import check_readiness

settings = get_settings()
configure_logging(settings.environment)


def create_app(app_settings: Settings | None = None) -> FastAPI:
    active_settings = app_settings or get_settings()
    application = FastAPI(
        title="Customer Support RAG Copilot API",
        version="0.1.0",
        description="Backend foundation for the CloudDesk support workspace.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.allowed_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.state.readiness_check = check_readiness
    register_request_logging(application)
    register_exception_handlers(application)
    application.include_router(api_router)
    application.include_router(root_router)
    return application


app = create_app(settings)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"service": "customer-support-rag-backend", "status": "scaffolded"}
