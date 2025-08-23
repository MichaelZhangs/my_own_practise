# -*- coding: utf-8 -*-
from fastapi import APIRouter, WebSocket, WebSocketDisconnect,HTTPException,Query,Depends, UploadFile, File
from utils.mongodb import MotorDB
from typing import List, Optional,Union, Any
from pydantic import BaseModel
import uuid
from config.settings import settings
from fastapi.responses import JSONResponse
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
import  re

# 初始化MongoDB连接
mongo = MotorDB(database="chat_db")

@app.on_event("startup")
async def startup_db_client():
    await mongo.connect()

router = APIRouter(tags=["聊天"])

active_connections: Dict[str, WebSocket] = {}

@router.websocket("/{user_id}/{target_id}")
async def chat_websocket(websocket: WebSocket, user_id: int , target_id: int,session: Session = Depends(get_session)):
    # 建立连接
    await websocket.accept()
    connection_key = f"{user_id}-{target_id}"

    # 存储连接信息到Redis
    store_websocket_connection(user_id, target_id, connection_key)
    r = get_websocket_connection(user_id, target_id)
    active_connections[connection_key] = websocket
    log_info(f"用户 {user_id} 连接到目标 {target_id}")

    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message = json.loads(data)
            log_info(f"收到消息 from {user_id} to {target_id}: {message}")

            # 构建要发送的消息
            msg = {
                "id": message.get("id", datetime.now().microsecond),
                "text": message.get("text") or "",
                "from": user_id,
                "to": target_id,
                "media": message.get("media") or '',
                "fromUsername": message.get("fromUsername") or '',  # 发送者用户名
                "fromPhoto": message.get("fromPhoto") or '',  # 发送者头像
                "is_delete": 0,
                "time": message.get("time", datetime.now().isoformat())
            }

            # 转发消息给目标用户
            target_key = f"{target_id}-{user_id}"
            if target_key in active_connections and message.get("text"):
                # 目标用户在线，直接发送消息
                target_socket = active_connections[target_key]
                await target_socket.send_text(json.dumps(msg))

                # 标记消息为已读（如果需要）
                if "message_id" in message:  # 如果客户端发送了原始消息ID
                    mark_message_as_read(str(message["message_id"]))
            else:
                # 目标用户离线，记录离线消息（可选）
                log_info(f"目标用户 {target_id} 离线，消息将存储为离线消息")

            crud = UserCRUD(session)
            print(f"{message}")
            # 存储消息到MongoDB,如果有文本信息或媒体文件
            if message.get("text") or message.get("media"):
                inserted_id = await mongo.single_db.insert(msg)
                msg["id"] = str(inserted_id)  # 使用MongoDB生成的ID
                user = crud.get_user_by_user_id(target_id)
                # 更新最近聊天记录
                recent_chat = RecentChat(
                    user_id=user_id,
                    target_id=target_id,
                    target_username=user.username or '',
                    target_photo=user.photo or '',
                    last_message_time=datetime.now(),
                    unread_count=0  # 发送方的未读计数为0
                )
                await add_recent_chat(recent_chat)

                # 更新接收方的最近聊天记录和未读计数
                if target_key not in active_connections:  # 如果接收方离线
                    receiver_recent_chat = RecentChat(
                        user_id=target_id,
                        target_id=user_id,
                        target_username= user.username or '',
                        target_photo= user.photo or '',
                        last_message_time=datetime.now(),
                        unread_count=1  # 离线时增加未读计数
                    )
                    await add_recent_chat(receiver_recent_chat)

    except WebSocketDisconnect:
        # 连接断开
        if connection_key in active_connections:
            del active_connections[connection_key]

        # 从Redis中移除连接信息
        remove_websocket_connection(user_id, target_id)

        log_info(f"用户 {user_id} 断开连接")


class Message(BaseModel):
    id: str
    text: str
    from_id: int
    to: int
    media:  Union[str, List[Dict[str, Any]]]
    fromUsername: Optional[str] = None
    fromPhoto: Optional[str] = None
    is_delete: int = 0
    time: datetime
    created_at: datetime

