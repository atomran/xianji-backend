"""FastAPI 主入口。"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import TZ_NAME, STORAGE_MODE, LOCAL_STORAGE_DIR
from .db import engine, get_db
from .models.database import Base
from .routers import auth, items, photos, households, device


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时创建数据库和表
    if os.getenv('AUTO_CREATE_TABLES', '1') == '1':
        from .config import DB_TYPE, DATABASE_URL, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
        if DB_TYPE == 'mysql':
            # 先连到 MySQL 服务器（不指定数据库），创建 fridge 数据库
            from sqlalchemy import create_engine, text
            server_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/?charset=utf8mb4"
            try:
                server_engine = create_engine(server_url, pool_pre_ping=True)
                with server_engine.connect() as conn:
                    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                    conn.commit()
                server_engine.dispose()
                print(f'数据库 {DB_NAME} 已确保创建', flush=True)
            except Exception as e:
                print(f'创建数据库警告: {e}', flush=True)
        # 创建表
        Base.metadata.create_all(bind=engine)
    print(f'鲜记后端已启动 (timezone={TZ_NAME}, storage={STORAGE_MODE})', flush=True)
    yield
    print('鲜记后端关闭', flush=True)


app = FastAPI(
    title='鲜记 · 家庭冰箱 API',
    version='1.0.0',
    lifespan=lifespan,
)

# CORS（小程序不需要，但 App 和开发调试需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)

# 注册路由
app.include_router(auth.router)
app.include_router(items.router)
app.include_router(photos.router)
app.include_router(households.router)
app.include_router(device.router)

# 本地存储模式：挂载静态文件服务（预览图访问）
if STORAGE_MODE == 'local':
    import os
    os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)
    app.mount('/static/uploads', StaticFiles(directory=LOCAL_STORAGE_DIR), name='uploads')


@app.get('/health')
def health():
    from .config import STORAGE_MODE, DEV_MODE, DB_TYPE
    return dict(
        ok=True, service='鲜记 · 家庭冰箱', version='1.0.0',
        storage=STORAGE_MODE, dev_mode=DEV_MODE, db_type=DB_TYPE,
    )
