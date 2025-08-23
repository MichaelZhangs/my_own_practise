# main.py
from fastapi import  HTTPException,APIRouter,Depends,Query
from sqlmodel import Session, select,func
from utils.bigdata_person_mysql import PersonInfo
from typing import List,Optional,Generator,Dict
from pydantic import BaseModel
from utils.database import get_db_session  # 假设你已经配置了数据库引擎
from utils.log import log_info, log_error
from config.settings import Settings
from utils.spark_session import get_spark_session
from utils.redis import set_code, get_code
import json
from init import app

router = APIRouter(tags=["用户信息"])


def get_db(db_alias: str = "db1") -> Generator[Session, None, None]:
    """Generator function for dependency injection (FastAPI style)"""
    with get_db_session(db_alias) as session:
        yield session

# 单个用户响应模型
class UserResponseItem(BaseModel):
    id: int
    name: str
    idno: str
    sex: str
    bplace: Optional[str] = None
    idtype: str
    sort:  Optional[int] = None
    province: Optional[str] = None
    age: Optional[int] = None
    birthday: Optional[int] = None

# 分页响应模型
class UserResponse(BaseModel):
    data: List[UserResponseItem]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("/bigdata-users", response_model=UserResponse)
async def get_bigdata_users_info(
        page: int = Query(1, ge=1, description="页码，从1开始"),
        page_size: int = Query(100, ge=1, le=200, description="每页数量，最大200"),
        name: Optional[str] = Query(None, description="按姓名模糊搜索"),
        idno: Optional[str] = Query(None, description="按证件号搜索"),
        sex: Optional[str] = Query(None, description="按性别筛选"),
        province: Optional[str] = Query(None, description="按省份筛选"),
        min_age: Optional[int] = Query(None, ge=0, description="最小年龄"),
        max_age: Optional[int] = Query(None, ge=0, description="最大年龄"),
        session: Session = Depends(get_db)
):
    try:
        # Calculate offset
        offset = (page - 1) * page_size

        # Base query
        query = select(PersonInfo)

        # Apply filters
        if name:
            query = query.where(PersonInfo.name.contains(name))
        if idno:
            query = query.where(PersonInfo.idno.contains(idno))
        if sex:
            query = query.where(PersonInfo.sex == sex)
        if province:
            query = query.where(PersonInfo.province == province)
        if min_age is not None:
            query = query.where(PersonInfo.age >= min_age)
        if max_age is not None:
            query = query.where(PersonInfo.age <= max_age)

        # Get total count (optimized)
        count_query = select(func.count()).select_from(query.subquery())
        total = session.exec(count_query).one()

        # Get paginated results
        users = session.exec(
            query.offset(offset).limit(page_size)
        ).all()
        return {
            "data": list(users),
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total
        }

    except Exception as e:
        log_error(f"获取用户列表失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取用户列表失败: {str(e)}"
        )


# 新增的响应模型
class GenderDistributionResponse(BaseModel):
    male_count: int
    female_count: int
    total: int
    male_percentage: float
    female_percentage: float

class AgeDistributionResponse(BaseModel):
    age_groups: List[str]
    male_counts: List[int]
    female_counts: List[int]
    total_counts: List[int]

class ProDistributionResponse(BaseModel):
    province_counts: Dict[str, int]
    total: int
    province_percentages: Dict[str, float]

class FirstNameDistributionResponse(BaseModel):
    first_names: Dict[str, int]
    total: int
    first_name_percentages: Dict[str, float]


@router.get("/gender-distribution", response_model=GenderDistributionResponse)
async def get_gender_distribution():
    spark = None
    try:
        redis_key = "gender_distribution"
        # 先从 Redis 中获取数据
        cached_result = get_code(redis_key)
        if cached_result:
            try:
                # 将 JSON 字符串转换为 Python 字典
                result = json.loads(cached_result)
                return result
            except json.JSONDecodeError:
                log_error("Failed to decode JSON from Redis.")

        spark = get_spark_session()
        # app.spark.sparkContext.setLogLevel("WARN")  # 设置日志级别为WARN减少日志输出

        # 从settings.py获取数据库配置
        db_config = Settings.DATABASES["db1"]
        # JDBC连接配置
        jdbc_url = f"jdbc:mysql://{db_config['HOST']}:{db_config['PORT']}/{db_config['DB']}?useSSL=false&characterEncoding=UTF-8&useUnicode=true&serverTimezone=UTC"
        print(f"jdbc_url : {jdbc_url}")
        properties = {
            "user": db_config["USER"],
            "password": db_config["PASSWORD"],
            "driver": "com.mysql.cj.jdbc.Driver"  # 使用新版驱动类名
        }

        # 使用更高效的查询方式
        query = "(SELECT sex, COUNT(*) as count FROM person_info GROUP BY sex) as gender_stats"

        # 读取数据
        sdf = spark.read \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", query) \
            .option("user", properties["user"]) \
            .option("password", properties["password"]) \
            .load()

        # 处理结果
        counts = {row["sex"]: int(row["count"]) for row in sdf.collect()}

        total = sum(counts.values())

        result = {
            "male_count": counts.get("男"),
            "female_count": counts.get("女"),
            "total": total,
            "male_percentage": round((counts["男"] / total) * 100, 2) if total > 0 else 0,
            "female_percentage": round((counts["女"] / total) * 100, 2) if total > 0 else 0,
        }
        # 将结果存储到 Redis 中

        set_code(redis_key, json.dumps(result),expire=1800)

        return  result
    except Exception as e:
        log_error(f"获取性别分布失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取性别分布失败: {str(e)}"
        )
    finally:
        if spark:
            spark.stop()  # 确保Spark会话被正确关闭


