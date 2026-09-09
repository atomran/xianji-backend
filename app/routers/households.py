"""家庭管理路由。"""
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..auth.jwt import get_current_user
from ..models.database import User, Household, HouseholdMember
from ..models.schemas import CreateHouseholdRequest, JoinHouseholdRequest

router = APIRouter(prefix='/v1/households', tags=['households'])


@router.post('')
def create_household(req: CreateHouseholdRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """创建家庭。"""
    invite_code = secrets.token_hex(4).upper()
    household = Household(name=req.name, invite_code=invite_code, created_by=user.id)
    db.add(household)
    db.commit()
    db.refresh(household)
    member = HouseholdMember(household_id=household.id, user_id=user.id, role='owner')
    db.add(member)
    db.commit()
    return dict(id=household.id, name=household.name, invite_code=household.invite_code, role='owner')


@router.post('/join')
def join_household(req: JoinHouseholdRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """通过邀请码加入家庭。"""
    household = db.query(Household).filter(Household.invite_code == req.invite_code.upper()).first()
    if not household:
        raise HTTPException(404, '邀请码无效')
    existing = db.query(HouseholdMember).filter(HouseholdMember.household_id == household.id, HouseholdMember.user_id == user.id).first()
    if existing:
        raise HTTPException(409, '已加入该家庭')
    member = HouseholdMember(household_id=household.id, user_id=user.id, role='member')
    db.add(member)
    db.commit()
    return dict(id=household.id, name=household.name, role='member')


@router.get('')
def list_households(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """列出我加入的家庭。"""
    members = db.query(HouseholdMember).filter(HouseholdMember.user_id == user.id).all()
    result = []
    for m in members:
        h = db.query(Household).filter(Household.id == m.household_id).first()
        if h:
            result.append(dict(id=h.id, name=h.name, invite_code=h.invite_code, role=m.role))
    return dict(households=result)


@router.get('/{household_id}/members')
def list_members(household_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """家庭成员列表。"""
    member = db.query(HouseholdMember).filter(HouseholdMember.household_id == household_id, HouseholdMember.user_id == user.id).first()
    if not member:
        raise HTTPException(403, '你不属于该家庭')
    members = db.query(HouseholdMember).filter(HouseholdMember.household_id == household_id).all()
    result = []
    for m in members:
        u = db.query(User).filter(User.id == m.user_id).first()
        result.append(dict(id=u.id, nickname=u.nickname, avatar_url=u.avatar_url, role=m.role, joined_at=m.joined_at.isoformat() if m.joined_at else None))
    return dict(members=result)
