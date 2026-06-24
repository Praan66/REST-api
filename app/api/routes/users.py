# libs, moduls, methods
from uuid import UUID
from fastapi import APIRouter, Depends
from app.db.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.users import GetUserResponse

from app.services.users import users_route, user_by_id_route, my_profile
from app.auth.main import require_roles

router = APIRouter(prefix="/users") # mini application

# ENDPOINTS
# http - GET method(all user)
@router.get("/", response_model=list[GetUserResponse])
async def get_users_route(db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_roles(["admin"]))):
    users = await users_route(db)
    return users

@router.get("/me", response_model=GetUserResponse)
async def get_my_profile(db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_roles(["user"]))):
    me_user = await my_profile(db, UUID(current_user["sub"]))
    return me_user

# http - GET method(get particular user)
@router.get("/{user_id}", response_model=GetUserResponse)
async def get_user_by_id_route(user_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_roles(["admin"]))):
    users = await user_by_id_route(db, user_id)
    return users

