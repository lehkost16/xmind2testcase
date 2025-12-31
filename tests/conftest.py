"""
测试配置文件
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture
def app():
    """FastAPI 应用实例"""
    from app.main import create_app
    return create_app()

@pytest.fixture
def client(app):
    """测试客户端"""
    from fastapi.testclient import TestClient
    return TestClient(app)

@pytest.fixture
def sample_xmind_file():
    """示例 XMind 文件路径"""
    return project_root / "docs" / "xmind_testcase_template.xmind"
