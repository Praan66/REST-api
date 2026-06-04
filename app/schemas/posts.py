from typing import List

from pydantic import BaseModel, EmailStr, HttpUrl, field_serializer
from uuid import UUID
from datetime import datetime
from zoneinfo import ZoneInfo

class TypeUrl(BaseModel):
    type: str
    url: str

class PostCreatePostResponse(BaseModel):
    message: str
    post_id: UUID
    content: str
    caption: str
    media: List[TypeUrl]

class VideoURLResponse(BaseModel):
    video_url: HttpUrl

class ImageURLResponse(BaseModel):
    image_url: HttpUrl

class PutEditUserPostResponse(BaseModel):
    id: UUID
    content: str
    caption: str
    media: str


class UserPublicSchema(BaseModel):
    id: UUID
    username: str
    email_id: EmailStr
    model_config = {"from_attributes": True}

class MediaSchema(BaseModel):
    id: UUID
    url: str
    type: str
    order_index: int
    model_config = {"from_attributes": True}

class PostDetailResponse(BaseModel):
    id: UUID
    content: str
    caption: str
    created_at: datetime
    user: UserPublicSchema
    media: List[MediaSchema]
    model_config = {"from_attributes": True}
    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime):
        ist = dt.astimezone(ZoneInfo("Asia/Kolkata"))
        return ist.strftime("%B %d, %Y %I:%M %p")