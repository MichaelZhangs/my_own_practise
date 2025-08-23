import pymysql
from config.settings import settings

class DatabaseManager:
    def __init__(self, db_name: str = "default"):
        """
        初始化数据库管理器
        :param db_name: 数据库名称，默认为 'default'
        """
        self.db_name = db_name
        self.connection = None
        self.connect()

    def connect(self):
        """
        连接到数据库
        """
        db_config = settings.DATABASES.get(self.db_name)
        if not db_config:
            raise ValueError(f"数据库配置 '{self.db_name}' 不存在")

        self.connection = pymysql.connect(
            host=db_config["HOST"],
            port=db_config["PORT"],
            user=db_config["USER"],
            password=db_config["PASSWORD"],
            db=db_config["DB"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )

    def close(self):
        """
        关闭数据库连接
        """
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute(self, query: str, params=None):
        """
        执行 SQL 查询
        :param query: SQL 查询语句
        :param params: 查询参数
        :return: 查询结果
        """
        if not self.connection:
            self.connect()

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            if query.strip().lower().startswith("select"):
                result = cursor.fetchall()
            else:
                self.connection.commit()
                result = cursor.rowcount
        return result

    def __enter__(self):
        """
        进入上下文时连接数据库
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        退出上下文时关闭数据库连接
        """
        self.close()


class MysqlBaseModel:
    def __init__(self, db_name: str = "default"):
        """
        初始化模型类
        :param db_name: 数据库名称，默认为 'default'
        """
        self.db = DatabaseManager(db_name)

    def create_table(self, table_name: str, columns: dict):
        """
        创建表
        :param table_name: 表名
        :param columns: 列定义，例如 {"id": "INT AUTO_INCREMENT PRIMARY KEY", "name": "VARCHAR(255)"}
        """
        columns_sql = ", ".join([f"{col} {defn}" for col, defn in columns.items()])
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_sql})"
        self.db.execute(query)

    def insert(self, table_name: str, data: dict):
        """
        插入数据
        :param table_name: 表名
        :param data: 数据字典，例如 {"name": "Alice", "age": 25}
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        self.db.execute(query, list(data.values()))

    def select(self, table_name: str, where: dict = None, limit: int = None, offset: int = None):
        """
        查询数据
        :param table_name: 表名
        :param where: 条件字典，例如 {"username LIKE": "%王%", "sex": "male"}
        :param limit: 限制返回的行数
        :param offset: 偏移量
        :return: 查询结果
        """
        query = f"SELECT * FROM {table_name}"
        params = []
        if where:
            conditions = []
            for key, value in where.items():
                if " LIKE" in key:  # 处理 LIKE 条件
                    conditions.append(f"{key} %s")
                    params.append(value)
                else:  # 处理普通条件
                    conditions.append(f"{key} = %s")
                    params.append(value)
            query += " WHERE " + " AND ".join(conditions)
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        if offset is not None:
            query += " OFFSET %s"
            params.append(offset)
        return self.db.execute(query, params)

    def update(self, table_name: str, data: dict, where: dict):
        """
        更新数据
        :param table_name: 表名
        :param data: 更新的数据字典，例如 {"age": 26}
        :param where: 条件字典，例如 {"name": "Alice"}
        """
        set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
        conditions = " AND ".join([f"{k} = %s" for k in where.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {conditions}"
        self.db.execute(query, list(data.values()) + list(where.values()))

    def delete(self, table_name: str, where: dict):
        """
        删除数据
        :param table_name: 表名
        :param where: 条件字典，例如 {"name": "Alice"}
        """
        conditions = " AND ".join([f"{k} = %s" for k in where.keys()])
        query = f"DELETE FROM {table_name} WHERE {conditions}"
        self.db.execute(query, list(where.values()))


def init_db():
    """
    初始化 ai_db 数据库和表
    """
    connection = None
    try:
        # 连接到 MySQL（不指定数据库）
        connection = pymysql.connect(
            host=settings.DATABASES["default"]["HOST"],
            port=settings.DATABASES["default"]["PORT"],
            user=settings.DATABASES["default"]["USER"],
            password=settings.DATABASES["default"]["PASSWORD"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        with connection.cursor() as cursor:
            # 创建数据库（如果不存在）
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.DATABASES['default']['DB']}")
            connection.commit()

        # 切换到 ai_db 数据库
        connection.select_db(settings.DATABASES["default"]["DB"])
        with connection.cursor() as cursor:
            # 创建用户表（如果不存在）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    phone VARCHAR(15) UNIQUE,
                    email VARCHAR(255) UNIQUE,
                    username VARCHAR(255) ,
                    sex ENUM('male', 'female', 'other') DEFAULT 'other',
                    password VARCHAR(255),
                    description TEXT,
                    photo VARCHAR(255),
                    qrcode VARCHAR(255) UNIQUE, -- 二维码地址值
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
        print("数据库和表初始化成功")
    except Exception as e:
        print(f"数据库初始化失败: {str(e)}")
    finally:
        if connection:
            connection.close()