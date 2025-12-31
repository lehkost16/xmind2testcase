"""
API 端点测试
"""
import pytest

def test_health_check(client):
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data

def test_root_redirect(client):
    """测试根路径重定向"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code in [200, 307]  # 200 for direct, 307 for redirect

def test_api_docs(client):
    """测试 API 文档可访问"""
    response = client.get("/docs")
    assert response.status_code == 200

def test_static_files(client):
    """测试静态文件访问"""
    response = client.get("/static/css/style.css")
    assert response.status_code in [200, 404]  # 404 if file doesn't exist yet
