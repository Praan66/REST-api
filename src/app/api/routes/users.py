# libs, moduls, mets
from fastapi import APIRouter, HTTPException
from app.schemas.users import User_post
from src.app.db.db import get_db, engine
from sqlalchemy.orm import Session
# from sqlalchemy.ext.asyncio import AsyncSession



# mini application
router = APIRouter(
    prefix="/users"
)


users_list = {
    1:{"id": 1, "title": "New1 Post", "content": "naughty naughty"},
    2:{"id": 2, "title": "New2 Post", "content": "naughty naughty"},
    3:{"id": 3, "title": "New3 Post", "content": "naughty naughty"},
    4:{"id": 4, "title": "New4 Post", "content": "naughty naughty"},
}

# ENDPOINTS
# http - GET method(all user)
@router.get("")
def get_users():
    return users_list

# http - GET method(get particular user)
@router.get("/{user_id}")
def get_user_by_id(user_id: int):
    if user_id not in users_list:
        raise HTTPException(status_code=404, detail="User not found!!")
    return users_list.get(user_id)

# http - POST method(add user)
@router.post("/createposts", status_code=201)
def add_user(user_model: User_post):
    users_list[user_model.id] = user_model
    return user_model

# http - PUT method(update user data)
@router.put("/{user_id}")
def change_user_detail(user_id:int, userchanges: User_post):
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
