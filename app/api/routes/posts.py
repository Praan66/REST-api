from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enum.enum import MediaType
from app.db.models.medias import PostMedia
from app.db.models.posts import Post
from app.schemas.posts import (
    ImageURLResponse,
    PostCreatePostResponse,
    PostDetailResponse,
    TypeUrl,
    VideoURLResponse,
)
from ...auth.main import require_roles
from ...services.posts import (
    all_user_post,
    create_posts,
    del_users_account,
    del_users_post,
    image_url,
    users_feeds,
    users_posts,
    video_url,
)
from ...db.db import get_db

router = APIRouter()


@router.post("/posts", response_model=PostCreatePostResponse)
async def post_create_posts(
    files: List[UploadFile] = File(default=[]),
    content: str = Form(..., examples=[""]),
    caption: str = Form(..., examples=[""]),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles(["user"])),
):
    post = await create_posts(
        db=db,
        user_id=UUID(current_user["sub"]),
        content=content,
        caption=caption,
        files=files,
    )
    # return PostCreatePostResponse(
    #     id=post.id, content=post.content, caption=post.caption
    # )
    return PostCreatePostResponse(
        message="Post created successfully",
        post_id=str(post["post"].id),
        content=post["post"].content,
        caption=post["post"].caption,
        media=[TypeUrl(type=media.type, url=media.url) for media in post["media"]],
    )
    # return {
    #     "message": "Post created successfully",
    #     "post_id": str(post["post"].id),
    #     "content": post["post"].content,
    #     "caption": post["post"].caption,
    #     "media": [
    #         {
    #         "type": media.type,
    #         "url": media.url,
    #         }
    #         for media in post["media"]
    #     ]
    # }


@router.get("/watch/image/{image_id}", response_model=ImageURLResponse)
async def watch_image(
    image_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_roles(["user"]))
):
    image_path = await image_url(db=db, image_id=image_id)
    return {"image_url": f"http://127.0.0.1:8000/{image_path}"}


@router.get("/watch/video/{video_id}", response_model=VideoURLResponse)
async def watch_video(
    video_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_roles(["user"]))
):
    video_path = await video_url(db=db, video_id=video_id)
    return {"video_url": f"http://127.0.0.1:8000/{video_path}"}


@router.put("/edit/posts/{posts_id}", response_model=PostCreatePostResponse)
async def put_users_posts(
    posts_id: UUID,
    files: List[UploadFile] = File(default=[]),
    content: str = Form(..., examples=[""]),
    caption: str = Form(..., examples=[""]),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles(["user"])),
):
    post = await users_posts(
        db=db,
        user_id=UUID(current_user["sub"]),
        posts_id=posts_id,
        content=content,
        caption=caption,
        files=files,
    )
    return PostCreatePostResponse(
        message="Post created successfully",
        post_id=str(post["post"].id),
        content=post["post"].content,
        caption=post["post"].caption,
        media=[TypeUrl(type=media.type, url=media.url) for media in post["media"]],
    )


@router.get("/feeds", response_model=List[PostDetailResponse])
async def post_users_feeds(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles(["user"])),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
):
    calculate_offset = (page - 1) * size
    feed_posts = await users_feeds(
        db=db, user_id=current_user["sub"], limit=size, offset=calculate_offset
    )
    return feed_posts


@router.get("/allposts", response_model=List[PostDetailResponse])
async def get_all_user_post(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles(["user"])),
):
    all_post = await all_user_post(db=db, user_id=UUID(current_user["sub"]))
    return all_post


@router.delete("/admin/delete/post/{post_id}")
async def admin_delete_users_posts(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles(["admin"])),
):
    post = await del_users_post(db=db, post_id=post_id)
    return {"post": "Post deleted successfully", **post}


@router.delete("/delete/mypost/{post_id}")
async def delete_users_posts(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles(["user"])),
):
    post = await del_users_post(
        db=db, post_id=post_id, user_id=UUID(current_user["sub"])
    )
    return {"post": "Post deleted successfully", **post}


@router.delete("/admin/delete/{user_id}")
async def admin_delete_users_account(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles(["admin"])),
):
    account = await del_users_account(db=db, user_id=user_id)
    return {"account": "Account delete successfully", "detail": account}


@router.delete("/delete/account")
async def delete_users_account(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles(["user"])),
):
    account = await del_users_account(db=db, user_id=UUID(current_user["sub"]))
    return {"account": "Account delete successfully", "detail": account}


