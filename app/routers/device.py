"""设备相关路由 — 墨水屏绑定 + 快照 + 精简视图（后续备选）。"""
import hashlib
import json
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
import secrets

from ..db import get_db
from ..auth.jwt import get_current_user, get_current_household, verify_device_token
from ..models.database import User, Household, Item, Device
from ..models.schemas import DeviceRegisterRequest
from ..services.domain import ordered

router = APIRouter(prefix='/v1/device', tags=['device'])
TZ = ZoneInfo('Asia/Shanghai')


@router.post('/register')
def register_device(
    req: DeviceRegisterRequest,
    household: Household = Depends(get_current_household),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """设备绑定：邀请码 → device_token。"""
    device_token = secrets.token_urlsafe(32)
    device = Device(
        household_id=household.id,
        device_token=device_token,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return dict(device_id=device.id, device_token=device_token)


@router.get('/snapshot')
def device_snapshot(device: Device = Depends(verify_device_token), db: Session = Depends(get_db)):
    """设备全量快照（Bearer token 认证）。"""
    rows = db.query(Item).filter(Item.household_id == device.household_id, Item.status == 'active').all()
    items = []
    for row in rows:
        payload = row.payload if isinstance(row.payload, dict) else json.loads(row.payload)
        items.append(dict(payload, id=row.id))
    items.sort(key=lambda i: i['id'])
    revision = hashlib.sha256(json.dumps(items, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return dict(
        schema_version=1,
        revision=revision,
        server_time=datetime.now(TZ).isoformat(),
        timezone='Asia/Shanghai',
        refresh_after_seconds=1800,
        display={'width': 400, 'height': 300, 'palette': ['white', 'black', 'red', 'yellow']},
        items=[dict(i, id=i['id'], name=i.get('name', ''), zone=i.get('zone', ''), quantity=i.get('quantity', 1)) for i in items],
    )


@router.get('/view')
def device_view(
    device: Device = Depends(verify_device_token),
    firmware: str = Header(None, alias='X-Fridge-Firmware'),
    db: Session = Depends(get_db),
):
    """设备精简视图（固定 payload 格式，兼容现有固件）。"""
    # 更新 last_seen
    device.last_seen = datetime.now(TZ)
    device.ip_address = None  # 由中间件填充
    if firmware:
        device.firmware_version = firmware
    db.commit()

    rows = db.query(Item).filter(Item.household_id == device.household_id, Item.status == 'active').all()
    items = []
    for row in rows:
        payload = row.payload if isinstance(row.payload, dict) else json.loads(row.payload)
        items.append(dict(payload, id=row.id))
    ordered_items = ordered(items, datetime.now(TZ).date())
    view_items = [
        dict(id=i['id'], name=i['name'], zone=i['zone'], quantity=i['quantity'],
             due_on=i['due_on'], estimated=i['is_estimated'])
        for i in ordered_items
    ]
    payload = json.dumps(
        dict(schema=1, epoch=int(datetime.now(TZ).timestamp()), timezone='Asia/Shanghai', items=view_items),
        ensure_ascii=False, separators=(',', ':')
    )
    return dict(payload=payload, sha256=hashlib.sha256(payload.encode()).hexdigest())
