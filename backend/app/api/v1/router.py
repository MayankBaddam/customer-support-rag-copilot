from fastapi import APIRouter

from app.api.v1.system import api_router as system_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(system_router)