"""
Let's break down the 5 core blocks (technically called **contexts**) of an NGINX configuration file.

The easiest way to learn NGINX is to look at it as a **Russian Nesting Doll**. The settings flow from the outside (system-level) down to the inside (specific folder/URL level).

Here is the ultimate master blueprint of how they sit inside each other:

```nginx
# 1. MAIN CONTEXT (The outside shell)

events {
    # 2. EVENTS CONTEXT
}

http {
    # 3. HTTP CONTEXT
    
    server {
        # 4. SERVER CONTEXT
        
        location / {
            # 5. LOCATION CONTEXT
        }
    }
}

```

---

## 1. Main Context (The OS Controller)

* **Where it lives:** At the absolute top of the file, outside of any curly braces `{}`.
* **What it does:** It handles system-level configurations. It tells the Linux operating system how the NGINX software process itself should run.
* **Key things you put here:**
* `user nginx;` $\rightarrow$ What Linux user account runs the process (for security).
* `worker_processes auto;` $\rightarrow$ How many CPU cores NGINX is allowed to use.
* `error_log /var/log/nginx/error.log;` $\rightarrow$ Where to write system crash logs.



---

## 2. `events { }` Context (The Network Juggler)

* **Where it lives:** Inside the Main context, sitting right near the top.
* **What it does:** It handleps low-level network performance tuning. It tells NGINX how to physically deal with incoming connections from the operating system kernel.
* **Key things you put here:**
* `worker_connections 1024;` $\rightarrow$ This means each CPU core can handle 1,024 users at the exact same time. If you have 4 cores (`worker_processes 4`), your server can handle $4 \times 1024 = 4096$ concurrent users.



---

## 3. `http { }` Context (The Web Master)

* **Where it lives:** Sibling to the `events` block, wrapping around everything else.
* **What it does:** This activates the HTTP web engine. Anything inside this block applies globally to **all** websites and APIs you host on this machine.
* **Key things you put here:**
* `gzip on;` $\rightarrow$ Automatically compresses your text files so your website loads faster.
* `keepalive_timeout 65;` $\rightarrow$ How long to hold a connection open for a user before cutting them off.
* `include /etc/nginx/mime.types;` $\rightarrow$ Tells NGINX how to recognize file types (like images, videos, and CSS files).



---

## 4. `server { }` Context (The Virtual Host)

* **Where it lives:** Nested directly inside the `http` context. You can have multiple `server` blocks if you host multiple websites on one machine.
* **What it does:** It acts as a specific website domain or IP address container.
* **Key things you put here:**
* `listen 80;` $\rightarrow$ Listen for normal HTTP web traffic on port 80.
* `server_name mysite.com;` $\rightarrow$ If a user types `mysite.com`, use *this* specific block.
* `ssl_certificate ...` $\rightarrow$ Holds the security certificates for HTTPS.
server {
    listen 443 ssl;

    add_header X-Frame-Options "DENY";
    add_header X-Content-Type-Options "nosniff";
    add_header Content-Security-Policy "default-src 'self'";
}


---

## 5. `location { }` Context (The Path Router)

* **Where it lives:** Nested directly inside a `server` context. You will usually have many of these.
* **What it does:** It looks at the specific URL path after the domain name (e.g., `/images`, `/api`, `/blog`) and decides what to do with it.
* **Key things you put here:**
* `root /var/www/html;` $\rightarrow$ Look inside this folder on the hard drive to find the file the user wants.
* `index index.html;` $\rightarrow$ If they don't specify a file, serve them the main landing page.
* `proxy_pass http://my_backend_servers;` $\rightarrow$ (As you learned before!) Forward this traffic to a pool of backend servers instead of looking for a local file.



---

## Putting It All Together: A Real-World `nginx.conf`

Here is a complete, working configuration file showing exactly how they all interact:

```nginx
# --- 1. MAIN CONTEXT ---
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;

# --- 2. EVENTS CONTEXT ---
events {
    worker_connections 1024;
}

# --- 3. HTTP CONTEXT ---
http {
    include /etc/nginx/mime.types;
    gzip on;

    # --- 4. SERVER CONTEXT (Your Website) ---
    server {
        listen 80;
        server_name example.com;

        # --- 5. LOCATION CONTEXT A (Serve static HTML) ---
        location / {
            root /var/www/my_website;
            index index.html;
        }

        # --- 5. LOCATION CONTEXT B (Route API calls to app) ---
        location /api/ {
            proxy_pass http://127.0.0.1:8080;
        }
    }
}
```
Now you know the complete anatomy of NGINX!
"""
