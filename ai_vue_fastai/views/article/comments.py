# encoding: UTF-8
from typing import List, Optional,Dict, Any
from fastapi import HTTPException, APIRouter, Depends, Query, UploadFile, File, Form,Request
from pydantic import BaseModel
from bson import ObjectId
from init import app
from utils.mongodb import MotorDB
from utils.mysql_crud import UserCRUD
from sqlmodel import Session
from utils.database import get_session
import os
from config.settings import settings
import uuid
from datetime import datetime
from fastapi.responses import JSONResponse

# 初始化MongoDB连接
mongo = MotorDB(database="article_db")
# collection 是article
router = APIRouter(tags=["朋友圈信息"])

@app.on_event("startup")
async def startup_db_client():
    await mongo.connect()

class DetailReplyResponse(BaseModel):
    replies: List[Dict] = []

class ReplyRequest(BaseModel):
    reply_user_id: int
    reply_comment: str
    comment_id: str
    reply_user_name: str

class SuccessResponseModel(BaseModel):
    msg: str
    status_code: int

class LikeResponseModel(SuccessResponseModel):
    user_id: int
    likes_count: int
    is_liked: int

class LikeCommentRequest(BaseModel):
    comment_id: str
    user_id: int
    is_like: bool

class Stats(BaseModel):
    likes: int
    comments: int
    shares: int

class LikeReplyRequest(BaseModel):
    user_id: int
    reply_id: str
    is_like: bool

@router.post("/like_comment",response_model=LikeResponseModel)
async def like_moment(request: LikeCommentRequest):
        try:
            # 使用原子操作确保数据一致性
            update_operation = {
                "$set": {"updated_at": datetime.now().isoformat()},
                "$inc": {"stats.likes": 1 if request.is_like else -1}
            }

            # 插入到Like表中
            like_dict = {
                "comment_id": request.comment_id,
                "user_id": request.user_id,
                "type": "comment",
                "create_dt": datetime.now().isoformat(),

            }

            if request.is_like:
                update_operation["$addToSet"] = {"like_users": request.user_id}
                like_dict["is_like"] = 1
                await mongo.like_db.insert(like_dict)
            else:
                update_operation["$pull"] = {"like_users": request.user_id}
                # 取消点赞
                result = await mongo.like_db.find_one(
                    {"comment_id": request.comment_id, "user_id": request.user_id, "type": "comment"})
                await mongo.like_db.update_one({"_id": result.get("_id")}, {"$set": {"is_like": 0}})

            result = await mongo.comment_db.update_one(
                {"_id": ObjectId(request.comment_id)},
                update_operation
            )

            # 返回完整状态
            updated = await mongo.comment_db.find_one(
                {"_id": ObjectId(request.comment_id)}
            )
            likes_count = updated.get("stats", {}).get("likes", 0) if updated else 0
            return {
                "msg": "success",
                "status_code": 200,
                "user_id": request.user_id,
                "is_liked": request.is_like,
                "likes_count":likes_count
            }
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"success": False, "msg": str(e)})

class ReplyResponseModel(SuccessResponseModel):
    reply_counts: int
    reply_comment: str
    reply_user_id: int



@router.post("/reply_comment",response_model=ReplyResponseModel)
async def post_moment(request: ReplyRequest, session: Session = Depends(get_session)):
    try:
        reply_user_id = request.reply_user_id
        reply_comment = request.reply_comment
        reply_user_name = request.reply_user_name
        comment_id = request.comment_id
        created_dt = datetime.now().isoformat()
        # 验证用户
        crud = UserCRUD(session)
        user = crud.get_user_by_user_id(reply_user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="用户不存在"
            )

        # 插入回复到 comment_db
        reply_data = {
                "reply_comment": reply_comment,
                "reply_user_id": reply_user_id,
                 "reply_user_name": reply_user_name,
                 "created_dt": created_dt,
                 "is_delete": 0
        }
        # 更新article_db
        update_operation = {
            "$push": {"reply": reply_data},
            "$inc": {"stats.comments": 1}
        }

        comment_dic = await mongo.comment_db.find_one({"_id": ObjectId(comment_id)})

        user_id = comment_dic.get("comment_user_id")

        # 更新到reply表中
        reply_data["comment_id"] = str(comment_id)
        reply_data["user_id"] = user_id

        await mongo.reply_db.insert(reply_data)

        # result = await mongo.comment_db.update_one(
        #     {"_id": ObjectId(comment_id)},
        #     update_operation
        # )
        # 获取更新后的文章信息
        updated = await mongo.comment_db.find_one(
            {"_id": ObjectId(comment_id)}
        )
        comments_count = updated.get("stats", {}).get("comments", 0) if updated else 0
        return {
            "msg": "success",
            "status_code": 200,
            "reply_user_id": reply_user_id,
            "reply_comment": reply_comment,
            "reply_counts": comments_count
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "msg": str(e)}
        )
