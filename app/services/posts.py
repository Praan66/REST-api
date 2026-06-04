import asyncio
import os
from pathlib import Path
import shutil
import subprocess
from uuid import UUID, uuid4

from fastapi import Depends, UploadFile, HTTPException, status, File
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from sqlalchemy.orm import joinedload, selectinload

from app.auth.main import get_current_user
from app.db.db import get_db
from app.db.models.users import User
from ..db.models.medias import PostMedia
from ..storage.storage_service import upload_image, upload_video
from ..db.models.enum.enum import MediaType
from ..db.models.posts import Post

"""
1. validate the input
2. create post logic
"""

UPLOAD_DIR = "mediaupload"
HLS_DIR = "hls"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(HLS_DIR, exist_ok=True)


def convert_to_hls(temp_video_path):
    input_path = os.path.normpath(temp_video_path)
    video_id = str(uuid4())
    output_dir = Path(HLS_DIR) / video_id
    output_dir.mkdir(parents=True, exist_ok=True)
    playlist_path = output_dir / "playlist.m3u8"
    command = [
        "ffmpeg",
        "-i",
        input_path,
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-preset",
        "fast",
        "-g",
        "48",
        "-sc_threshold",
        "0",
        "-hls_time",
        "6",
        "-hls_playlist_type",
        "vod",
        "-hls_segment_filename",
        str(output_dir / "segment_%03d.ts"),
        str(playlist_path),
    ]
    subprocess.run(command, check=True)
    return f"/hls/{video_id}/playlist.m3u8", video_id


async def create_posts(
    db: AsyncSession, user_id: UUID, content: str, caption: str, files: List[UploadFile]
):
    content = content.strip()
    caption = caption.strip()
    if not content or not caption:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both Content and Caption Required!!",
        )
    try:
        post = Post(user_id=user_id, content=content, caption=caption)
        db.add(post)
        await db.flush()
        media_list = []
        if files:
            for index, mediafile in enumerate(files):
                if not mediafile.content_type:
                    continue
                if mediafile.content_type.startswith("image"):
                    media_type = MediaType.image
                    file_url = await upload_image(mediafile)
                elif mediafile.content_type.startswith("video"):
                    media_type = MediaType.video
                    temp_video_path = await upload_video(mediafile)
                    try:
                        file_url, video_id = await asyncio.to_thread(
                            convert_to_hls, temp_video_path
                        )
                    finally:
                        if os.path.exists(temp_video_path):
                            os.remove(temp_video_path)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Only Image/Video allowed!",
                    )

                # file_url = await upload_file(mediafile)

                media = PostMedia(
                    post_id=post.id, type=media_type, url=file_url, order_index=index
                )
                media_list.append(media)
            if media_list:
                db.add_all(media_list)
        # db.add_all(media_list)
        await db.commit()
        await db.refresh(post)
        # return post
        return {"post": post, "media": media_list}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"post creation failed: {str(e)}",
        )

async def image_url(db: AsyncSession, image_id: UUID) -> str:
    query = await db.execute(select(PostMedia).where(PostMedia.id == image_id))
    media = query.scalar_one_or_none()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Image not found or invalid ID"
        )
    if media.type != MediaType.image:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The requested ID belongs to a video, not an image"
        )
    return media.url.lstrip("/")

async def video_url(db: AsyncSession, video_id: UUID) -> str:
    query = await db.execute(select(PostMedia).where(PostMedia.id == video_id))
    media = query.scalar_one_or_none()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Image not found or invalid ID"
        )
    if media.type != MediaType.video:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The requested ID belongs to a image, not an video"
        )
    return media.url.lstrip("/")

