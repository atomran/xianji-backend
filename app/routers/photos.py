"""照片上传 + 识别路由。"""
import uuid
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from typing import List, Optional

from ..db import get_db
from ..auth.jwt import get_current_user, get_current_household
from ..models.database import User, Household, Item, Photo
from ..models.schemas import RecognizeRequest
from ..services.recognition import recognize, status as recog_status
from ..services.media import prepare as prepare_media
from ..oss.storage import upload_photo, upload_preview, get_file_url, get_file_bytes, get_signed_url, download_by_file_id
from ..config import MAX_PHOTO_SIZE, STORAGE_MODE, LOCAL_STORAGE_DIR

router = APIRouter(prefix='/v1', tags=['photos'])
TZ = ZoneInfo('Asia/Shanghai')


@router.post('/photos', status_code=201)
async def upload_photos(
    request: Request,
    household: Household = Depends(get_current_household),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传照片 → 存储 → 返回 photo_id + 预览 URL。
    支持两种方式：
    - multipart 文件上传（HTTP 开发模式，字段名 file）
    - JSON {file_id}（微信云存储，云托管模式）
    """
    raw = None
    content_type = request.headers.get('content-type', '')

    if 'multipart/form-data' in content_type:
        # multipart 上传
        form = await request.form()
        file = form.get('file')
        if file is None:
            raise HTTPException(400, '缺少文件字段 file')
        raw = await file.read()
    elif 'application/json' in content_type:
        # JSON file_id
        body = await request.json()
        file_id = body.get('file_id')
        if not file_id:
            raise HTTPException(400, '缺少 file_id')
        try:
            raw = await _download_from_cloud(file_id)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(400, f'云存储文件读取失败: {e}')
    else:
        raise HTTPException(400, '请提供文件或 file_id')

    if not raw or len(raw) > MAX_PHOTO_SIZE:
        raise HTTPException(413, '请上传 15 MB 以内的文件')

    # 判断格式
    if raw.startswith(b'\xff\xd8\xff'):
        ext = 'jpg'
    elif raw.startswith(b'\x89PNG\r\n\x1a\n'):
        ext = 'png'
    elif len(raw) > 12 and raw[4:8] == b'ftyp' and raw[8:12] in (b'heic', b'heix', b'mif1'):
        ext = 'heic'
    else:
        raise HTTPException(400, '仅支持 JPEG、PNG 或 HEIC 照片')

    # Pillow 处理：EXIF 提取 + 预览生成
    preview_bytes, metadata = prepare_media(raw)

    # 上传存储
    storage_key, photo_id = upload_photo(household.id, raw, ext)
    preview_key = upload_preview(household.id, photo_id, preview_bytes)

    metadata.update(photo_id=photo_id, oss_key=storage_key, preview_key=preview_key)
    preview_url = get_file_url(preview_key)

    # 存数据库
    row = Photo(
        id=photo_id, household_id=household.id, user_id=user.id,
        oss_key=storage_key, preview_key=preview_key, photo_metadata=metadata,
    )
    db.add(row)
    db.commit()

    return dict(
        photo_id=f'{photo_id}.{ext}',
        preview_url=preview_url,
        captured_on=metadata.get('captured_on'),
        capture_source=metadata.get('capture_source'),
        width=metadata.get('width'),
        height=metadata.get('height'),
    )


@router.post('/recognize')
def recognize_photos(
    req: RecognizeRequest,
    household: Household = Depends(get_current_household),
    db: Session = Depends(get_db),
):
    """图片识别：photo_ids → 调 DashScope → 返回待确认草稿。"""
    if not (1 <= len(req.photo_ids) <= 3):
        raise HTTPException(400, '请选择 1–3 张照片')

    # 查照片记录
    photos = []
    for pid in req.photo_ids:
        # photo_id 可能带扩展名
        clean_id = pid.split('.')[0] if '.' in pid else pid
        row = db.query(Photo).filter(Photo.id == clean_id, Photo.household_id == household.id).first()
        if not row:
            raise HTTPException(400, f'照片不存在: {pid}')
        photos.append(row)

    if not recog_status()['available']:
        raise HTTPException(503, '识别服务暂不可用，照片已保存，可先手动填写')

    # 从存储层读取预览图用于识别
    image_bytes_list = []
    for photo in photos:
        image_bytes = get_file_bytes(photo.preview_key)
        image_bytes_list.append(image_bytes)

    captured_on = photos[0].photo_metadata.get('captured_on') if isinstance(photos[0].photo_metadata, dict) else json.loads(photos[0].photo_metadata).get('captured_on')
    if not captured_on:
        captured_on = datetime.now(TZ).date().isoformat()

    result = recognize(image_bytes_list, captured_on)
    return result


@router.get('/photos/{photo_id}/preview')
def get_photo_preview(
    photo_id: str,
    household: Household = Depends(get_current_household),
    db: Session = Depends(get_db),
):
    """获取照片预览 URL。"""
    clean_id = photo_id.split('.')[0] if '.' in photo_id else photo_id
    row = db.query(Photo).filter(Photo.id == clean_id, Photo.household_id == household.id).first()
    if not row:
        raise HTTPException(404, '照片不存在')
    url = get_file_url(row.preview_key)
    return dict(url=url)


# ---- 本地存储静态文件服务（开发模式）----
if STORAGE_MODE == 'local':
    from fastapi.staticfiles import StaticFiles
    import os

    _uploads_dir = LOCAL_STORAGE_DIR
    if os.path.isdir(_uploads_dir):
        from fastapi import FastAPI
        # 通过 mount 方式提供静态文件访问
        # 注意：需要在 main.py 中 mount


async def _download_from_cloud(file_id: str) -> bytes:
    """从微信云存储下载文件（fileID 格式: cloud://env.bucket/path）。"""
    if STORAGE_MODE == 'wxcos':
        return download_by_file_id(file_id)
    raise HTTPException(400, '当前模式不支持云存储 fileID')
