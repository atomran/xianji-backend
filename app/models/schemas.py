"""Pydantic 请求/响应模型。"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field


# ---- Auth ----
class WxLoginRequest(BaseModel):
    code: str
    nickname: str = ''
    avatar_url: str = ''


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    expires_in: int = 7200


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfile(BaseModel):
    id: int
    nickname: str = ''
    avatar_url: str = ''


# ---- Household ----
class CreateHouseholdRequest(BaseModel):
    name: str = '我的冰箱'


class JoinHouseholdRequest(BaseModel):
    invite_code: str


# ---- Items ----
class ItemPayload(BaseModel):
    name: str
    zone: str
    quantity: int = 1
    produced_on: Optional[str] = None
    shelf_days: Optional[int] = None
    expires_on: Optional[str] = None
    opened_on: Optional[str] = None
    opened_days: Optional[int] = None
    planned_until: Optional[str] = None
    photo_id: Optional[str] = None
    photo_ids: Optional[List[str]] = None
    note: str = ''
    kind: Optional[str] = None
    shelf_value: Optional[int] = None
    shelf_unit: Optional[str] = None
    captured_on: Optional[str] = None
    capture_source: Optional[str] = None
    estimate_days: Optional[int] = None
    estimate_rule: Optional[str] = None
    condition: Optional[str] = None


class ItemUpdateRequest(BaseModel):
    version: int
    name: Optional[str] = None
    zone: Optional[str] = None
    quantity: Optional[int] = None
    produced_on: Optional[str] = None
    shelf_days: Optional[int] = None
    expires_on: Optional[str] = None
    opened_on: Optional[str] = None
    opened_days: Optional[int] = None
    planned_until: Optional[str] = None
    photo_id: Optional[str] = None
    photo_ids: Optional[List[str]] = None
    note: Optional[str] = None
    kind: Optional[str] = None
    shelf_value: Optional[int] = None
    shelf_unit: Optional[str] = None
    captured_on: Optional[str] = None
    capture_source: Optional[str] = None
    estimate_days: Optional[int] = None
    estimate_rule: Optional[str] = None
    condition: Optional[str] = None
    status: Optional[str] = None


# ---- Recognize ----
class RecognizeRequest(BaseModel):
    photo_ids: List[str] = Field(..., min_length=1, max_length=3)


class EstimateRequest(BaseModel):
    name: str
    captured_on: str
    rule_key: Optional[str] = None
    condition: str = 'whole'
    zone: str = '蔬果'


# ---- Device ----
class DeviceRegisterRequest(BaseModel):
    invite_code: str
