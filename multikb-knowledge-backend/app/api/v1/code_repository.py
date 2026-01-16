"""
代码库 API 路由
MVP 版本 - 8 个核心接口
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict
from pydantic import BaseModel
import json
from datetime import datetime, timedelta

from app.core.logging import logger
from app.core.response import success_response, error_response
from app.dependencies.database import get_db
from app.services.git_service import GitService
from app.services.code_parser_service import CodeParserService
from app.services.code_analyzer_service import CodeAnalyzerService
from app.services.code_qa_service import CodeQAService
from app.tasks.celery_app import celery_app
from app.services.code_file_service import get_code_file_service
from app.services.code_symbol_service import get_code_symbol_service


router = APIRouter(prefix="/code-analysis", tags=["代码库分析"])


# =============================================
# 0. 获取仓库列表（新增）
# =============================================

@router.get("/repositories")
async def list_repositories(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    clone_status: str = None,
    parse_status: str = None,
    db: Session = Depends(get_db)
):
    """
    获取仓库列表
    
    Args:
        page: 页码
        page_size: 每页数量
        search: 搜索关键词（仓库名称）
        clone_status: 克隆状态过滤
        parse_status: 解析状态过滤
        
    Returns:
        仓库列表（分页）
    """
    try:
        from app.models.code_repository import CodeRepository
        
        # 构建查询
        query = db.query(CodeRepository)
        
        if search:
            query = query.filter(CodeRepository.repo_name.like(f"%{search}%"))
        
        if clone_status:
            query = query.filter(CodeRepository.clone_status == clone_status)
        
        if parse_status:
            query = query.filter(CodeRepository.parse_status == parse_status)
        
        # 查询总数
        total = query.count()
        
        # 查询列表（分页）
        offset = (page - 1) * page_size
        repos = query.order_by(CodeRepository.created_at.desc()).offset(offset).limit(page_size).all()
        
        # 构建响应
        items = []
        for repo in repos:
            items.append({
                "id": repo.id,
                "repo_url": repo.repo_url,
                "repo_name": repo.repo_name,
                "repo_type": repo.repo_type,
                "default_branch": repo.default_branch,
                "last_commit_hash": repo.last_commit_hash,
                "last_commit_date": repo.last_commit_date.isoformat() if repo.last_commit_date else None,
                "local_path": repo.local_path,
                "clone_status": repo.clone_status,
                "clone_progress": repo.clone_progress,
                "parse_status": repo.parse_status,
                "parse_progress": repo.parse_progress,
                "total_files": repo.total_files,
                "total_lines": repo.total_lines,
                "language_stats": repo.language_stats if repo.language_stats else {},
                "is_deleted": repo.is_deleted if hasattr(repo, 'is_deleted') else False,  # 添加删除状态
                "created_at": repo.created_at.isoformat() if repo.created_at else None,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None
            })
        
        response_data = {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
        return success_response(response_data)
    
    except Exception as e:
        logger.error(f"获取仓库列表失败: {e}")
        return error_response(f"获取仓库列表失败: {str(e)}")


# =============================================
# 1. 导入仓库
# =============================================

@router.post("/repositories")
async def create_repository(
    repo_url: str,
    branch: str = "main",
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    导入代码仓库
    
    Args:
        repo_url: GitHub 仓库 URL
        branch: 分支名称（默认 main）
        
    Returns:
        仓库ID 和 任务ID
    """
    try:
        from app.models.code_repository import CodeRepository
        
        # 提取仓库名称
        repo_name = repo_url.rstrip('/').split('/')[-2:]
        repo_name = '/'.join(repo_name) if len(repo_name) == 2 else repo_url
        
        # 检查是否已存在
        existing = db.query(CodeRepository).filter(CodeRepository.repo_name == repo_name).first()
        
        if existing:
            return error_response("仓库已存在")
        
        # 创建仓库记录
        new_repo = CodeRepository(
            repo_url=repo_url,
            repo_name=repo_name,
            repo_type='github',
            default_branch=branch,
            clone_status='pending',
            parse_status='pending'
        )
        db.add(new_repo)
        db.commit()
        db.refresh(new_repo)
        
        repo_id = new_repo.id
        
        logger.info(f"创建仓库记录: {repo_id} - {repo_name}")
        
        # 异步任务：克隆 + 解析
        task = celery_app.send_task(
            'tasks.code_repository_tasks.clone_and_analyze',
            args=[repo_id, repo_url, branch]
        )
        
        return success_response({
            "repository_id": repo_id,
            "repo_name": repo_name,
            "clone_status": "cloning",
            "task_id": task.id
        })
    
    except Exception as e:
        logger.error(f"创建仓库失败: {e}")
        db.rollback()
        return error_response(f"创建仓库失败: {str(e)}")


# =============================================
# 2. 获取仓库信息
# =============================================

