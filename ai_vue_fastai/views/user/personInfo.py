from fastapi import APIRouter, Depends, HTTPException, UploadFile, File,Query
from pydantic import BaseModel,Field
from typing import Optional
from typing import List
import base64
import os
from config.settings import settings
from utils.log import log_info, log_error
from utils.mysql import MysqlBaseModel
from enum import Enum
import qrcode
from io import BytesIO
import random
import os
from PIL import Image
import requests
from typing import Optional

router = APIRouter( tags=["用户信息"])

# # 配置静态文件目录
# STATIC_DIR = "static"
# os.makedirs(STATIC_DIR, exist_ok=True)


class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"

class UserInfo(BaseModel):
    username: str
    phone: str
    email: str
    sex: Gender
    description: str
    qrcode: str
    photo: str

class SaveQrcodeRequest(BaseModel):
    phone: str
    qrcode: str

class SaveAvatarRequest(BaseModel):
    phone: str
    photo: str


class UpdateUserInfoRequest(BaseModel):
    phone: str
    username: str
    email: Optional[str]
    sex: Gender  # 使用枚举类型
    description: Optional[str]


class UpdatePhoneRequest(BaseModel):
    new_phone: str
    verification_code: str

class UserList(BaseModel):
    id: int
    username: str
    phone: str
    sex: Gender  # 使用枚举类型
    photo: str

class PagedResponse(BaseModel):
    data: List[UserList]
    total: int
    page: int
    page_size: int


# 临时存储验证码（生产环境应使用Redis）
sms_codes = {}

