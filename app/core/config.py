import os

class Settings:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    APP_DIR = os.path.join(BASE_DIR, 'app')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    DATABASE_PATH = os.path.join(BASE_DIR, 'data.db3')
    SCHEMA_PATH = os.path.join(BASE_DIR, 'schema.sql')
    LOG_FILE = os.path.join(BASE_DIR, 'running.log')
    ALLOWED_EXTENSIONS = {'xmind'}
    DEBUG = True
    
    # 功能开关
    ENABLE_ZENTAO = True
    ENABLE_TESTLINK = True

settings = Settings()
