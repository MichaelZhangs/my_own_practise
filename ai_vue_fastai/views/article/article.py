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
from utils.log import log_info
# 初始化MongoDB连接
mongo = MotorDB(database="article_db")
# collection 是article
router = APIRouter(tags=["朋友圈信息"])



@app.on_event("startup")
async def startup_db_client():
    await mongo.connect()


# 数据模型
class MediaItem(BaseModel):
    type: str  # 'image' or 'video'
    url: str

class CreateMomentRequest(BaseModel):
    content: str
    media: List[MediaItem] = []
    user_id: int
    visibility: str = "public"

class Like(BaseModel):
    user_id: str
    created_at: datetime

class Stats(BaseModel):
    likes: int
    comments: int
    shares: int

class UserInfo(BaseModel):
    username: str
    photo: Optional[str] = None

class LikeMomentRequest(BaseModel):
    moment_id: str
    user_id: int
    is_like: bool  # 1 表示点赞， -1 表示取消点赞

class MomentResponse(BaseModel):
    id: str
    user_id: int
    content: str
    media: List[MediaItem]
    stats: Optional[Stats] = None
    visibility: Optional[str] = None
    is_delete: int
    like_users: List[int] = []
    user: UserInfo
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class DetailMomentResponse(MomentResponse):
    comments: List[Dict] = []
    like_users: List[int] = []
    stats: Optional[Stats] = None

class DeleteMomentRequest(BaseModel):
    moment_id: str

class SuccessResponseModel(BaseModel):
    msg: str
    status_code: int

class LikeResponseModel(SuccessResponseModel):
    user_id: int
    likes_count: int
    is_liked: bool

class CommentResponseMode(SuccessResponseModel):
    comments_count: int
    comment: str
    comment_user_name: str
    comment_user_id: int

class CommentRequest(BaseModel):
    comment_user_id: int
    comment: str
    moment_id: str
    comment_user_name: str


@router.post("/moments", response_model=SuccessResponseModel)
async def create_moment(
    request: CreateMomentRequest,
    session: Session = Depends(get_session)
):
    # 验证用户
    crud = UserCRUD(session)
    user = crud.get_user_by_user_id(request.user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="用户不存在"
        )

    # 验证media数据结构
    # 自动通过Pydantic验证media结构
    media_data = [item.dict() for item in request.media]
    # 构建用户信息
    user_dict = {
        "username": user.username,
        "photo": user.photo
    }

    # 创建动态文档
    moment_data = {
        "user_id": request.user_id,
        "content": request.content,
        "media": media_data,
        "like_users":[],
        "stats": {
            "likes": 0,
            "comments": 0,
            "shares": 0
        },
        "visibility": request.visibility,
        "is_delete": 0,
        "user": user_dict,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    try:
        # 插入数据库
        inserted_id = await mongo.article_db.insert(moment_data)
        if not inserted_id:
            raise HTTPException(
                status_code=400,
                detail="动态创建失败"
            )
        result = {
            "msg": "success",
            "status_code": 200
        }

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )


@router.get("/moments", response_model=List[DetailMomentResponse])
async def get_moments(
        last_id: Optional[str] = Query(None),
        limit: int = Query(10, gt=0, le=50),
        session: Session = Depends(get_session)
):
    try:
        query = {"is_delete": 0}
        if last_id:
            # 确保 last_id 是有效的 ObjectId
            if not ObjectId.is_valid(last_id):
                raise HTTPException(status_code=400, detail="无效的last_id格式")

            last_moment = await mongo.article_db.find_one({"_id": ObjectId(last_id)})
            if not last_moment:
                raise HTTPException(status_code=400, detail="无效的last_id")
            query["created_at"] = {"$lt": last_moment["created_at"]}
        sort = [("created_at", -1)]

        moments = await mongo.article_db.find_many(
            query=query,
            sort=sort,
            limit=limit
        )

        crud = UserCRUD(session)
        moments_list = []
        for moment in moments:
            user = crud.get_user_by_user_id(moment["user_id"])
            if user:
                user_dict = {
                    "username": user.username,
                    "photo": user.photo
                }
                moment["user"] = user_dict
            else:
                moment["user"] = {
                    "username": "未知用户",
                    "photo": ""
                }
            moment["id"] = str(moment.pop("_id"))
            log_info(f"moment: {moment}")
            moments_list.append(moment)
        return moments_list

    except TypeError as e:
        raise HTTPException(status_code=400, detail=f"参数类型错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")

