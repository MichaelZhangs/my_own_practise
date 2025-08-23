# -*- coding: utf-8 -*-
from fastapi import APIRouter, WebSocket, WebSocketDisconnect,HTTPException,Query,Depends, UploadFile, File
from utils.mongodb import MotorDB
from typing import List, Optional,Union,Any
from pydantic import BaseModel
import uuid
import json,os
from utils.mysql_crud import UserCRUD
from sqlmodel import Session
from utils.database import get_session
from init import app
from utils.log import log_info,log_error
from typing import Dict, List
from enum import Enum
from datetime import datetime
from utils.redis import (store_websocket_connection,
                            remove_websocket_connection,
                            is_user_online,
                            mark_message_as_read,
                            is_message_read,
get_websocket_connection, get_all_websocket_connections
                             )
from utils.encryption import generate_key_from_uuid, encrypt
from views.chat.single_chat import add_recent_chat

# 初始化MongoDB连接
mongo = MotorDB(database="chat_db")

@app.on_event("startup")
async def startup_db_client():
    await mongo.connect()

router = APIRouter(tags=["聊天"])

active_connections: Dict[str, WebSocket] = {}


@router.websocket("/{group_id}/{user_id}")
async def group_chat_websocket(websocket: WebSocket, user_id: int, group_id: str,
                               session: Session = Depends(get_session)):
    # 建立连接
    await websocket.accept()
    connection_key = f"{str(user_id)}-{group_id}"  # 用户ID-群ID作为连接键

    # 存储连接信息到Redis
    store_websocket_connection(str(user_id), group_id, connection_key)
    active_connections[connection_key] = websocket
    log_info(f"用户 {user_id} 加入群聊 {group_id}")

    try:
        # 获取群信息，检查用户是否是群成员
        group = await mongo.group_db.find_one({"group_id": group_id})
        if not group or user_id not in group.get("members", []):
            await websocket.send_text(json.dumps({"error": "不是群成员"}))
            await websocket.close()
            return

        # 获取群名称和头像
        group_name = group.get("name", "未知群组")

        while True:
            # 接收消息
            data = await websocket.receive_text()
            message = json.loads(data)
            log_info(f"收到来自用户 {user_id} 发送到群 {group_id} 的消息: {message}")

            # 获取发送者信息
            crud = UserCRUD(session)
            sender = crud.get_user_by_user_id(user_id)
            sender_username = sender.username if sender else "未知用户"
            sender_photo = sender.photo if sender else ""

            # 构建要广播的消息
            msg = {
                "id": message.get("id", datetime.now().microsecond),
                "text": message.get("text") or "",
                "from": user_id,
                "to": group_id,
                "media": message.get("media") or '',
                "from_username": sender_username,
                "from_photo": sender_photo,
                "group_name": group_name,
                "is_delete": 0,
                "time": message.get("time", datetime.now().isoformat())
            }

            # 广播消息给所有群成员
            members = group.get("members", [])
            online_count = 0
            offline_members = []

            for member_id in members:
                if member_id == user_id:  # 不发送给自己
                    continue

                member_key = f"{str(member_id)}-{group_id}"
                if member_key in active_connections and message.get("text"):
                    # 成员在线，发送消息
                    member_socket = active_connections[member_key]
                    try:
                        # 加密整个消息对象
                        uuid_key = str(uuid.uuid4())
                        publick_key = generate_key_from_uuid(uuid_key)
                        encrypted_data = encrypt(json.dumps(msg), publick_key)
                        encrypted_data_msg = {
                            "encrypt_data": encrypted_data,
                            "publick_key": uuid_key
                        }
                        await member_socket.send_text(json.dumps(msg))
                        online_count += 1
                    except Exception as e:
                        log_error(f"发送消息到用户 {member_id} 失败: {str(e)}")
                else:
                    # 成员离线，记录离线成员
                    offline_members.append(member_id)

                # 更新接收方的最近聊天记录和未读计数
                if member_key not in active_connections:  # 如果接收方离线
                    receiver_recent_chat = RecentChat(
                        user_id=user_id,
                        target_id=group_id,
                        group_owner_id=group.get("creator_id"),
                        target_username=group_name,
                        group_name=group_name,
                        group_members=members,
                        is_group=True,
                        members_count=group.get("members_count"),
                        last_message_time=datetime.now(),
                        unread_count=0  # 发送方的未读计数为0
                    )
                    await add_recent_chat(receiver_recent_chat)

            log_info(f"消息已广播给 {online_count} 个在线成员，{len(offline_members)} 个成员离线")

            # 存储消息到MongoDB,如果有文本信息或媒体文件
            print(f"{message}")
            # 存储消息到MongoDB,如果有文本信息或媒体文件
            if message.get("text") or message.get("media"):
                inserted_id = await mongo.group_chat_db.insert(msg)
                msg["id"] = str(inserted_id)  # 使用MongoDB生成的ID
                # 更新最近聊天记录
                recent_chat = RecentChat(
                    user_id=user_id,
                    target_id=group_id,
                    group_owner_id = group.get("creator_id"),
                    target_username=group_name,
                    group_name= group_name,
                    group_members = members,
                    is_group = True,
                    members_count= group.get("members_count"),
                    last_message_time=datetime.now(),
                    unread_count=0  # 发送方的未读计数为0
                )
                await add_recent_chat(recent_chat)

    except WebSocketDisconnect:
        # 连接断开
        if connection_key in active_connections:
            del active_connections[connection_key]

        # 从Redis中移除连接信息
        remove_websocket_connection(str(user_id), group_id)

        log_info(f"用户 {user_id} 离开群聊 {group_id}")
    except Exception as e:
        log_error(f"WebSocket异常: {str(e)}")
        if connection_key in active_connections:
            del active_connections[connection_key]
        remove_websocket_connection(str(user_id), group_id)
        await websocket.close()
