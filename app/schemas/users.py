from pydantic import BaseModel, EmailStr, field_serializer
from uuid import UUID
from datetime import datetime
from zoneinfo import ZoneInfo

# Request & Response
class GetUserResponse(BaseModel):
    id: UUID
    username: str
    email_id: EmailStr
    created_at: datetime
    model_config = {"from_attributes": True}
    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime):
        ist = dt.astimezone(ZoneInfo("Asia/Kolkata"))
        return ist.strftime("%B %d, %Y %I:%M %p")
        # %B(month), %d(date), %Y(year), %I(Hour):%M(minute) %p(AM/PM)

class ProfileResponse(BaseModel):
    message: str
    detail: GetUserResponse



"""
Smart move — this is exactly how you should think if you want to build fast without repeating yourself.

I’ll give you a **clean, structured prompt** that captures everything we designed so you can resume anytime without re-explaining.

---

# 🚀 MASTER CONTEXT PROMPT (save this)

You can paste this at the start of your next conversation:

---

## 🧠 Prompt

```text
I am building a social media backend using FastAPI + SQLAlchemy + PostgreSQL.

Here is my current system design:

1. USER SYSTEM:
- Users table with UUID primary key
- Separate credentials table (one-to-one relationship)

2. POSTS SYSTEM:
- Post table:
  - id (UUID, primary key)
  - user_id (FK to users.id)
  - text (NOT NULL, text is mandatory)
  - created_at
- One user can have many posts

3. MEDIA SYSTEM:
- PostMedia table:
  - id (UUID, primary key)
  - post_id (FK to posts.id, cascade delete)
  - type (ENUM: image, video)
  - url (stored from S3)
  - order_index (to maintain order of media)
- One post can have multiple media (images/videos mixed)
- Media must always be ordered using order_index

4. RELATIONSHIPS:
- User.posts ↔ Post.user (one-to-many)
- Post.media ↔ PostMedia.post (one-to-many)
- Using back_populates correctly
- Post.media includes:
  - cascade="all, delete-orphan"
  - order_by="PostMedia.order_index"

5. VALIDATION RULES:
- Text is mandatory for every post
- Media is optional
- Allowed media types: image and video only
- Media type is determined by backend using file.content_type (NOT frontend)

6. STORAGE:
- Using AWS S3 for storing images/videos
- Files are uploaded via backend using boto3
- Only file URL is stored in DB
- Unique filenames generated using UUID
- Bucket is public (for now)

7. ARCHITECTURE:
- Clean separation:
  - routes → API layer
  - services → business logic
  - models → DB
- storage_service handles S3 uploads
- post_service handles post creation logic

8. POST CREATION FLOW:
- Validate text
- Create post
- Upload files to S3
- Detect media type (image/video)
- Create PostMedia rows with order_index
- Return structured response

9. FEED SYSTEM:
- GET /posts
- Ordered by created_at DESC
- Uses selectinload(Post.media, Post.user) to avoid N+1 problem
- Supports pagination (limit, offset)

10. CURRENT STATUS:
- DB schema is complete
- S3 integration is done
- Post creation API is implemented
- Feed API is implemented

I want to continue building the system further in a scalable and production-ready way.

Continue helping me from here without re-explaining basics.
```

---

# 🧠 Why this works

This prompt gives:

✔ Your architecture
✔ Your DB design
✔ Your rules
✔ Your current progress

So next time you can directly say:

```text
Continue from here → build likes system
```

or

```text
Optimize feed for performance
```

---

# 🔥 Pro tip (very important)

Save versions like:

```text
v1 → schema done  
v2 → post + media  
v3 → feed  
v4 → likes  
```

So you can evolve your system cleanly.

---

# 🚀 What you can ask next (tomorrow)

You can directly jump into:

* “Design likes system”
* “Add comments with nesting”
* “Implement follow system”
* “Convert feed to cursor pagination”
* “Add Redis caching”

---

# ✅ Final note

You’ve actually built a **solid backend foundation** — not beginner-level anymore.

Next steps will feel more like **system design** than coding.

---

When you come back, just paste that prompt and say:

👉 *“continue”*
or
👉 *“build next feature: likes”*

And we’ll move forward without restarting 👍

"""


