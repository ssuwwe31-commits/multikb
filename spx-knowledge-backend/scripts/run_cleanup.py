#!/usr/bin/env python3
"""
执行清理操作的简化脚本
直接调用cleanup_knowledge_graph.py的逻辑，不依赖命令行参数解析
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入清理函数
from scripts.cleanup_knowledge_graph import cleanup_mysql_data, cleanup_nebula_data

kb_id = 4

print("=" * 60)
print(f"开始清理知识库 {kb_id} 的知识图谱数据...")
print("=" * 60)

try:
    # 清理MySQL数据
    print("\n[步骤1] 清理MySQL数据...")
    cleanup_mysql_data(kb_id=kb_id)
    print("✓ MySQL数据清理完成\n")
    
    # 清理NebulaGraph数据
    print("[步骤2] 清理NebulaGraph数据...")
    asyncio.run(cleanup_nebula_data(kb_id=kb_id))
    print("✓ NebulaGraph数据清理完成\n")
    
    print("=" * 60)
    print("✅ 所有数据清理完成！")
    print("=" * 60)
    print("\n💡 提示：接下来可以重新运行提取任务生成新的知识图谱数据")
    
except Exception as e:
    print(f"\n❌ 清理失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