@router.get("/repositories/{repo_id}")
async def get_repository(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """
    获取仓库详细信息
    
    Args:
        repo_id: 仓库ID
        
    Returns:
        仓库信息
    """
    try:
        from app.models.code_repository import CodeRepository
        
        repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        
        if not repo:
            return error_response("仓库不存在")
        
        # 构建响应
        data = {
            "id": repo.id,
            "repo_url": repo.repo_url,
            "repo_name": repo.repo_name,
            "repo_type": repo.repo_type,
            "default_branch": repo.default_branch,
            "last_commit_hash": repo.last_commit_hash,
            "last_commit_date": repo.last_commit_date.isoformat() if repo.last_commit_date else None,
            "local_path": repo.local_path,
            "clone_status": repo.clone_status,
            "clone_progress": repo.clone_progress,
            "parse_status": repo.parse_status,
            "parse_progress": repo.parse_progress,
            "total_files": repo.total_files,
            "total_lines": repo.total_lines,
            "language_stats": repo.language_stats if repo.language_stats else {},
            "created_at": repo.created_at.isoformat() if repo.created_at else None,
            "updated_at": repo.updated_at.isoformat() if repo.updated_at else None
        }
        
        return success_response(data)
    
    except Exception as e:
        logger.error(f"获取仓库信息失败: {e}")
        return error_response(f"获取仓库信息失败: {str(e)}")


# =============================================
# 3. 删除仓库
# =============================================

@router.delete("/repositories/{repo_id}")
async def delete_repository(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """
    删除仓库（异步任务）
    
    注意：删除操作改为异步任务，避免长时间阻塞API响应
    删除大量数据（特别是NebulaGraph）可能耗时较长
    
    Args:
        repo_id: 仓库ID
        
    Returns:
        任务信息（包含task_id，前端可轮询任务状态）
    """
    try:
        from app.models.code_repository import CodeRepository
        from app.tasks.celery_app import celery_app
        
        # 检查仓库是否存在
        repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        
        if not repo:
            return error_response("仓库不存在")
        
        # 立即标记为删除中，防止其他操作（如 Wiki 生成）继续执行
        repo.is_deleted = True
        db.commit()
        logger.info(f"已标记仓库为删除中: repo_id={repo_id}")
        
        # 发送异步删除任务
        logger.info(f"发送删除仓库任务: repo_id={repo_id}")
        task = celery_app.send_task(
            'tasks.code_repository_tasks.delete_repository',
            args=[repo_id],
            queue='code'  # 使用代码库任务队列
        )
        
        return success_response({
            "message": "删除任务已提交",
            "task_id": task.id,
            "repository_id": repo_id,
            "status": "pending",
            "note": "删除操作正在后台执行，请使用 task_id 查询任务状态"
        })
    
    except Exception as e:
        logger.error(f"提交删除任务失败: {e}", exc_info=True)
        return error_response(f"提交删除任务失败: {str(e)}")


# =============================================
# 4. 获取代码结构
# =============================================

@router.get("/repositories/{repo_id}/structure")
async def get_code_structure(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """
    获取代码结构（文件树 + 符号）
    优先从数据库表 code_files 获取完整数据，如果没有则从缓存获取统计信息
    
    Args:
        repo_id: 仓库ID
        
    Returns:
        代码结构数据（包含完整的文件列表）
    """
    try:
        from app.models.code_repository import CodeRepository
        from app.services.code_file_service import CodeFileService
        
        # 1. 检查仓库是否存在且未删除
        repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        if not repo:
            return error_response("仓库不存在")
        if repo.is_deleted:
            return error_response("仓库正在删除或已删除，无法获取代码结构")
        
        # 2. 检查数据库表中是否有文件数据（优先使用数据库表）
        file_service = CodeFileService(db)
        files_result = file_service.list_files(
            repository_id=repo_id,
            language=None,
            page=1,
            page_size=10000  # 获取所有文件
        )
        
        if files_result['total'] > 0:
            logger.info(f"从数据库表获取代码结构: repo_id={repo_id}, 文件数={files_result['total']}")
            
            # 从数据库表获取统计信息
            stats_result = db.execute(
                text("""SELECT 
                    COUNT(*) as total_files,
                    SUM(lines_of_code) as total_lines,
                    SUM(symbols_count) as total_symbols,
                    COUNT(DISTINCT language) as language_count
                FROM code_files 
                WHERE repository_id = :repo_id"""),
                {"repo_id": repo_id}
            ).fetchone()
            
            # 获取语言分布
            lang_result = db.execute(
                text("""SELECT language, COUNT(*) as count, SUM(lines_of_code) as `lines`
                FROM code_files 
                WHERE repository_id = :repo_id AND language IS NOT NULL
                GROUP BY language
                ORDER BY count DESC"""),
                {"repo_id": repo_id}
            ).fetchall()
            
            languages = {row[0]: {"count": row[1], "lines": row[2]} for row in lang_result}
            
            # 调试日志：记录语言分布数据
            if lang_result:
                logger.info(f"语言分布统计: repo_id={repo_id}, 语言种类数={len(lang_result)}")
                for lang, count, lines in lang_result[:5]:  # 只记录前5个
                    logger.debug(f"  - {lang}: {count} 个文件, {lines} 行代码")
            else:
                logger.warning(f"语言分布数据为空: repo_id={repo_id}, 可能原因: 1) 文件未分析 2) language字段为NULL")
            
            # 从 code_symbols 表获取函数和类数量
            symbol_stats_result = db.execute(
                text("""SELECT 
                    symbol_type,
                    COUNT(*) as count
                FROM code_symbols 
                WHERE repository_id = :repo_id AND is_deleted = 0
                GROUP BY symbol_type"""),
                {"repo_id": repo_id}
            ).fetchall()
            
            symbol_stats = {row[0]: row[1] for row in symbol_stats_result}
            total_functions = symbol_stats.get('function', 0) + symbol_stats.get('method', 0)
            total_classes = symbol_stats.get('class', 0)
            
            # 尝试从缓存获取 API 端点和数据库表统计（如果存在）
            # 这些统计信息在分析时计算，存储在缓存中
            api_stats = {"frontend": 0, "backend": 0}
            database_tables = 0
            
            cache_result = db.execute(
                text("""SELECT cache_data FROM code_analysis_cache 
                WHERE repository_id = :repo_id AND cache_type = 'statistics' AND cache_key = 'full'
                AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY created_at DESC LIMIT 1"""),
                {"repo_id": repo_id}
            )
            cached_stats = cache_result.fetchone()
            
            if cached_stats:
                try:
                    cached_data = json.loads(cached_stats[0])
                    if 'api_endpoints' in cached_data:
                        api_stats = cached_data['api_endpoints']
                    if 'database_tables' in cached_data:
                        database_tables = cached_data.get('database_tables', 0)
                except Exception as e:
                    logger.warning(f"解析缓存统计信息失败: {e}")
            
            # 构建完整的统计信息
            statistics = {
                "total_files": stats_result[0] or 0,
                "total_lines": stats_result[1] or 0,
                "total_symbols": stats_result[2] or 0,
                "total_functions": total_functions,
                "total_classes": total_classes,
                "api_endpoints": api_stats,
                "database_tables": database_tables,
                "languages": languages
            }
            
            # 转换为前端需要的格式
            files = []
            for file in files_result['files']:
                files.append({
                    "file_path": file.file_path,
                    "file_name": file.file_name,
                    "language": file.language,
                    "lines": file.lines_of_code,
                    "file_size": file.file_size,
                    "complexity": {"cyclomatic": file.complexity_score or 0},
                    "symbols_count": file.symbols_count,
                    "imports_count": file.imports_count
                })
            
            return success_response({
                "files": files,
                "statistics": statistics
            })
        
        # 2. 如果没有数据库数据，尝试从缓存获取（降级方案）
        result = db.execute(
            text("""SELECT cache_data FROM code_analysis_cache 
            WHERE repository_id = :repo_id AND cache_type = 'structure' AND cache_key = 'full'
            AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY created_at DESC LIMIT 1"""),
            {"repo_id": repo_id}
        )
        cached = result.fetchone()
        
        if cached:
            logger.info(f"使用缓存的代码结构: repo_id={repo_id}")
            cache_data = json.loads(cached[0])
            # 缓存中可能只有统计信息，需要补充files字段
            if 'files' not in cache_data or len(cache_data.get('files', [])) == 0:
                cache_data['files'] = cache_data.get('sample_files', [])
            return success_response(cache_data)
        
        # 3. 如果都没有，返回提示信息
        repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        if not repo:
            return error_response("仓库不存在")
        
        if not repo.local_path:
            return error_response("仓库未克隆")
        
        # 返回空数据，提示需要解析
        return success_response({
            "files": [],
            "statistics": {},
            "status": "not_analyzed",
            "message": "代码结构尚未解析，请点击刷新按钮触发解析"
        })
    
    except Exception as e:
        logger.error(f"获取代码结构失败: {e}", exc_info=True)
        return error_response(f"获取代码结构失败: {str(e)}")


@router.post("/repositories/{repo_id}/structure/analyze")
async def analyze_code_structure(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """
    触发代码结构异步解析任务（刷新时调用）
    
    Args:
        repo_id: 仓库ID
        
    Returns:
        任务信息
    """
    try:
        from app.models.code_repository import CodeRepository
        
        # 1. 检查仓库是否存在
        repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        
        if not repo:
            return error_response("仓库不存在")
        
        if not repo.local_path:
            return error_response("仓库未克隆")
        
        # 2. 发送异步任务
        logger.info(f"发送代码结构解析任务: repo_id={repo_id}")
        task = celery_app.send_task(
            'tasks.code_repository_tasks.analyze_code_structure',
            args=[repo_id],
            queue='code'  # 使用代码库任务队列
        )
        
        return success_response({
            "task_id": task.id,
            "repository_id": repo_id,
            "status": "processing",
            "message": "代码结构解析任务已提交，请稍后刷新页面查看结果"
        })
    
    except Exception as e:
        logger.error(f"提交代码结构解析任务失败: {e}", exc_info=True)
        return error_response(f"提交代码结构解析任务失败: {str(e)}")


# =============================================
# 5. 获取依赖关系图
# =============================================

@router.get("/repositories/{repo_id}/dependencies")
async def get_dependencies(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """
    获取依赖关系图 - 仅从缓存读取
    
    Args:
        repo_id: 仓库ID
        
    Returns:
        依赖图（nodes + edges）或提示信息
    """
    try:
        from app.models.code_repository import CodeRepository
        
        # 1. 检查仓库是否存在且未删除
        repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        if not repo:
            return error_response("仓库不存在")
        if repo.is_deleted:
            return error_response("仓库正在删除或已删除，无法获取依赖关系")
        
        # 2. 检查缓存
        result = db.execute(
            text("""SELECT cache_data FROM code_analysis_cache 
            WHERE repository_id = :repo_id AND cache_type = 'dependencies' AND cache_key = 'graph'
            AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY created_at DESC LIMIT 1"""),
            {"repo_id": repo_id}
        )
        cached = result.fetchone()
        
        if cached:
            logger.info(f"使用缓存的依赖图: repo_id={repo_id}")
            return success_response(json.loads(cached[0]))
        
        # 2. 如果没有缓存，返回提示信息
        repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        if not repo:
            return error_response("仓库不存在")
        
        if not repo.local_path:
            return error_response("仓库未克隆")
        
        # 返回空数据，提示需要解析
        return success_response({
            "nodes": [],
            "edges": [],
            "status": "not_analyzed",
            "message": "依赖关系尚未解析，请点击刷新按钮触发解析"
        })
    
    except Exception as e:
        logger.error(f"获取依赖图失败: {e}")
        return error_response(f"获取依赖图失败: {str(e)}")




# =============================================
# 6. 分析单个文件
# =============================================

@router.get("/files/{file_path:path}/analysis")
async def analyze_file(
    file_path: str,
    repository_id: int,
    db: Session = Depends(get_db)
):
    """
    分析单个文件
    
    Args:
        file_path: 文件相对路径
        repository_id: 仓库ID
        
    Returns:
        文件分析结果
    """
    try:
        from app.models.code_repository import CodeRepository
        import os
        
        # 获取仓库路径
        repo = db.query(CodeRepository).filter(CodeRepository.id == repository_id).first()
        
        if not repo or not repo.local_path:
            return error_response("仓库未克隆")
        
        # 解析文件
        full_path = os.path.join(repo.local_path, file_path)
        
        if not os.path.exists(full_path):
            return error_response("文件不存在")
        
        parser = CodeParserService()
        analysis = parser.parse_file(full_path)
        
        if not analysis:
            return error_response("解析文件失败")
        
        return success_response(analysis)
    
    except Exception as e:
        logger.error(f"分析文件失败: {e}")
        return error_response(f"分析文件失败: {str(e)}")


# =============================================
# 7. 代码问答
# =============================================

class CodeQARequest(BaseModel):
    """代码问答请求"""
    repository_id: int
    question: str
    context_files: Optional[List[str]] = None


@router.post("/qa")
async def code_qa(
    request: CodeQARequest,
    db: Session = Depends(get_db)
):
    """
    代码问答
    
    Args:
        request: 问答请求，包含 repository_id、question 和可选的 context_files
        
    Returns:
        问答结果
    """
    try:
        from app.models.code_repository import CodeRepository
        
        # 获取仓库路径
        repo = db.query(CodeRepository).filter(CodeRepository.id == request.repository_id).first()
        
        if not repo or not repo.local_path:
            return error_response("仓库未克隆")
        
        # 调用问答服务（传入 db 以支持向量搜索和 rerank）
        qa_service = CodeQAService(db=db)
        answer = await qa_service.answer_question(
            repo_path=repo.local_path,
            question=request.question,
            context_files=request.context_files,
            use_vector_search=True,  # 启用混合搜索（向量 + 关键词）
            use_rerank=True  # 启用 Rerank 精排
        )
        
        return success_response(answer)
    
    except Exception as e:
        logger.error(f"代码问答失败: {e}")
        return error_response(f"代码问答失败: {str(e)}")


# =============================================
# 8. 生成 Wiki 内容（统一生成所有 AI 内容）
# =============================================

@router.get("/repositories/{repo_id}/wiki-content")
async def get_wiki_content(
    repo_id: int,
    force_refresh: bool = False,
    db: Session = Depends(get_db)
):
    """
    获取 Wiki 页面的所有 AI 内容（优先从缓存获取）
    
    Args:
        repo_id: 仓库ID
        force_refresh: 是否强制刷新（忽略缓存）
        
    Returns:
        Wiki 内容或任务信息：
        - 如果有缓存：直接返回 Wiki 内容
        - 如果没有缓存：返回任务信息，触发异步生成
    """
    try:
        from app.models.code_repository import CodeRepository
        
        # 1. 检查仓库是否存在且未删除
        repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        
        if not repo:
            return error_response("仓库不存在")
        
        if repo.is_deleted:
            return error_response("仓库正在删除或已删除，无法生成 Wiki 内容")
        
        if not repo.local_path:
            return error_response("仓库未克隆")
        
        # 2. 检查缓存（如果不强制刷新）
        if not force_refresh:
            result = db.execute(
                text("""SELECT cache_data FROM code_analysis_cache 
                WHERE repository_id = :repo_id AND cache_type = 'wiki_content' AND cache_key = 'full'
                AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY created_at DESC LIMIT 1"""),
                {"repo_id": repo_id}
            )
            cached = result.fetchone()
            
            if cached:
                logger.info(f"使用缓存的 Wiki 内容: repo_id={repo_id}")
                return success_response(json.loads(cached[0]))
        
        # 3. 如果没有缓存或强制刷新，检查是否有正在运行的任务
        # 使用 Redis 锁检查是否有任务正在运行（避免重复发送任务）
        from app.core.cache import cache_manager
        import asyncio
        
        lock_key = f"wiki_generation_lock:{repo_id}"
        
        # 检查锁是否存在（如果有锁，说明有任务正在运行）
        try:
            lock_exists = asyncio.run(cache_manager.exists(lock_key))
            
            if lock_exists:
                # 已有任务正在运行，返回提示信息（不发送新任务）
                logger.info(f"Wiki 生成任务已在运行中: repo_id={repo_id}")
                return success_response({
                    "repository_id": repo_id,
                    "status": "processing",
                    "message": "Wiki 内容正在生成中，请稍后刷新页面（检测到已有任务在运行）"
                })
        except Exception as e:
            # Redis 不可用时，继续发送任务（降级处理）
            logger.warning(f"检查任务锁失败，继续发送任务: {e}")
        
        # 发送异步任务
        logger.info(f"发送 Wiki 内容生成任务: repo_id={repo_id}, force_refresh={force_refresh}")
        task = celery_app.send_task(
            'tasks.code_repository_tasks.generate_wiki_content',
            args=[repo_id],
            queue='code'  # 使用代码库任务队列
        )
        
        return success_response({
            "task_id": task.id,
            "repository_id": repo_id,
            "status": "processing",
            "message": "Wiki 内容正在生成中，请稍后刷新页面"
        })
    
    except Exception as e:
        logger.error(f"获取 Wiki 内容失败: {e}", exc_info=True)
        return error_response(f"获取 Wiki 内容失败: {str(e)}")


# 已废弃：wiki-content/result 接口不再需要
# 现在直接使用 GET /repositories/{repo_id}/wiki-content 接口
# 该接口会优先从缓存获取，如果没有缓存才触发异步任务


# =============================================
# 9. 生成项目摘要（已废弃，建议使用 wiki-content 接口）
# =============================================
# 注意：此接口已废弃，建议使用 /repositories/{repo_id}/wiki-content 接口
# 新接口提供更完整的 Wiki 内容，包括项目概述、核心组件、价值主张等
# 保留此接口仅为了向后兼容，未来版本可能会移除

# @router.post("/repositories/{repo_id}/summary")
# async def generate_summary(
#     repo_id: int,
#     use_cache: bool = True,
#     db: Session = Depends(get_db)
# ):
#     """
#     生成项目整体文档摘要（已废弃）
#     
#     注意：建议使用 /repositories/{repo_id}/wiki-content 接口替代
#     
#     Args:
#         repo_id: 仓库ID
#         use_cache: 是否使用缓存
#         
#     Returns:
#         项目摘要
#     """
#     try:
#         from app.models.code_repository import CodeRepository
#         
#         # 1. 检查缓存
#         if use_cache:
#             result = db.execute(
#                 text("""SELECT cache_data FROM code_analysis_cache 
#                 WHERE repository_id = :repo_id AND cache_type = 'summary' AND cache_key = 'full'
#                 AND (expires_at IS NULL OR expires_at > NOW())"""),
#                 {"repo_id": repo_id}
#             )
#             cached = result.fetchone()
#             
#             if cached:
#                 logger.info(f"使用缓存的摘要: repo_id={repo_id}")
#                 return success_response(json.loads(cached[0]))
#         
#         # 2. 获取仓库路径
#         repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
#         
#         if not repo or not repo.local_path:
#             return error_response("仓库未克隆")
#         
#         # 3. 生成摘要
#         analyzer = CodeAnalyzerService()
#         analysis = analyzer.analyze_repository(repo.local_path)
#         
#         summary_data = {
#             "summary": analysis['summary'],
#             "statistics": analysis['statistics']
#         }
#         
#         # 4. 缓存结果（24小时）
#         expires_at = datetime.now() + timedelta(hours=24)
#         db.execute(
#             text("""INSERT INTO code_analysis_cache 
#             (repository_id, cache_type, cache_key, cache_data, expires_at)
#             VALUES (:repo_id, 'summary', 'full', :cache_data, :expires_at)
#             ON DUPLICATE KEY UPDATE cache_data = VALUES(cache_data), expires_at = VALUES(expires_at)"""),
#             {"repo_id": repo_id, "cache_data": json.dumps(summary_data), "expires_at": expires_at}
#         )
#         db.commit()
#         
#         return success_response(summary_data)
#     
#     except Exception as e:
#         logger.error(f"生成摘要失败: {e}")
#         return error_response(f"生成摘要失败: {str(e)}")


# =============================================
# 9. 代码文件管理 API
# =============================================

@router.get("/repositories/{repo_id}/files")
async def list_code_files(
    repo_id: int,
    language: str = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    """
    获取仓库的代码文件列表
    
    Args:
        repo_id: 仓库ID
        language: 语言筛选
        page: 页码
        page_size: 每页大小
        
    Returns:
        文件列表（分页）
    """
    try:
        file_service = get_code_file_service(db)
        result = file_service.list_files(
            repository_id=repo_id,
            language=language,
            page=page,
            page_size=page_size
        )
        
        # 转换为 JSON 可序列化格式
        items = []
        for file in result['files']:
            items.append({
                "id": file.id,
                "file_path": file.file_path,
                "file_name": file.file_name,
                "language": file.language,
                "lines_of_code": file.lines_of_code,
                "file_size": file.file_size,
                "symbols_count": file.symbols_count,
                "complexity_score": file.complexity_score,
                "vector_indexed": file.vector_indexed,
                "created_at": file.created_at.isoformat() if file.created_at else None
            })
        
        return success_response({
            "items": items,
            "total": result['total'],
            "page": result['page'],
            "page_size": result['page_size']
        })
    
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        return error_response(f"获取文件列表失败: {str(e)}")


@router.get("/files/{file_id}")
async def get_code_file(
    file_id: int,
    db: Session = Depends(get_db)
):
    """
    获取代码文件详情
    
    Args:
        file_id: 文件ID
        
    Returns:
        文件详情
    """
    try:
        file_service = get_code_file_service(db)
        code_file = file_service.get_file(file_id)
        
        if not code_file:
            return error_response("文件不存在")
        
        return success_response({
            "id": code_file.id,
            "repository_id": code_file.repository_id,
            "knowledge_base_id": code_file.knowledge_base_id,
            "file_path": code_file.file_path,
            "file_name": code_file.file_name,
            "file_type": code_file.file_type,
            "language": code_file.language,
            "content_hash": code_file.content_hash,
            "lines_of_code": code_file.lines_of_code,
            "file_size": code_file.file_size,
            "symbols_count": code_file.symbols_count,
            "imports_count": code_file.imports_count,
            "complexity_score": code_file.complexity_score,
            "vector_indexed": code_file.vector_indexed,
            "vector_updated_at": code_file.vector_updated_at.isoformat() if code_file.vector_updated_at else None,
            "created_at": code_file.created_at.isoformat() if code_file.created_at else None,
            "updated_at": code_file.updated_at.isoformat() if code_file.updated_at else None
        })
    
    except Exception as e:
        logger.error(f"获取文件详情失败: {e}")
        return error_response(f"获取文件详情失败: {str(e)}")


@router.post("/files/{file_id}/sync-graph")
async def sync_file_to_graph(
    file_id: int,
    db: Session = Depends(get_db)
):
    """
    同步代码文件到知识图谱
    
    Args:
        file_id: 文件ID
        
    Returns:
        同步结果
    """
    try:
        file_service = get_code_file_service(db)
        result = await file_service.sync_to_graph(file_id)
        
        return success_response(result)
    
    except Exception as e:
        logger.error(f"同步文件到图谱失败: {e}")
        return error_response(f"同步文件到图谱失败: {str(e)}")


# =============================================
# 10. 代码符号管理 API
# =============================================

@router.get("/files/{file_id}/symbols")
async def list_file_symbols(
    file_id: int,
    symbol_type: str = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    """
    获取文件的代码符号列表
    
    Args:
        file_id: 文件ID
        symbol_type: 符号类型筛选
        page: 页码
        page_size: 每页大小
        
    Returns:
        符号列表（分页）
    """
    try:
        symbol_service = get_code_symbol_service(db)
        result = symbol_service.list_symbols(
            file_id=file_id,
            symbol_type=symbol_type,
            page=page,
            page_size=page_size
        )
        
        # 转换为 JSON 可序列化格式
        items = []
        for symbol in result['symbols']:
            items.append({
                "id": symbol.id,
                "symbol_name": symbol.symbol_name,
                "symbol_type": symbol.symbol_type,
                "qualified_name": symbol.qualified_name,
                "signature": symbol.signature,
                "start_line": symbol.start_line,
                "end_line": symbol.end_line,
                "docstring": symbol.docstring,
                "complexity_score": symbol.complexity_score,
                "lines_count": symbol.lines_count,
                "vector_indexed": symbol.vector_indexed
            })
        
        return success_response({
            "items": items,
            "total": result['total'],
            "page": result['page'],
            "page_size": result['page_size']
        })
    
    except Exception as e:
        logger.error(f"获取符号列表失败: {e}")
        return error_response(f"获取符号列表失败: {str(e)}")


@router.get("/symbols/{symbol_id}")
async def get_code_symbol(
    symbol_id: int,
    db: Session = Depends(get_db)
):
    """
    获取代码符号详情
    
    Args:
        symbol_id: 符号ID
        
    Returns:
        符号详情
    """
    try:
        symbol_service = get_code_symbol_service(db)
        symbol = symbol_service.get_symbol(symbol_id)
        
        if not symbol:
            return error_response("符号不存在")
        
        return success_response({
            "id": symbol.id,
            "file_id": symbol.file_id,
            "repository_id": symbol.repository_id,
            "knowledge_base_id": symbol.knowledge_base_id,
            "symbol_name": symbol.symbol_name,
            "symbol_type": symbol.symbol_type,
            "qualified_name": symbol.qualified_name,
            "signature": symbol.signature,
            "start_line": symbol.start_line,
            "end_line": symbol.end_line,
            "docstring": symbol.docstring,
            "parameters": symbol.parameters,
            "return_type": symbol.return_type,
            "parent_symbol_id": symbol.parent_symbol_id,
            "modifiers": symbol.modifiers,
            "complexity_score": symbol.complexity_score,
            "lines_count": symbol.lines_count,
            "vector_indexed": symbol.vector_indexed,
            "vector_updated_at": symbol.vector_updated_at.isoformat() if symbol.vector_updated_at else None,
            "created_at": symbol.created_at.isoformat() if symbol.created_at else None,
            "updated_at": symbol.updated_at.isoformat() if symbol.updated_at else None
        })
    
    except Exception as e:
        logger.error(f"获取符号详情失败: {e}")
        return error_response(f"获取符号详情失败: {str(e)}")


@router.post("/files/{file_id}/extract-symbols")
async def extract_symbols(
    file_id: int,
    db: Session = Depends(get_db)
):
    """
    从代码文件中提取符号
    
    Args:
        file_id: 文件ID
        
    Returns:
        提取统计
    """
    try:
        file_service = get_code_file_service(db)
        symbol_service = get_code_symbol_service(db)
        
        # 获取文件信息
        code_file = file_service.get_file(file_id)
        if not code_file:
            return error_response("文件不存在")
        
        # 读取文件内容
        from app.models.code_repository import CodeRepository
        repo = db.query(CodeRepository).filter(
            CodeRepository.id == code_file.repository_id
        ).first()
        
        if not repo or not repo.local_path:
            return error_response("仓库未克隆到本地")
        
        import os
        file_full_path = os.path.join(repo.local_path, code_file.file_path)
        
        if not os.path.exists(file_full_path):
            return error_response("文件不存在于本地")
        
        with open(file_full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取符号
        result = symbol_service.extract_symbols_from_file(file_id, content)
        
        return success_response(result)
    
    except Exception as e:
        logger.error(f"提取符号失败: {e}")
        return error_response(f"提取符号失败: {str(e)}")


@router.post("/symbols/{symbol_id}/sync-graph")
async def sync_symbol_to_graph(
    symbol_id: int,
    db: Session = Depends(get_db)
):
    """
    同步代码符号到知识图谱
    
    Args:
        symbol_id: 符号ID
        
    Returns:
        同步结果
    """
    try:
        symbol_service = get_code_symbol_service(db)
        result = await symbol_service.sync_to_graph(symbol_id)
        
        return success_response(result)
    
    except Exception as e:
        logger.error(f"同步符号到图谱失败: {e}")
        return error_response(f"同步符号到图谱失败: {str(e)}")


@router.get("/repositories/{repo_id}/symbols/stats")
async def get_symbol_stats(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """
    获取仓库的符号统计信息
    
    Args:
        repo_id: 仓库ID
        
    Returns:
        符号统计
    """
    try:
        symbol_service = get_code_symbol_service(db)
        stats = symbol_service.get_symbol_stats(repository_id=repo_id)
        
        return success_response(stats)
    
    except Exception as e:
        logger.error(f"获取符号统计失败: {e}")
        return error_response(f"获取符号统计失败: {str(e)}")


@router.get("/symbols/search")
async def search_symbols(
    keyword: str,
    repository_id: int = None,
    symbol_type: str = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    搜索代码符号
    
    Args:
        keyword: 搜索关键词
        repository_id: 仓库ID筛选
        symbol_type: 符号类型筛选
        limit: 返回数量限制
        
    Returns:
        符号列表
    """
    try:
        symbol_service = get_code_symbol_service(db)
        symbols = symbol_service.search_symbols(
            keyword=keyword,
            repository_id=repository_id,
            symbol_type=symbol_type,
            limit=limit
        )
        
        # 转换为 JSON 可序列化格式
        items = []
        for symbol in symbols:
            items.append({
                "id": symbol.id,
                "symbol_name": symbol.symbol_name,
                "symbol_type": symbol.symbol_type,
                "qualified_name": symbol.qualified_name,
                "file_id": symbol.file_id,
                "repository_id": symbol.repository_id,
                "docstring": symbol.docstring[:200] if symbol.docstring else None,  # 截断
                "start_line": symbol.start_line,
                "complexity_score": symbol.complexity_score
            })
        
        return success_response({"items": items, "total": len(items)})
    
    except Exception as e:
        logger.error(f"搜索符号失败: {e}")
        return error_response(f"搜索符号失败: {str(e)}")


# =============================================
# 11. 知识库关联 API
# =============================================

@router.post("/repositories/{repo_id}/link-kb")
async def link_repository_to_kb(
    repo_id: int,
    knowledge_base_id: int,
    db: Session = Depends(get_db)
):
    """
    将代码仓库关联到知识库
    
    Args:
        repo_id: 仓库ID
        knowledge_base_id: 知识库ID
        
    Returns:
        关联结果
    """
    try:
        from app.models.code_repository import CodeRepository
        from app.models.knowledge_base import KnowledgeBase
        
        # 检查仓库是否存在
        repo = db.query(CodeRepository).filter(
            CodeRepository.id == repo_id
        ).first()
        
        if not repo:
            return error_response("代码仓库不存在")
        
        # 检查知识库是否存在
        kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == knowledge_base_id
        ).first()
        
        if not kb:
            return error_response("知识库不存在")
        
        # 关联
        repo.knowledge_base_id = knowledge_base_id
        db.commit()
        
        # 同步到图谱
        try:
            from app.services.nebula_code_service import get_nebula_code_service
            nebula_service = get_nebula_code_service(db)
            await nebula_service.sync_repository(repo_id)
        except Exception as e:
            logger.warning(f"同步到图谱失败: {e}")
        
        logger.info(f"关联代码仓库到知识库: repo={repo_id}, kb={knowledge_base_id}")
        
        return success_response({
            "repository_id": repo_id,
            "knowledge_base_id": knowledge_base_id,
            "message": "关联成功"
        })
    
    except Exception as e:
        logger.error(f"关联代码仓库失败: {e}")
        db.rollback()
        return error_response(f"关联代码仓库失败: {str(e)}")


@router.delete("/repositories/{repo_id}/unlink-kb")
async def unlink_repository_from_kb(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """
    取消代码仓库与知识库的关联
    
    Args:
        repo_id: 仓库ID
        
    Returns:
        取消关联结果
    """
    try:
        from app.models.code_repository import CodeRepository
        
        repo = db.query(CodeRepository).filter(
            CodeRepository.id == repo_id
        ).first()
        
        if not repo:
            return error_response("代码仓库不存在")
        
        # 取消关联
        repo.knowledge_base_id = None
        repo.kb_document_id = None
        db.commit()
        
        logger.info(f"取消代码仓库关联: repo={repo_id}")
        
        return success_response({"message": "取消关联成功"})
    
    except Exception as e:
        logger.error(f"取消代码仓库关联失败: {e}")
        db.rollback()
        return error_response(f"取消代码仓库关联失败: {str(e)}")


@router.get("/knowledge-bases/{kb_id}/repositories")
async def get_kb_repositories(
    kb_id: int,
    db: Session = Depends(get_db)
):
    """
    获取知识库关联的代码仓库列表
    
    Args:
        kb_id: 知识库ID
        
    Returns:
        仓库列表
    """
    try:
        from app.models.code_repository import CodeRepository
        
        repos = db.query(CodeRepository).filter(
            CodeRepository.knowledge_base_id == kb_id
        ).all()
        
        items = []
        for repo in repos:
            items.append({
                "id": repo.id,
                "repo_name": repo.repo_name,
                "repo_url": repo.repo_url,
                "description": repo.description,
                "clone_status": repo.clone_status,
                "total_files": repo.total_files,
                "total_lines": repo.total_lines,
                "language_stats": repo.language_stats,
                "created_at": repo.created_at.isoformat() if repo.created_at else None
            })
        
        return success_response({
            "total": len(items),
            "items": items
        })
    
    except Exception as e:
        logger.error(f"获取知识库代码仓库失败: {e}")
        return error_response(f"获取知识库代码仓库失败: {str(e)}")


# =============================================
# Agent 分析端点（新增）
# =============================================

@router.post("/repositories/{repo_id}/analyze-with-agent")
async def analyze_repository_with_agent(
    repo_id: int,
    use_cache: bool = True,
    db: Session = Depends(get_db)
):
    """
    使用 Agent 分析代码库（智能决策和迭代优化）- 异步任务
    
    Args:
        repo_id: 仓库ID
        use_cache: 是否使用缓存
        
    Returns:
        任务信息：
        {
            "task_id": "...",
            "repository_id": 1,
            "status": "pending"
        }
    """
    try:
        from app.models.code_repository import CodeRepository
        
        # 1. 检查仓库是否存在
        repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        
        if not repo:
            return error_response("仓库不存在")
        
        if not repo.local_path:
            return error_response("仓库未克隆")
        
        # 2. 发送异步任务
        logger.info(f"发送 Agent 分析任务: repo_id={repo_id}")
        task = celery_app.send_task(
            'tasks.code_repository_tasks.analyze_with_agent',
            args=[repo_id, use_cache],
            queue='code'  # 使用代码库任务队列
        )
        
        return success_response({
            "task_id": task.id,
            "repository_id": repo_id,
            "status": "pending",
            "message": "Agent 分析任务已提交，请使用 task_id 查询任务状态"
        })
    
    except Exception as e:
        logger.error(f"提交 Agent 分析任务失败: {e}", exc_info=True)
        return error_response(f"提交 Agent 分析任务失败: {str(e)}")


@router.get("/repositories/{repo_id}/analyze-with-agent/result")
async def get_agent_analysis_result(
    repo_id: int,
    use_cache: bool = True,
    db: Session = Depends(get_db)
):
    """
    获取 Agent 分析结果（同步接口，优先返回缓存）
    
    Args:
        repo_id: 仓库ID
        use_cache: 是否使用缓存
        
    Returns:
        Agent 分析结果（如果存在）
    """
    try:
        from app.models.code_repository import CodeRepository
        
        # 1. 检查缓存
        if use_cache:
            result = db.execute(
                text("""SELECT cache_data FROM code_analysis_cache 
                WHERE repository_id = :repo_id AND cache_type = 'agent_analysis' AND cache_key = 'full'
                AND (expires_at IS NULL OR expires_at > NOW())"""),
                {"repo_id": repo_id}
            )
            cached = result.fetchone()
            
            if cached:
                logger.info(f"返回缓存的 Agent 分析结果: repo_id={repo_id}")
                return success_response(json.loads(cached[0]))
        
        return error_response("未找到分析结果，请先执行分析任务")
    
    except Exception as e:
        logger.error(f"获取 Agent 分析结果失败: {e}", exc_info=True)
        return error_response(f"获取 Agent 分析结果失败: {str(e)}")
