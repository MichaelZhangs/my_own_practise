# # encoding: UTF-8
# app/dependencies/auth.py


from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional
from config.settings import settings
from utils.log import log_info,log_error
import base64
import json

# JWT配置
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM

# Token模型
class TokenData(BaseModel):
    id: int

# HTTP Bearer认证
oauth2_scheme = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    """
    从JWT token中获取当前用户信息
    """
    token = credentials.credentials
    try:
        parts = token.split('.')
        if len(parts) == 3:
            payload_encoded = parts[1]
            payload_decoded = base64.urlsafe_b64decode(payload_encoded + '==').decode('utf-8')
            manual_payload = json.loads(payload_decoded)
            log_info(f"手动解析的payload: {manual_payload}")

            # 检查过期时间
            from datetime import datetime
            exp = manual_payload.get('exp')
            if exp:
                expire_time = datetime.fromtimestamp(exp)
                current_time = datetime.utcnow()
                log_info(f"Token过期时间: {expire_time}")
                log_info(f"当前时间: {current_time}")
                if current_time > expire_time:
                    log_error("Token已过期!")
                    raise HTTPException(status_code=401, detail="认证凭证已过期")

            user_id = manual_payload.get("sub")

            return TokenData(id=user_id)

    except JWTError as e:
        log_error(f"JWT验证失败: {str(e)}")

        # 尝试使用字节格式的secret
        try:

            payload = jwt.decode(token, settings.SECRET_KEY.encode('utf-8'), algorithms=[settings.ALGORITHM])

            user_id = payload.get("sub")
            return TokenData(id=user_id)
        except JWTError as byte_error:
            log_error(f"字节格式也失败: {str(byte_error)}")

            raise HTTPException(status_code=401, detail="认证凭证无效或已过期")

def get_current_user_id(current_user: TokenData = Depends(get_current_user)):
    """
    获取当前用户ID
    """
    return current_user.id

#  - 创建token - 使用的SECRET_KEY:abc12#@$%^&1
#  创建token - 使用的ALGORITHM:HS256