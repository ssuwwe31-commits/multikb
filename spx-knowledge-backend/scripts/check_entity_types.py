#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库中的实体类型数据
"""
import sys
import os
from pathlib import Path

# 设置输出编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from app.config.settings import settings

def check_entity_types():
    """检查实体类型数据"""
    # 构建数据库连接URL
    db_url = settings.DATABASE_URL
    if not db_url or "user:password" in db_url:
        # 如果使用默认值，尝试从环境变量构建
        db_url = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    
    print(f"连接数据库: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")
    print(f"用户: {settings.MYSQL_USER}")
    
    try:
        engine = create_engine(db_url, echo=False)
        
        with engine.connect() as conn:
            # 检查 entity_types 表是否存在
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = :db_name 
                AND table_name = 'entity_types'
            """), {"db_name": settings.MYSQL_DATABASE})
            
            table_exists = result.fetchone()[0] > 0
            
            if not table_exists:
                print("[ERROR] entity_types 表不存在！")
                return
            
            print("[OK] entity_types 表存在")
            
            # 查询所有实体类型
            result = conn.execute(text("""
                SELECT 
                    id, code, name, level, parent_id, 
                    is_enabled, is_system, is_deleted,
                    created_at
                FROM entity_types
                ORDER BY level, id
            """))
            
            types = result.fetchall()
            print(f"\n[实体类型总数]: {len(types)}")
            
            if len(types) == 0:
                print("[ERROR] 数据库中没有实体类型数据！")
                print("\n建议：")
                print("1. 运行迁移脚本创建默认实体类型")
                print("2. 或使用行业模板创建实体类型")
                return
            
            # 按层级统计
            level_stats = {}
            enabled_count = 0
            disabled_count = 0
            system_count = 0
            user_count = 0
            
            for type_row in types:
                level = type_row[3] or 0
                is_enabled = type_row[5]
                is_system = type_row[6]
                
                level_stats[level] = level_stats.get(level, 0) + 1
                if is_enabled:
                    enabled_count += 1
                else:
                    disabled_count += 1
                if is_system:
                    system_count += 1
                else:
                    user_count += 1
            
            print(f"\n[统计信息]")
            print(f"  - 启用的类型: {enabled_count}")
            print(f"  - 禁用的类型: {disabled_count}")
            print(f"  - 系统类型: {system_count}")
            print(f"  - 用户类型: {user_count}")
            print(f"\n[按层级分布]")
            for level in sorted(level_stats.keys()):
                print(f"  - {level}级分类: {level_stats[level]}个")
            
            # 显示前10个实体类型
            print(f"\n[实体类型列表（前10个）]")
            for i, type_row in enumerate(types[:10], 1):
                type_id, code, name, level, parent_id, is_enabled, is_system, is_deleted, created_at = type_row
                status = "[启用]" if is_enabled else "[禁用]"
                sys_flag = "系统" if is_system else "用户"
                deleted_flag = "已删除" if is_deleted else "正常"
                print(f"  {i}. [{code}] {name} (level={level}, {status}, {sys_flag}, {deleted_flag})")
            
            if len(types) > 10:
                print(f"  ... 还有 {len(types) - 10} 个类型")
            
            # 检查知识库实体类型配置
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = :db_name 
                AND table_name = 'knowledge_base_entity_types'
            """), {"db_name": settings.MYSQL_DATABASE})
            
            kb_config_exists = result.fetchone()[0] > 0
            
            if kb_config_exists:
                result = conn.execute(text("""
                    SELECT 
                        kb.knowledge_base_id,
                        kb.entity_type_id,
                        kb.is_enabled,
                        et.code,
                        et.name
                    FROM knowledge_base_entity_types kb
                    JOIN entity_types et ON kb.entity_type_id = et.id
                    ORDER BY kb.knowledge_base_id, kb.entity_type_id
                """))
                
                kb_configs = result.fetchall()
                print(f"\n[知识库实体类型配置总数]: {len(kb_configs)}")
                
                if len(kb_configs) > 0:
                    kb_stats = {}
                    for config in kb_configs:
                        kb_id = config[0]
                        is_enabled = config[2]
                        if kb_id not in kb_stats:
                            kb_stats[kb_id] = {"enabled": 0, "disabled": 0}
                        if is_enabled:
                            kb_stats[kb_id]["enabled"] += 1
                        else:
                            kb_stats[kb_id]["disabled"] += 1
                    
                    print(f"\n[按知识库统计]")
                    for kb_id in sorted(kb_stats.keys()):
                        stats = kb_stats[kb_id]
                        print(f"  - 知识库ID {kb_id}: {stats['enabled']}个启用, {stats['disabled']}个禁用")
                else:
                    print("[WARNING] 没有知识库配置实体类型")
            
    except Exception as e:
        print(f"[ERROR] 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_entity_types()
