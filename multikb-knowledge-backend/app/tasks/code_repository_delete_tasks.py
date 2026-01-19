"""
代码库删除相关任务
包含删除仓库、清理旧仓库等操作
"""

import asyncio
from sqlalchemy import text

from app.tasks.celery_app import celery_app
from app.core.logging import logger
from app.services.git_service import GitService
from app.config.settings import settings
from app.tasks.code_repository_helpers import delete_cache as _delete_cache


@celery_app.task(name='tasks.code_repository_tasks.cleanup_old_repositories')
def cleanup_old_repositories(days: int = 30):
    """
    定期清理旧仓库
    
    Args:
        days: 清理多少天未访问的仓库
    """
    try:
        logger.info(f"开始清理 {days} 天未访问的仓库")
        
        git_service = GitService()
        cleaned = git_service.cleanup_old_repositories(days=days)
        
        logger.info(f"清理完成，共清理 {cleaned} 个仓库")
        
        return {
            'status': 'completed',
            'cleaned_count': cleaned
        }
    
    except Exception as e:
        logger.error(f"清理仓库失败: {e}")
        raise


@celery_app.task(bind=True, name='tasks.code_repository_tasks.delete_repository')
def delete_repository(self, repo_id: int):
    """
    异步删除仓库（彻底删除所有相关数据）
    
    清理范围：
    1. 本地克隆的代码文件（文件系统）
    2. OpenSearch 向量索引（code_files, code_symbols, wiki_content）
    3. NebulaGraph 图数据库（节点和边）
    4. MySQL 数据库记录（所有关联表）
    5. MinIO 对象存储（缓存文件）
    6. Redis 缓存和锁（wiki_generation_lock 等）
    
    Args:
        repo_id: 仓库ID
        
    Returns:
        删除结果
    """
    from app.config.database import engine
    from sqlalchemy.orm import sessionmaker
    from app.models.code_repository import CodeRepository
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        logger.info(f"[Task {self.request.id}] ========== 开始删除仓库 ==========")
        logger.info(f"[Task {self.request.id}] 📦 仓库ID: {repo_id}")
        
        # 检查仓库是否存在
        repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        
        if not repo:
            logger.warning(f"[Task {self.request.id}] ⚠️ 仓库不存在: repo_id={repo_id}")
            return {
                'status': 'error',
                'message': '仓库不存在',
                'repository_id': repo_id
            }
        
        deleted_items = []
        
        # 1. 删除本地代码文件
        try:
            logger.info(f"[Task {self.request.id}] 🗑️ 删除本地代码文件")
            git_service = GitService()
            if git_service.delete_repository(repo_id):
                deleted_items.append("本地代码文件")
                logger.info(f"[Task {self.request.id}] ✅ 已删除本地代码: repo_id={repo_id}")
            else:
                logger.warning(f"[Task {self.request.id}] ⚠️ 本地代码文件不存在或已删除")
        except Exception as e:
            logger.warning(f"[Task {self.request.id}] ⚠️ 删除本地代码失败: {e}")
        
        # 2. 删除 OpenSearch 向量索引
        try:
            logger.info(f"[Task {self.request.id}] 🗑️ 删除 OpenSearch 索引")
            from app.services.opensearch_service import OpenSearchService
            
            opensearch = OpenSearchService()
            
            # 删除代码文件索引
            try:
                try:
                    index_exists = opensearch.client.indices.exists(index='code_files')
                except Exception as check_error:
                    logger.warning(f"[Task {self.request.id}] ⚠️ 检查代码文件索引失败: {check_error}")
                    index_exists = False
                
                if index_exists:
                    opensearch.client.delete_by_query(
                        index='code_files',
                        body={'query': {'term': {'repository_id': repo_id}}},
                        wait_for_completion=True,
                        timeout=60
                    )
                    deleted_items.append("代码文件向量索引")
                    logger.info(f"[Task {self.request.id}] ✅ 已删除代码文件索引: repo_id={repo_id}")
                else:
                    logger.info(f"[Task {self.request.id}] ℹ️ 代码文件索引不存在，跳过")
            except Exception as e:
                error_str = str(e).lower()
                if 'index_not_found_exception' in error_str or 'not_found' in error_str or '404' in error_str:
                    logger.info(f"[Task {self.request.id}] ℹ️ 代码文件索引不存在，跳过")
                else:
                    logger.warning(f"[Task {self.request.id}] ⚠️ 删除代码文件索引失败: {e}")
            
            # 删除代码符号索引
            try:
                try:
                    index_exists = opensearch.client.indices.exists(index='code_symbols')
                except Exception as check_error:
                    logger.warning(f"[Task {self.request.id}] ⚠️ 检查代码符号索引失败: {check_error}")
                    index_exists = False
                
                if index_exists:
                    opensearch.client.delete_by_query(
                        index='code_symbols',
                        body={'query': {'term': {'repository_id': repo_id}}},
                        wait_for_completion=True,
                        timeout=60
                    )
                    deleted_items.append("代码符号向量索引")
                    logger.info(f"[Task {self.request.id}] ✅ 已删除代码符号索引: repo_id={repo_id}")
                else:
                    logger.info(f"[Task {self.request.id}] ℹ️ 代码符号索引不存在，跳过")
            except Exception as e:
                error_str = str(e).lower()
                if 'index_not_found_exception' in error_str or 'not_found' in error_str or '404' in error_str:
                    logger.info(f"[Task {self.request.id}] ℹ️ 代码符号索引不存在，跳过")
                else:
                    logger.warning(f"[Task {self.request.id}] ⚠️ 删除代码符号索引失败: {e}")
            
            # 删除 Wiki 内容索引
            try:
                from opensearch_schemas.code_indices import WIKI_CONTENT_INDEX
                try:
                    wiki_index_exists = opensearch.client.indices.exists(index=WIKI_CONTENT_INDEX)
                except Exception as check_error:
                    logger.warning(f"[Task {self.request.id}] ⚠️ 检查 Wiki 内容索引失败: {check_error}")
                    wiki_index_exists = False
                
                if wiki_index_exists:
                    opensearch.client.delete_by_query(
                        index=WIKI_CONTENT_INDEX,
                        body={'query': {'term': {'repository_id': repo_id}}},
                        wait_for_completion=True,
                        timeout=60
                    )
                    deleted_items.append("Wiki 内容向量索引")
                    logger.info(f"[Task {self.request.id}] ✅ 已删除 Wiki 内容索引: repo_id={repo_id}")
                else:
                    logger.info(f"[Task {self.request.id}] ℹ️ Wiki 内容索引不存在，跳过")
            except Exception as e:
                error_str = str(e).lower()
                if 'index_not_found_exception' in error_str or 'not_found' in error_str or '404' in error_str:
                    logger.info(f"[Task {self.request.id}] ℹ️ Wiki 内容索引不存在，跳过")
                else:
                    logger.warning(f"[Task {self.request.id}] ⚠️ 删除 Wiki 内容索引失败: {e}")
                
        except Exception as e:
            logger.warning(f"[Task {self.request.id}] ⚠️ 清理 OpenSearch 数据失败: {e}")
        
        # 3. 删除 NebulaGraph 图数据库数据
        try:
            logger.info(f"[Task {self.request.id}] 🗑️ 删除 NebulaGraph 数据")
            from app.services.nebula_code_service import get_nebula_code_service
            
            if settings.USE_NEBULA_GRAPH:
                nebula_service = get_nebula_code_service(db)
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        nebula_service.delete_repository_from_graph(repo_id)
                    )
                    
                    if result.get("status") == "success":
                        stats = result.get("deleted_stats", {})
                        repo_count = stats.get('repository_nodes', 0)
                        file_count = stats.get('file_nodes', 0)
                        symbol_count = stats.get('symbol_nodes', 0)
                        deleted_items.append(f"图数据库（仓库:{repo_count}, 文件:{file_count}, 符号:{symbol_count}）")
                        logger.info(f"[Task {self.request.id}] ✅ 已清理图数据库: repo_id={repo_id}")
                    else:
                        logger.warning(f"[Task {self.request.id}] ⚠️ 图数据库清理失败: {result.get('error', 'unknown')}")
                finally:
                    loop.close()
            else:
                logger.info(f"[Task {self.request.id}] ℹ️ 图数据库未启用，跳过清理")
                
        except Exception as e:
            logger.warning(f"[Task {self.request.id}] ⚠️ 清理图数据库失败: {e}")
        
        # 4. 删除分析缓存（code_analysis_cache表，包括 MinIO 文件）
        try:
            logger.info(f"[Task {self.request.id}] 🗑️ 删除分析缓存（MySQL + MinIO）")
            _delete_cache(db, repo_id)
            deleted_items.append("分析缓存数据（MySQL + MinIO）")
            logger.info(f"[Task {self.request.id}] ✅ 已删除分析缓存: repo_id={repo_id}")
        except Exception as e:
            logger.warning(f"[Task {self.request.id}] ⚠️ 删除分析缓存失败: {e}")
        
        # 5. 删除 Redis 缓存和锁
        try:
            logger.info(f"[Task {self.request.id}] 🗑️ 删除 Redis 缓存和锁")
            from app.core.cache import cache_manager
            
            redis_patterns = [
                f"wiki_generation_lock:{repo_id}",
                f"code_repository:{repo_id}:*",
                f"repository:{repo_id}:*",
                f"repo:{repo_id}:*",
            ]
            
            deleted_redis_keys = 0
            for pattern in redis_patterns:
                try:
                    count = cache_manager.delete_pattern(pattern)
                    deleted_redis_keys += count
                    if count > 0:
                        logger.debug(f"[Task {self.request.id}] 已删除 Redis 键: {pattern} ({count} 个)")
                except Exception as pattern_error:
                    logger.warning(f"[Task {self.request.id}] 删除 Redis 模式失败: {pattern}, 错误: {pattern_error}")
            
            try:
                lock_key = f"wiki_generation_lock:{repo_id}"
                cache_manager.redis_client.delete(lock_key)
                deleted_redis_keys += 1
            except Exception as lock_error:
                logger.debug(f"[Task {self.request.id}] 删除锁键失败（可能不存在）: {lock_error}")
            
            if deleted_redis_keys > 0:
                deleted_items.append(f"Redis 缓存和锁（{deleted_redis_keys} 个键）")
                logger.info(f"[Task {self.request.id}] ✅ 已删除 Redis 缓存和锁: {deleted_redis_keys} 个键")
            else:
                logger.info(f"[Task {self.request.id}] ℹ️ 未找到需要删除的 Redis 键")
        except Exception as e:
            logger.warning(f"[Task {self.request.id}] ⚠️ 删除 Redis 缓存失败: {e}")
        
        # 6. 删除关联映射（code_kb_mappings表）
        try:
            logger.info(f"[Task {self.request.id}] 🗑️ 删除知识库关联映射")
            db.execute(
                text("DELETE FROM code_kb_mappings WHERE code_file_id IN (SELECT id FROM code_files WHERE repository_id = :repo_id) OR code_symbol_id IN (SELECT id FROM code_symbols WHERE repository_id = :repo_id)"),
                {"repo_id": repo_id}
            )
            deleted_items.append("知识库关联映射")
            logger.info(f"[Task {self.request.id}] ✅ 已删除知识库映射: repo_id={repo_id}")
        except Exception as e:
            logger.warning(f"[Task {self.request.id}] ⚠️ 删除知识库映射失败: {e}")
        
        # 7. 删除代码文件记录（code_files表）
        try:
            logger.info(f"[Task {self.request.id}] 🗑️ 删除代码文件记录")
            db.execute(
                text("DELETE FROM code_files WHERE repository_id = :repo_id"),
                {"repo_id": repo_id}
            )
            deleted_items.append("代码文件记录")
            logger.info(f"[Task {self.request.id}] ✅ 已删除代码文件记录: repo_id={repo_id}")
        except Exception as e:
            logger.warning(f"[Task {self.request.id}] ⚠️ 删除代码文件记录失败: {e}")
        
        # 8. 删除代码符号记录（code_symbols表）
        try:
            logger.info(f"[Task {self.request.id}] 🗑️ 删除代码符号记录")
            db.execute(
                text("DELETE FROM code_symbols WHERE repository_id = :repo_id"),
                {"repo_id": repo_id}
            )
            deleted_items.append("代码符号记录")
            logger.info(f"[Task {self.request.id}] ✅ 已删除代码符号记录: repo_id={repo_id}")
        except Exception as e:
            logger.warning(f"[Task {self.request.id}] ⚠️ 删除代码符号记录失败: {e}")
        
        # 9. 删除依赖关系记录（code_dependencies表）
        try:
            logger.info(f"[Task {self.request.id}] 🗑️ 删除依赖关系记录")
            db.execute(
                text("DELETE FROM code_dependencies WHERE repository_id = :repo_id"),
                {"repo_id": repo_id}
            )
            deleted_items.append("依赖关系记录")
            logger.info(f"[Task {self.request.id}] ✅ 已删除依赖关系: repo_id={repo_id}")
        except Exception as e:
            logger.warning(f"[Task {self.request.id}] ⚠️ 删除依赖关系失败: {e}")
        
        # 10. 最后删除仓库主记录（code_repositories表）
        logger.info(f"[Task {self.request.id}] 🗑️ 删除仓库主记录")
        db.execute(
            text("DELETE FROM code_repositories WHERE id = :repo_id"),
            {"repo_id": repo_id}
        )
        db.commit()
        deleted_items.append("仓库主记录")
        
        logger.info(f"[Task {self.request.id}] ========== ✅ 硬删除完成 ==========")
        logger.info(f"[Task {self.request.id}] 📊 已清理: {', '.join(deleted_items)}")
        
        return {
            'status': 'completed',
            'message': '硬删除成功',
            'deleted_items': deleted_items,
            'repository_id': repo_id
        }
    
    except Exception as e:
        logger.error(f"[Task {self.request.id}] ❌ 硬删除仓库失败: {e}", exc_info=True)
        db.rollback()
        return {
            'status': 'error',
            'message': f'删除仓库失败: {str(e)}',
            'repository_id': repo_id
        }
    finally:
        db.close()
