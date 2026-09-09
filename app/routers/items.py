"""食物管理路由 — items CRUD + alerts + produce-rules。"""
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..auth.jwt import get_current_user, get_current_household
from ..models.database import User, Household, Item
from ..models.schemas import ItemPayload, ItemUpdateRequest, EstimateRequest
from ..services.domain import validate, ordered, deadline, ZONES
from ..services.produce import public_rules, estimate

router = APIRouter(prefix='/v1', tags=['items'])
TZ = ZoneInfo('Asia/Shanghai')

FIELDS = ('name', 'zone', 'quantity', 'produced_on', 'shelf_days', 'expires_on', 'opened_on', 'opened_days',
          'planned_until', 'photo_id', 'photo_ids', 'note', 'status', 'kind', 'shelf_value', 'shelf_unit',
          'captured_on', 'capture_source', 'estimate_days', 'estimate_rule', 'condition')


def _now():
    return datetime.now(TZ)


@router.get('/items')
def list_items(household: Household = Depends(get_current_household), db: Session = Depends(get_db)):
    """库存清单（按到期日排序）。"""
    rows = db.query(Item).filter(Item.household_id == household.id, Item.status == 'active').all()
    items = []
    for row in rows:
        payload = row.payload if isinstance(row.payload, dict) else __import__('json').loads(row.payload)
        items.append(dict(payload, id=row.id, version=row.version, updated_at=row.updated_at.isoformat() if row.updated_at else None))
    return dict(items=ordered(items, _now().date()), server_time=_now().isoformat())


@router.post('/items', status_code=201)
def create_item(req: ItemPayload, household: Household = Depends(get_current_household), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """新建食物。"""
    item = {k: getattr(req, k, None) for k in FIELDS}
    item['status'] = 'active'
    item['note'] = req.note or ''
    validate(item)
    identifier = uuid.uuid4().hex
    stamp = _now().isoformat()
    row = Item(id=identifier, household_id=household.id, version=1, payload=item, status='active')
    db.add(row)
    db.commit()
    return dict(item=dict(item, id=identifier), id=identifier, version=1, updated_at=stamp)


@router.patch('/items/{item_id}')
def update_item(item_id: str, req: ItemUpdateRequest, household: Household = Depends(get_current_household), db: Session = Depends(get_db)):
    """更新食物（乐观锁）。"""
    row = db.query(Item).filter(Item.id == item_id, Item.household_id == household.id).first()
    if not row:
        raise HTTPException(404, '食物不存在')
    if req.version != row.version:
        raise HTTPException(409, '其他家人已修改这条记录，请刷新后重试')

    import json
    item = row.payload if isinstance(row.payload, dict) else json.loads(row.payload)
    update_data = {k: v for k, v in req.model_dump(exclude_unset=True).items() if k != 'version' and v is not None}
    item.update(update_data)
    validate(item)

    row.payload = item
    row.version += 1
    row.updated_at = _now()
    if item.get('status'):
        row.status = item['status']
    db.commit()
    return dict(item=dict(item, id=item_id), id=item_id, version=row.version, updated_at=row.updated_at.isoformat())


@router.get('/alerts')
def get_alerts(household: Household = Depends(get_current_household), db: Session = Depends(get_db)):
    """到期提醒。"""
    rows = db.query(Item).filter(Item.household_id == household.id, Item.status == 'active').all()
    items = []
    for row in rows:
        payload = row.payload if isinstance(row.payload, dict) else __import__('json').loads(row.payload)
        items.append(dict(payload, id=row.id, version=row.version))
    ordered_items = ordered(items, _now().date())
    return dict(items=[i for i in ordered_items if i['urgency'] != 'fresh'], date=_now().date().isoformat())


@router.get('/produce-rules')
def get_produce_rules():
    """蔬果规则。"""
    return dict(rules=public_rules(), assumption='新鲜、及时冷藏（≤4°C）；拍摄前的存放时间未知，提醒日期可调整。')


@router.post('/estimate')
def estimate_shelf(req: EstimateRequest):
    """蔬果保存期估算。"""
    return dict(estimate=estimate(req.name, req.captured_on, req.rule_key, req.condition, req.zone))
