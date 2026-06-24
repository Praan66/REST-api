from uuid import UUID

# from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
# from ..auth.auth_model.Ulogin import User_tb 
from app.db.models.users import User

async def users_route(db: AsyncSession):
    query = select(User).order_by(User.id)
    result = await db.execute(query)
    users = result.scalars().all()
    if not users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No Users!!")
    return users

    # using raw sql
    # users = await db.execute(text("SELECT * FROM users"))
    # return users.mappings().all()
    # if not users:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No Users!!")
    # return users

async def user_by_id_route(db: AsyncSession, user_id: UUID):
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!!")
    return user

    # query = text("SELECT * FROM users WHERE id = :user_id")
    # result = await db.execute(query, {"user_id": str(user_id)})
    # user_row = result.fetchone()
    # if not user_row:
        # raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!!")
    # return user_row

async def my_profile(db: AsyncSession, user_id: UUID):
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!!")
    return user