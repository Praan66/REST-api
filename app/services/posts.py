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
from app.db.models.medias import PostMedia
from app.storage.storage_service import upload_image, upload_video
from app.db.models.enum.enum import MediaType
from app.db.models.posts import Post

"""
1. validate the input
2. create post logic
"""

HLS_DIR = "hls"
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
            detail="Video not found or invalid ID"
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
        new_media = []
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
                    file_path = media.url.split("/")[-1]
                    image_path = os.path.join("Image",file_path)
                    if os.path.exists(image_path):
                        os.remove(image_path)
                elif media.type == MediaType.video:
                    in_parts = media.url.split("/")
                    if len(in_parts) >= 3:
                        video_folder = os.path.join(HLS_DIR, in_parts[2])
                        if os.path.exists(video_folder):
                            shutil.rmtree(video_folder)
            await db.execute(delete(PostMedia).where(PostMedia.post_id == posts_id))
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
        users_post_result = await db.execute(
            select(PostMedia).where(PostMedia.post_id == del_post.id)
        )
        media_files = users_post_result.scalars().all()
        for media in media_files:
            if media.type == MediaType.image:
                img_filename = media.url.split("/")[-1]
                image_path = os.path.join("Image", img_filename)
                if os.path.exists(image_path):
                    os.remove(image_path)
            elif media.type == MediaType.video:
                vid_filename = media.url.split("/")
                if len(vid_filename) >= 3:
                    folder_id = vid_filename[2]
                    hls_folder = os.path.join("hls", folder_id)
                    if os.path.exists(hls_folder):
                        shutil.rmtree(hls_folder)
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
