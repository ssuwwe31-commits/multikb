"""
Test Document API
"""

import pytest
from fastapi.testclient import TestClient
from io import BytesIO

def test_get_documents(client):
    """测试获取文档列表"""
    response = client.get("/api/v1/documents/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_upload_document(client):
    """测试上传文档"""
    # 创建测试文件
    test_file = BytesIO(b"test content")
    test_file.name = "test.txt"
    
    files = {"file": ("test.txt", test_file, "text/plain")}
    data = {"knowledge_base_id": 1}
    
    response = client.post("/api/v1/documents/upload", files=files, data=data)
    assert response.status_code == 200

def test_get_document(client):
    """测试获取文档详情"""
    # 先上传一个文档
    test_file = BytesIO(b"test content")
    test_file.name = "test.txt"
    
    files = {"file": ("test.txt", test_file, "text/plain")}
    data = {"knowledge_base_id": 1}
    
    upload_response = client.post("/api/v1/documents/upload", files=files, data=data)
    doc_id = upload_response.json()["id"]
    
    # 获取文档详情
    response = client.get(f"/api/v1/documents/{doc_id}")
    assert response.status_code == 200
    assert response.json()["original_filename"] == "test.txt"

def test_update_document(client):
    """测试更新文档"""
    # 先上传一个文档
    test_file = BytesIO(b"test content")
    test_file.name = "test.txt"
    
    files = {"file": ("test.txt", test_file, "text/plain")}
    data = {"knowledge_base_id": 1}
    
    upload_response = client.post("/api/v1/documents/upload", files=files, data=data)
    doc_id = upload_response.json()["id"]
    
    # 更新文档
    update_data = {"original_filename": "updated.txt"}
    response = client.put(f"/api/v1/documents/{doc_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["original_filename"] == "updated.txt"

def test_delete_document(client):
    """测试删除文档"""
    # 先上传一个文档
    test_file = BytesIO(b"test content")
    test_file.name = "test.txt"
    
    files = {"file": ("test.txt", test_file, "text/plain")}
    data = {"knowledge_base_id": 1}
    
    upload_response = client.post("/api/v1/documents/upload", files=files, data=data)
    doc_id = upload_response.json()["id"]
    
    # 删除文档
    response = client.delete(f"/api/v1/documents/{doc_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "文档删除成功"

def test_reprocess_document(client):
    """测试重新处理文档"""
    # 先上传一个文档
    test_file = BytesIO(b"test content")
    test_file.name = "test.txt"
    
    files = {"file": ("test.txt", test_file, "text/plain")}
    data = {"knowledge_base_id": 1}
    
    upload_response = client.post("/api/v1/documents/upload", files=files, data=data)
    doc_id = upload_response.json()["id"]
    
    # 重新处理文档
    response = client.post(f"/api/v1/documents/{doc_id}/reprocess")
    assert response.status_code == 200
    assert response.json()["message"] == "文档重新处理已启动"
