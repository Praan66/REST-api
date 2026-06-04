import os
from pathlib import Path
import tempfile
import aiofiles
from uuid import uuid4
from fastapi import UploadFile

UPLOAD_IMAGE = "Image"


async def upload_image(file: UploadFile) -> str:
    os.makedirs(UPLOAD_IMAGE, exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_IMAGE, filename)

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)
    await file.close()
    return f"/image/{filename}"


async def upload_video(file: UploadFile) -> str:
    suffix = Path(file.filename).suffix
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    async with aiofiles.open(temp.name, "wb") as f:
        content = await file.read()
        await f.write(content)
    await file.close()
    return temp.name
