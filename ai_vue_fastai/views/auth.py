from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel
from config.settings import settings
from utils.redis import set_code, get_code
from utils.log import log_info, log_error
from utils.mysql import MysqlBaseModel
import random

router = APIRouter()

# 用户注册模型
class UserRegister(BaseModel):
    username: str
    phone: str
    password: str

# 发送验证码请求模型
class SendCodeRequest(BaseModel):
    phone: str

# 登录请求模型
class LoginRequest(BaseModel):
    phone: str
    password: str

# 重置密码的校验码
class SendVerificationCodeRequest(BaseModel):
    identifier: str
    newPassword: str


# 生成 Token
def create_access_token(data: dict, expires_delta: int):
    to_encode = data.copy()
    expire = timedelta(minutes=expires_delta)
    to_encode.update({"exp": datetime.utcnow() + expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# 注册用户（仅校验手机号）
def register_user(username: str, phone: str, password: str):
    """
    注册用户函数
    :param username: 用户名
    :param phone: 手机号
    :param password: 密码
    :return: 注册成功的用户信息
    """
    try:
        model = MysqlBaseModel()

        # 检查手机号是否已存在
        user_by_phone = model.select("users", {"phone": phone})
        if user_by_phone:
            raise HTTPException(status_code=400, detail="手机号已存在")

        # 插入新用户
        model.insert("users", {
            "username": username,
            "phone": phone,
            "password": password,
        })

        log_info(f"用户注册成功: username={username}, phone={phone}")
        return {
            "username": username,
            "phone": phone,
            "password": password,
        }
    except HTTPException as e:
        raise e  # 直接抛出 HTTPException
    except Exception as e:
        log_error(f"注册用户失败: {str(e)}")
        raise HTTPException(status_code=500, detail="注册失败")

# 注册接口
@router.post("/register")
async def register(request: UserRegister):
    """
    用户注册接口
    :param request: 用户注册请求模型
    :return: 注册成功的用户信息
    """
    try:
        user = register_user(
            username=request.username,
            phone=request.phone,
            password=request.password
        )
        return {"message": "注册成功", "user": user}
    except HTTPException as e:
        raise e
    except Exception as e:
        log_error(f"注册接口失败: {str(e)}")
        raise HTTPException(status_code=500, detail="注册接口失败")

@router.post("/check-user")
async def check_user(request: SendCodeRequest):
    phone = request.phone
    try:
        model = MysqlBaseModel()
        user = model.select("users", {"phone": phone})
        return {"exists": user is not None}
    except Exception as e:
        log_error(f"检查用户失败: {str(e)}")
        raise HTTPException(status_code=500, detail="检查用户失败")

# 发送验证码
@router.post("/send-code")
async def send_code(request: SendCodeRequest):
    phone = request.phone
    code = str(random.randint(100000, 999999))  # 生成 6 位随机验证码
    set_code(phone, code)  # 存储验证码到 Redis
    log_info(f"发送验证码: phone={phone}, code={code}")
    return {"code": code}

@router.post("/login")
async def login(request: LoginRequest):
    phone = request.phone
    password = request.password
    print(f"登录请求: username={phone}, password={password}")
    log_info(f"登录请求: username={phone}, password={password}")

    # 检查验证码是否正确
    stored_code = get_code(phone)
    print(f"验证码错误: stored_code={stored_code}")
    if not stored_code or stored_code != password:
        log_error(f"验证码错误: username={phone}")
        raise HTTPException(status_code=400, detail="验证码错误")

    try:
        model = MysqlBaseModel()
        # 检查用户是否存在
        user = model.select("users", {"phone": phone})
        if not user:  # 用户不存在，自动注册
            user = register_user(phone, phone, "")  # 密码为空
        else:
            user = user[0]  # 获取第一条记录
        print(f"user = {user}")
        # 生成 Token
        access_token_expires = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        access_token = create_access_token(
            data={"sub": user["username"]}, expires_delta=access_token_expires
        )

        log_info(f"登录成功: phone={phone}")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "username": user["username"],
                "phone": user["phone"],
                # "email": user["email"],
            },
        }
    except Exception as e:
        log_error(f"登录失败: {str(e)}")
        raise HTTPException(status_code=500, detail="登录失败")

@router.post("/password-login")
async def password_login(request: LoginRequest):
    phone = request.phone
    password = request.password
    try:
        model = MysqlBaseModel()
        # 检查用户是否存在
        user = model.select("users", {"phone": phone})
        print(f"user : {user}")
        if not user:  # 用户不存在，自动注册
            user = register_user (phone, phone, "")  # 密码为空
        else:
            user = user[0]  # 获取第一条记录

        # 检查密码是否正确
        if user["password"] != password:
            raise HTTPException(status_code=400, detail="密码错误")

        # 生成 Token
        access_token_expires = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        access_token = create_access_token(
            data={"sub": user["username"]}, expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "username": user["username"],
                "phone": user["phone"],
                "email": user["email"],
            },
        }
    except Exception as e:
        log_error(f"密码登录失败: {str(e)}")
        raise HTTPException(status_code=500, detail="密码登录失败")

# 新增 /send-verification-code 接口
@router.post("/send-verification-code")
async def send_verification_code(request: SendVerificationCodeRequest):
    identifier = request.identifier
    newPassword = request.newPassword
    try:
        model = MysqlBaseModel()
        # 检查用户是否存在
        user = model.select("users", {"phone": identifier}) or model.select("users", {"email": identifier})
        if not user:
            raise HTTPException(status_code=400, detail="用户不存在")

        # 生成 6 位随机验证码
        code = str(random.randint(100000, 999999))
        # 存储验证码到 Redis
        set_code(identifier, code)
        log_info(f"发送验证码: identifier={identifier}, code={code}")
        return {"code": code}
    except Exception as e:
        log_error(f"发送验证码失败: {str(e)}")
        raise HTTPException(status_code=500, detail="发送验证码失败")