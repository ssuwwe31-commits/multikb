"""
代码库分析相关任务
包含 Agent 分析、代码结构分析等任务
"""

import json
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.tasks.celery_app import celery_app
from app.core.logging import logger
from app.services.code_analyzer_service import CodeAnalyzerService
from app.services.code_analysis_agent_v2 import CodeAnalysisAgentV2
from app.tasks.code_repository_helpers import (
    get_cache_data as _get_cache_data,
    save_cache_with_retry as _save_cache_with_retry
)


@celery_app.task(bind=True, name='tasks.code_repository_tasks.analyze_with_agent')
def analyze_with_agent(self, repo_id: int, use_cache: bool = True):
    """
    使用 Agent 异步分析代码库（智能决策和迭代优化）
    
    Args:
        repo_id: 仓库ID
        use_cache: 是否使用缓存
        
    Returns:
        Agent 分析结果
    """
    from app.config.database import engine
    from app.models.code_repository import CodeRepository
    from sqlalchemy.orm import sessionmaker
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        logger.info(f"[Task {self.request.id}] 开始 Agent 分析: repo_id={repo_id}")
        
        # 1. 检查缓存
        if use_cache:
            cached_data = _get_cache_data(db, repo_id, 'agent_analysis', 'full')
            
            if cached_data:
                logger.info(f"[Task {self.request.id}] 使用缓存的 Agent 分析结果: repo_id={repo_id}")
                return {
                    'status': 'completed',
                    'repository_id': repo_id,
                    'from_cache': True,
                    'result': cached_data
                }
        
        # 2. 获取仓库路径
        repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        
        if not repo:
            logger.warning(f"[Task {self.request.id}] 仓库 {repo_id} 不存在，跳过 Agent 分析（可能已被删除）")
            return {
                'status': 'skipped',
                'repository_id': repo_id,
                'message': '仓库不存在，跳过 Agent 分析'
            }
        
        if not repo.local_path:
            logger.warning(f"[Task {self.request.id}] 仓库 {repo_id} 未克隆，跳过 Agent 分析")
            return {
                'status': 'skipped',
                'repository_id': repo_id,
                'message': '仓库未克隆，跳过 Agent 分析'
            }
        
        # 3. 更新任务进度
        self.update_state(
            state='PROGRESS',
            meta={'progress': 0.1, 'stage': 'observing'}
        )
        
        # 4. 使用 Agent V2 分析
        logger.info(f"[Task {self.request.id}] 使用 Agent V2 分析代码库: repo_id={repo_id}, path={repo.local_path}")
        agent = CodeAnalysisAgentV2(db=db)
        
        self.update_state(
            state='PROGRESS',
            meta={'progress': 0.2, 'stage': 'thinking'}
        )
        
        agent_result = agent.analyze_repository(repo.local_path)
        
        self.update_state(
            state='PROGRESS',
            meta={'progress': 1.0, 'stage': 'completed'}
        )
        
        # 5. 缓存结果（2小时）
        expires_at = datetime.now() + timedelta(hours=2)
        agent_result_json = json.dumps(agent_result)
        
        data_size_mb = len(agent_result_json.encode('utf-8')) / (1024 * 1024)
        if data_size_mb > 50:
            logger.warning(f"[Task {self.request.id}] Agent 结果数据过大 ({data_size_mb:.2f} MB)，只存储关键信息")
            agent_result_json = json.dumps({
                'agent_metadata': agent_result.get('agent_metadata', {}),
                'summary': agent_result.get('summary', ''),
                'statistics': agent_result.get('statistics', {})
            })
        
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
            with engine.connect() as conn:
                _save_cache_with_retry(conn, repo_id, 'agent_analysis', 'full', agent_result_json, expires_at, max_retries=3)
                conn.commit()
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
                SessionLocal = sessionmaker(bind=engine)
                db = SessionLocal()
                repo_check = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
                if not repo_check:
                    logger.warning(f"[Task {self.request.id}] 仓库 {repo_id} 不存在，跳过缓存保存")
                    return {
                        'status': 'skipped',
                        'repository_id': repo_id,
                        'message': '仓库不存在，跳过缓存保存'
                    }
                with engine.connect() as conn:
                    _save_cache_with_retry(conn, repo_id, 'agent_analysis', 'full', agent_result_json, expires_at, max_retries=3)
                    conn.commit()
            else:
                raise
        
        logger.info(f"[Task {self.request.id}] Agent V2 分析完成: repo_id={repo_id}, "
                   f"迭代次数={len(agent_result.get('agent_metadata', {}).get('iterations', []))}, "
                   f"LLM调用={agent_result.get('agent_metadata', {}).get('total_llm_calls', 0)}, "
                   f"工具调用={agent_result.get('agent_metadata', {}).get('total_tool_calls', 0)}, "
                   f"思考过程={len(agent_result.get('agent_metadata', {}).get('thinking_process', []))}")
        
        return {
            'status': 'completed',
            'repository_id': repo_id,
            'from_cache': False,
            'result': agent_result
        }
    
    except Exception as e:
        logger.error(f"[Task {self.request.id}] Agent 分析失败: {e}", exc_info=True)
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name='tasks.code_repository_tasks.analyze_code_structure')
def analyze_code_structure(self, repo_id: int):
    """
    异步解析代码结构
    
    Args:
        repo_id: 仓库ID
        
    Returns:
        解析结果
    """
    from app.config.database import engine
    from app.models.code_repository import CodeRepository
    from sqlalchemy.orm import sessionmaker
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        logger.info(f"[Task {self.request.id}] 开始解析代码结构: repo_id={repo_id}")
        
        # 1. 获取仓库路径
        repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        
        if not repo:
            logger.warning(f"[Task {self.request.id}] 仓库 {repo_id} 不存在，跳过代码结构解析（可能已被删除）")
            return {
                'status': 'skipped',
                'repository_id': repo_id,
                'message': '仓库不存在，跳过代码结构解析'
            }
        
        if not repo.local_path:
            logger.warning(f"[Task {self.request.id}] 仓库 {repo_id} 未克隆，跳过代码结构解析")
            return {
                'status': 'skipped',
                'repository_id': repo_id,
                'message': '仓库未克隆，跳过代码结构解析'
            }
        
        # 2. 更新任务进度
        self.update_state(
            state='PROGRESS',
            meta={'progress': 0.1, 'stage': 'analyzing'}
        )
        
        # 3. 分析代码结构
        analyzer = CodeAnalyzerService()
        analysis = analyzer.analyze_repository(repo.local_path)
        
        structure_data = {
            "files": analysis['files'],
            "statistics": analysis['statistics']
        }
        
        # 4. 更新任务进度
        self.update_state(
            state='PROGRESS',
            meta={'progress': 1.0, 'stage': 'completed'}
        )
        
        # 5. 保存到 MySQL 缓存（24小时）
        expires_at = datetime.now() + timedelta(hours=24)
        
        cache_data = {
            'statistics': structure_data['statistics'],
            'file_count': len(structure_data['files']),
            'sample_files': structure_data['files'][:100] if len(structure_data['files']) > 100 else structure_data['files']
        }
        cache_json = json.dumps(cache_data)
        
        data_size_mb = len(cache_json.encode('utf-8')) / (1024 * 1024)
        logger.info(f"[Task {self.request.id}] 缓存数据大小: {data_size_mb:.2f} MB")
        
        if data_size_mb > 50:
            logger.warning(f"[Task {self.request.id}] 缓存数据过大，只存储统计信息")
            cache_data = {
                'statistics': structure_data['statistics'],
                'file_count': len(structure_data['files'])
            }
            cache_json = json.dumps(cache_data)
        
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
            with engine.connect() as conn:
                _save_cache_with_retry(conn, repo_id, 'structure', 'full', cache_json, expires_at, max_retries=3)
                conn.commit()
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
                SessionLocal = sessionmaker(bind=engine)
                db = SessionLocal()
                repo_check = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
                if not repo_check:
                    logger.warning(f"[Task {self.request.id}] 仓库 {repo_id} 不存在，跳过缓存保存")
                    return {
                        'status': 'skipped',
                        'repository_id': repo_id,
                        'message': '仓库不存在，跳过缓存保存'
                    }
                with engine.connect() as conn:
                    _save_cache_with_retry(conn, repo_id, 'structure', 'full', cache_json, expires_at, max_retries=3)
                    conn.commit()
            else:
                raise
        
        logger.info(f"[Task {self.request.id}] 代码结构解析完成: repo_id={repo_id}, "
                   f"文件数={len(analysis['files'])}, "
                   f"总行数={analysis['statistics']['total_lines']}")
        
        return {
            'status': 'completed',
            'repository_id': repo_id,
            'result': structure_data
        }
    
    except Exception as e:
        logger.error(f"[Task {self.request.id}] 代码结构解析失败: {e}", exc_info=True)
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise
    finally:
        db.close()
