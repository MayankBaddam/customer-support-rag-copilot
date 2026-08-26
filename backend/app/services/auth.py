from dataclasses import dataclass
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Profile


@dataclass(frozen=True)
class AuthenticatedUser:
    id: UUID
    email: str | None = None
    full_name: str | None = None


async def verify_access_token(token: str) -> AuthenticatedUser:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise RuntimeError("Supabase Auth is not configured.")
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}", "apikey": settings.supabase_anon_key},
        )
    if response.status_code != 200:
        raise ValueError("Supabase rejected the access token.")
    payload = response.json()
    return AuthenticatedUser(
        id=UUID(payload["id"]),
        email=payload.get("email"),
        full_name=(payload.get("user_metadata") or {}).get("full_name"),
    )


def get_or_create_profile(user: AuthenticatedUser, session: Session) -> Profile:
    profile = session.get(Profile, user.id)
    if profile is None:
        profile = Profile(id=user.id, full_name=user.full_name or user.email or "CloudDesk Agent")
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile