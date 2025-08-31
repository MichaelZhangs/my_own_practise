# encoding: UTF-8
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect,HTTPException,Query,Depends, UploadFile, File
from utils.mongodb import MotorDB
from typing import List, Optional,Dict,Union
from pydantic import BaseModel,validator,Field
from init import app
from utils.log import log_info,log_error
from datetime import datetime
import shortuuid
from utils.mysql_crud import UserCRUD
from sqlmodel import Session
from utils.database import get_session
from utils.redis import get_code,set_code,get_websocket_connection
from utils.get_current_user import get_current_user_id

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
            "delete": 0, # -1 表示群已经删除
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
        member_query = {"members": {"$in": [user_id]}, "delete": 0}
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

# 首先创建成员信息模型
class MemberInfo(BaseModel):
    id: int
    username: str
    photo: Optional[str] = None

class GroupMembersResponse(BaseModel):
    group_members: List[MemberInfo]
    group_id: str
    group_name: str
    creator_id: int
    members_count: int


@router.get("/group/{group_id}/members", response_model=GroupMembersResponse)
async def get_group_members(group_id: str, session: Session = Depends(get_session)):
    try:
        # 从MongoDB获取群信息
        group = await mongo.group_db.find_one({"group_id": group_id})
        if not group:
            raise HTTPException(
                status_code=404,
                detail="群组不存在"
            )

        # 获取成员ID列表
        member_ids = group.get("members", [])

        # 获取成员详细信息（使用缓存）
        members_info = []
        crud = UserCRUD(session)

        for user_id in member_ids:
            user_info = None
            photo = None

            # 检查缓存
            key = f"{user_id}_info"
            cached_data = get_code(key)
            if cached_data:
                try:
                    user_info = json.loads(cached_data)
                    photo = user_info.get("photo")
                except json.JSONDecodeError:
                    log_error(f"Failed to parse cached data for user {user_id}")

            # 如果缓存中没有，从数据库获取
            if not user_info:
                user = crud.get_user_by_user_id(user_id)
                if user:
                    user_info = {
                        "id": user.id,
                        "username": user.username,
                        "photo": user.photo
                    }
                    # 缓存用户信息
                    set_code(key, json.dumps(user_info), expire=3600)  # 缓存1小时
                else:
                    user_info = {
                        "id": user_id,
                        "username": f"用户{user_id}",
                        "photo": None
                    }

            members_info.append(user_info)

        # 构建返回的响应对象
        response_data = {
            "group_members": members_info,
            "group_id": group.get("group_id"),
            "group_name": group.get("name"),
            "creator_id": group.get("creator_id"),
            "members_count": group.get("members_count", len(member_ids))
        }

        log_info(f"返回群成员数据: {response_data}")
        return response_data

    except Exception as e:
        log_error(f"获取群成员失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取群成员失败: {str(e)}"
        )

class GroupMuteStatus(BaseModel):
    group_id: str
    muted: bool # 0: 打开, 1: 关闭
    create_dt: datetime = datetime.utcnow()

class MuteStatusResponse(BaseModel):
    muted: bool
    success: bool = True
    message: str = "操作成功"


class MuteRequest(BaseModel):
    muted: bool
    user_id: int

@router.get("/group/{group_id}/mute-status", response_model=MuteStatusResponse)
async def get_group_mute_status(
        group_id: str,
        user_id: int = Query(..., description="用户ID"),
        session: Session = Depends(get_session)
):
    """
    获取用户在群聊中的免打扰状态
    """
    try:
        log_info(f"获取免打扰状态 - 用户ID: {user_id}, 群ID: {group_id}")

        # 验证群组是否存在
        group = await mongo.group_db.find_one({"group_id": group_id})
        if not group:
            raise HTTPException(
                status_code=404,
                detail="群组不存在"
            )

        # 验证用户是否是群成员
        if user_id not in group.get("members", []):
            raise HTTPException(
                status_code=403,
                detail="用户不是群成员"
            )

        # 查询免打扰状态
        mute_status = await mongo.group_mute_db.find_one({
            "user_id": user_id,
            "group_id": group_id
        })

        # 如果没有记录，默认为打开状态 (muted=0)
        if not mute_status:
            log_info(f"为用户 {user_id} 在群 {group_id} 创建默认免打扰记录")

            # 创建默认记录
            default_mute_data = {
                "user_id": user_id,
                "group_id": group_id,
                "muted": False,  # 默认为打开状态
                "create_dt": datetime.utcnow()
            }

            # 插入数据库
            await mongo.group_mute_db.insert_one(default_mute_data)

            # 设置默认值
            muted_value = False
        else:
            # 如果有记录，使用数据库中的值
            muted_value = mute_status.get("muted", False)

        log_info(f"用户 {user_id} 在群 {group_id} 的免打扰状态: {muted_value}")

        return MuteStatusResponse(muted=muted_value)

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"获取免打扰状态失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取免打扰状态失败: {str(e)}"
        )


@router.post("/group/{group_id}/mute", response_model=MuteStatusResponse)
async def set_group_mute_status(
        group_id: str,
        request: MuteRequest,  # 改为接收请求体
        session: Session = Depends(get_session)
):
    """
    设置用户在群聊中的免打扰状态
    """
    try:
        user_id = request.user_id
        muted = request.muted

        log_info(f"设置免打扰状态 - 用户ID: {user_id}, 群ID: {group_id}, 状态: {muted}")

        # 验证群组是否存在
        group = await mongo.group_db.find_one({"group_id": group_id})
        if not group:
            raise HTTPException(
                status_code=404,
                detail="群组不存在"
            )

        # 验证用户是否是群成员
        if user_id not in group.get("members", []):
            raise HTTPException(
                status_code=403,
                detail="用户不是群成员"
            )

        # 更新或插入免打扰状态
        mute_data = {
            "user_id": user_id,
            "group_id": group_id,
            "muted": muted,
            "create_dt": datetime.utcnow()
        }

        await mongo.group_mute_db.update_one(
            {"user_id": user_id, "group_id": group_id},
            {"$set": mute_data},
            upsert=True
        )

        log_info(f"成功设置用户 {user_id} 在群 {group_id} 的免打扰状态为: {muted}")

        return MuteStatusResponse(muted=muted, message="免打扰状态设置成功")

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"设置免打扰状态失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"设置免打扰状态失败: {str(e)}"
        )

# 定义请求和响应模型
class UpdateGroupNameRequest(BaseModel):
    group_id: str
    name: str

class UpdateGroupNameResponse(BaseModel):
    success: bool
    message: str
    group_name: Optional[str] = None


@router.post("/group/update-name", response_model=UpdateGroupNameResponse)
async def update_group_name(
        request: UpdateGroupNameRequest,
        current_user_id: int = Depends(get_current_user_id),
        session: Session = Depends(get_session),
):
    """
    更新群组名称
    """
    try:
        group_id = request.group_id
        new_name = request.name.strip()

        log_info(f"更新群名称 - 群ID: {group_id}, 新名称: {new_name} ,用户: {current_user_id}")

        # 验证群名称长度
        if len(new_name) < 1 or len(new_name) > 20:
            raise HTTPException(
                status_code=400,
                detail="群名称长度必须在1-20个字符之间"
            )

        # 验证群组是否存在
        group = await mongo.group_db.find_one({"group_id": group_id})
        if not group:
            raise HTTPException(
                status_code=404,
                detail="群组不存在"
            )

        if current_user_id not in group.get("members"):
            raise HTTPException(
                status_code=403,
                detail="群不存在该成员"
            )

        # 更新群名称
        update_result = await mongo.group_db.update_one(
            {"group_id": group_id},
            {"$set": {
                "name": new_name,
                "update_dt": datetime.utcnow()
            }}
        )

        if not update_result:
            log_error(f"更新群名称失败 - 群ID: {group_id}")
            raise HTTPException(
                status_code=500,
                detail="更新群名称失败"
            )

        log_info(f"成功更新群名称 - 群ID: {group_id}, 新名称: {new_name}")

        # 如果需要，可以在这里发送群通知，告知所有成员群名称已更改

        return UpdateGroupNameResponse(
            success=True,
            message="群名称修改成功",
            group_name=new_name
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"更新群名称异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"更新群名称失败: {str(e)}"
        )


class RemoveMemberRequest(BaseModel):
    group_id: str
    user_id: int

class RemoveMemberResponse(BaseModel):
    success: bool
    message: str
    removed_user_id: Optional[int] = None