class DeleteCommentRequest(BaseModel):
    comment_id: str

@router.post("/delete/comment", response_model=SuccessResponseModel)
async def delete_moment(
    request: DeleteCommentRequest,
    session: Session = Depends(get_session),
):
    try:
        # 将 moment_id 转换为 ObjectId 类型
        moment_object_id = ObjectId(request.comment_id)

        # 更新动态文档，将 is_delete 字段设置为 -1
        result = await mongo.comment_db.update_one(
            {"_id": moment_object_id},
            {"$set": {"is_delete": -1, "updated_at": datetime.now().isoformat()}}
        )
        if result == 0:
            raise HTTPException(
                status_code=404,
                detail="未找到该动态"
            )

        result = {
            "msg": "success",
            "status_code": 200
        }
        return result

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="无效的动态 ID"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )

class DeleteReplyRequest(BaseModel):
    reply_id: str

@router.post("/delete/reply", response_model=SuccessResponseModel)
async def delete_reply(
    request: DeleteReplyRequest,
    session: Session = Depends(get_session),
):
    try:
        # 将 moment_id 转换为 ObjectId 类型

        obj_reply_id = ObjectId(request.reply_id)

        # 更新动态文档，将 is_delete 字段设置为 -1
        result = await mongo.reply_db.update_one(
            {"_id": obj_reply_id},
            {"$set": {"is_delete": -1, "updated_at": datetime.now().isoformat()}}
        )
        if result == 0:
            raise HTTPException(
                status_code=404,
                detail="未找到该动态"
            )

        result = {
            "msg": "success",
            "status_code": 200
        }
        return result

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="无效的动态 ID"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )

# 点赞评论的评论
@router.post("/like_reply",response_model=LikeResponseModel)
async def like_reply(request: LikeReplyRequest):
        try:
            # 使用原子操作确保数据一致性
            update_operation = {
                "$set": {"updated_at": datetime.now().isoformat()},
                "$inc": {"stats.likes": 1 if request.is_like else -1}
            }

            # 插入到Like表中
            like_dict = {
                "reply_id": request.reply_id,
                "user_id": request.user_id,
                "type": "reply",
                "create_dt": datetime.now().isoformat(),

            }

            if request.is_like:
                update_operation["$addToSet"] = {"like_users": request.user_id}
                like_dict["is_like"] = 1
                await mongo.like_db.insert(like_dict)
            else:
                update_operation["$pull"] = {"like_users": request.user_id}
                # 取消点赞
                result = await mongo.like_db.find_one(
                    {"reply_id": request.reply_id, "user_id": request.user_id, "type": "reply"})
                await mongo.like_db.update_one({"_id": result.get("_id")}, {"$set": {"is_like": 0}})

            result = await mongo.reply_db.update_one(
                {"_id": ObjectId(request.reply_id)},
                update_operation
            )

            # 返回完整状态
            updated = await mongo.reply_db.find_one(
                {"_id": ObjectId(request.reply_id)}
            )
            likes_count = updated.get("stats", {}).get("likes", 0) if updated else 0
            return {
                "msg": "success",
                "status_code": 200,
                "user_id": request.user_id,
                "is_liked": request.is_like,
                "likes_count":likes_count
            }
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"success": False, "msg": str(e)})