"""
Perfect — now you’re moving into the *real backend structure*: separating **routes (API layer)** and **services (business logic)**. This is exactly how production systems are built.

We’ll design it clean, step-by-step, like a real social app backend.

---

# 🧠 1. Architecture idea (important)

We split responsibilities:

```text id="arch1"
ROUTES   → handle HTTP (request/response)
SERVICES → business logic (create post, upload media)
MODELS   → database tables
```

---

# 🏗️ Why this matters

If you don’t separate:

❌ routes become messy
❌ logic gets duplicated
❌ hard to maintain

If you do separate:

✔ clean code
✔ scalable
✔ easy to test
✔ easy to upgrade storage later (S3, etc.)

---

# 📦 2. Folder structure (final design)

```text id="arch2"
app/
 ├── models/
 ├── routes/
 │    └── post_routes.py
 ├── services/
 │    └── post_service.py
 │    └── storage_service.py
 ├── db/
 ├── enums/
```

---

# ⚙️ 3. Service Layer (CORE LOGIC)

## 👉 `services/storage_service.py`

This handles file uploads.

```python id="svc1"
import os
from uuid import uuid4
from fastapi import UploadFile

UPLOAD_DIR = "uploads/"

async def upload_file(file: UploadFile):
    ext = file.filename.split(".")[-1]
    filename = f"{uuid4()}.{ext}"

    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        content = await file.read()
        f.write(content)

    return f"/uploads/{filename}"
```

---

# 🧠 4. Post Service (business logic)

## 👉 `services/post_service.py`

This is the HEART of your system.

```python id="svc2"
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
from typing import List

from app.models.post import Post
from app.models.post_media import PostMedia, MediaType
from app.services.storage_service import upload_file
```

---

## 🔥 Create Post logic

```python id="svc3"
async def create_post(
    db: Session,
    user_id,
    text: str,
    files: List[UploadFile]
):
    # 1. Validate text
    if not text or not text.strip():
        raise HTTPException(400, "Text is required")

    # 2. Create post
    post = Post(user_id=user_id, text=text)
    db.add(post)
    db.flush()  # get post.id

    media_objects = []

    # 3. Handle files
    for i, file in enumerate(files):

        if file.content_type.startswith("image"):
            media_type = MediaType.image

        elif file.content_type.startswith("video"):
            media_type = MediaType.video

        else:
            raise HTTPException(400, "Only image/video allowed")

        file_url = await upload_file(file)

        media_objects.append(
            PostMedia(
                post_id=post.id,
                type=media_type,
                url=file_url,
                order_index=i
            )
        )

    db.add_all(media_objects)
    db.commit()
    db.refresh(post)

    return post
```

---

# 🌐 5. Route Layer (API)

## 👉 `routes/post_routes.py`

This is ONLY HTTP handling.

```python id="route1"
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.services.post_service import create_post

router = APIRouter()
```

---

## 🔥 Create Post Endpoint

```python id="route2"
@router.post("/posts")
async def create_post_route(
    text: str = Form(...),
    files: List[UploadFile] = File([]),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):

    post = await create_post(
        db=db,
        user_id=current_user.id,
        text=text,
        files=files
    )

    return {
        "id": post.id,
        "text": post.text
    }
```

---

# 🧠 6. Why this design is powerful

## Route layer:

* handles request
* handles auth
* sends response

## Service layer:

* handles logic
* handles DB operations
* handles file upload

---

# ⚡ 7. Add GET Post service

## service

```python id="svc4"
def get_post(db: Session, post_id):
    return db.query(Post).filter(Post.id == post_id).first()
```

---

## route

```python id="route3"
@router.get("/posts/{post_id}")
def get_post_route(post_id: str, db: Session = Depends(get_db)):

    post = get_post(db, post_id)

    return {
        "id": post.id,
        "text": post.text,
        "media": [
            {
                "type": m.type,
                "url": m.url
            }
            for m in post.media
        ]
    }
```

---

# 🚀 8. What you have now

You now built:

✔ Clean architecture
✔ Service layer separation
✔ File handling abstraction
✔ Post creation flow
✔ Media handling

This is already close to how systems like Instagram backend are structured.

---

# 🧠 9. Mental model (VERY IMPORTANT)

```text id="model"
Route → Service → DB → Service → Route → Response
```

---

# 🔥 10. What to do next (IMPORTANT)

Now you should NOT add more endpoints randomly.

Next steps:

### Phase 1 (next)

👉 GET /posts feed (with selectinload + pagination)

---

### Phase 2

👉 likes system ❤️
👉 comments 💬

---

### Phase 3

👉 follow system 👤

---

# ✅ Final conclusion

You are now at a **real backend architecture stage**.

What you just built is:

✔ scalable structure
✔ production pattern
✔ clean separation of logic

---

If you want next, I can guide you step-by-step:

👉 “How to build Instagram-style feed API (pagination + performance + joins)”

"""

