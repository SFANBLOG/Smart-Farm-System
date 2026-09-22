"""影像模块：上传图片/视频，视频自动抽帧，像素内核分析，落库。"""
import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form
from app.common.result import Result
from app.common.crud import dump_one, to_page
from app.models import Media, Field
from app.services import vision, video

router = APIRouter(prefix="/media", tags=["影像"])
UPLOAD_DIR = "uploads"


@router.post("/upload", response_model=Result, summary="影像-上传")
async def upload(file: UploadFile = File(...), field_id: int | None = Form(None)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, name)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)

    is_video = ext.lower() in (".mp4", ".avi", ".mov", ".mkv")
    meta = {"size": len(content)}
    frames = []
    if is_video:
        frame_dir = os.path.join(UPLOAD_DIR, uuid.uuid4().hex)
        frames = video.extract_frames(path, frame_dir)
        meta["frames"] = len(frames)
        if frames:
            meta["pixel"] = vision.analyze_pixels(frames[0])
    else:
        meta["pixel"] = vision.analyze_remote_or_local(path)

    m = await Media.create(kind="video" if is_video else "image", path=f"/uploads/{name}",
                           filename=file.filename, field_id=field_id, meta=meta)
    return Result.ok({**dump_one(m), "media_path": path, "frames": frames})


@router.get("/page", response_model=Result, summary="影像-分页")
async def page(page: int = 1, size: int = 20):
    return Result.ok(await to_page(Media, page, size, order="-id"))


@router.get("", response_model=Result, summary="影像-列表")
async def list_media():
    rows = await Media.all().order_by("-id").limit(200)
    return Result.ok([dump_one(r) for r in rows])
