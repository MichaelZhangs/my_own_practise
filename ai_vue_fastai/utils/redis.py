import redis
from config.settings import settings
from typing import Dict, Optional
# 初始化 Redis 连接
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,  # 自动解码为字符串
)
def set_userinfo_to_redis(key: str, value: str):
    redis_client.set(key, value)

def set_code(key: str, value: str, expire: int = 60):
    redis_client.set(key, value, ex=expire)

def get_code(key: str) -> str:
    return redis_client.get(key)


def store_websocket_connection(user_id: str, target_id: str, connection_key: str):
    """将WebSocket连接信息存储到Redis"""
    try:
        # 使用哈希表存储用户的连接信息，键格式: ws_connections:{user_id}
        key = f"ws_connections:{user_id}"
        # 字段为目标用户ID，值为connection_key
        redis_client.hset(key, target_id, connection_key)

        # 设置过期时间（例如24小时）
        redis_client.expire(key, 86400)

        # 记录用户在线状态（5分钟过期，需心跳维持）
        redis_client.set(f"user_online:{user_id}", "1", ex=300)
    except redis.RedisError as e:
        print(f"Redis操作失败: {e}")


def get_websocket_connection(user_id: str, target_id: str) -> Optional[str]:
    """从Redis获取用户的WebSocket连接信息"""
    try:
        key = f"ws_connections:{user_id}"
        return redis_client.hget(key, target_id)
    except redis.RedisError as e:
        print(f"Redis操作失败: {e}")
        return None


def remove_websocket_connection(user_id: str, target_id: str):
    """从Redis移除用户的WebSocket连接信息"""
    try:
        key = f"ws_connections:{user_id}"
        redis_client.hdel(key, target_id)

        # 检查用户是否还有其他连接
        connections = redis_client.hgetall(key)
        if not connections:
            # 没有其他连接，标记用户为离线
            redis_client.delete(f"user_online:{user_id}")
    except redis.RedisError as e:
        print(f"Redis操作失败: {e}")

# 获取用户的所有WebSocket连接
def get_all_websocket_connections(user_id: str) -> Dict[bytes, bytes]:
    """获取用户的所有WebSocket连接"""
    key = f"ws:connections:{user_id}"
    return redis_client.hgetall(key)

# 新增：检查用户是否在线
def is_user_online(user_id: str) -> bool:
    """检查用户是否在线"""
    return redis_client.exists(f"user:online:{user_id}") == 1


# 新增：记录消息已读状态
def mark_message_as_read(message_id: str):
    """标记消息为已读"""
    redis_client.set(f"message:read:{message_id}", "1", ex=86400)  # 1天过期


# 新增：检查消息是否已读
def is_message_read(message_id: str) -> bool:
    """检查消息是否已读"""
    return redis_client.exists(f"message:read:{message_id}") == 1

