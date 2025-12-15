#!/usr/bin/env python3
"""
知识图谱数据清理脚本
用于清理MySQL和NebulaGraph中的知识图谱数据，以便重新生成

使用方法:
    # 清理所有知识库的数据
    python cleanup_knowledge_graph.py --all
    
    # 清理指定知识库的数据
    python cleanup_knowledge_graph.py --kb-id 4
    
    # 只清理MySQL数据，不清理NebulaGraph
    python cleanup_knowledge_graph.py --kb-id 4 --mysql-only
    
    # 只清理NebulaGraph数据，不清理MySQL
    python cleanup_knowledge_graph.py --kb-id 4 --nebula-only
"""

import sys
import os
import asyncio
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config.database import SessionLocal
from app.models.knowledge_graph import (
    KnowledgeGraphEntity,
    KnowledgeGraphRelationship,
    KnowledgeGraphEntityDocument,
    KnowledgeGraphExtractionTask
)
from app.services.graph_storage_service import get_graph_storage
from app.core.logging import logger


def cleanup_mysql_data(kb_id: int = None, db=None):
    """清理MySQL中的知识图谱数据"""
    should_close = False
    if not db:
        db = SessionLocal()
        should_close = True
    
    try:
        if kb_id:
            logger.info(f"开始清理知识库 {kb_id} 的MySQL数据...")
            
            # 1. 删除实体-文档关联
            entity_ids_query = db.query(KnowledgeGraphEntity.id).filter(
                KnowledgeGraphEntity.knowledge_base_id == kb_id,
                KnowledgeGraphEntity.is_deleted == False
            ).subquery()
            
            deleted_count = db.query(KnowledgeGraphEntityDocument).filter(
                KnowledgeGraphEntityDocument.entity_id.in_(
                    db.query(entity_ids_query.c.id)
                )
            ).delete(synchronize_session=False)
            logger.info(f"已删除 {deleted_count} 条实体-文档关联记录")
            
            # 2. 删除关系
            deleted_count = db.query(KnowledgeGraphRelationship).filter(
                KnowledgeGraphRelationship.knowledge_base_id == kb_id,
                KnowledgeGraphRelationship.is_deleted == False
            ).delete(synchronize_session=False)
            logger.info(f"已删除 {deleted_count} 条关系记录")
            
            # 3. 删除实体
            deleted_count = db.query(KnowledgeGraphEntity).filter(
                KnowledgeGraphEntity.knowledge_base_id == kb_id,
                KnowledgeGraphEntity.is_deleted == False
            ).delete(synchronize_session=False)
            logger.info(f"已删除 {deleted_count} 条实体记录")
            
            # 4. 删除提取任务（可选）
            deleted_count = db.query(KnowledgeGraphExtractionTask).filter(
                KnowledgeGraphExtractionTask.knowledge_base_id == kb_id,
                KnowledgeGraphExtractionTask.is_deleted == False
            ).delete(synchronize_session=False)
            logger.info(f"已删除 {deleted_count} 条提取任务记录")
            
            db.commit()
            logger.info(f"知识库 {kb_id} 的MySQL数据清理完成")
            
        else:
            logger.info("开始清理所有知识库的MySQL数据...")
            
            # 清理所有数据
            deleted_count = db.query(KnowledgeGraphEntityDocument).delete(synchronize_session=False)
            logger.info(f"已删除 {deleted_count} 条实体-文档关联记录")
            
            deleted_count = db.query(KnowledgeGraphRelationship).delete(synchronize_session=False)
            logger.info(f"已删除 {deleted_count} 条关系记录")
            
            deleted_count = db.query(KnowledgeGraphEntity).delete(synchronize_session=False)
            logger.info(f"已删除 {deleted_count} 条实体记录")
            
            deleted_count = db.query(KnowledgeGraphExtractionTask).delete(synchronize_session=False)
            logger.info(f"已删除 {deleted_count} 条提取任务记录")
            
            db.commit()
            logger.info("所有知识库的MySQL数据清理完成")
            
    except Exception as e:
        logger.error(f"清理MySQL数据失败: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        if should_close:
            db.close()


async def cleanup_nebula_data(kb_id: int = None):
    """清理NebulaGraph中的知识图谱数据"""
    nebula_storage = get_graph_storage()
    
    if kb_id:
        space = f"kb_{kb_id}"
        logger.info(f"开始清理知识库 {kb_id} 的NebulaGraph数据 (space: {space})...")
        
        try:
            # 查询所有实体
            query_nGQL = """
            MATCH (n:entity)
            RETURN id(n) as vid
            LIMIT 10000;
            """
            entities = await nebula_storage._execute(query_nGQL, space=space)
            logger.info(f"找到 {len(entities)} 个实体需要删除")
            
            deleted_count = 0
            failed_count = 0
            
            for entity in entities:
                vid = str(entity.get('vid', '')).strip('"\'')
                try:
                    await nebula_storage.delete_entity(space, vid)
                    deleted_count += 1
                    if deleted_count % 100 == 0:
                        logger.info(f"已删除 {deleted_count} 个实体...")
                except Exception as e:
                    failed_count += 1
                    logger.warning(f"删除实体失败: vid={vid}, 错误={e}")
            
            logger.info(f"NebulaGraph清理完成: 成功={deleted_count}, 失败={failed_count}")
            
            # 可选：删除整个空间（完全重建时）
            # drop_space_nGQL = f"DROP SPACE IF EXISTS {space};"
            # await nebula_storage._execute(drop_space_nGQL, space="")  # 需要在root空间执行
            # logger.info(f"已删除NebulaGraph空间: {space}")
            
        except Exception as e:
            if "Space not found" in str(e) or "not exist" in str(e).lower():
                logger.info(f"NebulaGraph空间 {space} 不存在，无需清理")
            else:
                logger.error(f"清理NebulaGraph数据失败: {e}", exc_info=True)
                raise
    else:
        logger.warning("清理所有知识库的NebulaGraph数据需要手动指定知识库ID列表")
        logger.info("请使用 --kb-id 参数逐个清理，或者手动在NebulaGraph中删除空间")


async def main():
    parser = argparse.ArgumentParser(description="清理知识图谱数据")
    parser.add_argument("--all", action="store_true", help="清理所有知识库的数据")
    parser.add_argument("--kb-id", type=int, help="指定要清理的知识库ID")
    parser.add_argument("--mysql-only", action="store_true", help="只清理MySQL数据")
    parser.add_argument("--nebula-only", action="store_true", help="只清理NebulaGraph数据")
    parser.add_argument("--confirm", action="store_true", help="确认执行清理操作（防止误操作）")
    
    args = parser.parse_args()
    
    if not args.confirm:
        print("=" * 60)
        print("⚠️  警告：此操作将删除知识图谱数据！")
        print("=" * 60)
        if args.all:
            print("将清理所有知识库的MySQL和NebulaGraph数据")
        elif args.kb_id:
            print(f"将清理知识库 {args.kb_id} 的MySQL和NebulaGraph数据")
        print("=" * 60)
        print("如果确认执行，请添加 --confirm 参数")
        print("例如: python cleanup_knowledge_graph.py --kb-id 4 --confirm")
        sys.exit(1)
    
    kb_id = None if args.all else args.kb_id
    
    # 清理MySQL数据
    if not args.nebula_only:
        try:
            cleanup_mysql_data(kb_id=kb_id)
        except Exception as e:
            logger.error(f"清理MySQL数据失败: {e}")
            sys.exit(1)
    
    # 清理NebulaGraph数据
    if not args.mysql_only:
        try:
            asyncio.run(cleanup_nebula_data(kb_id=kb_id))
        except Exception as e:
            logger.error(f"清理NebulaGraph数据失败: {e}")
            sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("✅ 数据清理完成！")
    logger.info("=" * 60)
    logger.info("接下来可以重新运行提取任务生成新的知识图谱数据")


if __name__ == "__main__":
    asyncio.run(main())