"""
Perfect — now we continue exactly from where you are.

You already have:
✔ Post creation
✔ Media upload
✔ Basic structure

Now we build the **real social media core: FEED API (Instagram/Twitter style)**

---

# 🧠 STEP 1: What is a “feed” actually?

A feed is NOT a new concept.

It is simply:

```text id="f1"
A list of posts sorted + optimized for fast reading
```

Like in Instagram:

👉 You are NOT creating new data
👉 You are only **reading posts efficiently**

---

# ⚡ STEP 2: Basic Feed API (first version)

## 👉 Route

```python id="r1"
@router.get("/posts")
def get_posts(db: Session = Depends(get_db)):
```

---

## 👉 Simple query

```python id="q1"
posts = (
    db.query(Post)
    .order_by(Post.created_at.desc())
    .all()
)
```

👉 This means:

* newest posts first
* simplest feed possible

---

# 🚨 STEP 3: Problem with simple version (important)

If you do this:

```python id="p1"
for post in posts:
    post.media
    post.user
```

👉 You may get:

```text id="n1"
1 query for posts
+ N queries for media
+ N queries for user
= SLOW ❌
```

This is called:

👉 **N+1 problem**

---

# ⚡ STEP 4: FIX IT (PROPER FEED)

We optimize using:

```python id="s1"
from sqlalchemy.orm import selectinload
```

---

## 🔥 Optimized query

```python id="q2"
posts = (
    db.query(Post)
    .options(
        selectinload(Post.media),
        selectinload(Post.user)
    )
    .order_by(Post.created_at.desc())
    .all()
)
```

---

# 🧠 WHY THIS IS IMPORTANT

Instead of:

```text id="bad"
1 query → posts
100 queries → media
100 queries → user
```

We get:

```text id="good"
1 query → posts
1 query → media
1 query → user
```

✔ FAST
✔ SCALABLE
✔ PRODUCTION READY

---

# 📦 STEP 5: Return clean response

Never return raw DB objects.

```python id="r2"
return [
    {
        "id": post.id,
        "text": post.text,
        "user": {
            "id": post.user.id,
            "username": post.user.username
        },
        "media": [
            {
                "type": m.type,
                "url": m.url,
                "order": m.order_index
            }
            for m in post.media
        ],
        "created_at": post.created_at
    }
    for post in posts
]
```

---

# ⚡ STEP 6: Add Pagination (VERY IMPORTANT)

Without pagination, your app will break when data grows.

## Add query params:

```python id="p2"
@router.get("/posts")
def get_posts(limit: int = 10, offset: int = 0, db: Session = Depends(get_db)):
```

---

## Apply pagination:

```python id="q3"
posts = (
    db.query(Post)
    .options(
        selectinload(Post.media),
        selectinload(Post.user)
    )
    .order_by(Post.created_at.desc())
    .limit(limit)
    .offset(offset)
    .all()
)
```

---

# 🧠 STEP 7: How feed works in real apps

In systems like Twitter:

Feed is:

```text id="f2"
1. Fetch posts
2. Sort them
3. Paginate
4. Attach user + media
5. Return JSON
```

---

# 🔥 STEP 8: What you now have

You now built:

✔ Post system
✔ Media system
✔ Upload system
✔ Feed system
✔ Performance optimization (selectinload)
✔ Pagination

---

# 🚀 STEP 9: What comes next (VERY IMPORTANT)

Now you move to real social features:

## Phase 2:

### ❤️ Likes system

* post likes table
* like/unlike API

### 💬 Comments system

* nested comments

---

## Phase 3:

### 👤 Follow system

* user feed personalization

---

## Phase 4:

### ⚡ Feed ranking

* trending posts
* algorithm-based ordering

---

# 🧠 FINAL BIG IDEA

You are not building “posts API”

You are building:

```text id="core"
A feed system (read-heavy + optimized backend)
```

---

# ✅ If you’re ready next step

I suggest we go to:

👉 **Likes system (this is where backend relationships become real)**

OR

👉 **Comments system (slightly harder, very important for social apps)**

Just tell me 👍

"""

