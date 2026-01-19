"""
初始化代码索引脚本
执行此脚本以在 OpenSearch 中创建代码文件和符号的索引
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.logging import logger
from app.services.opensearch_service import OpenSearchService
from opensearch_schemas.code_indices import (
    init_code_indices,
    CODE_FILES_INDEX,
    CODE_SYMBOLS_INDEX,
    CODE_QA_RECORDS_INDEX,
    CODE_FILES_INDEX_CONFIG,
    CODE_SYMBOLS_INDEX_CONFIG,
    CODE_QA_RECORDS_INDEX_CONFIG
)


async def main():
    """主函数"""
    print("=" * 60)
    print("初始化 OpenSearch 代码索引")
    print("=" * 60)
    print()
    
    try:
        # 1. 连接 OpenSearch
        print("[INFO] 连接到 OpenSearch...")
        opensearch_service = OpenSearchService()
        client = opensearch_service.client
        
        if not client:
            print("[ERROR] OpenSearch 客户端未初始化")
            return False
        
        print("[SUCCESS] OpenSearch 连接成功")
        print()
        
        # 2. 创建代码文件索引
        print(f"[INFO] 创建代码文件索引: {CODE_FILES_INDEX}")
        
        if client.indices.exists(index=CODE_FILES_INDEX):
            print(f"[WARN] 索引已存在: {CODE_FILES_INDEX}")
            
            user_input = input("是否删除并重建？(y/n): ")
            if user_input.lower() == 'y':
                client.indices.delete(index=CODE_FILES_INDEX)
                print(f"[INFO] 已删除旧索引")
                
                client.indices.create(
                    index=CODE_FILES_INDEX,
                    body=CODE_FILES_INDEX_CONFIG
                )
                print(f"[SUCCESS] 重建索引成功: {CODE_FILES_INDEX}")
            else:
                print(f"[SKIP] 跳过索引: {CODE_FILES_INDEX}")
        else:
            client.indices.create(
                index=CODE_FILES_INDEX,
                body=CODE_FILES_INDEX_CONFIG
            )
            print(f"[SUCCESS] 创建索引成功: {CODE_FILES_INDEX}")
        
        print()
        
        # 3. 创建代码符号索引
        print(f"[INFO] 创建代码符号索引: {CODE_SYMBOLS_INDEX}")
        
        if client.indices.exists(index=CODE_SYMBOLS_INDEX):
            print(f"[WARN] 索引已存在: {CODE_SYMBOLS_INDEX}")
            
            user_input = input("是否删除并重建？(y/n): ")
            if user_input.lower() == 'y':
                client.indices.delete(index=CODE_SYMBOLS_INDEX)
                print(f"[INFO] 已删除旧索引")
                
                client.indices.create(
                    index=CODE_SYMBOLS_INDEX,
                    body=CODE_SYMBOLS_INDEX_CONFIG
                )
                print(f"[SUCCESS] 重建索引成功: {CODE_SYMBOLS_INDEX}")
            else:
                print(f"[SKIP] 跳过索引: {CODE_SYMBOLS_INDEX}")
        else:
            client.indices.create(
                index=CODE_SYMBOLS_INDEX,
                body=CODE_SYMBOLS_INDEX_CONFIG
            )
            print(f"[SUCCESS] 创建索引成功: {CODE_SYMBOLS_INDEX}")
        
        print()
        
        # 4. 创建代码问答记录索引
        print(f"[INFO] 创建代码问答记录索引: {CODE_QA_RECORDS_INDEX}")
        
        if client.indices.exists(index=CODE_QA_RECORDS_INDEX):
            print(f"[WARN] 索引已存在: {CODE_QA_RECORDS_INDEX}")
            
            user_input = input("是否删除并重建？(y/n): ")
            if user_input.lower() == 'y':
                client.indices.delete(index=CODE_QA_RECORDS_INDEX)
                print(f"[INFO] 已删除旧索引")
                
                client.indices.create(
                    index=CODE_QA_RECORDS_INDEX,
                    body=CODE_QA_RECORDS_INDEX_CONFIG
                )
                print(f"[SUCCESS] 重建索引成功: {CODE_QA_RECORDS_INDEX}")
            else:
                print(f"[SKIP] 跳过索引: {CODE_QA_RECORDS_INDEX}")
        else:
            client.indices.create(
                index=CODE_QA_RECORDS_INDEX,
                body=CODE_QA_RECORDS_INDEX_CONFIG
            )
            print(f"[SUCCESS] 创建索引成功: {CODE_QA_RECORDS_INDEX}")
        
        print()
        
        # 5. 验证索引
        print("[CHECK] 验证创建的索引...")
        
        indices = client.cat.indices(index="code_*", format="json")
        print(f"[OK] 找到 {len(indices)} 个代码相关索引:")
        for idx in indices:
            print(f"  - {idx['index']}: {idx['docs.count']} docs, {idx['store.size']}")
        
        print()
        print("=" * 60)
        print("[SUCCESS] 代码索引初始化完成！")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
