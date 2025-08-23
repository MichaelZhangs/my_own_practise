# encoding: UTF-8
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect,HTTPException,Query,Depends, UploadFile, File
from utils.mongodb import MotorDB
from typing import List, Optional
from pydantic import BaseModel,validator
from init import app
from utils.log import log_info,log_error
from datetime import datetime
from typing import List
import shortuuid
from utils.mysql_crud import UserCRUD
from sqlmodel import Session
from utils.database import get_session
from utils.redis import get_code
from bson import  ObjectId

# 初始化MongoDB连接
mongo = MotorDB(database="chat_db")

@app.on_event("startup")
async def startup_db_client():
    await mongo.connect()


router = APIRouter(tags=["建群"])

class GroupCreateRequest(BaseModel):
    name: str
    user_id: int
    members: List[int]  # 成员ID列表，包含创建者


class GroupModel(BaseModel):
    group_id: str
    name: str
    creator_id: int
    members: List[int]
    created_at: datetime
    photo: str = None
    description: str = None


class SuccessModel(BaseModel):
    status: int = 200
    msg: str
    data: dict = None

class GroupChatMode(BaseModel):
    creator_id: int
    group_id: str
    members: List[int]
    created_at: datetime
    name: str
    members_count: int
    unread_count: int = 0
    photo: Optional[str] =None

class GroupInfoResponse(BaseModel):
    creator_id: int
    group_id: str
    group_members: List[int]
    create_time: datetime
    group_name: str
    avatar_members: List[str]
    members_count: int
    unread_count: int = 0
    photo: Optional[str] =None

@router.post("/group/create", response_model=SuccessModel)
async def create_group(group_data: GroupCreateRequest):
    """
    创建群组
    参数:
    - name: 群名称
    - members: 成员ID列表 (包含创建者)
    """
    try:
        # 生成唯一的群组ID
        group_id = f"group_{shortuuid.ShortUUID().random(length=8)}"

        # 确保创建者在成员列表中
        if group_data.user_id not in group_data.members:
            group_data.members.append(group_data.user_id)

        # 创建群组文档
        group = {
            "group_id": group_id,
            "name": group_data.name,
            "creator_id": group_data.user_id,
            "members": group_data.members,
            "members_count": len(group_data.members),
            "created_at": datetime.utcnow(),
            "photo": None,
            "description": None
        }

        # 保存到数据库
        inserted_id= await mongo.group_db.insert(group)

        # 群组添加大最近聊天
        for user_id in group_data.members:
            recent_chat = {
                "group_owner_id": group_data.user_id,
                "target_id": group_id,
                "insert_id": inserted_id,
                "group_members": group_data.members,
                "group_name": group_data.name,
                "user_id": user_id,
                "members_count": len(group_data.members),
                "target_photo": None,
                "last_message_time": datetime.utcnow(),
                "unread_count": 0,
                "is_group": True
            }
            await mongo.recent_chats_db.insert(recent_chat)
        return SuccessModel(
            msg="群组创建成功",
            data={
                "group_id": group_id,
                "target_id": group_id,
                "name": group_data.name,
                "members_count": len(group_data.members),
                "members": group_data.members
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"创建群组失败: {str(e)}"
        )

@router.get('/group/get-joined-groups/{user_id}', response_model=List[GroupChatMode])
async def get_joined_groups(
        user_id: int,
        limit: int = Query(10, gt=0, le=50),
):
    """获取用户加入的群聊列表（简化版）"""
    try:
        # 1. 从group_members表查询用户加入的所有群ID
        member_query = {"members": {"$in": [user_id]}}
        group_member_docs = await mongo.group_db.find_many(member_query)
        # print(f"group_members: {group_member_docs}")
        log_info(f"group_members: {group_member_docs}")
        if not group_member_docs:
            return []  # 没有加入任何群聊

        # 3. 补充target_id字段（与群ID一致，方便前端统一处理）
        for doc in group_member_docs:
            # doc["target_id"] = doc["_id"]  # 前端可通过target_id识别聊天对象
            doc["_id"] = str(doc["_id"])  # ObjectId转字符串

        return group_member_docs

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取群聊列表失败: {str(e)}")

@router.get("/group/get-group-avatar/{group_id}",response_model=List[str])
async def get_group_avatar(group_id:str,session: Session = Depends(get_session)):
    try:
        # 1. 获取群信息，包括成员列表和创建者ID
        group = await mongo.group_db.find_one({"group_id": group_id})
        if not group:
            raise HTTPException(
                status_code=404,
                detail="群组不存在"
            )

        creator_id = group.get("creator_id")
        members = group.get("members", [])

        # 2. 确保创建者在第一位
        unique_members = list(dict.fromkeys(members))  # 去重
        if creator_id in unique_members:
            # 将创建者移到列表首位
            unique_members.remove(creator_id)
            unique_members.insert(0, creator_id)

        # 3. 限制最多返回9个成员
        selected_members = unique_members[:9]
        log_info(f"select_members: {selected_members}")
        avatar = []

        for user_id in selected_members:
            user_dic = None
            photo = None
            crud = UserCRUD(session)
            key = f"{user_id}_info"

            # 检查缓存
            cached_data = get_code(key)
            if cached_data:
                try:
                    user_dic = json.loads(cached_data)
                    log_info(f"user_dic from cache: {user_dic}")
                    photo = user_dic.get("photo")
                except json.JSONDecodeError:
                    log_error(f"Failed to parse cached data for user {user_id}")

            # 如果缓存中没有或解析失败，从数据库获取
            if not photo:
                user = crud.get_user_by_user_id(user_id)
                log_info(f"user from DB: {user}")
                if user and user.photo:
                    photo = user.photo
                else:
                    photo = ''  # 或者设置默认头像路径
            avatar.append(photo)
        log_info(f"avatar : {avatar}")
        return avatar

    except Exception as e:
        log_info(f"获取群头像失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取群头像失败: {str(e)}"
        )

@router.get("/group/{group_id}", response_model=GroupInfoResponse)
async def get_group_info(group_id: str,session: Session = Depends(get_session)):
    try:
        # 从MongoDB获取群信息
        group = await mongo.group_db.find_one({"group_id": group_id})
        if not group:
            raise HTTPException(
                status_code=404,
                detail="群组不存在"
            )
        # 获取成员数量
        members = group.get("members", [])
        avatar_members = await get_group_avatar(group_id, session)        # 构建返回的群信息对象
        log_info(f"打印 群成员 图片: {avatar_members}")
        group_info = {
            "group_id": group.get("group_id"),
            "group_name": group.get("name"),
            "group_avatar": group.get("group_avatar"),
            "creator_id": group.get("creator_id"),
            "avatar_members": avatar_members,
            "group_members": members,
            "members_count": group.get("members_count"),
            "create_time": group.get("created_at"),
        }

        return group_info

    except Exception as e:
        log_error(f"获取群信息失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取群信息失败: {str(e)}"
        )

