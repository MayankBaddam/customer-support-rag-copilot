from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ProfileRole


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    role: ProfileRole