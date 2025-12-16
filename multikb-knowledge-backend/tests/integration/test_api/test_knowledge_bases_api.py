"""
Test Knowledge Base API
"""

import pytest
from fastapi.testclient import TestClient

def test_get_knowledge_bases(client):
    """测试获取知识库列表"""
    response = client.get("/api/v1/knowledge-bases/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_knowledge_base(client):
    """测试创建知识库"""
    data = {
        "name": "测试知识库",
        "description": "这是一个测试知识库"
    }
    response = client.post("/api/v1/knowledge-bases/", json=data)
    assert response.status_code == 200
    assert response.json()["name"] == "测试知识库"

def test_get_knowledge_base(client):
    """测试获取知识库详情"""
    # 先创建一个知识库
    data = {"name": "测试知识库"}
    create_response = client.post("/api/v1/knowledge-bases/", json=data)
    kb_id = create_response.json()["id"]
    
    # 获取知识库详情
    response = client.get(f"/api/v1/knowledge-bases/{kb_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "测试知识库"

def test_update_knowledge_base(client):
    """测试更新知识库"""
    # 先创建一个知识库
    data = {"name": "测试知识库"}
    create_response = client.post("/api/v1/knowledge-bases/", json=data)
    kb_id = create_response.json()["id"]
    
    # 更新知识库
    update_data = {"name": "更新后的知识库"}
    response = client.put(f"/api/v1/knowledge-bases/{kb_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["name"] == "更新后的知识库"

def test_delete_knowledge_base(client):
    """测试删除知识库"""
    # 先创建一个知识库
    data = {"name": "测试知识库"}
    create_response = client.post("/api/v1/knowledge-bases/", json=data)
    kb_id = create_response.json()["id"]
    
    # 删除知识库
    response = client.delete(f"/api/v1/knowledge-bases/{kb_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "知识库删除成功"

def test_get_nonexistent_knowledge_base(client):
    """测试获取不存在的知识库"""
    response = client.get("/api/v1/knowledge-bases/99999")
    assert response.status_code == 404