@router.get("/get-users", response_model=PagedResponse)
async def get_users(
    username: Optional[str] = Query(None, description="用户名（模糊匹配）"),
    phone: Optional[str] = Query(None, description="手机号（模糊匹配）"),
    sex: Optional[str] = Query(None, description="性别（male/female/other）"),
    page: int = Query(1, description="当前页码", ge=1),  # 页码从 1 开始
    page_size: int = Query(10, description="每页数据量", ge=1, le=100),  # 每页最多 100 条
):
    try:
        model = MysqlBaseModel()

        # 构建查询条件
        where = {}
        if username:
            where["username LIKE"] = f"%{username}%"  # 注意键包含 LIKE
        if phone:
            where["phone LIKE"] = f"%{phone}%"  # 注意键包含 LIKE
        if sex:
            where["sex"] = sex  # 普通条件

        # 获取总数据量
        total_count = len(model.select("users", where))  # 使用 select 方法获取总数据量

        # 计算分页偏移量
        offset = (page - 1) * page_size

        # 获取分页数据
        users = model.select("users", where, limit=page_size, offset=offset)
        print(f"数据库查询结果: {users}")  # 打印查询结果

        if not users:
            raise HTTPException(status_code=404, detail="没有用户数据")

        # 格式化返回数据
        user_list = []
        for user in users:
            user_list.append({
                "id": user.get("id"),
                "username": user.get("username"),
                "phone": user.get("phone"),
                "sex": user.get("sex", "male") or 'other',
                "photo": user.get("photo", "") or '',
            })

        # 返回分页数据和总数据量
        return {
            "data": user_list,
            "total": total_count,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        log_error(f"获取用户列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户列表失败")

@router.get("/info", response_model=UserInfo)
async def get_user_info(phone: str):
    try:
        model = MysqlBaseModel()
        user = model.select("users", {"phone": phone})
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        user = user[0]
        return {
            "username": user["username"],
            "phone": user["phone"],
            "email": user.get("email", "") or '',
            "sex": user.get("sex", "mail"),
            "description": user.get("description", "") or '',
            "qrcode": user.get("qrcode", "") or '',
            "photo": user.get("photo","") or ''
        }
    except Exception as e:
        log_error(f"获取用户信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户信息失败")


@router.put("/info")
async def update_user_info(request: UpdateUserInfoRequest):
    try:
        model = MysqlBaseModel()
        # 验证用户存在性
        user = model.select("users", {"phone": request.phone})
        print(f"request: {request.dict()}" )
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 构造更新数据
        update_data = {}
        if request.username:
            update_data["username"] = request.username
        if request.email:  # 仅当 email 不为空时更新
            update_data["email"] = request.email
        if request.sex:
            update_data["sex"] = request.sex
        if request.description:
            update_data["description"] = request.description

        # update_data.pop("phone")  # 移除phone字段，不作为更新内容

        model.update(
            table_name="users",
            where={"phone": request.phone},  # 使用phone作为查询条件
            data=update_data
        )
        return {"message": "更新成功", "code": 200}
    except Exception as e:
        log_error(f"更新失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

#保存二维码
@router.post("/save-qrcode")
async def save_qrcode(request: SaveQrcodeRequest):
    try:
        # 解码Base64图片数据
        phone = request.phone
        qrcode = request.qrcode
        image_data = base64.b64decode(qrcode.split(",")[1])
        # 确保二维码目录存在，如果不存在则创建
        os.makedirs(settings.QRCODE_DIR, exist_ok=True)
        # 保存文件
        file_name = f"qrcode_{phone}.png"
        file_path = os.path.join(settings.QRCODE_DIR, file_name)
        with open(file_path, "wb") as f:
            f.write(image_data)

        # 将二维码路径保存到数据库
        qrcode_url = f"/{settings.QRCODE_DIR}/{file_name}"  # 生成访问路径
        model = MysqlBaseModel()
        model.update(
            table_name="users",
            where={"phone": phone},  # 使用phone作为查询条件
            data={"qrcode": qrcode_url}  # 更新qrcode字段
        )

        return {"message": "二维码保存成功", "file_path": file_path, "qrcode_url": qrcode_url}
    except Exception as e:
        log_error(f"二维码保存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"二维码保存失败: {str(e)}")

@router.post("/update-phone")
async def update_phone(request: UpdatePhoneRequest):
    try:
        # 验证短信验证码
        if sms_codes.get(request.new_phone) != request.verification_code:
            raise HTTPException(status_code=400, detail="验证码错误或已过期")

        model = MysqlBaseModel()
        model.update("users", {"phone": request.old_phone}, {"phone": request.new_phone})

        del sms_codes[request.new_phone]
        return {"message": "手机号更新成功"}
    except Exception as e:
        log_error(f"更新手机号失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新手机号失败")


@router.post("/send-sms")
async def send_sms_code(phone: str):
    try:
        # 生成6位随机验证码
        code = str(random.randint(100000, 999999))
        sms_codes[phone] = code

        # TODO: 调用实际短信服务
        print(f"发送短信验证码到 {phone}: {code}")
        return {"message": "验证码已发送"}
    except Exception as e:
        log_error(f"发送短信失败: {str(e)}")
        raise HTTPException(status_code=500, detail="发送短信失败")

# 前端做
# @router.post("/generate-qrcode")
# async def generate_qrcode(request: GenerateQrCodeRequest):
#     try:
#         # 下载用户头像
#         avatar_response = requests.get(request.avatar_url)
#         avatar = Image.open(BytesIO(avatar_response.content))
#
#         # 生成二维码
#         qr = qrcode.QRCode(
#             version=5,
#             error_correction=qrcode.constants.ERROR_CORRECT_H,
#             box_size=10,
#             border=2,
#         )
#         qr.add_data(f"USER:{request.username}|PHONE:{request.phone}")
#         qr.make(fit=True)
#
#         # 创建带logo的二维码
#         qr_img = qr.make_image(fill_color="#07c160", back_color="white").convert('RGB')
#
#         # 添加头像
#         avatar_size = 120  # 二维码尺寸的1/4
#         avatar = avatar.resize((avatar_size, avatar_size))
#         pos = ((qr_img.size[0] - avatar_size) // 2, (qr_img.size[1] - avatar_size) // 2)
#         qr_img.paste(avatar, pos)
#
#         # 保存文件
#         filename = f"qr-{request.phone}-{random.randint(1000, 9999)}.png"
#         save_path = os.path.join(STATIC_DIR, filename)
#         qr_img.save(save_path)
#
#         # 更新数据库
#         qr_url = f"{settings.server_host}/static/{filename}"
#         model = MysqlBaseModel()
#         model.update("users", {"phone": request.phone}, {"qrcode": qr_url})
#
#         return {"qrcode_url": qr_url}
#     except Exception as e:
#         log_error(f"生成二维码失败: {str(e)}")
#         raise HTTPException(status_code=500, detail="生成二维码失败")

@router.post("/upload-avatar")
async def upload_avatar(request: SaveAvatarRequest):
    try:
        # 检查用户是否存在
        phone = request.phone
        avatar = request.photo
        print(f"/upload-avatar : {phone}")

        model = MysqlBaseModel()
        user = model.select("users", {"phone": phone})
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 解码 Base64 图片数据
        image_data = base64.b64decode(avatar.split(",")[1])

        # 确保头像目录存在，如果不存在则创建
        os.makedirs(settings.AVATAR_DIR, exist_ok=True)

        # 生成文件名
        filename = f"ph_{phone}.png"
        save_path = os.path.join(settings.AVATAR_DIR, filename)

        # 保存图片到本地
        with open(save_path, "wb") as f:
            f.write(image_data)

        # 将头像路径保存到数据库
        avatar_url = f"/{settings.AVATAR_DIR}/{filename}"  # 生成访问路径
        model.update(
            table_name="users",
            where={"phone": phone},
            data={"photo": avatar_url}  # 更新 photo 字段
        )

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