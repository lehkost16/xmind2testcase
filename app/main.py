"""
XMind2TestCase - FastAPI Application Entry Point
现代化测试用例管理平台
"""
import logging
import os
import sys
from pathlib import Path
import mimetypes
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# 注册 XMind MIME 类型
mimetypes.add_type('application/vnd.xmind.workbook', '.xmind')
mimetypes.add_type('application/x-xmind', '.xmind')

from app.core.config import settings
from app.core.database import init_db

# 确保 app/lib 在 Python 路径中（用于 xmind2testcase 和 xmindparser）
sys.path.append(os.path.join(settings.APP_DIR, "lib"))

from app.api.routers import web, conversion, project, records

# ==================== 日志配置 ====================
def setup_logging():
    """配置应用日志"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(module)s.%(funcName)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件处理器
    file_handler = logging.FileHandler(
        log_dir / 'app.log',
        encoding='UTF-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # 控制台处理器
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    
    # 根日志器
    logger = logging.getLogger("xmind2testcase")
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
    return logger

logger = setup_logging()

# ==================== FastAPI 应用 ====================
def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""
    
    app = FastAPI(
        title="XMind2TestCase",
        description="现代化测试用例管理平台 - 支持 XMind 导入导出",
        version="2.0.0",
        debug=settings.DEBUG,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # ==================== 中间件 ====================
    # CORS 支持
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # ==================== 异常处理 ====================
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """全局异常处理器"""
        logger.error(f"未处理的异常: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "服务器内部错误，请查看日志获取详细信息",
                "error": str(exc) if settings.DEBUG else "Internal Server Error"
            }
        )
    
    # ==================== 生命周期事件 ====================
    @app.on_event("startup")
    async def startup_event():
        """应用启动事件"""
        logger.info("=" * 60)
        logger.info("🚀 XMind2TestCase 应用启动")
        logger.info(f"📦 版本: 2.0.0")
        logger.info(f"🐛 调试模式: {settings.DEBUG}")
        logger.info(f"📁 上传目录: {settings.UPLOAD_FOLDER}")
        logger.info(f"💾 数据库: {settings.DATABASE_PATH}")
        logger.info("=" * 60)
        
        # 初始化数据库
        try:
            init_db()
            logger.info("✅ 数据库初始化成功")
        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            raise
        
        # 确保必要的目录存在
        for directory in [settings.UPLOAD_FOLDER, "logs", "backups"]:
            Path(directory).mkdir(exist_ok=True)
            logger.debug(f"✓ 目录已创建/验证: {directory}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭事件"""
        logger.info("=" * 60)
        logger.info("👋 XMind2TestCase 应用关闭")
        logger.info("=" * 60)
    
    # ==================== 健康检查 ====================
    @app.get("/health", tags=["System"])
    async def health_check():
        """健康检查端点"""
        db_exists = os.path.exists(settings.DATABASE_PATH)
        upload_dir_exists = os.path.exists(settings.UPLOAD_FOLDER)
        
        return {
            "status": "healthy" if db_exists and upload_dir_exists else "degraded",
            "version": "2.0.0",
            "database": db_exists,
            "upload_directory": upload_dir_exists,
            "debug_mode": settings.DEBUG
        }
    
    # ==================== 静态文件 ====================
    static_dir = os.path.join(settings.APP_DIR, "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.debug(f"✓ 静态文件目录已挂载: {static_dir}")
    else:
        logger.warning(f"⚠️ 静态文件目录不存在: {static_dir}")
    
    # ==================== 路由注册 ====================
    app.include_router(web.router, tags=["Web"])
    app.include_router(conversion.router, tags=["Conversion"])
    app.include_router(project.router, prefix="/api/projects", tags=["Projects"])
    app.include_router(records.router, prefix="/api/records", tags=["Records"])
    
    logger.debug("✓ 所有路由已注册")
    
    return app

# 创建应用实例
app = create_app()

# ==================== 主程序入口 ====================
if __name__ == '__main__':
    import uvicorn
    
    logger.info("🌟 直接运行模式启动")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