@router.get("/age-distribution", response_model=AgeDistributionResponse)
async def get_age_distribution():
    spark = None
    try:
        redis_key = "age_distribution"
        # 先从 Redis 中获取数据
        cached_result = get_code(redis_key)
        if cached_result:
            try:
                return json.loads(cached_result)
            except json.JSONDecodeError:
                log_error("Failed to decode JSON from Redis.")

        spark = get_spark_session()
        spark.sparkContext.setLogLevel("WARN")

        # 从settings.py获取数据库配置
        db_config = Settings.DATABASES["db1"]
        # JDBC连接配置
        jdbc_url = f"jdbc:mysql://{db_config['HOST']}:{db_config['PORT']}/{db_config['DB']}?useSSL=false&characterEncoding=UTF-8&useUnicode=true&serverTimezone=UTC"
        properties = {
            "user": db_config["USER"],
            "password": db_config["PASSWORD"],
            "driver": "com.mysql.cj.jdbc.Driver"
        }

        # 创建年龄段分组条件
        age_bucket_expr = """
        CASE 
            WHEN age BETWEEN 0 AND 10 THEN '0-10'
            WHEN age BETWEEN 11 AND 20 THEN '11-20'
            WHEN age BETWEEN 21 AND 30 THEN '21-30'
            WHEN age BETWEEN 31 AND 40 THEN '31-40'
            WHEN age BETWEEN 41 AND 50 THEN '41-50'
            WHEN age BETWEEN 51 AND 60 THEN '51-60'
            WHEN age BETWEEN 61 AND 70 THEN '61-70'
            WHEN age BETWEEN 71 AND 80 THEN '71-80'
            WHEN age BETWEEN 81 AND 90 THEN '81-90'
            WHEN age BETWEEN 91 AND 90 THEN '91-100'
            ELSE '>101'
        END as age_group
        """

        # 查询语句：按年龄段和性别分组统计
        query = f"""
        (SELECT 
            {age_bucket_expr},
            sex,
            COUNT(*) as count 
        FROM person_info 
        GROUP BY age_group, sex) as age_stats
        """

        # 读取数据
        sdf = spark.read \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", query) \
            .option("user", properties["user"]) \
            .option("password", properties["password"]) \
            .load()

        # 处理结果
        age_groups = [
            "0-10", "11-20", "21-30", "31-40", "41-50",
            "51-60", "61-70", "71-80", "81-90", "91-100", ">101"
        ]

        # 初始化结果结构
        result = {
            "age_groups": age_groups,
            "male_counts": [0] * len(age_groups),
            "female_counts": [0] * len(age_groups),
            "total_counts": [0] * len(age_groups)
        }

        # 填充数据
        for row in sdf.collect():
            try:
                age_group = row["age_group"]
                sex = row["sex"]
                count = int(row["count"])

                index = age_groups.index(age_group)
                result["total_counts"][index] += count

                if sex == "男":
                    result["male_counts"][index] = count
                elif sex == "女":
                    result["female_counts"][index] = count
            except ValueError:
                continue

        # 存储到Redis
        set_code(redis_key, json.dumps(result), expire=1800)

        return result

    except Exception as e:
        log_error(f"获取年龄分布失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取年龄分布失败: {str(e)}"
        )
    finally:
        if spark:
            spark.stop()