async def users_posts(
    db: AsyncSession,
    user_id: UUID,
    posts_id: UUID,
    content: str,
    caption: str,
    files: List[UploadFile],
):
    try:
        result_query = await db.execute(select(Post).where(Post.id == posts_id))
        post = result_query.scalar_one_or_none()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!!"
            )
        if post.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed"
            )
        content = content.strip()
        caption = caption.strip()
        if not content or not caption:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both Content and Caption Required!!",
            )
        post.content = content
        post.caption = caption
        if files:
            media_query = await db.execute(
                select(PostMedia).where(PostMedia.post_id == posts_id)
            )
            old_media = media_query.scalars().all()
            for media in old_media:
                if media.type == MediaType.image:
                    file_path = media.url.lstrip("/")
                    if os.path.exists(file_path):
                        os.remove(file_path)
                elif media.type == MediaType.video:
                    in_parts = media.url.split("/")
                    if len(in_parts) >= 3:
                        video_folder = os.path.join(HLS_DIR, in_parts[2])
                        if os.path.exists(video_folder):
                            shutil.rmtree(video_folder)
            await db.execute(delete(PostMedia).where(PostMedia.post_id == posts_id))
            new_media = []
            for index, mediafile in enumerate(files):
                if not mediafile.content_type:
                    continue
                if mediafile.content_type.startswith("image"):
                    media_type = MediaType.image
                    file_url = await upload_image(mediafile)
                elif mediafile.content_type.startswith("video"):
                    media_type = MediaType.video
                    temp_video_path = await upload_video(mediafile)
                    try:
                        file_url, video_id = await asyncio.to_thread(
                            convert_to_hls, temp_video_path
                        )
                    finally:
                        if os.path.exists(temp_video_path):
                            os.remove(temp_video_path)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Only Image/Video allowed!!",
                    )
                # file_url = await upload_file(mediafile)
                new_media.append(
                    PostMedia(
                        post_id=posts_id,
                        type=media_type,
                        url=file_url,
                        order_index=index,
                    )
                )
            if new_media:
                db.add_all(new_media)
        await db.commit()
        await db.refresh(post)
        media = db.execute(select)
        return {"post": post, "media": new_media}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


async def users_feeds(db: AsyncSession, user_id: UUID, limit: int, offset: int):
    try:
        query = (
            select(Post)
            .options(joinedload(Post.user), selectinload(Post.media))
            .order_by(Post.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        all_feeds = result.scalars().all()
        return all_feeds
    except Exception as e:
        await db.rollback()
        print(f"error: {e}")
        raise HTTPException(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Couldn't fetch feed"
        )


async def del_users_account(db: AsyncSession, user_id: UUID):
    try:
        del_user = await db.get(User, user_id)
        if not del_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User Not Found!!"
            )
        await db.delete(del_user)
        await db.commit()
        return {"deleted_user_id": str(del_user)}
    except HTTPException as h:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


async def all_user_post(db: AsyncSession, user_id: UUID):
    try:
        query = (
            select(Post)
            .where(Post.user_id == user_id)
            .options(selectinload(Post.user), selectinload(Post.media))
            .order_by(Post.created_at.desc())
        )
        result = await db.execute(query)
        all_posts = result.scalars().all()
        return all_posts
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise e


async def del_users_post(db: AsyncSession, post_id: UUID, user_id: UUID | None = None):
    try:
        del_post = await db.get(Post, post_id)
        if not del_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!!"
            )
        if user_id and del_post.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot delete this post!!",
            )
        deleted_post_id = str(del_post.id)
        await db.delete(del_post)
        await db.commit()
        return {"deleted_post_id": deleted_post_id}
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


