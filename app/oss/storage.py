"""照片存储 — 支持 local（本地文件）和 wxcos（微信云存储COS）双模式。

微信云托管 COS 使用临时密钥（通过内部 API http://api.weixin.qq.com/_/cos/getauth 获取），
不使用永久密钥（COS_SECRET_ID/COS_SECRET_KEY）。
"""
import os
import uuid
import time
import json
import urllib.request
from pathlib import Path
from typing import Optional

from ..config import STORAGE_MODE, LOCAL_STORAGE_DIR, COS_BUCKET, COS_REGION


# ============================================================
# 本地文件存储
# ============================================================

def _ensure_local_dir():
    """确保本地存储目录存在。"""
    Path(LOCAL_STORAGE_DIR).mkdir(parents=True, exist_ok=True)


def _local_upload(household_id: int, image_bytes: bytes, ext: str = 'jpg') -> tuple:
    """上传到本地文件系统，返回 (storage_key, photo_id)。"""
    _ensure_local_dir()
    photo_id = uuid.uuid4().hex
    storage_key = f'photos/{household_id}/{photo_id}.{ext}'
    file_path = Path(LOCAL_STORAGE_DIR) / storage_key
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(image_bytes)
    return storage_key, photo_id


def _local_upload_preview(household_id: int, photo_id: str, preview_bytes: bytes) -> str:
    """上传预览图到本地，返回 preview_key。"""
    _ensure_local_dir()
    preview_key = f'photos/{household_id}/{photo_id}-preview.jpg'
    file_path = Path(LOCAL_STORAGE_DIR) / preview_key
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(preview_bytes)
    return preview_key


def _local_get_url(storage_key: str, expires: int = 3600) -> str:
    """本地文件返回相对路径 URL（开发模式下直接通过 FastAPI 静态服务）。"""
    return f'/static/uploads/{storage_key}'


def _local_get_bytes(storage_key: str) -> bytes:
    """从本地存储读取文件字节。"""
    file_path = Path(LOCAL_STORAGE_DIR) / storage_key
    return file_path.read_bytes()


def _local_delete(storage_key: str, preview_key: str = None):
    """删除本地文件。"""
    base = Path(LOCAL_STORAGE_DIR)
    fp = base / storage_key
    if fp.exists():
        fp.unlink()
    if preview_key:
        fp2 = base / preview_key
        if fp2.exists():
            fp2.unlink()


# ============================================================
# 微信云存储 COS — 临时密钥模式
# ============================================================

_cos_client = None
_cos_cred = None
_cos_cred_expire = 0


def _get_cos_credentials():
    """从微信云托管内部 API 获取临时 COS 密钥。"""
    global _cos_cred, _cos_cred_expire
    # 缓存密钥，提前 5 分钟刷新
    if _cos_cred and time.time() < _cos_cred_expire - 300:
        return _cos_cred

    url = 'http://api.weixin.qq.com/_/cos/getauth'
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        _cos_cred = data
        _cos_cred_expire = data.get('ExpiredTime', int(time.time()) + 3600)
        return _cos_cred
    except Exception as e:
        if _cos_cred:
            # 使用旧密钥兜底
            return _cos_cred
        raise RuntimeError(f'获取 COS 临时密钥失败: {e}')


def _get_cos_client():
    """初始化 COS 客户端（使用临时密钥）。每次检查密钥是否需要刷新。"""
    global _cos_client
    cred = _get_cos_credentials()
    # 如果密钥即将过期，重建客户端
    if _cos_client is None or time.time() >= _cos_cred_expire - 300:
        from qcloud_cos import CosConfig, CosS3Client
        config = CosConfig(
            SecretId=cred['TmpSecretId'],
            SecretKey=cred['TmpSecretKey'],
            Region=COS_REGION,
            SecurityToken=cred.get('Token', ''),
        )
        _cos_client = CosS3Client(config)
    return _cos_client


