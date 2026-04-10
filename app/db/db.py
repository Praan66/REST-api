import os

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
# from sqlalchemy.orm import sessionmaker
from .base import Base
from dotenv import load_dotenv

load_dotenv()
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DBNAME")

def create_tables():
    sync_postgres_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    sync_engine = create_engine(sync_postgres_url, echo=True, future=True)
    with sync_engine.begin() as conn:
        Base.metadata.create_all(conn)
    # Base.metadata.create_all(sync_engine)


session_postgres_url = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
print("Connecting to:", session_postgres_url)
async_engine = create_async_engine(session_postgres_url, echo=True, future=True)

AsyncSessionLocal = async_sessionmaker(bind=async_engine, class_=AsyncSession,autoflush=False, expire_on_commit=False)


import app.db.models


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db
    # db = AsyncSessionLocal()
    # try:
    #     yield db
    # finally:
    #     await db.close()




if __name__ == "__main__":
    create_tables()
    print("Tables created successfully!!")
