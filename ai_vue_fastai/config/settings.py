import os
from typing import Dict, Any

class Settings:
    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = None

    # MySQL 默认配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "123456"
    MYSQL_DB: str = "ai_db"

    # 多数据库配置
    DATABASES: Dict[str, Dict[str, Any]] = {
        "default": {
            "HOST": MYSQL_HOST,
            "PORT": MYSQL_PORT,
            "USER": MYSQL_USER,
            "PASSWORD": MYSQL_PASSWORD,
            "DB": MYSQL_DB,
        },
        "db1": {
            "HOST": "localhost",
            "PORT": 3306,
            "USER": "root",
            "PASSWORD": "123456",
            "DB": "bigdata",
        },
        "db2": {
            "HOST": "localhost",
            "PORT": 3306,
            "USER": "root",
            "PASSWORD": "123456",
            "DB": "heima",
        },
    }

    # JWT 配置
    SECRET_KEY: str = "abc12#@$%^&1"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1
    QRCODE_DIR: str = 'qrcode' # 二维码
    AVATAR_DIR: str = 'avatar' #头像
    ARTICLE_MEDIA: str = 'article_media'
    CHAT_MEDIA:  str = 'chat_media'

    server_host = "http://localhost:8000"

    # 日志配置
    LOG_DIR: str = "logs"
    LOG_FILE: str = os.path.join(LOG_DIR, "app.log")

    # 在配置文件中设置密钥
    MESSAGE_KEY = "b1d8f7e3a9c5e7b4d9f1e3a8c7e5f9b3d7e1a9c5e7b4d9f1e3a8c7e5f9b3d"

    ALLOWED_IMAGE_TYPES = [
        "image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp",
        "image/svg+xml", "image/tiff", "image/x-icon", "image/vnd.adobe.photoshop"
    ]

    ALLOWED_VIDEO_TYPES = [
        "video/mp4", "video/quicktime", "video/x-msvideo", "video/x-ms-wmv",
        "video/x-flv", "video/webm", "video/mpeg", "video/x-matroska",
        "video/3gpp", "video/3gpp2"
    ]

    ALLOWED_AUDIO_TYPES = [
        "audio/mpeg", "audio/flac", "audio/wav", "audio/ogg", "audio/aac",
        "audio/x-m4a", "audio/x-wma", "audio/mp4", "audio/webm",
        "audio/x-aiff", "audio/x-pn-realaudio", "audio/x-wav", "audio/x-ms-wma"
    ]

    ALLOWED_DOCUMENT_TYPES = [
        # PDF
        'application/pdf',

        # Microsoft Office
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',

        # OpenDocument Format
        'application/vnd.oasis.opendocument.text',
        'application/vnd.oasis.opendocument.spreadsheet',
        'application/vnd.oasis.opendocument.presentation',

        # 文本文件
        'text/plain', 'text/csv', 'text/html', 'text/xml', 'text/css',
        'text/javascript', 'application/json', 'application/xml',

        # 电子书
        'application/epub+zip', 'application/x-mobipocket-ebook'
    ]

    ALLOWED_ARCHIVE_TYPES = [
        'application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed',
        'application/x-tar', 'application/gzip', 'application/x-bzip2',
        'application/x-compress', 'application/x-zip-compressed',
        'application/x-apple-diskimage'  # .dmg files
    ]

    ALLOWED_CODE_TYPES = [
        # 编程语言文件
        'text/x-python', 'text/x-java-source', 'text/x-c', 'text/x-c++',
        'text/x-php', 'text/x-ruby', 'text/x-go', 'text/x-swift',
        'text/x-typescript', 'application/x-httpd-php',

        # 配置文件
        'text/x-ini', 'text/x-properties', 'application/x-yaml',

        # 脚本文件
        'application/x-shellscript', 'application/x-bat', 'application/x-sh'
    ]

    ALLOWED_EXECUTABLE_TYPES = [
        # Windows 可执行文件
        'application/x-msdownload',  # .exe, .dll
        'application/x-ms-installer',  # .msi

        # Linux/Unix 可执行文件
        'application/x-executable', 'application/x-sharedlib',

        # macOS 应用程序
        'application/x-apple-diskimage',  # .dmg
        'application/x-iso9660-image',  # .iso

        # 移动应用
        'application/vnd.android.package-archive'  # .apk
    ]

    ALLOWED_FONT_TYPES = [
        'font/ttf', 'font/otf', 'font/woff', 'font/woff2',
        'application/x-font-truetype', 'application/x-font-opentype'
    ]

    ALLOWED_DATABASE_TYPES = [
        'application/x-sql', 'application/x-sqlite3',
        'application/vnd.ms-access', 'application/x-dbf'
    ]

    # 所有允许的文件类型汇总
    ALLOWED_FILE_TYPES = (
            ALLOWED_IMAGE_TYPES +
            ALLOWED_VIDEO_TYPES +
            ALLOWED_AUDIO_TYPES +
            ALLOWED_DOCUMENT_TYPES +
            ALLOWED_ARCHIVE_TYPES +
            ALLOWED_CODE_TYPES +
            ALLOWED_EXECUTABLE_TYPES +
            ALLOWED_FONT_TYPES +
            ALLOWED_DATABASE_TYPES
    )

    class Config:
        env_file = ".env"

# 实例化配置
settings = Settings()