# main.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel, Field
from utils.redis import set_code, get_code, set_userinfo_to_redis
from enum import Enum
import uuid
import base64
import os
from config.settings import settings
from utils.log import log_info, log_error
from utils.database import get_session
from utils.mysql_model import User, SexEnum, UserPublic, UserUpdate, UserInfo
from utils.mysql_crud import UserCRUD
from sqlmodel import Session
import json

router = APIRouter(tags=["用户信息"])

class SaveQrcodeRequest(BaseModel):
    phone: str
    qrcode: str

class SearchPhoneRequest(BaseModel):
    username: str  # 必填
    phone: str  # 必填
    email: Optional[str] = None  # 可选
    sex: Optional[SexEnum] = None  # 可选
    description: Optional[str] = None
    qrcode: Optional[str] = None
    photo: Optional[str] = None

class GetUserList(BaseModel):
    username: str
    phone: str
    photo:  Optional[str]
    sex: SexEnum
    id: int

class PagedResponse(BaseModel):
    data: List[GetUserList]
    total: int
    page: int
    page_size: int

class SaveAvatarRequest(BaseModel):
    phone: str
    photo: str

class UpdatePhoneRequest(BaseModel):
    new_phone: str
    verification_code: str


@router.get("/get-users", response_model=PagedResponse)
async def get_users(
        username: Optional[str] = Query(None),
        phone: Optional[str] = Query(None),
        sex: Optional[str] = Query(None),
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
        session: Session = Depends(get_session)
):
    try:
        crud = UserCRUD(session)

        # 获取总数
        total = crud.count_users(username, phone, sex)

        # 计算偏移量
        offset = (page - 1) * page_size

        # 获取分页数据
        users = crud.get_users(
            username=username,
            phone=phone,
            sex=sex,
            skip=offset,
            limit=page_size
        )

        return {
            "data": users,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        log_error(f"获取用户列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户列表失败")


@router.get("/search", response_model=PagedResponse)
async def search_users(
        keyword: Optional[str] = Query(None, description="搜索关键词，同时匹配用户名和手机号"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量"),
        session: Session = Depends(get_session)
):
    try:
        crud = UserCRUD(session)
        print(f"keyword = {keyword}")
        # 构建查询条件
        filters = {}
        if keyword:
            # 同时匹配用户名和手机号
            filters["search_term"] = keyword

        # 获取总数
        total = crud.count_users(**filters)

        print(f"total = {total}")
        # 计算偏移量
        offset = (page - 1) * page_size

        # 获取分页数据
        users = crud.get_users(
            skip=offset,
            limit=page_size,
            **filters
        )
        print(f"users = {users}")
        # 转换为前端可用的格式
        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "username": user.username,
                "phone": user.phone,
                "email": user.email or '',
                "sex": user.sex or 'other',
                "description": user.description or '',
                "qrcode": user.qrcode or '',
                "photo": user.photo or ''
            })
        print(f"user_list = {user_list}")
        return {
            "data": users,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    except Exception as e:
        log_error(f"搜索用户失败: {str(e)}")
        raise HTTPException(status_code=500, detail="搜索用户失败")

@router.get("/info", response_model=UserInfo)
async def get_user_info(
        id: str,
        session: Session = Depends(get_session)
):
    try:
        if id.startswith("group_"):
            raise HTTPException(
                status_code=400,
                detail="此接口用于查询用户信息，请使用群组信息接口"
            )
        id = int(id)
        print(f"user_id : {id}")
        crud = UserCRUD(session)
        user = crud.get_user_by_user_id(id)

        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        return {
            "username": user.username ,
            "phone": user.phone,
            "email": user.email or '',
            "sex": user.sex or 'other',
            "description": user.description or '',
            "qrcode": user.qrcode or '',
            "photo": user.photo or '',
            "id": user.id
        }
    except Exception as e:
        log_error(f"获取用户信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户信息失败")

@router.put("/info")
async def update_user_info(
        request: UserUpdate,
        session: Session = Depends(get_session)
):
    try:
        print(f"phone=: {request.phone}")

        if request.email == "":
            request.email = None

        crud = UserCRUD(session)

        updated_user = crud.update_user(request.phone,request)

        user_dic = {
                "username": updated_user.username,
                "phone": updated_user.phone,
                "id": updated_user.id,
                "photo": updated_user.photo,
                "email": updated_user.email or "",
            }

        set_userinfo_to_redis(f"{updated_user.id}_info", json.dumps(user_dic))

        if not updated_user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return {"message": "更新成功", "code": 200}
    except Exception as e:
        log_error(f"更新失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-qrcode")
async def save_qrcode(
        request: SaveQrcodeRequest,
        session: Session = Depends(get_session)
):
    try:
        # 解码并保存图片
        image_data = base64.b64decode(request.qrcode.split(",")[1])
        os.makedirs(settings.QRCODE_DIR, exist_ok=True)
        file_name = f"qrcode_{request.phone}.png"
        file_path = os.path.join(settings.QRCODE_DIR, file_name)

        with open(file_path, "wb") as f:
            f.write(image_data)

        # 更新数据库
        qrcode_url = f"/{settings.QRCODE_DIR}/{file_name}"
        crud = UserCRUD(session)
        updated_user = crud.update_user_field(request.phone, "qrcode", qrcode_url)

        if not updated_user:
            raise HTTPException(status_code=404, detail="用户不存在")

        return {
            "message": "二维码保存成功",
            "file_path": file_path,
            "qrcode_url": qrcode_url
        }
    except Exception as e:
        log_error(f"二维码保存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"二维码保存失败: {str(e)}")


@router.post("/upload-avatar")
async def upload_avatar(
        request: SaveAvatarRequest,
        session: Session = Depends(get_session)
):
    try:
        # 解码并保存图片
        image_data = base64.b64decode(request.photo.split(",")[1])
        os.makedirs(settings.AVATAR_DIR, exist_ok=True)
        unique_id = uuid.uuid4().hex[:4]
        filename = f"ph_{request.phone}_{unique_id}.png"
        save_path = os.path.join(settings.AVATAR_DIR, filename)

        with open(save_path, "wb") as f:
            f.write(image_data)


        # 更新数据库
        avatar_url = f"/{settings.AVATAR_DIR}/{filename}"
        crud = UserCRUD(session)
        updated_user = crud.update_user_field(request.phone, "photo", avatar_url)

        if not updated_user:
            raise HTTPException(status_code=404, detail="用户不存在")

        return {
            "message": "头像上传成功",
            "file_path": save_path,
            "avatar_url": avatar_url
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        log_error(f"上传头像失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传头像失败: {str(e)}")

# 其他路由保持不变...