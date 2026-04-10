from uuid import UUID

# from sqlalchemy.orm import Session
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.models.users import User

async def get_users(db: AsyncSession):
    query = select(User).order_by(User.id)
    result = await db.execute(query)
    users = result.scalars().all()
    return users

    # using raw sql
    # users = await db.execute(text("SELECT * FROM users"))
    # return users.mappings().all()

async def get_user_by_id(user_id: UUID,db: AsyncSession):
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found!!")
    return user

    # query = text("SELECT * FROM users WHERE id = :user_id")
    # result = await db.execute(query, {"user_id": str(user_id)})
    # user_row = result.fetchone()
    # if not user_row:
    #     raise HTTPException(status_code=404, detail="User not found!!")
    # return user_row

