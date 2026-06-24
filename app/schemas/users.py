from pydantic import BaseModel, EmailStr, field_serializer
from uuid import UUID
from datetime import datetime
from zoneinfo import ZoneInfo

# Request & Response
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
