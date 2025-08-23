from fastapi import FastAPI
from utils.spark_session import get_spark_session

app = FastAPI()

# 将spark对象绑定到app上
app.spark = get_spark_session()