"""
Your FastAPI app is already structured well.
Now you’re entering the **production engineering / DevOps phase**.

A solid next step stack for your FastAPI backend is:

* **Nginx** → Reverse proxy + load balancer + caching
* **Gunicorn + Uvicorn workers** → Production ASGI serving
* **Redis** → Caching + rate limiting
* **Prometheus + Grafana** → Monitoring
* **Loki + Promtail** → Logging
* **Docker + Docker Compose** → Deployment
* **Pytest** → Testing
* **GitHub Actions** → CI/CD

---

# 1. Production Architecture

```text
Client
   │
   ▼
Nginx
   │
   ├── Load Balancing
   ├── SSL/TLS
   ├── Rate Limiting
   ├── Caching
   ▼
Gunicorn + Uvicorn Workers
   │
   ▼
FastAPI App
   │
   ├── PostgreSQL
   ├── Redis
   ├── MinIO/S3 (media)
   └── Prometheus Metrics
```

---

# 2. Install Production Dependencies

```bash
pip install gunicorn redis slowapi prometheus-fastapi-instrumentator
```

Optional:

```bash
pip install aioredis python-json-logger
```

---

# 3. Run FastAPI in Production

DO NOT use:

```bash
uvicorn main:app --reload
```

Use:

```bash
gunicorn main:app \
  -k uvicorn.workers.UvicornWorker \
  -w 4 \
  -b 0.0.0.0:8000
```

Explanation:

* `-w 4` → 4 worker processes
* `-k uvicorn.workers.UvicornWorker` → ASGI support
* Gunicorn handles crashes/restarts

---

# 4. Add Nginx Reverse Proxy

Install nginx:

```bash
sudo apt install nginx
```

Create config:

```nginx
upstream fastapi_backend {
    server app1:8000;
    server app2:8000;
    server app3:8000;
}

server {
    listen 80;

    client_max_body_size 100M;

    location / {
        proxy_pass http://fastapi_backend;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Enable:

```bash
sudo ln -s /etc/nginx/sites-available/fastapi /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

# 5. Load Balancing

Nginx already supports this.

Example:

```nginx
upstream fastapi_backend {
    least_conn;

    server app1:8000;
    server app2:8000;
    server app3:8000;
}
```

Algorithms:

* round_robin (default)
* least_conn
* ip_hash

---

# 6. Add Rate Limiting

Install:

```bash
pip install slowapi
```

Example:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)

app.state.limiter = limiter
```

Use on routes:

```python
@app.get("/feeds")
@limiter.limit("10/minute")
async def feeds(request: Request):
    return {"ok": True}
```

Nginx-level rate limiting:

```nginx
http {
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    server {
        location / {
            limit_req zone=api_limit burst=20 nodelay;

            proxy_pass http://fastapi_backend;
        }
    }
}
```

---

# 7. Add Redis Caching

Install Redis:

```bash
sudo apt install redis
```

Install package:

```bash
pip install fastapi-cache2 redis
```

Example:

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
```

Cache endpoint:

```python
from fastapi_cache.decorator import cache

@app.get("/feeds")
@cache(expire=60)
async def get_feeds():
    return {"feeds": []}
```

---

# 8. Monitoring with Prometheus

Install:

```bash
pip install prometheus-fastapi-instrumentator
```

Add:

```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

Metrics endpoint:

```text
/metrics
```

---

# 9. Grafana Dashboard

Docker compose service:

```yaml
grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
```

Add Prometheus datasource:

```text
http://prometheus:9090
```

Useful metrics:

* request count
* latency
* error rate
* memory usage
* CPU usage

---

# 10. Centralized Logging

Use structured JSON logs.

Example:

```python
import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger()
handler = logging.StreamHandler()

formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)

logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

Nginx logs:

```nginx
access_log /var/log/nginx/access.log;
error_log /var/log/nginx/error.log;
```

Production stack:

* Loki
* Promtail
* Grafana

---

# 11. Dockerize Everything

## Dockerfile

```dockerfile
FROM python:3.12

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "main:app",
     "-k", "uvicorn.workers.UvicornWorker",
     "-w", "4",
     "-b", "0.0.0.0:8000"]
```

---

# 12. Docker Compose

```yaml
version: "3.9"

services:

  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - redis
      - postgres

  nginx:
    image: nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - app

  redis:
    image: redis

  postgres:
    image: postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: appdb

  prometheus:
    image: prom/prometheus

  grafana:
    image: grafana/grafana
```

---

# 13. Testing

Install:

```bash
pip install pytest pytest-asyncio httpx
```

Example test:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_users():

    async with AsyncClient(
        base_url="http://localhost:8000"
    ) as ac:

        response = await ac.get("/users")

    assert response.status_code == 200
```

Run:

```bash
pytest
```

---

# 14. CI/CD with GitHub Actions

`.github/workflows/deploy.yml`

```yaml
name: Deploy

on:
  push:
    branches:
      - main

jobs:

  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: pip install -r requirements.txt

      - run: pytest
```

---

# 15. Add HTTPS

Install certbot:

```bash
sudo apt install certbot python3-certbot-nginx
```

Run:

```bash
sudo certbot --nginx -d yourdomain.com
```

---

# 16. Recommended Production Stack

For your social-media-style API:

| Layer         | Recommended          |
| ------------- | -------------------- |
| API           | FastAPI              |
| ASGI          | Gunicorn + Uvicorn   |
| Reverse Proxy | Nginx                |
| DB            | PostgreSQL           |
| Cache         | Redis                |
| Queue         | Celery + Redis       |
| Monitoring    | Prometheus + Grafana |
| Logging       | Loki                 |
| CDN           | Cloudflare           |
| Media Storage | MinIO / AWS S3       |
| Deployment    | Docker               |
| CI/CD         | GitHub Actions       |

---

# 17. Important Improvements for Your Current API

## A. Move Video URLs to ENV

Instead of:

```python
"http://127.0.0.1:8000/hls/"
```

Use:

```python
settings.MEDIA_BASE_URL
```

---

## B. Add Pagination Everywhere

You already did this well in `/feeds`.

Do same for:

* `/users`
* `/allposts`

---

## C. Add Request Validation

Use:

```python
constr(min_length=1)
```

for caption/content.

---

## D. Add Global Exception Handlers

```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )
```

---

# 18. Deployment Recommendation

For learning:

* VPS (Ubuntu + Docker)
* DigitalOcean
* Hetzner

For production:

* Kubernetes
* AWS ECS
* GCP Cloud Run

---

# 19. Best Next Step

Your best order now:

1. Dockerize app
2. Add PostgreSQL + Redis
3. Add Nginx
4. Add rate limiting
5. Add caching
6. Add monitoring
7. Add logging
8. Add CI/CD
9. Deploy VPS
10. Add HTTPS

---

# 20. Most Important Advice

Your app is becoming a real backend system now.

Focus on:

* observability
* security
* scalability
* reliability

Not just routes/endpoints anymore.

That transition is what separates:

* backend beginner
  from
* production backend engineer.


so i have made rest api now what to learn and implement ngnix reverse proxy, load balance, rate limiting, caching, monitoring, logging, testing nd deploying (ngrok) all this
i have made rest api now i want to do ngnix reverse proxy, load balance, rate limiting, caching, monitoring, logging, testing nd deploying (ngrok)
"""









