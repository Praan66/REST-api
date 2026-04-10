from fastapi import FastAPI
from .routes import users
from .routes import health
# CORS(Cross-Origin Resource Sharing)
from ..middleware.middleware import setup_cors

app = FastAPI(title="Production-Grade API")

# CORS
setup_cors(app)

@app.get("/")
async def get_root():
    return {"Welcome to": "API"}


# endpoints(routes)
app.include_router(health.router)
app.include_router(users.router)