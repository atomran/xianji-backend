"""认证相关路由。"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from ..db import get_db
from ..auth.jwt import wx_login, dev_login, wx_openid_login, refresh_access_token, get_current_user
from ..config import DEV_MODE
from ..models.database import User
from ..models.schemas import WxLoginRequest, TokenResponse, RefreshRequest, UserProfile

router = APIRouter(prefix='/v1/auth', tags=['auth'])


@router.post('/wx-login', response_model=TokenResponse)
def login(req: WxLoginRequest, db: Session = Depends(get_db)):
    """微信登录：code → JWT。"""
    tokens = wx_login(req.code, req.nickname, req.avatar_url, db)
    return tokens


@router.post('/dev-login', response_model=TokenResponse)
def login_dev(
    db: Session = Depends(get_db),
    openid: str = 'dev_user_001',
    nickname: str = '开发者',
    avatar_url: str = '',
):
    """开发模式登录：跳过微信code2session，直接用指定 openid。"""
    if not DEV_MODE:
        raise HTTPException(403, '开发模式未启用，请设置 DEV_MODE=true')
    tokens = dev_login(openid, nickname, avatar_url, db)
    return tokens


@router.post('/cloud-login', response_model=TokenResponse)
def login_cloud(
    db: Session = Depends(get_db),
    wx_openid: str = Header(None, alias='X-WX-OPENID'),
    nickname: str = '微信用户',
    avatar_url: str = '',
):
    """云托管登录：通过 X-WX-OPENID header（callContainer 自动注入）获取 openid。"""
    if not wx_openid:
        raise HTTPException(400, '缺少 X-WX-OPENID header')
    tokens = wx_openid_login(wx_openid, nickname, avatar_url, db)
    return tokens


@router.post('/refresh', response_model=TokenResponse)
def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    """刷新 access_token。"""
    return refresh_access_token(req.refresh_token, db)


@router.get('/profile', response_model=UserProfile)
def profile(user: User = Depends(get_current_user)):
    """获取当前用户信息。"""
    return UserProfile(id=user.id, nickname=user.nickname, avatar_url=user.avatar_url)
