from os import path
import time
import uuid

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import users, health, posts
from app.auth import main

# CORS(Cross-Origin Resource Sharing)
from app.middleware.middleware import setup_cors
from app.core.logger import setup_logging, logger

from prometheus_fastapi_instrumentator import Instrumentator

from contextlib import asynccontextmanager
from app.db.db import create_tables
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield
setup_logging()
app = FastAPI(title="Production-Grade API", lifespan=lifespan)

# CORS
setup_cors(app)
Instrumentator().instrument(app).expose(app)

# Global Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")
    start_time = time.perf_counter()
    method = request.method
    url_path = request.url.path
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    logger.error(
        "unhandled_exception on {method} {url_path}",
        exc_info=True,
        extra={
            "extra_data": {
                "correlation_id": correlation_id,
                "http_method": method,
                "http_path": url_path,
                "latency_ms": latency_ms,
            }
        }
    )
    return JSONResponse(
        status_code=500,
        content={"message": "An Internal Server Error"}
    )


# Global HTTP logging
@app.middleware("http")
async def log_http_requests(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    start_time = time.perf_counter()
    method = request.method
    url_path = request.url.path

    response = await call_next(request)
    latency_ms = round((time.perf_counter()- start_time) * 1000, 2)
    extra_info = {
        "extra_data": {
            "correlation_id": correlation_id,
            "http_method": method,
            "http_path": url_path,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
        }
    }
    if response.status_code >= 500:
        logger.error("HTTP request failed", extra=extra_info)
    elif response.status_code >= 400:
        logger.warning("HTTP request client error", extra=extra_info)
    else:
        logger.info("HTTP request successfull", extra=extra_info)

    response.headers["X-Correlation-ID"] = correlation_id
    return response
    


@app.get("/")
async def get_root():
    return {"Welcome to": "API"}

# testing api 5xx metrics on grafana
@app.get("/error")
async def error_metrics():
    raise HTTPException(status_code=500, detail="Testing my Grafana dashboard for 5xx error metrics!!")


app.mount("/hls", StaticFiles(directory="hls"), name="hls")
app.mount("/image", StaticFiles(directory="Image"), name="image")

# endpoints(routes)
app.include_router(main.router) #auth
app.include_router(health.router)
app.include_router(users.router)
app.include_router(posts.router)