@router.post("/group/remove-member", response_model=RemoveMemberResponse)
async def remove_group_member(
        request: RemoveMemberRequest,
        current_user_id: int = Depends(get_current_user_id),
        session: Session = Depends(get_session),
):
    """
    从群组中移除成员
    """
    try:
        group_id = request.group_id
        user_id_to_remove = request.user_id

        log_info(f"移除群成员 - 群ID: {group_id}, 要移除的用户ID: {user_id_to_remove}, 操作者: {current_user_id}")

        # 验证群组是否存在
        group = await mongo.group_db.find_one({"group_id": group_id})
        if not group:
            raise HTTPException(
                status_code=404,
                detail="群组不存在"
            )

        # 检查操作者是否是群主
        if group.get("creator_id") != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="只有群主可以移除成员"
            )

        # 检查要移除的用户是否在群中
        members = group.get("members", [])
        if user_id_to_remove not in members:
            raise HTTPException(
                status_code=404,
                detail="该用户不在群组中"
            )

        # 不能移除自己
        if user_id_to_remove == current_user_id:
            raise HTTPException(
                status_code=400,
                detail="不能移除自己"
            )

        # 不能移除群主
        if user_id_to_remove == group.get("creator_id"):
            raise HTTPException(
                status_code=400,
                detail="不能移除群主"
            )

        # 更新群组成员列表
        updated_members = [member for member in members if member != user_id_to_remove]

        update_result =  await mongo.group_db.update_one(
                    {"group_id": group_id},
                    {
                        "$pull": {"members": user_id_to_remove},  # 从数组中移除指定成员
                        "$inc": {"members_count": -1},  # 成员数量减1
                        "$set": {"update_dt": datetime.utcnow()}
                    }
                )

        if not update_result:
            log_error(f"移除群成员失败 - 群ID: {group_id}")
            raise HTTPException(
                status_code=500,
                detail="移除成员失败"
            )

        log_info(f"成功移除群成员 - 群ID: {group_id}, 被移除用户ID: {user_id_to_remove}")

        # 发送系统通知（可选）
        # await send_group_notification(group_id, f"用户 {user_id_to_remove} 已被移出群聊")

        return RemoveMemberResponse(
            success=True,
            message="成员移除成功",
            removed_user_id=user_id_to_remove
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"移除群成员异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"移除成员失败: {str(e)}"
        )

class ExitGroupRequest(BaseModel):
    group_id: str

class ExitGroupResponse(BaseModel):
    success: bool
    message: str
    exited_group_id: Optional[str] = None


@router.post("/group/exit", response_model=ExitGroupResponse)
async def exit_group(
        request: ExitGroupRequest,
        current_user_id: int = Depends(get_current_user_id),
        session: Session = Depends(get_session),
):
    """
    退出群聊
    """
    try:
        group_id = request.group_id

        log_info(f"退出群聊 - 群ID: {group_id}, 用户ID: {current_user_id}")

        # 验证群组是否存在
        group = await mongo.group_db.find_one({"group_id": group_id})
        if not group:
            raise HTTPException(
                status_code=404,
                detail="群组不存在"
            )

        # 检查用户是否在群中
        members = group.get("members", [])
        if current_user_id not in members:
            raise HTTPException(
                status_code=404,
                detail="您不在该群组中"
            )

        # 群主不能直接退出，需要先转让群主或解散群
        if group.get("creator_id") == current_user_id:
            raise HTTPException(
                status_code=400,
                detail="群主不能直接退出群聊，请先转让群主或解散群"
            )

        # 使用原子操作更新群组成员和计数
        update_result = await mongo.group_db.update_one(
            {"group_id": group_id},
            {
                "$pull": {"members": current_user_id},
                "$inc": {"members_count": -1},
                "$set": {"update_dt": datetime.utcnow()}
            }
        )

        if not update_result:
            log_error(f"退出群聊失败 - 群ID: {group_id}")
            raise HTTPException(
                status_code=500,
                detail="退出群聊失败"
            )

        log_info(f"成功退出群聊 - 群ID: {group_id}, 用户ID: {current_user_id}")

        # 发送系统通知（可选）
        # await send_group_notification(group_id, f"用户 {current_user_id} 已退出群聊")

        return ExitGroupResponse(
            success=True,
            message="已成功退出群聊",
            exited_group_id=group_id
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"退出群聊异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"退出群聊失败: {str(e)}"
        )


class DismissGroupRequest(BaseModel):
    group_id: str

class BaseResponse(BaseModel):
    success: bool
    message: str


