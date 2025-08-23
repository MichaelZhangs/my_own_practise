import os
import logging
from datetime import datetime
from config.settings import settings

# 确保日志目录存在
os.makedirs(settings.LOG_DIR, exist_ok=True)

# 日志文件名
log_file = os.path.join(settings.LOG_DIR, datetime.now().strftime("%Y-%m-%d.txt"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)

def log_info(message: str):
    logger.info(message)

def log_error(message: str):
    logger.error(message)