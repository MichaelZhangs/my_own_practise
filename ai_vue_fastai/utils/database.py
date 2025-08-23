# database.py
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.engine import URL,Engine
from config.settings import settings
from contextlib import contextmanager
from typing import Generator,Dict
from functools import lru_cache

# 构建 MySQL 连接 URL
def get_database_url(db_alias="default"):
    db_config = settings.DATABASES[db_alias]
    return URL.create(
        drivername="mysql+pymysql",
        username=db_config["USER"],
        password=db_config["PASSWORD"],
        host=db_config["HOST"],
        port=db_config["PORT"],
        database=db_config["DB"],
    )

# 创建默认数据库引擎
engine = create_engine(
    get_database_url(),
    pool_size=5,  # 连接池大小
    max_overflow=10,  # 最大溢出连接数
    pool_pre_ping=True,  # 连接前先 ping 测试
    echo=True  # 是否输出 SQL 日志
)


@lru_cache(maxsize=None)
def create_db_engine(db_alias: str = "default"):
    """Create and cache database engine with connection pooling"""
    db_config = settings.DATABASES[db_alias]

    # Common engine parameters
    engine_params = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
    }

    # Add additional parameters if specified in settings
    if "ENGINE_PARAMS" in db_config:
        engine_params.update(db_config["ENGINE_PARAMS"])

    return create_engine(get_database_url(db_alias), **engine_params)

# 获取数据库会话
def get_session():
    with Session(engine) as session:
        yield session

# 创建多数据库引擎
# engines = {
#     db_alias: create_engine(get_database_url(db_alias))
#     for db_alias in settings.DATABASES.keys()
#     # 'default': create_engine(get_database_url('default')),
#     # 'bigdata': create_engine(get_database_url('bigdata'))
# }

engines: Dict[str, Engine] = {
    db_alias: create_db_engine(db_alias)
    for db_alias in settings.DATABASES.keys()
}

@contextmanager
def get_db_session(db_alias: str = "default"):
    """获取数据库会话的上下文管理器"""
    session = Session(engines[db_alias])
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