@router.get("/history/{user_id}/{target_id}", response_model=List[Message])
async def get_chat_history(
        user_id: int,
        target_id: int,
        limit: int = Query(100, gt=0, le=1000),  # 限制返回的消息数量，默认100条，最大1000条
        before_time: datetime = Query(None),  # 分页参数：获取某个时间之前的消息
):
    """获取两个用户之间的聊天历史记录"""

    # 验证用户ID和目标ID是否有效（简单示例，实际中可能需要更复杂的验证）
    if not user_id or not target_id:
        raise HTTPException(status_code=400, detail="用户ID和目标ID不能为空")

    # 构建查询条件：消息的发送者或接收者是当前用户，并且接收者或发送者是目标用户
    query = {
        "$or": [
            {"from": user_id, "to": target_id},
            {"from": target_id, "to": user_id}
        ],
        "is_delete": 0  # 只返回未删除的消息
    }

    # 如果提供了before_time参数，则获取该时间之前的消息
    if before_time:
        query["time"] = {"$lt": before_time}
    sort = [("time", -1)]
    # 查询数据库并按时间降序排序（最新消息在前）
    messages_list = await mongo.single_db.find_many(query=query, limit=limit, sort=sort)

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

    # 加密整个消息列表

    # encrypted_messages = app.encryptor(messages)

    return messages

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
    await mongo.recent_chats_db.update_one(query, update, upsert=True)
    return {"message": "最近聊天记录已更新"}



@router.get("/recent-chats/{user_id}", response_model=List[RecentChat])
async def get_recent_chats(user_id: int, limit: int = Query(10, gt=0, le=50)):
    """获取用户的最近聊天列表"""
    query = {"user_id": user_id}
    sort = [("last_message_time", -1)]  # 按最后消息时间降序排列
    recent_chats = await mongo.recent_chats_db.find_many(query=query, limit=limit, sort=sort)
    return recent_chats

@router.post("/recent-chats/{user_id}/clear-unread/{target_id}")
async def clear_unread_count(user_id: int, target_id: Union[int,str]):
    """清除与特定用户的未读消息计数"""
    query = {"user_id": user_id, "target_id": target_id}
    update = {"$set": {"unread_count": 0}}
    await mongo.recent_chats_db.update_one(query, update)
    return {"message": "未读计数已清除"}


@router.post("/upload/media")
async def upload_media(file: UploadFile = File(...)):
    try:
        # 允许的文件类型检查
        print(f"{file.content_type}")
        if file.content_type not in settings.ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型"
            )
        print(f"{file} {file.filename}")
        # 获取原始文件名和扩展名
        original_filename = file.filename
        file_extension = original_filename.split('.')[-1].lower() if '.' in original_filename else ''

        # 创建对应的存储目录
        base_media_dir = settings.CHAT_MEDIA

        # 确定文件存储子目录
        if 'image' in file.content_type:
            sub_dir = 'images'
        elif 'video' in file.content_type:
            sub_dir = 'videos'
        elif 'audio' in file.content_type:
            sub_dir = 'audios'
        else:
            sub_dir = 'files'  # 其他文件类型

        media_dir = f"{base_media_dir}/{sub_dir}"
        os.makedirs(media_dir, exist_ok=True)

        # 生成唯一文件名（保留原始扩展名）
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = uuid.uuid4().hex[:8]

        # 清理文件名（移除特殊字符）
        safe_filename = re.sub(r'[^\w.-]', '_', original_filename.split('.')[0])
        file_name = f"{safe_filename}_{timestamp}_{unique_id}.{file_extension}" if file_extension else f"{safe_filename}_{timestamp}_{unique_id}"
        file_path = os.path.join(media_dir, file_name)

        # 保存文件
        file_size = 0
        with open(file_path, "wb") as f:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                f.write(content)
                file_size += len(content)

        # 构造访问URL
        media_url = f"/{settings.ARTICLE_MEDIA}/{sub_dir}/{file_name}"

        # 获取文件类型（简化分类）
        if 'image' in file.content_type:
            file_type = 'image'
        elif 'video' in file.content_type:
            file_type = 'video'
        elif 'audio' in file.content_type:
            file_type = 'audio'
        else:
            file_type = 'file'

        return {
            "success": True,
            "url": media_url,
            "type": file_type,
            "content_type": file.content_type,
            "original_name": original_filename,
            "size": file_size,
            "message": "文件上传成功"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"上传失败: {str(e)}"
        )