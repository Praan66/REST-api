# from datetime import datetime
from pydantic import BaseModel

# user_post schema
class UserRegistration(BaseModel):
    # id: int
    username: str
    email_id: str
    password: str
    # created_at: datetime
    # updated_at: datetime
    
class UserLogin(BaseModel):
    email_id: str
    password: str

    class config:
        from_attribute = True