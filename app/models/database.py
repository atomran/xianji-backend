"""SQLAlchemy 数据模型。"""
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def gen_uuid():
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    openid = Column(String(64), unique=True, nullable=False)
    unionid = Column(String(64), unique=True, nullable=True)
    nickname = Column(String(64), default='')
    avatar_url = Column(String(512), default='')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    households = relationship('HouseholdMember', back_populates='user')


class Household(Base):
    __tablename__ = 'households'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, default='我的冰箱')
    invite_code = Column(String(16), unique=True, nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    members = relationship('HouseholdMember', back_populates='household')
    items = relationship('Item', back_populates='household')
    devices = relationship('Device', back_populates='household')


class HouseholdMember(Base):
    __tablename__ = 'household_members'
    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, ForeignKey('households.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    role = Column(Enum('owner', 'member'), default='member')
    joined_at = Column(DateTime, default=datetime.utcnow)
    household = relationship('Household', back_populates='members')
    user = relationship('User', back_populates='households')

    __table_args__ = (Index('idx_household_user', 'household_id', 'user_id', unique=True),)


class Item(Base):
    __tablename__ = 'items'
    id = Column(String(32), primary_key=True, default=gen_uuid)
    household_id = Column(Integer, ForeignKey('households.id'), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    payload = Column(JSON, nullable=False)
    status = Column(Enum('active', 'consumed', 'discarded'), default='active')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    household = relationship('Household', back_populates='items')

    __table_args__ = (
        Index('idx_household_status', 'household_id', 'status'),
        Index('idx_updated', 'updated_at'),
    )


class Photo(Base):
    __tablename__ = 'photos'
    id = Column(String(32), primary_key=True, default=gen_uuid)
    household_id = Column(Integer, ForeignKey('households.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    oss_key = Column(String(256), nullable=False)
    preview_key = Column(String(256), nullable=False)
    photo_metadata = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index('idx_photo_household', 'household_id'),)


class Device(Base):
    __tablename__ = 'devices'
    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, ForeignKey('households.id'), nullable=False)
    device_token = Column(String(64), unique=True, nullable=False)
    firmware_version = Column(String(32), nullable=True)
    last_seen = Column(DateTime, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    household = relationship('Household', back_populates='devices')