@router.post("/group/dismiss", response_model=BaseResponse)
async def dismiss_group(
        request: DismissGroupRequest,
        current_user_id: int = Depends(get_current_user_id),
        session: Session = Depends(get_session),
):
    """
    解散群聊
    """
    try:
        group_id = request.group_id

        log_info(f"解散群聊 - 群ID: {group_id}, 操作者: {current_user_id}")

        # 验证群组是否存在
        group = await mongo.group_db.find_one({"group_id": group_id})
        if not group:
            raise HTTPException(
                status_code=404,
                detail="群组不存在"
            )

        # 检查操作者是否是群主
        if group.get("creator_id") != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="只有群主可以解散群聊"
            )

            # 检查群组是否已经被删除
        if group.get("delete") == -1:
            raise HTTPException(
                status_code=400,
                detail="群组已被解散"
            )

        # 软删除群组：设置delete字段为-1
        update_result = await mongo.group_db.update_one(
            {"group_id": group_id},
            {
                "$set": {
                    "delete": -1,
                    "dismissed_at": datetime.utcnow(),
                    "update_dt": datetime.utcnow()
                }
            }
        )

        if not update_result:
            log_error(f"解散群聊失败 - 群ID: {group_id}")
            raise HTTPException(
                status_code=500,
                detail="解散群聊失败"
            )

        log_info(f"成功解散群聊 - 群ID: {group_id}")

        # 可选：发送解散通知给所有成员
        # members = group.get("members", [])
        # for member_id in members:
        #     if member_id != current_user_id:
        #         await send_notification(member_id, f"群聊 {group.get('name')} 已被群主解散")

        return BaseResponse(
            success=True,
            message="群聊已成功解散"
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"解散群聊异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"解散群聊失败: {str(e)}"
        )

class AddGroupMembersRequest(BaseModel):
    group_id: str = Field(..., description="群组ID")
    user_ids: List[int] = Field(..., description="要添加的用户ID列表")

    class Config:
        schema_extra = {
            "example": {
                "group_id": "group_123456",
                "user_ids": [1, 2, 3]
            }
        }

@router.post("/group/add-members", response_model=BaseResponse)
async def add_group_members(
        request: AddGroupMembersRequest,
        current_user_id: int = Depends(get_current_user_id),
        session: Session = Depends(get_session),
):
    """
    添加群成员
    """
    try:
        group_id = request.group_id
        user_ids = request.user_ids

        log_info(f"添加群成员 - 群ID: {group_id}, 操作者: {current_user_id}, 要添加的用户: {user_ids}")

        # 验证群组是否存在且未被删除
        group = await mongo.group_db.find_one({"group_id": group_id, "delete": 0})
        if not group:
            raise HTTPException(
                status_code=404,
                detail="群组不存在或已被解散"
            )
        crud = UserCRUD(session)

        user_info_list = []
        for user_id in user_ids:
            user = crud.get_user_by_user_id(user_id)
            if not user:
                log_error(f"用户不存在 - 用户ID: {user_id}")
                continue
            user_info_list.append(user)


        # 更新群组成员
        update_result = await mongo.group_db.update_one(
            {"group_id": group_id},
            {
                "$push": {
                    "members": {
                        "$each": user_ids  # 添加多个用户ID到members数组
                    }
                },
                "$inc": {"members_count": len(user_ids)},  # 增加成员数量
                "$set": {"update_dt": datetime.utcnow()}
            }
        )

        if not update_result:
            log_error(f"添加群成员失败 - 群ID: {group_id}")
            raise HTTPException(
                status_code=500,
                detail="添加成员失败"
            )

        log_info(f"成功添加群成员 - 群ID: {group_id}, 添加了 {len(user_info_list)} 个成员")

        # 发送通知给被添加的用户
        for user in user_info_list:
            # 这里可以添加发送通知的逻辑
            log_info(f"用户 {user.username} 被添加到群 {group_id}")


        return BaseResponse(
            success=True,
            message=f"成功添加 {len(user_info_list)} 个成员到群聊"
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"添加群成员异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"添加成员失败: {str(e)}"
        )