# teach me nginx every about it which a engineer need to know for production level api or project

"""
To take an API or project to a **production-ready level** with Nginx, you need to move past the basic "it just works" setup and configure it for **security, speed, high availability, and failure tolerance**.

This is the comprehensive, engineering-level masterclass on Nginx. We will cover the architecture, traffic routing, security hardening, performance optimization, and load balancing.

---

## 1. The Architecture: How Nginx Handles 100K+ Concurrent Requests

Traditional servers (like Apache) create a new thread or process for every single user connection. If 10,000 users visit, the server creates 10,000 threads, running out of RAM instantly.

Nginx uses an **Asynchronous, Event-Driven, Non-Blocking Architecture**.

### Master vs. Worker Processes

* **Master Process:** Runs as `root`. Its only job is to read the configuration files, bind to ports (80/443), and manage the worker processes. It *never* handles client traffic.
* **Worker Processes:** Run as a non-privileged user (like `www-data`). They utilize an **Event Loop** (using `epoll` in Linux) to handle thousands of connections simultaneously on a single thread.

### Essential Production Directives for Architecture (`nginx.conf`)

```nginx
user www-data;
worker_processes auto; # Automatically spawns 1 worker per CPU core
pid /run/nginx.pid;

events {
    worker_connections 1024; # Max simultaneous connections per worker
    use epoll;               # Optimized connection method for Linux
    multi_accept on;         # Accept all new connections at once
}

```

* **Total Max Clients Capacity** = `worker_processes` $\times$ `worker_connections`.

---

## 2. Advanced Reverse Proxy & Header Management

In production, Nginx acts as a shield for your backend API (Node.js, Go, Python, etc.). Your backend should *never* be exposed directly to the internet.

When proxying traffic, your backend application completely loses sight of the original client unless Nginx explicitly forwards that metadata.

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location /api/v1/ {
        proxy_pass http://127.0.0.1:5000; # Points to internal API port
        
        # --- Network Optimization ---
        proxy_http_version 1.1;         # Required for keepalive connections
        proxy_set_header Upgrade $http_upgrade; # Crucial for WebSockets
        proxy_set_header Connection "upgrade";

        # --- Client Metadata Forwarding ---
        proxy_set_header Host $host;                      # Pass original domain name
        proxy_set_header X-Real-IP $remote_addr;          # Pass client's actual IP
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; # IP chain through proxies
        proxy_set_header X-Forwarded-Proto $scheme;       # Pass http or https

        # --- Production Timeouts ---
        proxy_connect_timeout 60s; # Time to establish connection to backend
        proxy_send_timeout 60s;    # Time to transmit request to backend
        proxy_read_timeout 60s;    # Time to wait for backend response (Prevents hanging)
    }
}

```

---

## 3. Production Security & SSL/TLS Hardening

A production API cannot run on HTTP (Port 80). It must run on HTTPS (Port 443), use modern encryption protocols, and block malicious traffic.

### SSL Termination Config with Strict Security

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$host$request_uri; # Force HTTP to HTTPS global redirect
}

server {
    listen 443 ssl http2; # http2 provides massive multiplexing speed boosts
    server_name api.yourdomain.com;

    # SSL Certificates
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Protocols & Ciphers (Disables insecure TLS 1.0, 1.1)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';

    # SSL Session Optimization (Reduces TLS handshake latency for returning users)
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # --- Security Headers (Crucial for OWASP compliance) ---
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    # Strict Transport Security (HSTS) - Forces browsers to use HTTPS for 1 year
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    location / {
        proxy_pass http://127.0.0.1:5000;
    }
}

```

---

## 4. High Availability & Load Balancing

When your application scales, a single instance of your backend API will fail under pressure. Nginx can split traffic among multiple server instances.

```nginx
# Define the pool of backend servers
upstream api_servers {
    # Load Balancing Algorithm (Default is Round Robin)
    # Options: least_conn (send to least busy), ip_hash (sticky sessions)
    least_conn; 

    server 10.0.0.10:5000 max_fails=3 fail_timeout=10s; # Server A
    server 10.0.0.11:5000 max_fails=3 fail_timeout=10s; # Server B
    server 10.0.0.12:5000 backup;                       # Only used if A and B die
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://api_servers; # Routes traffic to the upstream pool
    }
}

```

* `max_fails` and `fail_timeout` act as a **passive health check**. If Server A throws 3 errors within 10 seconds, Nginx marks it as dead and stops sending traffic to it for 10 seconds.

---

## 5. Performance Optimization: Caching & Compression

### Gzip Compression

Text payloads (JSON, HTML, CSS, JS) should be compressed over the network to save bandwidth and drastically reduce response latency.

```nginx
# Put this inside the http block of nginx.conf
gzip on;
gzip_comp_level 5; # 1 (Fastest, low compression) to 9 (Slowest, high compression). 5 is optimal.
gzip_min_length 256; # Don't waste CPU compressing tiny files
gzip_proxied any;
gzip_types
    application/json
    application/javascript
    text/css
    text/xml
    text/plain;

```

### Static Asset Caching

If your project serves frontend files (React/Vue builds, images), do not let them touch your backend server. Nginx should handle them out of RAM/Disk cache.

```nginx
location /static/ {
    root /var/www/my_project/dist;
    expires 30d; # Tell browser to keep cache for 30 days
    add_header Cache-Control "public, no-transform";
    access_log off; # Turn off logging to save Disk I/O operations
}

```

---

## 6. Rate Limiting & DDOS Protection

To make an API production-ready, you must prevent bad actors or broken scripts from overwhelming your database with infinite loops of requests.

Nginx uses the **Leaky Bucket Algorithm** for rate limiting.

```nginx
# Define the rate limit zone in the HTTP block
# allocates 10MB of RAM (holds ~160,000 IP addresses) allowing 10 requests per second per IP
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

server {
    listen 443 ssl;
    
    location /api/v1/login {
        # Apply the rate limit here
        # burst=5 means if a user sends 15 requests at once, 5 are put in a queue to process later
        # nodelay means don't slow down the burst requests, process immediately, but reject the 16th request with a 429
        limit_req zone=api_limit burst=5 nodelay;
        limit_req_status 429; # Standard HTTP status code for Too Many Requests

        proxy_pass http://127.0.0.1:5000;
    }
}

```

---

## 7. Zero-Downtime Operations (The Production Workflow)

In production, you cannot afford to take down your web server to update code or change a configuration setting.

### The Essential CLI Commands

1. **Syntax Check:** Every time you edit an Nginx file, run this *before* breaking production:
```bash
sudo nginx -t

```


If it returns `syntax is ok` and `test is successful`, you are safe.
2. **Zero-Downtime Reload:** This tells the Master process to spawn new workers with the new config, gracefully let old workers finish their active client connections, and kill the old workers without dropping a single packet of traffic.

```bash
    sudo systemctl reload nginx
    # OR
    sudo nginx -s reload
    ```

### How to read logs during an outage
When your app returns a `502 Bad Gateway` or `504 Gateway Timeout`, your backend application is down or timing out. Use the Nginx logs to debug:
*   `tail -f /var/log/nginx/access.log` (Shows live traffic incoming)
*   `tail -f /var/log/nginx/error.log` (Shows exact connection errors between Nginx and your app)

---

### Implementation Road Map
To build this, do not try to configure everything at once. Build it sequentially:
1.  **Milestone 1:** Get Nginx to successfully `proxy_pass` to your local app port on HTTP (Port 80).
2.  **Milestone 2:** Secure it with an SSL certificate (using Let's Encrypt / Certbot) to open Port 443.
3.  **Milestone 3:** Add Security Headers and turn on Gzip compression.
4.  **Milestone 4:** Introduce Rate Limiting on your highly vulnerable API endpoints (like `/login` or `/register`).

```
"""








