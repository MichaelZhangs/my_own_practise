# auth_router.py
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel
from config.settings import settings
from utils.redis import set_code, get_code, set_userinfo_to_redis
from utils.log import log_info, log_error
from utils.database import get_session
from utils.mysql_model import User, UserCreate, Token,UserRegisterDict
from utils.mysql_crud import UserCRUD
from sqlmodel import Session
import random
import json

router = APIRouter()


class UserRegisterRequest(BaseModel):
    username: str
    phone: str
    password: str


class SendCodeRequest(BaseModel):
    phone: str


class LoginRequest(BaseModel):
    phone: str
    password: str


class SendVerificationCodeRequest(BaseModel):
    identifier: str
    newPassword: str

def create_access_token(data: dict, expires_minutes: int) -> str:
    """
    创建访问令牌
    :param data: 要编码的数据
    :param expires_minutes: 过期时间(分钟)
    :return: JWT令牌字符串
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


@router.post("/register", response_model=UserRegisterDict)
async def register(
        request: UserRegisterRequest,
        session: Session = Depends(get_session)
):
    try:
        crud = UserCRUD(session)

        # 检查手机号是否已存在
        if crud.user_exists(request.phone):
            raise HTTPException(status_code=400, detail="手机号已存在")

        # 创建用户
        user = crud.create_user(UserCreate(
            username=request.username,
            phone=request.phone,
            password=request.password
        ))

        log_info(f"用户注册成功: username={request.username}, phone={request.phone}")
        log_info(f"{user}")
        userdict = {
            "username": user.username,
            "phone": user.phone,
            "password": user.password
        }
        user_info = {
            "username": user.username or "",
            "phone": user.phone,
            "id": user.id,
            "email": user.email or "",
            "photo": user.photo or ""
        }
        set_userinfo_to_redis(f"{user.id}_info", json.dumps(user_info))
        return {"message": "注册成功", "user":userdict}
    except HTTPException as e:
        raise e
    except Exception as e:
        log_error(f"注册失败: {str(e)}")
        raise HTTPException(status_code=500, detail="注册失败")


@router.post("/check-user")
async def check_user(
        request: SendCodeRequest,
        session: Session = Depends(get_session)
):
    try:
        crud = UserCRUD(session)
        exists = crud.user_exists(request.phone)
        return {"exists": exists}
    except Exception as e:
        log_error(f"检查用户失败: {str(e)}")
        raise HTTPException(status_code=500, detail="检查用户失败")


@router.post("/send-code")
async def send_code(request: SendCodeRequest):
    phone = request.phone
    code = str(random.randint(100000, 999999))
    set_code(phone, code)
    log_info(f"发送验证码: phone={phone}, code={code}")
    print(f"发送验证码: phone={phone}, code={code}")
    return {"code": code}


@router.post("/login", response_model=Token)
async def login(
        request: LoginRequest,
        session: Session = Depends(get_session)
):
    try:
        crud = UserCRUD(session)

        # 检查验证码
        stored_code = get_code(request.phone)
        if not stored_code or stored_code != request.password:
            raise HTTPException(status_code=400, detail="验证码错误")

        # 检查用户是否存在
        user = crud.get_user_by_phone(request.phone)
        # print(f"user: {user.username}, {user.phone}")
        if not user:
            # 自动注册
            user = crud.create_user(UserCreate(
                username=request.phone,
                phone=request.phone,
                password=""
            ))

        # 生成令牌 - 直接传递分钟数
        access_token = create_access_token(
            data={"sub": user.username},
            expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

        user_dic = {
                "username": user.username,
                "phone": user.phone,
                "id": user.id,
                "photo": user.photo
                # "email": user["email"],
            }
        user_info = {
                "username": user.username,
                "phone": user.phone,
                "id": user.id,
                "photo": user.photo,
                "email": user.email or "",
            }

        set_userinfo_to_redis(f"{user.id}_info", json.dumps(user_info))
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_dic,
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        log_error(f"登录失败: {str(e)}")
        raise HTTPException(status_code=500, detail="登录失败")


@router.post("/password-login", response_model=Token)
async def password_login(
        request: LoginRequest,
        session: Session = Depends(get_session)
):
    try:
        crud = UserCRUD(session)

        # 检查用户是否存在
        user = crud.get_user_by_phone(request.phone)
        if not user:
            raise HTTPException(status_code=400, detail="用户不存在")

        # 检查密码
        if user.password != request.password:
            raise HTTPException(status_code=400, detail="密码错误")

        # 生成 Token
        access_token = create_access_token(
            data={"sub": user.username},
            expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        user_info = {
                "username": user.username,
                "phone": user.phone,
                "email": user.email,
                "id": user.id,
                "photo": user.photo
        }
        # 关键信息持久存储到redis
        set_userinfo_to_redis(f"{user.id}_info", json.dumps(user_info))

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "username": user.username,
                "phone": user.phone,
                "email": user.email,
                "id": user.id
            },
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        log_error(f"密码登录失败: {str(e)}")
        raise HTTPException(status_code=500, detail="密码登录失败")


@router.post("/send-verification-code")
async def send_verification_code(
        request: SendVerificationCodeRequest,
        session: Session = Depends(get_session)
):
    try:
        crud = UserCRUD(session)

        # 检查用户是否存在
        user = crud.get_user_by_phone(request.identifier) or \
               crud.get_user_by_email(request.identifier)
        if not user:
            raise HTTPException(status_code=400, detail="用户不存在")

        # 生成并存储验证码
        code = str(random.randint(100000, 999999))
        set_code(request.identifier, code)
        log_info(f"发送验证码: identifier={request.identifier}, code={code}")
        return {"code": code}
    except HTTPException as e:
        raise e
    except Exception as e:
        log_error(f"发送验证码失败: {str(e)}")
        raise HTTPException(status_code=500, detail="发送验证码失败")