@router.post("/group/system-message")
async def receive_system_message(
        message_data: dict,
        current_user_id: int = Depends(get_current_user_id)
):
    """
    接收系统消息的HTTP接口
    """
    try:
        # 验证必需字段
        required_fields = ["to", "content", "from", "from_username", "action"]
        for field in required_fields:
            if field not in message_data:
                raise HTTPException(status_code=400, detail=f"缺少必需字段: {field}")

        group_id = message_data["to"]

        # 验证用户是否是群成员


        if not is_group_member(group_id, current_user_id):
            raise HTTPException(status_code=403, detail="不是群成员")

        # 验证发送者ID是否匹配当前用户
        if message_data["from"] != current_user_id:
            raise HTTPException(status_code=403, detail="发送者ID不匹配")

        # 构建完整的系统消息
        system_message = {
            "id": message_data.get("id", int(datetime.now().timestamp() * 1000)),
            "type": "system_message",
            "to": group_id,
            "content": message_data["content"],
            "from": current_user_id,
            "from_username": message_data["from_username"],
            "message_type": "system",
            "action": message_data["action"],
            "time": datetime.now().isoformat(),
            "is_system": True
        }

        log_info(f"接收系统消息: {system_message}")

        # 处理系统消息（广播、存储等）
        await mongo.group_chat_db.insert_one(system_message)

        return {
            "status": "success",
            "message": "系统消息发送成功",
            "message_id": system_message["id"],
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"处理系统消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="处理系统消息失败")

# active_connections: Dict[str, WebSocket] = {}
# async def broadcast_system_message(message: dict, group_id: str):
#     """
#     广播系统消息给所有在线群成员
#     """
#     try:
#         members = await get_group_members(group_id)
#         broadcast_count = 0
#
#         for member_id in members:
#             connection_key = f"{member_id}-{group_id}"
#             connection_key = get_websocket_connection(str(member_id), group_id)
#             active_connections[connection_key] = websocket
#             if connection_key in active_connections:
#                 try:
#                     await active_connections[connection_key].send_text(json.dumps(message))
#                     broadcast_count += 1
#                 except Exception as e:
#                     log_error(f"向用户 {member_id} 广播失败: {str(e)}")
#
#         log_info(f"系统消息广播给 {broadcast_count} 个在线成员")
#
#     except Exception as e:
#         log_error(f"广播系统消息失败: {str(e)}")


class NotificationMessage(BaseModel):
    id: str
    type: Optional[str] = None
    message_type: Optional[str] = None
    to: str
    content: str
    from_id: Optional[int] = None
    from_username: Optional[str] = None
    timestamp: Optional[int] = None
    created_at: Optional[Union[datetime, str]] = None
    action: Optional[str] = None
    is_system: Optional[bool] = None

async def is_group_member(group_id: str, user_id: int) -> bool:
    """检查用户是否是群组成员"""
    try:
        # 从group_db中查询群组信息
        group = await mongo.group_db.find_one({"group_id": group_id, "delete": 0})

        if not group:
            # 群组不存在
            return False

        # 检查members字段中是否存在该用户ID
        if user_id in group["members"]:
            return True

        return False

    except Exception as e:
        print(f"检查群组成员身份时出错: {e}")
        return False

@router.get("/group/{group_id}/system-message", response_model=List[NotificationMessage])
async def get_system_notification(
        group_id: str,
        current_user_id: int = Depends(get_current_user_id),
        limit: int = Query(100, gt=0, le=1000),  # 限制返回的消息数量，默认100条，最大1000条
        before_time: datetime = Query(None),  # 分页参数：获取某个时间之前的消息
):
    """获取群组的系统通知消息"""
    log_info(f"打印系统消息的信息： {group_id}, {current_user_id}")
    # 验证用户是否有权限访问该群组的通知
    # 首先检查用户是否是该群组的成员
    # 这里需要实现一个函数来检查用户是否是群组成员
    flag = await is_group_member(group_id, current_user_id)
    log_info(f"是否存在群： {flag}")
    if not flag:
        raise HTTPException(status_code=403, detail="您不是该群组成员，无权查看通知")

    # 构建查询条件：指定群组，系统消息类型，未删除的消息
    query = {
        "to": group_id,
        "$or": [
            {"message_type": "system"},
            {"type": "system_message"},
            {"is_system": True}
        ]
    }

    # 如果提供了before_time参数，则获取该时间之前的消息
    if before_time:
        query["time"] = {"$lt": before_time}

    # 按时间降序排序（最新消息在前）
    sort = [("time", 1)]

    # 查询数据库
    messages_list = await mongo.group_chat_db.find_many(query=query, limit=limit, sort=sort)

    log_info(f"群消息： {messages_list}")
    # 转换为前端需要的格式
    messages = []
    for msg in messages_list:
        # 处理MongoDB的_id字段
        msg["id"] = str(msg.pop("_id"))

        # 确保字段名与前端期望一致
        if "from" in msg:
            msg["from_id"] = msg["from"]

        if "time" in msg:
            msg["created_at"] = msg["time"]
        log_info(f"群消息通知： {msg}")
        messages.append(msg)
    log_info(f"群消息通知列表： {messages}")
    # 不需要反转列表，因为已经是按时间降序排列（最新消息在前）
    # 这样前端可以直接显示，最新的通知在最上面


    return messages