@router.post("/upload/media")
async def upload_media(file: UploadFile = File(...)):
    try:
        # 允许的文件类型检查
        allowed_types = (
                settings.ALLOWED_IMAGE_TYPES +
                settings.ALLOWED_VIDEO_TYPES +
                settings.ALLOWED_AUDIO_TYPES +
                settings.ALLOWED_FILE_TYPES  # 需要在settings.py中添加这个配置
        )

        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型，仅支持: {allowed_types}"
            )
        base_media_dir = settings.ARTICLE_MEDIA
            # 创建对应的存储目录
        # 创建子目录
        # sub_dir = "images" if file.content_type in ALLOWED_IMAGE_TYPES else "videos"
        # 确定文件存储子目录
        if 'image' in file.content_type:
            sub_dir = 'images'
        elif 'video' in file.content_type:
            sub_dir = 'videos'
        elif 'audio' in file.content_type:
            sub_dir = 'audios'
        else:
            sub_dir = 'files'  # 其他文件类型

        media_dir =f"{base_media_dir}/{sub_dir}"

        os.makedirs(media_dir, exist_ok=True)


        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d")
        unique_id = uuid.uuid4().hex[:4]
        file_extension = file.filename.split('.')[-1]
        file_name = f"media_{timestamp}_{unique_id}.{file_extension}"
        file_path = os.path.join(media_dir, file_name) # 使用Path对象拼接路径

        # 保存文件
        with open(file_path, "wb") as f:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                f.write(content)

        # 返回访问URL
        # media_url = f"/{settings.ARTICLE_MEDIA}/{'images' if file.content_type in settings.ALLOWED_IMAGE_TYPES else 'videos'}/{file_name}"

        if 'image' in file.content_type:
            media_url = f"/{settings.ARTICLE_MEDIA}/images/{file_name}"
        elif 'video' in file.content_type:
            media_url = f"/{settings.ARTICLE_MEDIA}/videos/{file_name}"
        elif 'audio' in file.content_type:
            media_url = f"/{settings.ARTICLE_MEDIA}/audios/{file_name}"
        else:
            media_url = f"/{settings.ARTICLE_MEDIA}/text/{file_name}"

        print(f"media_url: {media_url}")
        return JSONResponse({
            "success": True,
            "url": media_url,
            "type": file.content_type.split('/')[0],  # 'image' or 'video'
            "message": "文件上传成功"
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/delete/moment", response_model=SuccessResponseModel)
async def delete_moment(
    request: DeleteMomentRequest,
    session: Session = Depends(get_session),
):
    try:
        # 将 moment_id 转换为 ObjectId 类型
        moment_object_id = ObjectId(request.moment_id)
        # 更新动态文档，将 is_delete 字段设置为 -1
        result = await mongo.article_db.update_one(
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


@router.post("/like_moment",response_model=LikeResponseModel)
async def like_moment(request: LikeMomentRequest):
    try:
        # 使用原子操作确保数据一致性
        update_operation = {
            "$set": {"updated_at": datetime.now().isoformat()},
            "$inc": {"stats.likes": 1 if request.is_like else -1}
        }

        # 插入到Like表中
        like_dict = {
            "moment_id": request.moment_id,
            "user_id": request.user_id,
            "type": "moment",
            "create_dt": datetime.now().isoformat(),

        }
        # 先查看点赞表中是否存在：
        # like_result = await mongo.like_db.find_one(
        #     {"moment_id": request.moment_id, "user_id": request.user_id}
        # )
        # is_like = 0
        # if like_result:
        #     is_like = like_result.get("is_like")
        if request.is_like :
            update_operation["$addToSet"] = {"like_users": request.user_id}
            like_dict["is_like"] = 1
            await mongo.like_db.insert(like_dict)
        else:
            update_operation["$pull"] = {"like_users": request.user_id}
            #取消点赞
            result =  await mongo.like_db.find_one({"moment_id": request.moment_id, "user_id":request.user_id, "type": "moment"})
            await mongo.like_db.update_one({"_id": result.get("_id")}, {"$set": {"is_like": 0}})




        result = await mongo.article_db.update_one(
            {"_id": ObjectId(request.moment_id)},
            update_operation
        )

        # 返回完整状态
        updated = await mongo.article_db.find_one(
            {"_id": ObjectId(request.moment_id)}
        )
        return {
            "msg": "success",
            "status_code": 200,
            "user_id": request.user_id,
            "is_liked": request.is_like,
            "likes_count": updated["stats"]["likes"]
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "msg": str(e)}
        )

@router.post("/post_comment",response_model=CommentResponseMode)
async def post_moment(request: CommentRequest, session: Session = Depends(get_session)):
    try:
        comment_user_id = request.comment_user_id
        comment = request.comment
        moment_id = request.moment_id
        comment_user_name = request.comment_user_name
        created_dt = datetime.now().isoformat()
        # 验证用户
        crud = UserCRUD(session)
        user = crud.get_user_by_user_id(comment_user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="用户不存在"
            )

        # 插入评论到 comment_db
        comment_data = {
            "moment_id": moment_id,
            "comment": comment,
            "created_at": created_dt,
            "comment_user_name": user.username,
            "is_delete": 0,
            "like_users":[],
            "stats": {
                "likes": 0,
                "comments": 0,
                "shares": 0
            },
            "comment_user_id": comment_user_id
        }
        await mongo.comment_db.insert(comment_data)

        # 更新article_db
        update_operation = {
            "$inc": {"stats.comments": 1}
        }
        # 处理update_operation：
        # update_operation["$push"]["comments"]["comment_id"] = str(update_operation["$push"]["comments"].pop("_id"))
        # 评论内容容不放在 文章 里面
        result = await mongo.article_db.update_one(
            {"_id": ObjectId(moment_id)},
            update_operation
        )
        # 获取更新后的文章信息
        updated = await mongo.article_db.find_one(
            {"_id": ObjectId(moment_id)}
        )
        return {
            "msg": "success",
            "status_code": 200,
            "comment_user_id": comment_user_id,
            "comment_user_name": comment_user_name,
            "comment": comment,
            "comments_count": updated["stats"]["comments"]
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "msg": str(e)}
        )


@router.get("/moment", response_model=DetailMomentResponse)
async def get_moment_by_id(
        moment_id: str = Query(..., description="动态的唯一标识ID"),
        session: Session = Depends(get_session)
):
    """
    通过moment_id获取单个动态详情
    """
    try:
        # 验证moment_id格式
        if not ObjectId.is_valid(moment_id):
            raise HTTPException(status_code=400, detail="无效的moment_id格式")
        # 转换ObjectId
        obj_id = ObjectId(moment_id)
        crud = UserCRUD(session)
        # 查询数据库
        moment = await mongo.article_db.find_one({"_id": obj_id, "is_delete": 0})
        if not moment:
            raise HTTPException(status_code=404, detail="动态不存在")
        #加上user的信息，因为user有可能会更新
        # 先获取user_id
        user_id = moment.get("user_id")
        user_dic = crud.get_user_by_user_id(user_id) or {}
        log_info(f"user_dic = {user_dic}")
        user = {
            "username": user_dic.username,
            "photo": user_dic.photo
        }
        moment["user"] = user
        #查找comment的评论
        comments = await mongo.comment_db.find_many({"moment_id": moment_id, "is_delete": {"$ne": -1}})

        # 处理ObjecID
        if comments:
           comments = [{**{k: str(v) if k == '_id' else v for k, v in comment.items()}, 'comment_id': str(comment['_id'])} for comment in comments]


        for comment in comments:
            # 用户名称从数据库取
            user = crud.get_user_by_user_id(comment.get("comment_user_id"))
            comment["comment_user_name"] = user.username
            comment["comment_user_photo"] = user.photo
            # 获取reply
            comment_id = str(comment.get("_id"))
            reply = await mongo.reply_db.find_many({"comment_id": comment_id, "is_delete": 0}) or []
            # reply = comment.get("reply") or []
            for r in reply:
                r["_id"] = str(r.get("_id"))
                reply_user_id = r.get("reply_user_id")
                reply_user = crud.get_user_by_user_id(reply_user_id) or {}
                r["reply_user_photo"] = reply_user.photo
            comment["reply"] = reply

        moment["comments"] = comments
        moment["id"] = str(moment.pop("_id"))

        return moment

    except HTTPException as he:
        raise he  # 传递已处理的HTTP异常
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")

# 获取我喜欢的内容
@router.get("/liked_moments", response_model=List[DetailMomentResponse])
async def get_liked_moments(
        user_id: int = Query(...),  # 新增user_id参数，必需项
        last_id: Optional[str] = Query(None),
        limit: int = Query(10, gt=0, le=50),
        session: Session = Depends(get_session)
):
    try:
        # 构建点赞查询条件
        like_query = {
            "user_id": user_id,
            "type": "moment"  # 限定类型为moment
        }
        # 如果有last_id，添加时间限制条件
        if last_id:
            # 确保last_id是有效的ObjectId
            if not ObjectId.is_valid(last_id):
                raise HTTPException(status_code=400, detail="无效的last_id格式")

            last_like = await mongo.like_db.find_one({"_id": ObjectId(last_id)})
            if not last_like:
                raise HTTPException(status_code=400, detail="无效的last_id")
            like_query["create_dt"] = {"$lt": last_like["create_dt"]}
        # 从点赞表中查询用户点赞的动态ID
        # 按创建时间倒序排列，获取最新的点赞记录
        like_records = await mongo.like_db.find_many(
            query=like_query,
            sort=[("create_dt", -1)],
            limit=limit,
            projection={"moment_id": 1, "create_dt": 1}  # 只需要target_id和created_at字段
        )
        # 提取所有动态ID
        moment_ids = [ObjectId(record["moment_id"]) for record in like_records]
        if not moment_ids:
            return []  # 如果没有找到点赞记录，直接返回空列表

        # 从文章表中查询这些动态的详细信息
        # 使用$in操作符查询多个ID
        # 按点赞时间倒序排列，保持与点赞记录一致的顺序
        moments = await mongo.article_db.find_many(
            query={"_id": {"$in": moment_ids},"is_delete": 0},
            limit=limit,
            sort=[("created_at", -1)]
        )
        crud = UserCRUD(session)
        moments_list = []
        # 处理每个动态，添加用户信息
        for moment in moments:
            user_id = moment.get("user_id")
            user_dic = crud.get_user_by_user_id(user_id) or {}
            if user_dic:
                user_dict = {
                    "username": user_dic.username,
                    "photo": user_dic.photo,
                    "user_id": moment["user_id"]
                }
                moment["user"] = user_dict
            else:
                moment["user"] = {
                    "username": "未知用户",
                    "photo": "",
                    "user_id": moment["user_id"]
                }
            moment["id"] = str(moment.pop("_id"))
            moments_list.append(moment)

            # 查找对应的点赞记录，获取点赞时间
            # like_record = next((r for r in like_records if r["target_id"] == str(moment["_id"])), None)
            # if like_record:
            #     moment["liked_at"] = like_record["created_at"]  # 添加点赞时间信息

        return moments_list
    except TypeError as e:
        raise HTTPException(status_code=400, detail=f"参数类型错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")

# 我发布的
@router.get("/user_moments", response_model=List[DetailMomentResponse])
async def get_user_moments(
        user_id: int = Query(...),  # 新增user_id参数，必需项
        last_id: Optional[str] = Query(None),
        limit: int = Query(10, gt=0, le=50),
        session: Session = Depends(get_session)
):
    try:
        query = {"user_id":user_id, "is_delete": 0}
        if last_id:
            # 确保 last_id 是有效的 ObjectId
            if not ObjectId.is_valid(last_id):
                raise HTTPException(status_code=400, detail="无效的last_id格式")

            last_moment = await mongo.article_db.find_one({"_id": ObjectId(last_id)})
            if not last_moment:
                raise HTTPException(status_code=400, detail="无效的last_id")
            query["created_at"] = {"$lt": last_moment["created_at"]}
        sort = [("created_at", -1)]

        moments = await mongo.article_db.find_many(
            query=query,
            sort=sort,
            limit=limit
        )

        crud = UserCRUD(session)
        moments_list = []
        for moment in moments:
            user = crud.get_user_by_user_id(moment["user_id"])
            if user:
                user_dict = {
                    "username": user.username,
                    "photo": user.photo
                }
                moment["user"] = user_dict
            else:
                moment["user"] = {
                    "username": "未知用户",
                    "photo": ""
                }
            moment["id"] = str(moment.pop("_id"))

            moments_list.append(moment)
        return moments_list
    except TypeError as e:
        raise HTTPException(status_code=400, detail=f"参数类型错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")
