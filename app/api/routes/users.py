# libs, moduls, mets
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from ...schemas.users import UserLogin, UserRegistration
from ...db.db import get_db, async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from ...schemas.users import UserPostCreate, UserPostResponse, GetUserResponse

# from sqlalchemy.orm import Session
from sqlalchemy import select, text
from ...db.models.users import User
from ...services.users import get_users, get_user_by_id

# mini application
router = APIRouter(prefix="/users")


users_list = {
    1: {"id": 1, "title": "New1 Post", "content": "naughty naughty"},
    2: {"id": 2, "title": "New2 Post", "content": "naughty naughty"},
    3: {"id": 3, "title": "New3 Post", "content": "naughty naughty"},
    4: {"id": 4, "title": "New4 Post", "content": "naughty naughty"},
}


# ENDPOINTS
# http - GET method(all user)
@router.get("/", response_model=list[GetUserResponse])
async def get_users_route(db: AsyncSession = Depends(get_db)):
    # using sqlalchemy orm language
    users = await get_users(db)
    return users

    # using raw sql
    # users = await db.execute(text("SELECT * FROM users"))
    # return users.mappings().all()


# http - GET method(get particular user)
@router.get("/{user_id}", response_model=GetUserResponse)
async def get_user_by_id_route(user_id: UUID, db: AsyncSession = Depends(get_db)):
    users = await get_user_by_id(user_id, db)
    return users
    
    # query = select(User).where(User.id == user_id)
    # result = await db.execute(query)
    # users = result.scalars().all()
    # if not users:
    #     raise HTTPException(status_code=404, detail="User not found!!")
    # return users


# http - POST method(add user)
@router.post("/createposts", status_code=201)
async def add_user(user_model: UserPostCreate):
    users_list[user_model.id] = user_model
    return user_model


# http - PUT method(update user data)
@router.put("/{user_id}")
def change_user_detail(user_id: int, userchanges: UserPostCreate):
    if user_id in users_list:
        users_list[user_id] = userchanges
        return userchanges
    raise HTTPException(status_code=404, detail="User not found!!")


@router.delete("/{user_id}")
def delete_user_post(user_id: int):
    if user_id in users_list:
        delete = users_list.pop(user_id)
        return delete
    raise HTTPException(status_code=404, detail="User post not found!!")