"""
Good move — switching to S3 is exactly what you should do before your app grows. Let’s keep it **simple but production-correct**, so you understand what’s happening.

---

# 🧠 Big idea first

Right now:

```text
API → save file locally → store path
```

With S3:

```text
API → upload to S3 → store URL in DB
```

👉 Your DB **never stores files**, only URLs.

---

# ⚙️ Step 1: Install dependency

```bash
pip install boto3
```

---

# 🔐 Step 2: S3 configuration

You need:

* access key
* secret key
* bucket name
* region

Put in `.env`:

```text
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=ap-south-1
AWS_BUCKET_NAME=your-bucket
```

---

# 📦 Step 3: Storage service (S3 version)

## 👉 `services/storage_service.py`

```python
import boto3
from uuid import uuid4
from fastapi import UploadFile
import os

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)
```

---

## 🔥 Upload function

```python
async def upload_file(file: UploadFile):

    ext = file.filename.split(".")[-1]
    filename = f"{uuid4()}.{ext}"

    s3.upload_fileobj(
        file.file,
        BUCKET_NAME,
        filename,
        ExtraArgs={
            "ContentType": file.content_type
        }
    )

    file_url = f"https://{BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{filename}"

    return file_url
```

---

# 🧠 What this does

```text
1. Generates unique filename
2. Uploads file to S3 bucket
3. Returns public URL
```

---

# ⚡ Step 4: Use in your Post Service

You already have:

```python
file_url = await upload_file(file)
```

👉 Now it stores S3 URL instead of local path

---

# 🔐 Step 5: Make files public (IMPORTANT)

In S3 bucket:

* Go to **Permissions**
* Disable “Block public access” (or configure properly)
* Add bucket policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicRead",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::your-bucket/*"
    }
  ]
}
```

---

# 🧠 Alternative (better for production later)

Instead of public bucket:

👉 Use **pre-signed URLs**

But for now:
✔ public URL is fine

---

# ⚠️ Important validations (dont skip)

Before upload:

```python
if not file.content_type.startswith(("image", "video")):
    raise HTTPException(400, "Invalid file type")
```

---

# 🚀 Step 6: Folder structure in S3 (optional but clean)

Instead of dumping all files:

```python
filename = f"posts/{uuid4()}.{ext}"
```

Or:

```text
posts/images/...
posts/videos/...
```

---

# 🧠 Final flow (IMPORTANT)

```text
User uploads file
→ FastAPI receives file
→ upload_file() sends to S3
→ S3 returns URL
→ URL stored in PostMedia table
→ frontend uses URL
```

---

# 🔥 What you achieved

✔ Scalable file storage
✔ No server disk usage
✔ CDN-ready URLs
✔ Production-ready architecture

This is exactly how apps like Instagram handle media.

---

# 🚀 What I recommend next

Now that you have S3:

👉 Add **file size limits + compression**
👉 OR build **likes system (next core feature)**

---

If you want, I can show you:

👉 how to generate **pre-signed upload URLs (frontend uploads directly to S3 — very powerful)**

"""
