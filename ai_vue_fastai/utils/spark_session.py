from pyspark.sql import SparkSession
from pyspark.sql.functions import count
import findspark
import os

# 初始化Spark环境
spark_home = 'D:\\bigdata\\spark-3.3.2-bin-hadoop3'
os.environ['SPARK_HOME'] = spark_home
findspark.init(spark_home=spark_home)

# 添加MySQL驱动路径
os.environ['PYSPARK_SUBMIT_ARGS'] = '--jars file:///D:/bigdata/spark-3.3.2-bin-hadoop3/jars/mysql-connector-java-8.0.28.jar pyspark-shell'
os.environ['JAVA_HOME']='E:\jdk-11.0.6'

def get_spark_session():
    return SparkSession.builder \
        .appName("BigDataAnalysis") \
        .master("local[*]") \
        .config("spark.jars", "file:///D:/bigdata/spark-3.3.2-bin-hadoop3/jars/mysql-connector-java-8.0.13.jar") \
        .config("spark.driver.extraClassPath",
                "D:/bigdata/spark-3.3.2-bin-hadoop3/jars/mysql-connector-java-8.0.13.jar") \
        .config("spark.executor.extraClassPath",
                "D:/bigdata/spark-3.3.2-bin-hadoop3/jars/mysql-connector-java-8.0.13.jar") \
        .getOrCreate()