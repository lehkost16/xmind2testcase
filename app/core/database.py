import sqlite3
import logging
import os
from contextlib import closing
from app.core.config import settings

def get_db():
    """
    依赖注入：提供数据库连接
    
    注意：设置 check_same_thread=False 以支持 FastAPI 的异步处理
    这在 SQLite 中是安全的，因为我们使用了连接池模式
    """
    db = sqlite3.connect(
        settings.DATABASE_PATH,
        check_same_thread=False  # 允许在不同线程中使用连接
    )
    db.row_factory = sqlite3.Row  # 返回字典式的行对象
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库 Schema"""
    if not os.path.exists(settings.DATABASE_PATH):
        with closing(sqlite3.connect(
            settings.DATABASE_PATH,
            check_same_thread=False
        )) as db:
            with open(settings.SCHEMA_PATH, mode='r', encoding='utf-8') as f:
                db.cursor().executescript(f.read())
            db.commit()
        logging.info('✅ 数据库初始化成功!')