# 新增数据模型
class RecentChat(BaseModel):
    user_id: int
    target_id: Union[int,str]  # 单聊是int，群聊是str
    target_username: Optional[str] = None
    target_photo: Optional[str] = None
    last_message_time: datetime
    unread_count: int = 0
    is_group: Optional[bool] = None
    # 获取聊天记录的信息
    members_count: Optional[int] = None
    group_owner_id: Optional[int] =None
    group_members: Optional[List] = None
    group_name: Optional[str] = None

# 最近聊天相关API
@router.post("/recent-chats")
async def add_recent_chat(recent_chat: RecentChat):
    """添加或更新最近聊天记录"""

    query = {"user_id": recent_chat.user_id, "target_id": recent_chat.target_id}
    if not recent_chat.is_group:
        update = {
            "$set": {
                "target_username": recent_chat.target_username,
                "target_photo": recent_chat.target_photo,
                "last_message_time": recent_chat.last_message_time,
                "unread_count": recent_chat.unread_count
            },
            "$setOnInsert": {"user_id": recent_chat.user_id, "target_id": recent_chat.target_id}
        }
    else:
        update = {
            "$set": {
                "target_username": recent_chat.target_username,
                "target_photo": recent_chat.target_photo,
                "is_group":recent_chat.is_group,
                "last_message_time": recent_chat.last_message_time,
                "unread_count": recent_chat.unread_count
            },
            "$setOnInsert": {"user_id": recent_chat.user_id, "target_id": recent_chat.target_id}
        }
    await mongo.recent_chats_db.update_one(query, update, upsert=False)
    return {"message": "最近聊天记录已更新"}

class Message(BaseModel):
    created_at: datetime
    from_id: int
    group_name: str
    from_username: str
    from_photo: str
    to: str
    text: str
    id: str
    media: Union[str, List[Dict[str, Any]]]
    is_delete: int
    time: datetime

@router.get("/history/{user_id}/{target_id}", response_model=List[Message])
async def get_chat_history(
        user_id: int,
        target_id: str,
        limit: int = Query(100, gt=0, le=1000),  # 限制返回的消息数量，默认100条，最大1000条
        before_time: datetime = Query(None),  # 分页参数：获取某个时间之前的消息
):
    """获取两个用户之间的聊天历史记录"""

    # 验证用户ID和目标ID是否有效（简单示例，实际中可能需要更复杂的验证）
    if not user_id or not target_id:
        raise HTTPException(status_code=400, detail="用户ID和目标ID不能为空")

    # 构建查询条件：消息的发送者或接收者是当前用户，并且接收者或发送者是目标用户
    query = {
            "to": target_id,
           "is_delete": 0  # 只返回未删除的消息
    }

    # 如果提供了before_time参数，则获取该时间之前的消息
    if before_time:
        query["time"] = {"$lt": before_time}
    sort = [("time", -1)]
    # 查询数据库并按时间降序排序（最新消息在前）
    messages_list = await mongo.group_chat_db.find_many(query=query, limit=limit, sort=sort)

    # 转换为列表并反转（使消息按时间升序排列）
    messages = []
    for msg in messages_list:

        # 处理MongoDB的_id字段
        msg["id"] = str(msg.pop("_id"))
        msg["from_id"] = msg["from"]  # 前端使用from_id，后端使用from
        msg["created_at"] = msg["time"]  # 前端使用created_at，后端使用time
        messages.append(msg)

    # 反转列表，使消息按时间升序排列（最早的消息在前）
    messages.reverse()

    return messages