"""
Good — now I’ll turn that long checklist into a **proper learning path like a mid-level backend engineer roadmap**, not just topics.

You don’t need to “learn everything deeply at once”. You need to learn in **layers**, and build real systems while learning.

---

# 🎯 First: What “Mid-Level Backend Dev” actually means

A mid-level backend engineer can:

### 1. Deploy apps to production

* Linux server
* reverse proxy (NGINX)
* HTTPS setup

### 2. Handle real traffic issues

* 502/504 errors
* slow APIs
* memory leaks
* request spikes

### 3. Design production architecture

* app + DB + cache + queue
* scaling basics

### 4. Debug using logs

* server logs
* app logs
* NGINX logs

### 5. Make systems reliable

* retries
* timeouts
* rate limits
* backups

---

# 🧠 Your Learning Path (in correct order)

I’ll teach you this like a course roadmap.

---

# 🟢 PHASE 1 — NGINX FUNDAMENTALS (MOST IMPORTANT)

You start here.

## 1. What is Reverse Proxy (YOU MUST MASTER THIS FIRST)

Think:

> NGINX is a “traffic controller”

Flow:

```text
User → NGINX → FastAPI
```

You must understand:

* why we don’t expose FastAPI directly
* what “proxy_pass” means
* request forwarding

---

## 2. Basic NGINX config structure

Learn ONLY this first:

* server
* location
* listen
* server_name
* proxy_pass

👉 Goal: You can write this from memory:

```nginx
server {
    listen 80;

    server_name mysite.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

---

## 3. Run your FastAPI behind NGINX

This is your FIRST milestone.

You should be able to:

* run FastAPI on port 8000
* run NGINX on port 80
* connect them

✔ If you can do this → you are already ahead of beginners.

---

# 🟡 PHASE 2 — REAL PRODUCTION ESSENTIALS

Now you upgrade your system.

---

## 4. HTTPS (VERY IMPORTANT)

Learn:

* SSL certificate
* port 443
* redirect HTTP → HTTPS

👉 Use Let’s Encrypt

You should understand:

* why HTTPS is mandatory
* what TLS does

---

## 5. Headers (VERY IMPORTANT)

You MUST learn this:

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

Why?
Because otherwise:

* wrong user IP
* broken authentication
* broken logs

---

## 6. Timeouts

You must understand:

* slow APIs
* request hanging
* 504 gateway timeout

Learn:

* proxy_read_timeout
* proxy_connect_timeout

---

## 7. Upload limits (important for your project)

Since you handle images/videos:

```nginx
client_max_body_size 500M;
```

This is VERY real-world important.

---

# 🟠 PHASE 3 — SCALING BASICS

Now you start thinking like a backend engineer.

---

## 8. Load Balancing

Instead of 1 backend:

```text
NGINX → multiple FastAPI servers
```

Learn:

* round robin
* multiple upstream servers

---

## 9. Static + Media files

You already store files → now serve them properly:

* images
* videos
* downloads

NGINX is faster than FastAPI for this.

---

## 10. Caching (BIG performance upgrade)

Learn:

* browser caching
* proxy caching

Why?
Because:

> 1 request served from cache = no backend load

---

# 🔴 PHASE 4 — PRODUCTION ENGINEERING SKILLS

Now you become “mid-level”.

---

## 11. Linux (NON-NEGOTIABLE)

You must know:

* systemctl
* journalctl
* logs
* permissions
* processes

Because production runs on Linux.

---

## 12. Logging

You must understand:

* access logs
* error logs

And answer:

* “why is API slow?”
* “why 502 happened?”

---

## 13. Debugging real issues

You must be able to fix:

* 502 Bad Gateway
* 504 Timeout
* infinite redirects
* upload failures

---

# 🟣 PHASE 5 — PRODUCTION ARCHITECTURE

Now you think like system designer.

---

## 14. Docker (VERY IMPORTANT)

Learn:

* containerize FastAPI
* containerize NGINX
* containerize DB

Architecture:

```text
NGINX
  ↓
FastAPI
  ↓
PostgreSQL
```

---

## 15. Redis + background tasks

For your project:

* video processing
* image processing
* emails

Use:

* Redis
* Celery

---

## 16. Database production skills

Learn:

* indexing
* migrations
* query optimization

---

# 🟤 PHASE 6 — MID-LEVEL + ABOVE

Only after everything above.

---

## 17. CI/CD (auto deployment)

* push → auto deploy server
* GitHub Actions

---

## 18. Monitoring

Learn:

* metrics
* dashboards

Tools:

* Prometheus
* Grafana

---

## 19. Kubernetes (optional later)

Only after Docker is strong.

---

# 📊 REALISTIC LEARNING TIME

If you are consistent:

### Beginner → Mid-level backend engineer:

👉 3 to 6 months (hands-on)

Not by watching videos — by building + deploying.

---

# 🧠 SIMPLE RULE TO FOLLOW

If you want to become production-ready:

> “Every topic must end with deployment on a real server”

Not theory.

---

# 🚀 YOUR BEST NEXT STEP (IMPORTANT)

Since you already built FastAPI + DB + file uploads:

👉 Next thing you should do is:

### “Deploy your current project using:”

* NGINX
* Gunicorn
* Linux VPS

---

If you want, I can teach you step-by-step like a real course:

### Next lesson options:

1. 🧱 “What exactly is reverse proxy (deep visual explanation)”
2. 🖥️ “Deploy your FastAPI project on a real VPS step-by-step”
3. 🔐 “NGINX + HTTPS setup (production level)”
4. 📦 “Dockerize your FastAPI project properly”

Just tell me which one you want first.
teach me all this topics one by one how much i need to learn as per mid level dev or eng
"""
