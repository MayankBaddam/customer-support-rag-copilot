from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_profile
from app.models import Profile
from app.schemas.auth import ProfileResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me", response_model=ProfileResponse)
def get_me(profile: Annotated[Profile, Depends(get_current_profile)]) -> Profile:
    return profile