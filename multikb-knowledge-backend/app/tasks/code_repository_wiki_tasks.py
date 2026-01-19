"""
代码库 Wiki 相关任务
包含 Wiki 内容生成、索引等操作
"""

import json
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.tasks.celery_app import celery_app
from app.core.logging import logger
from app.services.code_analyzer_service import CodeAnalyzerService
from app.tasks.code_repository_helpers import (
    get_cache_data as _get_cache_data,
    save_cache_with_retry as _save_cache_with_retry
)


async def _index_wiki_content_to_opensearch(task_self, repo_id: int, repo_name: str, wiki_content: Dict):
    """
    将 Wiki 内容索引到 OpenSearch（用于语义搜索）
    
    Args:
        task_self: 任务实例
        repo_id: 仓库ID
        repo_name: 仓库名称
        wiki_content: Wiki 内容字典
    """
    try:
        from app.services.opensearch_service import OpenSearchService
        from app.services.vector_service import VectorService
        from opensearch_schemas.code_indices import WIKI_CONTENT_INDEX, WIKI_CONTENT_INDEX_CONFIG
        
        opensearch = OpenSearchService()
        vector_service = VectorService(db=None)
        
        # 确保索引存在
        index_exists = await opensearch.index_exists(WIKI_CONTENT_INDEX)
        if not index_exists:
            await opensearch.create_index(WIKI_CONTENT_INDEX, WIKI_CONTENT_INDEX_CONFIG)
            logger.info(f"[Task {task_self.request.id}] 创建 Wiki 内容索引: {WIKI_CONTENT_INDEX}")
        
        # 先删除该仓库的旧 Wiki 内容
        try:
            await opensearch.delete_by_query(
                WIKI_CONTENT_INDEX,
                {
                    "query": {
                        "term": {"repository_id": repo_id}
                    }
                }
            )
        except Exception as e:
            logger.warning(f"[Task {task_self.request.id}] 删除旧 Wiki 内容失败（可能不存在）: {e}")
        
        # 索引各个部分的 Wiki 内容
        indexed_count = 0
        now = datetime.now().isoformat()
        
        # 1. 项目概述
        if wiki_content.get('project_overview'):
            content_text = wiki_content['project_overview']
            vector = vector_service.generate_embedding(content_text)
            doc = {
                "repository_id": repo_id,
                "repo_name": repo_name,
                "content_type": "project_overview",
                "content_title": "项目概述",
                "content_text": content_text,
                "content_vector": vector,
                "section": "base",
                "created_at": now,
                "updated_at": now
            }
            await opensearch.index_document(
                WIKI_CONTENT_INDEX,
                f"wiki_{repo_id}_project_overview",
                doc
            )
            indexed_count += 1
        
        # 2. 项目是什么
        if wiki_content.get('what_is_project'):
            content_text = wiki_content['what_is_project']
            vector = vector_service.generate_embedding(content_text)
            doc = {
                "repository_id": repo_id,
                "repo_name": repo_name,
                "content_type": "what_is_project",
                "content_title": "项目是什么",
                "content_text": content_text,
                "content_vector": vector,
                "section": "base",
                "created_at": now,
                "updated_at": now
            }
            await opensearch.index_document(
                WIKI_CONTENT_INDEX,
                f"wiki_{repo_id}_what_is_project",
                doc
            )
            indexed_count += 1
        
        # 3. 系统架构
        if wiki_content.get('system_architecture'):
            arch = wiki_content['system_architecture']
            if arch.get('three_tier_architecture'):
                content_text = arch['three_tier_architecture']
                vector = vector_service.generate_embedding(content_text)
                doc = {
                    "repository_id": repo_id,
                    "repo_name": repo_name,
                    "content_type": "system_architecture",
                    "content_title": "三层架构说明",
                    "content_text": content_text,
                    "content_vector": vector,
                    "section": "architecture",
                    "created_at": now,
                    "updated_at": now
                }
                await opensearch.index_document(
                    WIKI_CONTENT_INDEX,
                    f"wiki_{repo_id}_three_tier_architecture",
                    doc
                )
                indexed_count += 1
            
            if arch.get('architectural_patterns'):
                content_text = arch['architectural_patterns']
                vector = vector_service.generate_embedding(content_text)
                doc = {
                    "repository_id": repo_id,
                    "repo_name": repo_name,
                    "content_type": "architectural_patterns",
                    "content_title": "架构模式",
                    "content_text": content_text,
                    "content_vector": vector,
                    "section": "architecture",
                    "created_at": now,
                    "updated_at": now
                }
                await opensearch.index_document(
                    WIKI_CONTENT_INDEX,
                    f"wiki_{repo_id}_architectural_patterns",
                    doc
                )
                indexed_count += 1
        
        # 4. 技术栈
        if wiki_content.get('technology_stack'):
            tech = wiki_content['technology_stack']
            if tech.get('core_technologies'):
                content_text = tech['core_technologies']
                vector = vector_service.generate_embedding(content_text)
                doc = {
                    "repository_id": repo_id,
                    "repo_name": repo_name,
                    "content_type": "tech_stack",
                    "content_title": "核心技术栈",
                    "content_text": content_text,
                    "content_vector": vector,
                    "section": "tech_stack",
                    "created_at": now,
                    "updated_at": now
                }
                await opensearch.index_document(
                    WIKI_CONTENT_INDEX,
                    f"wiki_{repo_id}_tech_stack",
                    doc
                )
                indexed_count += 1
        
        # 5. 组件关系
        if wiki_content.get('component_relationships'):
            rel = wiki_content['component_relationships']
            if rel.get('component_relationships'):
                content_text = rel['component_relationships']
                vector = vector_service.generate_embedding(content_text)
                doc = {
                    "repository_id": repo_id,
                    "repo_name": repo_name,
                    "content_type": "component_relationships",
                    "content_title": "组件关系",
                    "content_text": content_text,
                    "content_vector": vector,
                    "section": "relationships",
                    "created_at": now,
                    "updated_at": now
                }
                await opensearch.index_document(
                    WIKI_CONTENT_INDEX,
                    f"wiki_{repo_id}_component_relationships",
                    doc
                )
                indexed_count += 1
        
        # 6. 快速开始指南
        if wiki_content.get('getting_started'):
            gs = wiki_content['getting_started']
            if gs.get('quick_start_summary'):
                content_text = gs['quick_start_summary']
                vector = vector_service.generate_embedding(content_text)
                doc = {
                    "repository_id": repo_id,
                    "repo_name": repo_name,
                    "content_type": "getting_started",
                    "content_title": "快速开始指南",
                    "content_text": content_text,
                    "content_vector": vector,
                    "section": "getting_started",
                    "created_at": now,
                    "updated_at": now
                }
                await opensearch.index_document(
                    WIKI_CONTENT_INDEX,
                    f"wiki_{repo_id}_getting_started",
                    doc
                )
                indexed_count += 1
            
            if gs.get('installation_steps'):
                steps_text = "\n".join([
                    f"{step.get('step', '')}: {step.get('description', '')}"
                    for step in gs['installation_steps']
                ])
                if steps_text.strip():
                    vector = vector_service.generate_embedding(steps_text)
                    doc = {
                        "repository_id": repo_id,
                        "repo_name": repo_name,
                        "content_type": "installation_steps",
                        "content_title": "安装步骤",
                        "content_text": steps_text,
                        "content_vector": vector,
                        "section": "getting_started",
                        "created_at": now,
                        "updated_at": now
                    }
                    await opensearch.index_document(
                        WIKI_CONTENT_INDEX,
                        f"wiki_{repo_id}_installation_steps",
                        doc
                    )
                    indexed_count += 1
        
        # 7. 核心组件
        if wiki_content.get('core_components'):
            for idx, component in enumerate(wiki_content['core_components'][:10]):
                if component.get('purpose'):
                    content_text = f"{component.get('name', '')}: {component.get('purpose', '')}"
                    vector = vector_service.generate_embedding(content_text)
                    doc = {
                        "repository_id": repo_id,
                        "repo_name": repo_name,
                        "content_type": "core_component",
                        "content_title": f"核心组件: {component.get('name', '')}",
                        "content_text": content_text,
                        "content_vector": vector,
                        "section": "components",
                        "created_at": now,
                        "updated_at": now
                    }
                    await opensearch.index_document(
                        WIKI_CONTENT_INDEX,
                        f"wiki_{repo_id}_component_{idx}",
                        doc
                    )
                    indexed_count += 1
        
        # 8. 价值主张
        if wiki_content.get('value_propositions'):
            for idx, prop in enumerate(wiki_content['value_propositions'][:5]):
                if prop.get('description'):
                    content_text = f"{prop.get('feature', '')}: {prop.get('description', '')}"
                    vector = vector_service.generate_embedding(content_text)
                    doc = {
                        "repository_id": repo_id,
                        "repo_name": repo_name,
                        "content_type": "value_proposition",
                        "content_title": f"价值主张: {prop.get('feature', '')}",
                        "content_text": content_text,
                        "content_vector": vector,
                        "section": "base",
                        "created_at": now,
                        "updated_at": now
                    }
                    await opensearch.index_document(
                        WIKI_CONTENT_INDEX,
                        f"wiki_{repo_id}_value_prop_{idx}",
                        doc
                    )
                    indexed_count += 1
        
        logger.info(f"[Task {task_self.request.id}] ✅ Wiki 内容索引完成: repo_id={repo_id}, 索引文档数={indexed_count}")
        
    except Exception as e:
        logger.error(f"[Task {task_self.request.id}] 索引 Wiki 内容到 OpenSearch 失败: {e}", exc_info=True)
        raise


