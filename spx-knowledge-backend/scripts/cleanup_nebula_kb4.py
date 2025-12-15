#!/usr/bin/env python3
"""
清理知识库4的NebulaGraph数据
"""

import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"[INFO] 已加载环境变量文件: {env_file}")
else:
    print(f"[WARN] 未找到 .env 文件: {env_file}，使用系统环境变量")

# 添加项目根目录到Python路径
sys.path.insert(0, str(project_root))

from app.services.graph_storage_service import get_graph_storage
from app.core.logging import logger

kb_id = 4
space = f"kb_{kb_id}"

print("=" * 60)
print(f"开始清理知识库 {kb_id} 的NebulaGraph数据...")
print(f"Space: {space}")
print("=" * 60)

async def cleanup_nebula():
    """清理NebulaGraph数据"""
    nebula_storage = get_graph_storage()
    
    try:
        # 查询所有实体
        print("\n[步骤1] 查询所有实体...")
        query_nGQL = """
        MATCH (n:entity)
        RETURN id(n) as vid, n.name as name, n.mysql_id as mysql_id
        LIMIT 10000;
        """
        print(f"执行查询: {query_nGQL.strip()}")
        
        try:
            all_entities = await nebula_storage._execute(query_nGQL, space=space)
            print(f"[OK] 找到 {len(all_entities)} 个实体")
        except Exception as e:
            error_msg = str(e).lower()
            if "space not found" in error_msg or "not exist" in error_msg:
                print(f"[INFO] NebulaGraph空间 {space} 不存在，无需清理")
                return
            else:
                raise
        
        if not all_entities:
            print("[INFO] NebulaGraph中没有实体数据，无需清理")
            return
        
        # 删除所有实体（DELETE VERTEX会自动删除相关的关系）
        print("\n[步骤2] 删除所有实体（会同时删除相关关系）...")
        deleted_count = 0
        failed_count = 0
        
        for idx, entity in enumerate(all_entities):
            vid = str(entity.get('vid', '')).strip('"\'')
            name = entity.get('name', 'N/A')
            
            try:
                await nebula_storage.delete_entity(space, vid)
                deleted_count += 1
                if deleted_count % 50 == 0:
                    print(f"   已删除 {deleted_count}/{len(all_entities)} 个实体...")
            except Exception as e:
                failed_count += 1
                print(f"[WARN] 删除实体失败: vid={vid}, name={name}, 错误={e}")
        
        print(f"\n[OK] 删除完成:")
        print(f"   成功: {deleted_count}")
        print(f"   失败: {failed_count}")
        
        # 验证清理结果
        print("\n[步骤3] 验证清理结果...")
        try:
            remaining_entities = await nebula_storage._execute(query_nGQL, space=space)
            remaining_count = len(remaining_entities)
            if remaining_count == 0:
                print(f"[SUCCESS] NebulaGraph数据已完全清理！")
            else:
                print(f"[WARN] 仍有 {remaining_count} 个实体未清理完成")
        except Exception as e:
            print(f"[INFO] 验证查询完成（可能空间已空或不存在）")
        
    except Exception as e:
        print(f"\n[ERROR] 清理NebulaGraph数据失败: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    try:
        asyncio.run(cleanup_nebula())
        print("\n" + "=" * 60)
        print("[SUCCESS] NebulaGraph清理完成！")
        print("=" * 60)
    except Exception as e:
        print(f"\n[ERROR] 执行失败: {e}")
        sys.exit(1)