@router.get("/province-distribution",response_model=ProDistributionResponse)
async def get_province_distribution():
    spark = None
    try:
        redis_key = "province_distribution"
        # 先从 Redis 中获取数据
        cached_result = get_code(redis_key)
        if cached_result:
            try:
                # 将 JSON 字符串转换为 Python 字典
                result = json.loads(cached_result)
                return result
            except json.JSONDecodeError:
                log_error("Failed to decode JSON from Redis.")

        spark = get_spark_session()
        spark.sparkContext.setLogLevel("WARN")  # 设置日志级别为WARN减少日志输出

        # 从 settings.py 获取数据库配置
        db_config = Settings.DATABASES["db1"]
        # JDBC 连接配置
        jdbc_url = f"jdbc:mysql://{db_config['HOST']}:{db_config['PORT']}/{db_config['DB']}?useSSL=false&characterEncoding=UTF-8&useUnicode=true&serverTimezone=UTC"
        properties = {
            "user": db_config["USER"],
            "password": db_config["PASSWORD"],
            "driver": "com.mysql.cj.jdbc.Driver"  # 使用新版驱动类名
        }

        # 使用更高效的查询方式
        query = "(SELECT province, COUNT(*) as count FROM person_info GROUP BY province) as province_stats"

        # 读取数据
        sdf = spark.read \
           .format("jdbc") \
           .option("url", jdbc_url) \
           .option("dbtable", query) \
           .option("user", properties["user"]) \
           .option("password", properties["password"]) \
           .load()


        # 处理结果
        counts = {str(row["province"]) if row["province"] is not None else "Unknown": int(row["count"]) for row in sdf.collect()}

        total = sum(counts.values())

        result = {
            "province_counts": counts,
            "total": total,
            "province_percentages": {
                province: round((count / total) * 100, 2) if total > 0 else 0
                for province, count in counts.items()
            }
        }
        print(f"province  result : {result}")
        # 将结果存储到 Redis 中
        set_code(redis_key, json.dumps(result), expire=1800)

        return result
    except Exception as e:
        log_error(f"获取各省人口分布失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取各省人口分布失败: {str(e)}"
        )
    finally:
        if spark:
            spark.stop()  # 确保 Spark 会话被正确关闭


@router.get("/firstname-distribution", response_model=FirstNameDistributionResponse)
async def get_firstname_distribution():
    spark = None
    try:
        redis_key = "firstname_distribution"
        # 先从 Redis 中获取数据
        cached_result = get_code(redis_key)
        if cached_result:
            try:
                # 将 JSON 字符串转换为 Python 字典
                result = json.loads(cached_result)
                print(f"result : {result}")
                return result
            except json.JSONDecodeError:
                log_error("Failed to decode JSON from Redis.")

        spark = get_spark_session()
        spark.sparkContext.setLogLevel("WARN")  # 设置日志级别为WARN减少日志输出

        # 从 settings.py 获取数据库配置
        db_config = Settings.DATABASES["db1"]
        # JDBC 连接配置
        jdbc_url = f"jdbc:mysql://{db_config['HOST']}:{db_config['PORT']}/{db_config['DB']}?useSSL=false&characterEncoding=UTF-8&useUnicode=true&serverTimezone=UTC"
        properties = {
            "user": db_config["USER"],
            "password": db_config["PASSWORD"],
            "driver": "com.mysql.cj.jdbc.Driver"  # 使用新版驱动类名
        }

        # 使用更高效的查询方式，统计各个姓氏的人数
        query = "(SELECT LEFT(name, 1) AS first_name, COUNT(*) as count FROM person_info GROUP BY LEFT(name, 1)) as first_name_stats"

        # 读取数据
        sdf = spark.read \
           .format("jdbc") \
           .option("url", jdbc_url) \
           .option("dbtable", query) \
           .option("user", properties["user"]) \
           .option("password", properties["password"]) \
           .load()

        # 处理结果，获取各个姓氏的人数
        counts = {row["first_name"]: int(row["count"]) for row in sdf.collect()}
        # 按人数降序排序
        sorted_counts = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        # 取前 20 个姓氏
        top_20_counts = dict(sorted_counts[:20])
        # 计算其他姓氏的人数
        other_count = sum([count for _, count in sorted_counts[20:]])
        if other_count > 0:
            top_20_counts["其他"] = other_count
        total = sum(top_20_counts.values())
        result = {
            "first_names": top_20_counts,
            "total": total,
            "first_name_percentages": {
                first_name: round((count / total) * 100, 2) if total > 0 else 0
                for first_name, count in top_20_counts.items()
            }
        }

        # 将结果存储到 Redis 中
        set_code(redis_key, json.dumps(result), expire=1800)

        return result
    except Exception as e:
        log_error(f"获取前 20 个姓氏分布失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取前 20 个姓氏分布失败: {str(e)}"
        )
    finally:
        if spark:
            spark.stop()  # 确保 Spark 会话被正确关闭