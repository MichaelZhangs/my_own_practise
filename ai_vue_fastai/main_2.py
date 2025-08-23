from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from views.auth import router as router_auth
from views.user.personInfo import router as user_router

from utils.mysql import init_db
from fastapi.staticfiles import StaticFiles
from config.settings import settings
import os
from sqlmodel import SQLModel
from utils.database import create_engine, get_database_url


app = FastAPI()

# 启动时初始化数据库
@app.on_event("startup")
def startup_event():
    init_db()

# @app.on_event("startup")
# def init_db():
#     """初始化数据库和表"""
#     # 创建多数据库引擎
#     engines = {
#         db_alias: create_engine(get_database_url(db_alias))
#         for db_alias in settings.DATABASES.keys()
#     }

# 确保二维码目录存在，如果不存在则创建
os.makedirs(settings.QRCODE_DIR, exist_ok=True)
os.makedirs(settings.AVATAR_DIR, exist_ok=True)

# 配置静态文件服务
app.mount("/"+settings.QRCODE_DIR, StaticFiles(directory=settings.QRCODE_DIR), name=settings.QRCODE_DIR)
app.mount("/"+settings.AVATAR_DIR, StaticFiles(directory=settings.AVATAR_DIR), name=settings.AVATAR_DIR)

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
app.include_router(user_router,prefix="/user")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)