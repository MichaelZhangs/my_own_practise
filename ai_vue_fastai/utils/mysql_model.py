# models.py
from sqlmodel import SQLModel, Field, select
from typing import Optional, List, Dict, Any, Generator
from enum import Enum
from datetime import datetime
from pydantic import BaseModel



class SexEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"

class UserBase(SQLModel):
    phone: Optional[str] = Field(default=None, max_length=15, unique=True)
    email: Optional[str] = Field(default=None, max_length=255, unique=True)
    username: Optional[str] = Field(default=None, max_length=255)
    sex: SexEnum = Field(default=SexEnum.other)
    description: Optional[str] = Field(default=None)
    photo: Optional[str] = Field(default=None, max_length=255)
    qrcode: Optional[str] = Field(default=None, max_length=255, unique=True)
    password: Optional[str] = Field(default=None, max_length=255)

class User(UserBase, table=True):
    """用户表模型 - 对应数据库中的users表"""
    __tablename__ = "users"  # 明确指定表名

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)

class UserCreate(UserBase):
    password: str
    username: str
    phone: str

class UserUpdate(BaseModel):
    email: Optional[str] = Field(default=None)
    username: str
    sex: str
    description: Optional[str] = Field(default=None)
    phone: str
    qrcode: str


class UserInfo(BaseModel):
    username:  str           # 必填
    phone:  str           # 必填
    email: Optional[str] = None      # 可选
    sex: Optional[SexEnum] = None        # 可选
    description: Optional[str] = None
    qrcode: Optional[str] = None
    photo: Optional[str] = None
    password: Optional[str] = None
    id: int


class LoginInfo(BaseModel):
    username: str
    phone: str
    id: int
    photo: Optional[str] = None


class UserRegister(UserBase):
    username: str
    phone: str
    password: str

class UserRegisterDict(UserBase):
    user: UserRegister

class UserPublic(UserBase):
    id: int
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    user: LoginInfo


class TokenData(BaseModel):
    username: Optional[str] = None