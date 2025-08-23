
from fastapi.middleware.cors import CORSMiddleware
from views.auth_router import router as router_auth
from views.user.userinfo import router as router_user
from views.article.comments import router as router_comment
from utils.mysql import init_db
from fastapi.staticfiles import StaticFiles
from config.settings import settings
import os
from views.article.article import router as router_article
from utils.database import create_engine, get_database_url
from views.bigdata.person import router as router_bigdata
from views.chat.single_chat import router as router_chat
from views.chat.group import router as router_group
from views.chat.group_chat import router as router_group_chat
import sys
import io
# 强制标准输出使用UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from init import app

print(f"app.spark : {app.spark}")

@app.on_event("startup")
def init_db():
    """初始化数据库和表"""
    # 创建多数据库引擎
    engines = {
        db_alias: create_engine(get_database_url(db_alias))
        for db_alias in settings.DATABASES.keys()
    }

#   @app.on_event("startup")
# WARNING:  You must pass the application as an import string to enable 'reload' or 'workers'.

# 确保二维码目录存在，如果不存在则创建
os.makedirs(settings.QRCODE_DIR, exist_ok=True)
os.makedirs(settings.AVATAR_DIR, exist_ok=True)
os.makedirs(settings.ARTICLE_MEDIA, exist_ok=True)
os.makedirs(settings.CHAT_MEDIA, exist_ok=True)
# 配置静态文件服务
app.mount("/"+settings.QRCODE_DIR, StaticFiles(directory=settings.QRCODE_DIR), name=settings.QRCODE_DIR)
app.mount("/"+settings.AVATAR_DIR, StaticFiles(directory=settings.AVATAR_DIR), name=settings.AVATAR_DIR)
app.mount("/"+settings.ARTICLE_MEDIA, StaticFiles(directory=settings.ARTICLE_MEDIA), name=settings.ARTICLE_MEDIA)
app.mount("/"+settings.CHAT_MEDIA, StaticFiles(directory=settings.CHAT_MEDIA), name=settings.CHAT_MEDIA)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有域名访问，生产环境应限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有 HTTP 头
)
# 注册路由
app.include_router(router_auth, prefix="/api")
app.include_router(router_user,prefix="/user")
app.include_router(router_bigdata,prefix="/bigdata")
app.include_router(router_article,prefix="/article")
app.include_router(router_comment,prefix="/article")
app.include_router(router_chat, prefix='/ws/chat')
app.include_router(router_group)
app.include_router(router_group_chat, prefix='/ws/group/chat')

if __name__ == "__main__":
    import uvicorn
    # uvicorn.run("main:app", host="127.0.0.1",workers=5, port=8000)
    uvicorn.run("main:app", host="0.0.0.0", port=8000)