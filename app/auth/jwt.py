"""微信登录 + JWT 认证 — 支持开发模式 + X-WX-OPENID header。"""
import time
import json
import httpx
import secrets as secrets_mod
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import jwt
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from ..config import JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_HOURS, REFRESH_TOKEN_EXPIRE_DAYS, WX_APPID, WX_SECRET, DEV_MODE
from ..models.database import User, Household, HouseholdMember
from ..db import get_db


def _wx_code2session(code: str) -> dict:
    """调用微信 code2session 接口，获取 openid + session_key。"""
    url = 'https://api.weixin.qq.com/sns/jscode2session'
    params = {
        'appid': WX_APPID,
        'secret': WX_SECRET,
        'js_code': code,
        'grant_type': 'authorization_code',
    }
    resp = httpx.get(url, params=params, timeout=10)
    data = resp.json()
    if 'errcode' in data and data['errcode'] != 0:
        raise HTTPException(400, f"微信登录失败: {data.get('errmsg', '未知错误')}")
    return data


def _create_tokens(user_id: int) -> dict:
    """签发 JWT access_token + refresh_token。"""
    now = datetime.now(timezone.utc)
    access_payload = {
        'sub': str(user_id),
        'type': 'access',
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)).timestamp()),
    }
    refresh_payload = {
        'sub': str(user_id),
        'type': 'refresh',
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()),
    }
    access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer',
        'expires_in': ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    }


def _find_or_create_user(openid: str, nickname: str, avatar_url: str, db: Session) -> User:
    """查找或创建用户 + 默认家庭。"""
    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        user = User(openid=openid, nickname=nickname, avatar_url=avatar_url)
        db.add(user)
        db.commit()
        db.refresh(user)

        # 自动创建默认家庭
        invite_code = secrets_mod.token_hex(4).upper()
        household = Household(name='我的冰箱', invite_code=invite_code, created_by=user.id)
        db.add(household)
        db.commit()
        db.refresh(household)
        member = HouseholdMember(household_id=household.id, user_id=user.id, role='owner')
        db.add(member)
        db.commit()
    else:
        if nickname:
            user.nickname = nickname
        if avatar_url:
            user.avatar_url = avatar_url
        db.commit()
    return user


def wx_login(code: str, nickname: str, avatar_url: str, db: Session) -> dict:
    """微信登录全流程：code → openid → 查/建用户 → JWT。"""
    wx_data = _wx_code2session(code)
    openid = wx_data['openid']
    unionid = wx_data.get('unionid')

    user = _find_or_create_user(openid, nickname, avatar_url, db)
    if unionid and not user.unionid:
        user.unionid = unionid
        db.commit()
    return _create_tokens(user.id)


def dev_login(openid: str, nickname: str, avatar_url: str, db: Session) -> dict:
    """开发模式登录：跳过微信code2session，直接用指定 openid。"""
    if not DEV_MODE:
        raise HTTPException(403, '开发模式未启用，请设置 DEV_MODE=true')
    user = _find_or_create_user(openid, nickname, avatar_url, db)
    return _create_tokens(user.id)


def wx_openid_login(openid: str, nickname: str, avatar_url: str, db: Session) -> dict:
    """云托管登录：通过 X-WX-OPENID header 获取 openid（callContainer 自动注入）。"""
    user = _find_or_create_user(openid, nickname, avatar_url, db)
    return _create_tokens(user.id)


def refresh_access_token(refresh_token: str, db: Session) -> dict:
    """刷新 access_token。"""
    try:
        payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get('type') != 'refresh':
            raise HTTPException(401, '无效的刷新令牌')
        user_id = int(payload['sub'])
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(401, '用户不存在')
        return _create_tokens(user.id)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, '刷新令牌已过期，请重新登录')
    except jwt.InvalidTokenError:
        raise HTTPException(401, '无效的刷新令牌')


def get_current_user(
    authorization: str = Header(None),
    wx_openid: str = Header(None, alias='X-WX-OPENID'),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI 依赖：从 Authorization header（JWT）或 X-WX-OPENID header 获取当前用户。"""
    # 优先尝试 JWT
    if authorization and authorization.startswith('Bearer '):
        token = authorization.split(' ', 1)[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            if payload.get('type') != 'access':
                raise HTTPException(401, '无效的访问令牌')
            user_id = int(payload['sub'])
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(401, '用户不存在')
            return user
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, '令牌已过期，请重新登录')
        except jwt.InvalidTokenError:
            raise HTTPException(401, '无效的访问令牌')

    # 尝试 X-WX-OPENID header（微信云托管自动注入）
    if wx_openid:
        user = db.query(User).filter(User.openid == wx_openid).first()
        if user:
            return user
        # openid 对应的用户不存在，需要先登录
        raise HTTPException(401, '用户未注册，请先登录')

    raise HTTPException(401, '请先登录')


def get_current_household(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Household:
    """FastAPI 依赖：获取当前用户的默认家庭。"""
    member = db.query(HouseholdMember).filter(HouseholdMember.user_id == user.id).first()
    if not member:
        raise HTTPException(403, '尚未加入任何家庭')
    return db.query(Household).filter(Household.id == member.household_id).first()


def verify_device_token(authorization: str = Header(None), db: Session = Depends(get_db)):
    """设备端 Bearer token 认证。"""
    from ..models.database import Device
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401, '设备未认证')
    token = authorization.split(' ', 1)[1]
    device = db.query(Device).filter(Device.device_token == token).first()
    if not device:
        raise HTTPException(401, '设备令牌无效')
    return device
