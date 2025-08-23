import json

from pydantic import BaseModel
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import base64
import uuid
import os


class EncryptRequest(BaseModel):
    data: str
    uuid: str

class DecryptRequest(BaseModel):
    encrypted_data: str
    uuid: str


def generate_key_from_uuid(uuid_str: str) -> bytes:
    """从UUID字符串生成32字节AES密钥"""
    uuid_bytes = uuid.UUID(uuid_str).bytes
    # 确保密钥长度为32字节(256位)
    return uuid_bytes.ljust(32, b'\0')[:32]

def encrypt(data: str, key: bytes) -> str:
    """使用AES-256-CBC加密数据"""
    # 生成随机初始化向量
    iv = os.urandom(16)
    # 创建加密器
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    # 填充数据到16字节的倍数
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data.encode()) + padder.finalize()
    # 加密数据
    encrypted_bytes = encryptor.update(padded_data) + encryptor.finalize()
    # 将IV和加密数据一起编码为Base64
    return base64.b64encode(iv + encrypted_bytes).decode()

def decrypt(encrypted_data: str, key: bytes) -> str:
    """使用AES-256-CBC解密数据"""
    try:
        # 解码Base64数据
        encrypted_bytes = base64.b64decode(encrypted_data)
        # 提取IV和加密数据
        iv = encrypted_bytes[:16]
        encrypted_bytes = encrypted_bytes[16:]
        # 创建解密器
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        # 解密数据
        decrypted_padded = decryptor.update(encrypted_bytes) + decryptor.finalize()
        # 去除填充
        unpadder = padding.PKCS7(128).unpadder()
        decrypted_data = unpadder.update(decrypted_padded) + unpadder.finalize()
        return decrypted_data.decode()
    except Exception as e:
        raise {f"解密失败: {str(e)}"}



if __name__ == '__main__':
    a =  {"name": "张三"}
    uuid_key = str(uuid.uuid4())
    print(uuid_key)
    key = generate_key_from_uuid(uuid_key)
    print(key)
    encrypt_data = encrypt(json.dumps(a), key)
    print(encrypt(json.dumps(a), key))
    print(json.loads(decrypt(encrypt_data, key)))