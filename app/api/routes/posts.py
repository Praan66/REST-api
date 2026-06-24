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
from app.auth.main import require_roles
from app.services.posts import (
    all_user_post,
    create_posts,
    del_users_account,
    del_users_post,
    image_url,
    users_feeds,
    users_posts,
    video_url,
)
from app.db.db import get_db

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
    return {"image_url": f"http://locahost:80/{image_path}"}


@router.get("/watch/video/{video_id}", response_model=VideoURLResponse)
async def watch_video(
    video_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_roles(["user"]))
):
    video_path = await video_url(db=db, video_id=video_id)
    return {"video_url": f"http://localhost:80/{video_path}"}


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
        message="Post update successfully",
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
