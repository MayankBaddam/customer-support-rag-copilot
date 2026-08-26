from fastapi import APIRouter

from app.api.v1.system import api_router as system_router
from app.api.v1.auth import router as auth_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(system_router)
api_router.include_router(auth_router)