from pydantic import BaseModel, EmailStr, field_serializer
from uuid import UUID
from datetime import datetime
from zoneinfo import ZoneInfo


# user_post schema
class UserRegistration(BaseModel):
    # id: int
    username: str
    email_id: EmailStr
    password: str
    # created_at: datetime
    # updated_at: datetime


class UserLogin(BaseModel):
    email_id: EmailStr
    password: str


class GetUserResponse(BaseModel):
    id: UUID
    username: str
    email_id: EmailStr
    created_at: datetime
    model_config = {"from_attributes": True}
    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime):
        ist = dt.astimezone(ZoneInfo("Asia/Kolkata"))
        return ist.strftime("%B %d, %Y %I:%M %p")
        # %B(month), %d(date), %Y(year), %I(Hour):%M(minute) %p(AM/PM)

class ProfileResponse(BaseModel):
    message: str
    detail: GetUserResponse

class UserPostCreate(BaseModel):
    title: str
    content: str


class UserPostResponse(BaseModel):
    id: int
    title: str
    content: str

    model_config = {"from_attributes": True}
