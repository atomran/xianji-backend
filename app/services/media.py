"""图片处理 — 用 Pillow 替代 Swift fridge-photo，实现 EXIF 提取 + 预览生成。"""
from datetime import datetime
from io import BytesIO
from PIL import Image, ExifTags
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Shanghai')

# EXIF DateTimeOriginal 的 tag id
_EXIF_DATE_TAGS = {v: k for k, v in ExifTags.TAGS.items() if v in ('DateTimeOriginal', 'DateTimeDigitized')}


def _parse_exif_datetime(value, fallback_tz=TZ):
    """解析 EXIF 日期时间 '2026:09:01 10:30:00' → datetime。"""
    if not value:
        return None
    try:
        dt = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
        return dt.replace(tzinfo=fallback_tz)
    except (ValueError, TypeError):
        return None


def prepare(image_bytes, preview_max=1600):
    """
    处理上传的图片，返回 (preview_bytes, metadata)。
    替代原 Swift fridge-photo 的功能。
    """
    original = BytesIO(image_bytes)
    img = Image.open(original)

    # 尝试获取 EXIF 拍摄时间
    captured_at = None
    capture_source = 'upload_fallback'
    try:
        exif_data = img._getexif() or {}
        for tag_name in ('DateTimeOriginal', 'DateTimeDigitized'):
            tag_id = _EXIF_DATE_TAGS.get(tag_name)
            if tag_id and tag_id in exif_data:
                captured_at = _parse_exif_datetime(exif_data[tag_id])
                if captured_at:
                    capture_source = 'exif'
                    break
    except (AttributeError, KeyError, TypeError):
        pass

    # 确定图片格式
    fmt = img.format or 'JPEG'

    # 生成预览图（等比缩小到 preview_max 内）
    img.thumbnail((preview_max, preview_max), Image.LANCZOS)
    preview_buf = BytesIO()
    # 统一转 JPEG
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img.save(preview_buf, format='JPEG', quality=85)
    preview_buf.seek(0)

    width, height = img.size

    # 拍摄日期 (YYYY-MM-DD)
    captured_on = captured_at.date().isoformat() if captured_at else None

    metadata = {
        'captured_at': captured_at.isoformat() if captured_at else None,
        'captured_on': captured_on,
        'capture_source': capture_source,
        'width': width,
        'height': height,
        'format': fmt,
    }

    return preview_buf.getvalue(), metadata
