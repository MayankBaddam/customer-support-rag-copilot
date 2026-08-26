from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.api.v1.system import root_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.services.readiness import check_readiness

settings = get_settings()
configure_logging(settings.environment)


app = FastAPI(
    title="Customer Support RAG Copilot API",
    version="0.1.0",
    description="Backend foundation for the CloudDesk support workspace.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.readiness_check = check_readiness
register_exception_handlers(app)

app.include_router(api_router)
app.include_router(root_router)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"service": "customer-support-rag-backend", "status": "scaffolded"}