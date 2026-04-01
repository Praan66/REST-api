from fastapi import FastAPI
from app.api.routes import users
from app.api.routes import health


app = FastAPI(title="Production-Grade API")
@app.get("/")
async def get_root():
    return {"Welcome to": "API"}

# endpoints(routes)
app.include_router(health.router)
app.include_router(users.router)