from fastapi import FastAPI

from app import auth
from .routes import users
from .routes import health
from ..auth import main
# CORS(Cross-Origin Resource Sharing)
from ..middleware.middleware import setup_cors

# from contextlib import asynccontextmanager
# from ..db.db import create_tables
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     await create_tables()
#     yield

app = FastAPI(title="Production-Grade API")

# CORS
setup_cors(app)

@app.get("/")
async def get_root():
    return {"Welcome to": "API"}


# endpoints(routes)
app.include_router(main.router)
app.include_router(health.router)
app.include_router(users.router)