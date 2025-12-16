"""
Health Check Script
"""

import os
import sys
import requests
import time
from app.config.settings import settings

def check_database():
    """检查数据库连接"""
    try:
        from app.config.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("数据库连接正常")
        return True
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return False

def check_redis():
    """检查Redis连接"""
    try:
        from app.config.redis import get_redis
        redis_client = get_redis()
        redis_client.ping()
        print("Redis连接正常")
        return True
    except Exception as e:
        print(f"Redis连接失败: {e}")
        return False

def check_opensearch():
    """检查OpenSearch连接"""
    try:
        from app.config.opensearch import get_opensearch
        opensearch = get_opensearch()
        opensearch.info()
        print("OpenSearch连接正常")
        return True
    except Exception as e:
        print(f"OpenSearch连接失败: {e}")
        return False

def check_minio():
    """检查MinIO连接"""
    try:
        from app.config.minio import get_minio
        minio = get_minio()
        minio.list_buckets()
        print("MinIO连接正常")
        return True
    except Exception as e:
        print(f"MinIO连接失败: {e}")
        return False

def check_ollama():
    """检查Ollama连接"""
    try:
        response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
        response.raise_for_status()
        print("Ollama连接正常")
        return True
    except Exception as e:
        print(f"Ollama连接失败: {e}")
        return False

def check_api():
    """检查API服务"""
    try:
        response = requests.get(f"http://{settings.HOST}:{settings.PORT}/health", timeout=5)
        response.raise_for_status()
        print("API服务正常")
        return True
    except Exception as e:
        print(f"API服务失败: {e}")
        return False

def main():
    """主函数"""
    print("开始健康检查...")
    
    checks = [
        ("数据库", check_database),
        ("Redis", check_redis),
        ("OpenSearch", check_opensearch),
        ("MinIO", check_minio),
        ("Ollama", check_ollama),
        ("API服务", check_api)
    ]
    
    results = []
    for name, check_func in checks:
        print(f"检查 {name}...")
        result = check_func()
        results.append((name, result))
        time.sleep(1)
    
    print("\n健康检查结果:")
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")
    
    # 返回退出码
    failed_count = sum(1 for _, result in results if not result)
    sys.exit(failed_count)

if __name__ == "__main__":
    main()
