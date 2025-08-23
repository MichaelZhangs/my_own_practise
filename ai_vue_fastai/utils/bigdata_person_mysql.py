# models.py
from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime
from typing import TYPE_CHECKING
from enum import Enum

# 基础用户模型
class BigdataUserBase(SQLModel):
    name: str = Field(max_length=50, description="用户姓名")
    idno: str = Field(max_length=18, description="证件号码", index=True, unique=True)
    sex: str = Field(default=None,max_length=10, description="性别")
    bplace: str = Field(default=None,max_length=100, description="出生地")
    idtype: str = Field(default=None, description="证件类型")
    sort: int = Field(default=0, description="排序字段")
    province: str = Field(max_length=50, description="省份")
    age: Optional[int] = Field(default=None, description="年龄")
    birthday: Optional[int] = Field(default=None, description="生日")

class PersonInfo(BigdataUserBase, table=True):
    """用户表模型 - 对应数据库中的users表"""
    __tablename__ = "person_info"  # 明确指定表名

    id: Optional[int] = Field(default=None, primary_key=True)
