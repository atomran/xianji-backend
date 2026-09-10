"""配置管理 — 环境变量驱动。"""
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

BASE_DIR = Path(__file__).resolve().parents[2]

# ---- 存储模式 ----
# local: 本地文件系统（开发）
# wxcos: 微信云托管对象存储（生产）
STORAGE_MODE = os.getenv('STORAGE_MODE', 'local')
LOCAL_STORAGE_DIR = os.getenv('LOCAL_STORAGE_DIR', str(BASE_DIR / '.temp' / 'uploads'))

# ---- 数据库 ----
# 支持 sqlite（本地开发）和 mysql（生产）
DB_TYPE = os.getenv('DB_TYPE', 'mysql')
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'fridge')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'fridge_secret')
DB_NAME = os.getenv('DB_NAME', 'fridge')

if DB_TYPE == 'sqlite':
    SQLITE_PATH = os.getenv('SQLITE_PATH', str(BASE_DIR / '.temp' / 'fridge.db'))
    DATABASE_URL = f"sqlite:///{SQLITE_PATH}"
else:
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# ---- 开发模式 ----
DEV_MODE = os.getenv('DEV_MODE', 'false').lower() == 'true'

# ---- JWT ----
JWT_SECRET = os.getenv('JWT_SECRET', 'change_me_in_production')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_HOURS = 2
REFRESH_TOKEN_EXPIRE_DAYS = 30

# 生产环境安全校验
if not DEV_MODE:
    if JWT_SECRET == 'change_me_in_production':
        print('[FATAL] 生产环境必须设置 JWT_SECRET 环境变量', file=sys.stderr)
        sys.exit(1)
    if DB_TYPE != 'sqlite' and DB_PASSWORD == 'fridge_secret':
        print('[FATAL] 生产环境必须设置 DB_PASSWORD 环境变量', file=sys.stderr)
        sys.exit(1)

# ---- 微信小程序 ----
WX_APPID = os.getenv('WX_APPID', '')
WX_SECRET = os.getenv('WX_SECRET', '')

# ---- 微信云托管 ----
WX_CLOUD_ENV = os.getenv('WX_CLOUD_ENV', '')  # 云托管环境ID

# ---- DashScope (通义千问VL) ----
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY', '')
VL_MODEL = os.getenv('VL_MODEL', 'qwen-vl-plus')  # 默认 plus，性价比最优

# ---- 阿里云 OSS（备选存储）----
OSS_ACCESS_KEY_ID = os.getenv('OSS_ACCESS_KEY_ID', '')
OSS_ACCESS_KEY_SECRET = os.getenv('OSS_ACCESS_KEY_SECRET', '')
OSS_ENDPOINT = os.getenv('OSS_ENDPOINT', 'oss-cn-hangzhou.aliyuncs.com')
OSS_BUCKET = os.getenv('OSS_BUCKET', 'xianji-photos')

# ---- 微信云托管 COS ----
# 使用临时密钥（通过内部 API 获取），不需要永久密钥
COS_SECRET_ID = os.getenv('COS_SECRET_ID', '')  # 保留兼容，实际不使用
COS_SECRET_KEY = os.getenv('COS_SECRET_KEY', '')  # 保留兼容，实际不使用
COS_REGION = os.getenv('COS_REGION', 'ap-shanghai')
COS_BUCKET = os.getenv('COS_BUCKET', '')  # 格式: bucketname-appid

# ---- 服务 ----
TZ_NAME = 'Asia/Shanghai'
MAX_PHOTO_SIZE = 15 * 1024 * 1024  # 15MB
RECOGNIZE_RATE_LIMIT = 10  # 次/分钟/用户

# ---- 服务端口 ----
PORT = int(os.getenv('PORT', '8000'))
