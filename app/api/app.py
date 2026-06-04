from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import users, health, posts
from app.auth import main

# CORS(Cross-Origin Resource Sharing)
from app.middleware.middleware import setup_cors

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


app.mount("/hls", StaticFiles(directory="hls"), name="hls")
app.mount("/image", StaticFiles(directory="Image"), name="image")

# endpoints(routes)
app.include_router(main.router)
app.include_router(health.router)
app.include_router(users.router)
app.include_router(posts.router)
