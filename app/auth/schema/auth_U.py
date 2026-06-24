from pydantic import BaseModel, EmailStr, field_serializer
from uuid import UUID
from datetime import datetime
from zoneinfo import ZoneInfo

# schema for user signup or registration
# Request & Response
class UserSignUpRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str
class UserSignUpResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    role: str


class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str