def _parse_cloud_path(file_id: str) -> str:
    """解析 cloud:// fileID，返回 COS Key。
    fileID 格式: cloud://env-id.bucket-id/path/to/file.jpg
    COS Key: path/to/file.jpg
    """
    if file_id.startswith('cloud://'):
        # 去掉 cloud:// 前缀
        rest = file_id[8:]  # len('cloud://') = 8
        # rest = env-id.bucket-id/path/to/file.jpg
        # 找到第一个 / 的位置
        slash_idx = rest.find('/')
        if slash_idx > 0:
            return rest[slash_idx + 1:]
        return rest
    return file_id


def _cos_upload(household_id: int, image_bytes: bytes, ext: str = 'jpg') -> tuple:
    """上传到微信云存储COS，返回 (storage_key, photo_id)。"""
    photo_id = uuid.uuid4().hex
    storage_key = f'photos/{household_id}/{photo_id}.{ext}'
    client = _get_cos_client()
    client.put_object(
        Bucket=COS_BUCKET,
        Body=image_bytes,
        Key=storage_key,
        ContentType=f'image/{ext}',
    )
    return storage_key, photo_id


def _cos_upload_preview(household_id: int, photo_id: str, preview_bytes: bytes) -> str:
    """上传预览图到COS，返回 preview_key。"""
    preview_key = f'photos/{household_id}/{photo_id}-preview.jpg'
    client = _get_cos_client()
    client.put_object(
        Bucket=COS_BUCKET,
        Body=preview_bytes,
        Key=preview_key,
        ContentType='image/jpeg',
    )
    return preview_key


def _cos_get_url(storage_key: str, expires: int = 3600) -> str:
    """生成COS临时访问URL（预签名URL）。"""
    client = _get_cos_client()
    url = client.get_presigned_url(
        Method='GET',
        Bucket=COS_BUCKET,
        Key=storage_key,
        Expired=expires,
    )
    return url


def _cos_get_bytes(storage_key: str) -> bytes:
    """从COS下载文件字节。"""
    client = _get_cos_client()
    response = client.get_object(Bucket=COS_BUCKET, Key=storage_key)
    return response['Body'].get_raw_stream().read()


def _cos_delete(storage_key: str, preview_key: str = None):
    """删除COS上的文件。"""
    client = _get_cos_client()
    client.delete_object(Bucket=COS_BUCKET, Key=storage_key)
    if preview_key:
        client.delete_object(Bucket=COS_BUCKET, Key=preview_key)


# ============================================================
# 统一接口
# ============================================================

def upload_photo(household_id: int, image_bytes: bytes, ext: str = 'jpg') -> tuple:
    """上传原图，返回 (storage_key, photo_id)。"""
    if STORAGE_MODE == 'wxcos':
        return _cos_upload(household_id, image_bytes, ext)
    return _local_upload(household_id, image_bytes, ext)


def upload_preview(household_id: int, photo_id: str, preview_bytes: bytes) -> str:
    """上传预览图，返回 preview_key。"""
    if STORAGE_MODE == 'wxcos':
        return _cos_upload_preview(household_id, photo_id, preview_bytes)
    return _local_upload_preview(household_id, photo_id, preview_bytes)


def get_file_url(storage_key: str, expires: int = 3600) -> str:
    """获取文件访问URL。"""
    if STORAGE_MODE == 'wxcos':
        return _cos_get_url(storage_key, expires)
    return _local_get_url(storage_key, expires)


def get_file_bytes(storage_key: str) -> bytes:
    """获取文件字节（用于识别时读取预览图）。"""
    if STORAGE_MODE == 'wxcos':
        return _cos_get_bytes(storage_key)
    return _local_get_bytes(storage_key)


def delete_photo(storage_key: str, preview_key: str = None):
    """删除照片。"""
    if STORAGE_MODE == 'wxcos':
        return _cos_delete(storage_key, preview_key)
    return _local_delete(storage_key, preview_key)


def download_by_file_id(file_id: str) -> bytes:
    """通过 cloud:// fileID 下载文件（客户端 wx.cloud.uploadFile 上传的文件）。"""
    if STORAGE_MODE == 'wxcos':
        key = _parse_cloud_path(file_id)
        return _cos_get_bytes(key)
    raise ValueError('当前模式不支持云存储 fileID')


# 兼容旧接口名
def get_signed_url(storage_key: str, expires: int = 3600) -> str:
    """兼容旧接口：生成临时访问 URL。"""
    return get_file_url(storage_key, expires)