@celery_app.task(name='tasks.code_repository_tasks.delayed_release_wiki_lock')
def delayed_release_wiki_lock(lock_key: str, lock_value: str, repo_id: int):
    """
    延迟释放 Wiki 生成锁的后台任务
    
    Args:
        lock_key: 锁的键
        lock_value: 锁的值
        repo_id: 仓库ID
    """
    import asyncio
    from app.core.cache import cache_manager
    
    # 等待30秒，给前端足够时间读取缓存
    time.sleep(30)
    
    # 释放锁
    try:
        asyncio.run(cache_manager.release_lock(lock_key, value=lock_value))
        logger.debug(f"已释放 Wiki 生成锁: repo_id={repo_id}")
    except Exception as lock_err:
        logger.warning(f"释放 Wiki 生成锁失败: repo_id={repo_id}, 错误={lock_err}")


@celery_app.task(bind=True, name='tasks.code_repository_tasks.generate_wiki_content')
def generate_wiki_content(self, repo_id: int):
    """
    异步生成 Wiki 内容
    
    Args:
        repo_id: 仓库ID
        
    Returns:
        Wiki 内容
    """
    from app.config.database import engine
    from app.models.code_repository import CodeRepository
    from sqlalchemy.orm import sessionmaker
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    from app.core.cache import cache_manager
    from typing import Dict
    
    lock_key = f"wiki_generation_lock:{repo_id}"
    lock_timeout = 900  # 15分钟超时
    lock_value = str(self.request.id)
    
    # 先检查缓存（向后兼容：如果表没有 minio_path 字段，降级到只查询 cache_data）
    try:
        result = db.execute(
            text("""SELECT cache_data, minio_path, created_at FROM code_analysis_cache 
            WHERE repository_id = :repo_id AND cache_type = 'wiki_content' AND cache_key = 'full'
            AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY created_at DESC LIMIT 1"""),
            {"repo_id": repo_id}
        )
        cached = result.fetchone()
        if cached:
            cache_data_json, minio_path, created_at = cached
            minio_path_str = minio_path or 'MySQL' if minio_path is not None else 'MySQL'
    except Exception as e:
        # 如果查询失败（可能是表没有 minio_path 字段），降级到不包含 minio_path 的查询
        if 'minio_path' in str(e).lower() or 'unknown column' in str(e).lower():
            logger.debug(f"[Task {self.request.id}] 表结构不支持 minio_path，使用降级查询")
            result = db.execute(
                text("""SELECT cache_data, created_at FROM code_analysis_cache 
                WHERE repository_id = :repo_id AND cache_type = 'wiki_content' AND cache_key = 'full'
                AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY created_at DESC LIMIT 1"""),
                {"repo_id": repo_id}
            )
            cached = result.fetchone()
            if cached:
                cache_data_json, created_at = cached
                minio_path = None
                minio_path_str = 'MySQL'
        else:
            raise
    
    if cached:
        logger.info(f"[Task {self.request.id}] ✅ Wiki 内容已存在且未过期，跳过生成: repo_id={repo_id}, created_at={created_at}, minio_path={minio_path_str}")
        db.close()
        return {
            'status': 'skipped',
            'repository_id': repo_id,
            'message': 'Wiki 内容已存在且未过期，跳过生成',
            'cached': True
        }
    
    # 尝试获取锁
    lock_acquired = asyncio.run(cache_manager.acquire_lock(lock_key, timeout=lock_timeout, value=lock_value))
    
    if not lock_acquired:
        logger.warning(f"[Task {self.request.id}] Wiki 生成任务已在运行中，跳过: repo_id={repo_id}")
        db.close()
        return {
            'status': 'skipped',
            'repository_id': repo_id,
            'message': '已有任务正在运行，跳过本次执行'
        }
    
    try:
        logger.info(f"[Task {self.request.id}] 开始生成 Wiki 内容: repo_id={repo_id}")
        
        # 1. 获取仓库路径
        repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        
        if not repo:
            logger.warning(f"[Task {self.request.id}] 仓库 {repo_id} 不存在，跳过 Wiki 生成（可能已被删除）")
            return {
                'status': 'skipped',
                'repository_id': repo_id,
                'message': '仓库不存在，跳过 Wiki 生成'
            }
        
        if not repo.local_path:
            logger.warning(f"[Task {self.request.id}] 仓库 {repo_id} 未克隆，跳过 Wiki 生成")
            return {
                'status': 'skipped',
                'repository_id': repo_id,
                'message': '仓库未克隆，跳过 Wiki 生成'
            }
        
        # 2. 更新任务进度
        self.update_state(
            state='PROGRESS',
            meta={'progress': 0.1, 'stage': 'analyzing'}
        )
        
        # 3. 生成 Wiki 内容
        analyzer = CodeAnalyzerService()
        # 传递 db 和 repository_id 参数以支持 LLM 缓存
        analyzer.wiki_generator.db = db
        analyzer.wiki_generator.repository_id = repo_id
        analyzer.architecture_analyzer.db = db
        analyzer.architecture_analyzer.repository_id = repo_id
        wiki_content = analyzer.generate_wiki_content(repo.local_path, repo.repo_name)
        
        # 4. 更新任务进度
        self.update_state(
            state='PROGRESS',
            meta={'progress': 1.0, 'stage': 'completed'}
        )
        
        # 5. 缓存结果（24小时）
        expires_at = datetime.now() + timedelta(hours=24)
        
        logger.info(f"[Task {self.request.id}] 📦 Wiki 内容结构: "
                   f"system_architecture存在={bool(wiki_content.get('system_architecture'))}, "
                   f"getting_started存在={bool(wiki_content.get('getting_started'))}")
        
        if wiki_content.get('system_architecture'):
            arch = wiki_content['system_architecture']
            logger.info(f"[Task {self.request.id}] 📊 system_architecture 结构: "
                       f"子系统={len(arch.get('functional_subsystems_table', []))}, "
                       f"存储系统={len(arch.get('storage_systems_table', []))}, "
                       f"架构决策={len(arch.get('key_architectural_decisions', []))}")
        
        if wiki_content.get('getting_started'):
            gs = wiki_content['getting_started']
            logger.info(f"[Task {self.request.id}] 📊 getting_started 结构: "
                       f"前置条件={len(gs.get('prerequisites', []))}, "
                       f"安装步骤={len(gs.get('installation_steps', []))}, "
                       f"运行命令={'已设置' if gs.get('run_project_command') else '未设置'}")
        
        wiki_content_json = json.dumps(wiki_content)
        
        # 检查数据大小
        data_size_mb = len(wiki_content_json.encode('utf-8')) / (1024 * 1024)
        logger.info(f"[Task {self.request.id}] Wiki 内容大小: {data_size_mb:.2f} MB")
        
        if data_size_mb > 50:
            logger.warning(f"[Task {self.request.id}] Wiki 内容过大（{data_size_mb:.2f}MB），只存储关键信息")
            reduced_content = {
                'project_overview': wiki_content.get('project_overview', ''),
                'what_is_project': wiki_content.get('what_is_project', ''),
                'core_components': wiki_content.get('core_components', []),
                'value_propositions': wiki_content.get('value_propositions', []),
                'key_features': wiki_content.get('key_features', []),
                'getting_started': wiki_content.get('getting_started', {}),
                'system_architecture': wiki_content.get('system_architecture', {}),
                'technology_stack': {
                    'core_technologies': wiki_content.get('technology_stack', {}).get('core_technologies', ''),
                } if wiki_content.get('technology_stack') else {},
                'statistics': wiki_content.get('statistics', {}) if 'statistics' in wiki_content else {}
            }
            wiki_content_json = json.dumps(reduced_content)
            logger.info(f"[Task {self.request.id}] 📦 精简后的 Wiki 内容大小: {len(wiki_content_json.encode('utf-8')) / (1024 * 1024):.2f} MB")
        
        # 在保存缓存前再次检查仓库是否存在
        repo_check = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        if not repo_check:
            logger.warning(f"[Task {self.request.id}] 仓库 {repo_id} 不存在，跳过缓存保存（可能已被删除）")
            return {
                'status': 'skipped',
                'repository_id': repo_id,
                'message': '仓库不存在，跳过缓存保存'
            }
        
        # 使用重试机制保存
        try:
            logger.info(f"[Task {self.request.id}] 💾 开始保存 Wiki 内容到数据库: "
                       f"repo_id={repo_id}, cache_type=wiki_content, cache_key=full, "
                       f"数据大小={data_size_mb:.2f}MB")
            
            with engine.connect() as conn:
                _save_cache_with_retry(conn, repo_id, 'wiki_content', 'full', wiki_content_json, expires_at, max_retries=3)
                conn.commit()
            
            logger.info(f"[Task {self.request.id}] ✅ Wiki 内容已保存到数据库: "
                       f"repo_id={repo_id}, 表=code_analysis_cache, cache_type=wiki_content")
            
            # 验证入库后的数据
            try:
                cached_data = _get_cache_data(db, repo_id, 'wiki_content', 'full')
                if cached_data:
                    data_str = json.dumps(cached_data) if isinstance(cached_data, dict) else str(cached_data)
                    logger.debug(f"[Task {self.request.id}] 入库后验证 - 从缓存读取成功，数据大小={len(data_str)} 字符")
                    if cached_data.get('system_architecture'):
                        cached_arch = cached_data['system_architecture']
                        logger.debug(f"[Task {self.request.id}] 入库后验证 - system_architecture 字段完整: "
                                   f"子系统={len(cached_arch.get('functional_subsystems_table', []))}, "
                                   f"存储系统={len(cached_arch.get('storage_systems_table', []))}, "
                                   f"决策={len(cached_arch.get('key_architectural_decisions', []))}")
            except Exception as e:
                logger.warning(f"[Task {self.request.id}] ⚠️ 入库后验证失败: {e}")
        except IntegrityError as e:
            error_code = e.orig.args[0] if hasattr(e, 'orig') and hasattr(e.orig, 'args') and len(e.orig.args) > 0 else None
            if error_code == 1452 and 'foreign key constraint fails' in str(e).lower():
                logger.warning(f"[Task {self.request.id}] 仓库 {repo_id} 不存在，跳过缓存保存（可能已被删除）")
                db.rollback()
                return {
                    'status': 'skipped',
                    'repository_id': repo_id,
                    'message': '仓库不存在，跳过缓存保存'
                }
            else:
                raise
        except OperationalError as e:
            error_code = e.orig.args[0] if hasattr(e, 'orig') and hasattr(e.orig, 'args') else None
            if error_code in (2006, 2013) or 'gone away' in str(e).lower():
                logger.warning(f"[Task {self.request.id}] 数据库连接断开，重新连接后重试")
                db.rollback()
                db.close()
                from app.config.database import engine
                from sqlalchemy.orm import sessionmaker
                SessionLocal = sessionmaker(bind=engine)
                db = SessionLocal()
                repo_check = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
                if not repo_check:
                    logger.warning(f"[Task {self.request.id}] 仓库 {repo_id} 不存在，跳过缓存保存")
                    db.close()
                    return {
                        'status': 'skipped',
                        'repository_id': repo_id,
                        'message': '仓库不存在，跳过缓存保存'
                    }
                with engine.connect() as conn:
                    _save_cache_with_retry(conn, repo_id, 'wiki_content', 'full', wiki_content_json, expires_at, max_retries=3)
                    conn.commit()
            else:
                raise
        
        # 6. 索引 Wiki 内容到 OpenSearch
        try:
            logger.info(f"[Task {self.request.id}] 开始索引 Wiki 内容到 OpenSearch: repo_id={repo_id}")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_index_wiki_content_to_opensearch(self, repo_id, repo.repo_name, wiki_content))
                logger.info(f"[Task {self.request.id}] ✅ Wiki 内容已索引到 OpenSearch: repo_id={repo_id}")
            finally:
                loop.close()
        except Exception as e:
            logger.warning(f"[Task {self.request.id}] ⚠️ Wiki 内容索引到 OpenSearch 失败: {e}", exc_info=True)
        
        logger.info(f"[Task {self.request.id}] Wiki 内容生成完成: repo_id={repo_id}")
        
        return {
            'status': 'completed',
            'repository_id': repo_id,
            'result': wiki_content
        }
    
    except Exception as e:
        logger.error(f"[Task {self.request.id}] Wiki 内容生成失败: {e}", exc_info=True)
        return {
            'status': 'failed',
            'repository_id': repo_id,
            'error': str(e)
        }
    finally:
        db.close()
        
        # 使用后台任务延迟释放锁（30秒后）
        try:
            delayed_release_wiki_lock.apply_async(
                args=[lock_key, lock_value, repo_id],
                countdown=30
            )
            logger.debug(f"[Task {self.request.id}] 已安排延迟释放锁任务（30秒后）: repo_id={repo_id}")
        except Exception as delay_task_err:
            logger.warning(f"[Task {self.request.id}] 发送延迟释放锁任务失败，立即释放锁: {delay_task_err}")
            try:
                asyncio.run(cache_manager.release_lock(lock_key, value=lock_value))
                logger.debug(f"[Task {self.request.id}] 已立即释放 Wiki 生成锁: repo_id={repo_id}")
            except Exception as lock_err:
                logger.warning(f"[Task {self.request.id}] 释放锁失败: {lock_err}")
