#!/usr/bin/env python3
"""
快速清理知识库4的知识图谱数据
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 在导入前设置环境变量（如果需要）
import os
if not os.environ.get('PYTHONPATH'):
    os.environ['PYTHONPATH'] = str(project_root)

from app.config.database import SessionLocal
from app.models.knowledge_graph import (
    KnowledgeGraphEntity,
    KnowledgeGraphRelationship,
    KnowledgeGraphEntityDocument,
    KnowledgeGraphExtractionTask
)
from sqlalchemy import text

kb_id = 4

print("=" * 60)
print(f"开始清理知识库 {kb_id} 的知识图谱数据...")
print("=" * 60)

db = SessionLocal()

try:
    # 步骤1：删除实体-文档关联
    result = db.execute(text("""
        DELETE FROM knowledge_graph_entity_documents
        WHERE entity_id IN (
            SELECT id FROM knowledge_graph_entities
            WHERE knowledge_base_id = :kb_id AND is_deleted = FALSE
        )
    """), {"kb_id": kb_id})
    count1 = result.rowcount
    print(f"✓ 已删除 {count1} 条实体-文档关联记录")
    
    # 步骤2：删除关系
    result = db.execute(text("""
        DELETE FROM knowledge_graph_relationships
        WHERE knowledge_base_id = :kb_id AND is_deleted = FALSE
    """), {"kb_id": kb_id})
    count2 = result.rowcount
    print(f"✓ 已删除 {count2} 条关系记录")
    
    # 步骤3：删除实体
    result = db.execute(text("""
        DELETE FROM knowledge_graph_entities
        WHERE knowledge_base_id = :kb_id AND is_deleted = FALSE
    """), {"kb_id": kb_id})
    count3 = result.rowcount
    print(f"✓ 已删除 {count3} 条实体记录")
    
    # 步骤4：删除提取任务
    result = db.execute(text("""
        DELETE FROM knowledge_graph_extraction_tasks
        WHERE knowledge_base_id = :kb_id AND is_deleted = FALSE
    """), {"kb_id": kb_id})
    count4 = result.rowcount
    print(f"✓ 已删除 {count4} 条提取任务记录")
    
    db.commit()
    
    print("=" * 60)
    print("✅ MySQL数据清理完成！")
    print(f"   总计删除：{count1 + count2 + count3 + count4} 条记录")
    print("=" * 60)
    print("\n⚠️  注意：还需要清理NebulaGraph中的数据")
    print("   可以运行：python scripts/cleanup_nebula.py --kb-id 4")
    print("   或者使用API：POST /api/knowledge-graph/cleanup/orphaned-data?knowledge_base_id=4")
    
except Exception as e:
    db.rollback()
    print(f"❌ 清理失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    db.close()

