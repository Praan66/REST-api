from pydantic import BaseModel, EmailStr, field_serializer
from uuid import UUID
from datetime import datetime
from zoneinfo import ZoneInfo

# schema for user signup or registration
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str

# schema for user login schema
class UserLogin(BaseModel):
    username: str
    # email: EmailStr
    password: str