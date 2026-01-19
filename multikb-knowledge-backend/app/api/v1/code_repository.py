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
        
        # 构建查询（排除已删除的仓库）
        query = db.query(CodeRepository).filter(
            CodeRepository.is_deleted == False  # 只返回未删除的仓库
        )
        
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
        
        # ========== 优先从 MySQL 查询统计信息 ==========
        # 1. 从 code_files 表查询文件数和代码行数（实时统计）
        from app.models.code_file import CodeFile
        from app.models.code_symbol import CodeSymbol
        from sqlalchemy import func
        
        file_stats = db.query(
            func.count(CodeFile.id).label('total_files'),
            func.sum(CodeFile.lines_of_code).label('total_lines')
        ).filter(
            CodeFile.repository_id == repo_id,
            CodeFile.is_deleted == False
        ).first()
        
        total_files = file_stats.total_files or 0 if file_stats else 0
        total_lines = file_stats.total_lines or 0 if file_stats else 0
        
        # 2. 从 code_files 表查询语言分布（实时统计）
        language_stats_query = db.query(
            CodeFile.language,
            func.count(CodeFile.id).label('count'),
            func.sum(CodeFile.lines_of_code).label('lines')
        ).filter(
            CodeFile.repository_id == repo_id,
            CodeFile.is_deleted == False,
            CodeFile.language.isnot(None)
        ).group_by(CodeFile.language).all()
        
        languages = {}
        for stat in language_stats_query:
            if stat.language:
                languages[stat.language] = {
                    "count": stat.count or 0,
                    "lines": stat.lines or 0
                }
        
        # 3. 从 code_symbols 表查询函数和类数量
        symbol_stats = db.query(
            CodeSymbol.symbol_type,
            func.count(CodeSymbol.id).label('count')
        ).filter(
            CodeSymbol.repository_id == repo_id,
            CodeSymbol.is_deleted == False,
            CodeSymbol.symbol_type.in_(['function', 'class'])
        ).group_by(CodeSymbol.symbol_type).all()
        
        # 统计函数和类数量
        total_functions = 0
        total_classes = 0
        for stat in symbol_stats:
            if stat.symbol_type == 'function':
                total_functions = stat.count
            elif stat.symbol_type == 'class':
                total_classes = stat.count
        
        # 查询总符号数
        total_symbols = db.query(func.count(CodeSymbol.id)).filter(
            CodeSymbol.repository_id == repo_id,
            CodeSymbol.is_deleted == False
        ).scalar() or 0
        
        # 4. 尝试从缓存获取 API 端点和数据库表统计（如果存在）
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
        
        # 构建完整的统计信息（从 MySQL 表实时查询）
        statistics = {
            "total_files": total_files,
            "total_lines": total_lines,
            "total_symbols": total_symbols,
            "total_functions": total_functions,
            "total_classes": total_classes,
            "api_endpoints": api_stats,
            "database_tables": database_tables,
            "languages": languages
        }
        
        logger.info(f"从 MySQL 查询统计信息: repo_id={repo_id}, 文件数={total_files}, 代码行数={total_lines}, "
                   f"函数数={total_functions}, 类数={total_classes}, 符号数={total_symbols}")
        
        # 5. 尝试从 NebulaGraph 获取文件列表（可选，用于文件树展示）
        files_result = {'total': 0, 'files': []}
        from app.services.nebula_code_service import get_nebula_code_service
        from app.config.settings import settings
        
        if settings.USE_NEBULA_GRAPH:
            try:
                nebula_service = get_nebula_code_service(db)
                files_result = await nebula_service.get_repository_files(
                    repository_id=repo_id,
                    language=None,
                    page=1,
                    page_size=10000  # 获取所有文件
                )
                logger.info(f"从 NebulaGraph 查询文件列表: repo_id={repo_id}, 文件数={files_result.get('total', 0)}")
            except Exception as nebula_error:
                logger.debug(f"从 NebulaGraph 查询文件列表失败（不影响统计信息）: {nebula_error}")
            
            # 转换为前端需要的格式（如果没有文件数据，返回空列表）
            files = []
            # 注意：当从 code_repositories 表获取统计信息时，files_result['files'] 是空的
            # 文件列表需要从 NebulaGraph 或缓存获取
            if files_result.get('files'):
                for file in files_result['files']:
                    # 处理文件对象（可能是字典或对象）
                    if isinstance(file, dict):
                        files.append(file)
                    else:
                        files.append({
                            "file_path": getattr(file, 'file_path', ''),
                            "file_name": getattr(file, 'file_name', ''),
                            "language": getattr(file, 'language', ''),
                            "lines": getattr(file, 'lines_of_code', 0),
                            "file_size": getattr(file, 'file_size', 0),
                            "complexity": {"cyclomatic": getattr(file, 'complexity_score', 0) or 0},
                            "symbols_count": getattr(file, 'symbols_count', 0),
                            "imports_count": getattr(file, 'imports_count', 0)
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
    db: Session = Depends(get_db),
    max_nodes: int = 500
):
    """
    获取依赖关系图 - 从 NebulaGraph 查询
    
    Args:
        repo_id: 仓库ID
        max_nodes: 最大节点数
        
    Returns:
        依赖图（nodes + edges）
    """
    try:
        from app.models.code_repository import CodeRepository
        from app.services.nebula_code_service import get_nebula_code_service
        from app.config.settings import settings
        
        # 1. 检查仓库是否存在且未删除
        repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        if not repo:
            return error_response("仓库不存在")
        if repo.is_deleted:
            return error_response("仓库正在删除或已删除，无法获取依赖关系")
        
        # 2. 如果 NebulaGraph 未启用，返回提示
        if not settings.USE_NEBULA_GRAPH:
            return success_response({
                "nodes": [],
                "edges": [],
                "status": "nebula_disabled",
                "message": "NebulaGraph 未启用，无法获取依赖关系图"
            })
        
        # 3. 从 NebulaGraph 查询依赖图
        nebula_service = get_nebula_code_service(db)
        
        # 在异步函数中直接使用 await
        graph_data = await nebula_service.get_dependency_graph(repo_id, max_nodes)
        
        if not graph_data.get("nodes"):
            # 如果没有数据，检查是否已同步到图谱
            return success_response({
                "nodes": [],
                "edges": [],
                "status": "not_synced",
                "message": "依赖关系尚未同步到图谱，请等待分析完成或手动触发同步"
            })
        
        logger.info(f"[API] 从 NebulaGraph 获取依赖图: repo_id={repo_id}, nodes={len(graph_data.get('nodes', []))}, edges={len(graph_data.get('edges', []))}")
        return success_response(graph_data)
    
    except Exception as e:
        logger.error(f"获取依赖图失败: {e}", exc_info=True)
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
        # 注意：即使 force_refresh=False，也要检查是否有任务正在运行
        # 如果有任务正在运行，即使没有缓存，也应该等待任务完成而不是发送新任务
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
        
        # 2.5. 检查是否有任务正在执行（即使没有缓存，也要避免重复发送任务）
        from app.core.cache import cache_manager
        
        exec_lock_key = f"wiki_generation_lock:{repo_id}"
        try:
            exec_lock_exists = await cache_manager.exists(exec_lock_key)
            if exec_lock_exists:
                logger.info(f"Wiki 生成任务正在执行中: repo_id={repo_id}")
                return success_response({
                    "repository_id": repo_id,
                    "status": "processing",
                    "message": "Wiki 内容正在生成中，请稍后刷新页面（检测到已有任务在运行）"
                })
        except Exception as e:
            logger.warning(f"检查任务执行锁失败: {e}")
        
        # 2.6. 再次检查缓存（可能在检查锁的瞬间缓存刚写入）
        # 这是一个双重检查，避免在任务刚完成但锁还没释放时发送新任务
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
                logger.info(f"使用缓存的 Wiki 内容（二次检查）: repo_id={repo_id}")
                cached_data = json.loads(cached[0])
                # 记录关键字段用于调试
                logger.info(f"[API] 📤 步骤6: 准备返回 Wiki 内容: repo_id={repo_id}")
                logger.info(f"[API] 📤 步骤6.1: 从数据库读取的数据键: {list(cached_data.keys())}")
                
                if cached_data.get('getting_started'):
                    run_cmd = cached_data['getting_started'].get('run_project_command', 'N/A')
                    logger.info(f"[API] 📤 步骤6.2: getting_started.run_project_command: {run_cmd}")
                    logger.info(f"[API] 📤 步骤6.2: getting_started 完整结构: prerequisites={len(cached_data['getting_started'].get('prerequisites', []))}, installation_steps={len(cached_data['getting_started'].get('installation_steps', []))}")
                else:
                    logger.warning(f"[API] ⚠️ 步骤6.2失败: getting_started 字段不存在")
                
                if cached_data.get('system_architecture'):
                    arch = cached_data['system_architecture']
                    logger.info(f"[API] 📤 步骤6.3: 验证 system_architecture")
                    mermaid_api = arch.get('mermaid_api_diagram', '')
                    logger.info(f"[API] 📤 步骤6.3.1: mermaid_api_diagram 类型: {type(mermaid_api).__name__}")
                    logger.info(f"[API] 📤 步骤6.3.1: mermaid_api_diagram 长度: {len(mermaid_api)}")
                    logger.info(f"[API] 📤 步骤6.3.1: mermaid_api_diagram（完整）: {repr(mermaid_api)}")
                    if mermaid_api:
                        # 提取实际代码
                        api_code = mermaid_api.replace('```mermaid', '').replace('```', '').strip()
                        logger.info(f"[API] 📤 步骤6.3.2: 清理后的代码长度: {len(api_code)}")
                        logger.info(f"[API] 📤 步骤6.3.2: 清理后的代码（完整）: {repr(api_code)}")
                        logger.info(f"[API] 📤 步骤6.3.2: 清理后的代码（按行）:")
                        for i, line in enumerate(api_code.split('\n'), 1):
                            logger.info(f"[API] 📤      行{i}: {repr(line)}")
                    else:
                        logger.warning(f"[API] ⚠️ 步骤6.3.1失败: mermaid_api_diagram 为空")
                    logger.info(f"[API] 📤 步骤6.3.3: system_architecture 其他字段: functional_subsystems_table={len(arch.get('functional_subsystems_table', []))}, key_architectural_decisions={len(arch.get('key_architectural_decisions', []))}")
                else:
                    logger.warning(f"[API] ⚠️ 步骤6.3失败: system_architecture 字段不存在")
                
                logger.info(f"[API] 📤 步骤6.4: 准备返回数据，数据大小: {len(json.dumps(cached_data))} 字符")
                return success_response(cached_data)
        
        # 3. 如果没有缓存或强制刷新，使用原子锁机制避免重复发送任务
        from app.core.cache import cache_manager
        
        lock_key = f"wiki_generation_send_lock:{repo_id}"  # 使用不同的锁键，避免与任务执行锁冲突
        lock_timeout = 10  # 短超时（10秒），只用于防止重复发送任务
        
        # 尝试原子性地获取发送锁（如果获取失败，说明已有请求正在发送任务）
        try:
            lock_acquired = await cache_manager.acquire_lock(lock_key, timeout=lock_timeout)
            
            if not lock_acquired:
                # 已有请求正在发送任务，返回提示信息（不发送新任务）
                logger.info(f"Wiki 生成任务发送锁已被占用，可能有其他请求正在发送: repo_id={repo_id}")
                # 检查是否有任务正在执行
                exec_lock_key = f"wiki_generation_lock:{repo_id}"
                exec_lock_exists = await cache_manager.exists(exec_lock_key)
                if exec_lock_exists:
                    return success_response({
                        "repository_id": repo_id,
                        "status": "processing",
                        "message": "Wiki 内容正在生成中，请稍后刷新页面（检测到已有任务在运行）"
                    })
                else:
                    # 锁被占用但任务未执行，可能是其他请求正在发送，稍等后重试
                    return success_response({
                        "repository_id": repo_id,
                        "status": "processing",
                        "message": "Wiki 内容正在生成中，请稍后刷新页面"
                    })
            
            # 成功获取发送锁，发送任务后立即释放（任务内部会获取执行锁）
            try:
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
            finally:
                # 无论成功与否，都释放发送锁
                await cache_manager.release_lock(lock_key)
            
        except Exception as e:
            # Redis 不可用时，记录警告但继续发送任务（降级处理）
            logger.warning(f"获取任务发送锁失败，继续发送任务（降级处理）: {e}")
            # 降级：直接发送任务
            task = celery_app.send_task(
                'tasks.code_repository_tasks.generate_wiki_content',
                args=[repo_id],
                queue='code'
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
        # ========== 已优化：从 NebulaGraph 查询文件列表 ==========
        # 从 NebulaGraph 查询文件列表
        from app.services.nebula_code_service import get_nebula_code_service
        from app.config.settings import settings
        
        if not settings.USE_NEBULA_GRAPH:
            return error_response("NebulaGraph 未启用，无法获取文件列表")
        
        nebula_service = get_nebula_code_service(db)
        # 在异步函数中直接使用 await
        result = await nebula_service.get_repository_files(
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


@router.get("/files/{file_path:path}/content")
async def get_file_content(
    file_path: str,
    repository_id: int,
    db: Session = Depends(get_db)
):
    """
    获取代码文件内容
    
    Args:
        file_path: 文件相对路径
        repository_id: 仓库ID
        
    Returns:
        文件内容
    """
    try:
        from app.models.code_repository import CodeRepository
        import os
        
        # 获取仓库路径
        repo = db.query(CodeRepository).filter(CodeRepository.id == repository_id).first()
        
        if not repo or not repo.local_path:
            return error_response("仓库未克隆")
        
        # 构建完整路径
        full_path = os.path.join(repo.local_path, file_path)
        
        if not os.path.exists(full_path):
            return error_response("文件不存在")
        
        # 检查是否是文件（不是目录）
        if not os.path.isfile(full_path):
            return error_response("路径不是文件")
        
        # 读取文件内容
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 限制文件大小（超过 1MB 的文件只返回前 1MB）
            max_size = 1024 * 1024  # 1MB
            if len(content) > max_size:
                content = content[:max_size] + "\n\n... (文件过大，已截断)"
            
            return success_response({
                "file_path": file_path,
                "content": content,
                "size": len(content),
                "truncated": len(content) > max_size
            })
        except Exception as e:
            logger.error(f"读取文件内容失败: {e}")
            return error_response(f"读取文件内容失败: {str(e)}")
    
    except Exception as e:
        logger.error(f"获取文件内容失败: {e}")
        return error_response(f"获取文件内容失败: {str(e)}")


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
        # ========== 已优化：从 NebulaGraph 查询文件详情 ==========
        # 从 NebulaGraph 查询文件详情（file_id 现在是 VID）
        from app.services.nebula_code_service import get_nebula_code_service
        from app.config.settings import settings
        
        if not settings.USE_NEBULA_GRAPH:
            return error_response("NebulaGraph 未启用，无法获取文件详情")
        
        nebula_service = get_nebula_code_service(db)
        # 在异步函数中直接使用 await
        # file_id 现在是 VID（如 code_file_xxxxx）
        file_vid = file_id if isinstance(file_id, str) and file_id.startswith('code_file_') else f"code_file_{file_id}"
        code_file = await nebula_service.get_file_by_vid(file_vid)
        
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
# 11. 代码查询 API（基于 NebulaGraph）
# =============================================

@router.get("/query/call-chain")
async def query_call_chain(
    repository_id: int,
    source: str,
    target: str,
    max_hops: int = 3,
    db: Session = Depends(get_db)
):
    """
    查询调用链（从源符号到目标符号的调用路径）
    
    Args:
        repository_id: 仓库ID
        source: 源符号名称或文件路径
        target: 目标符号名称或文件路径
        max_hops: 最大跳数
        
    Returns:
        调用链路径列表
    """
    try:
        from app.models.code_repository import CodeRepository
        from app.services.nebula_code_service import get_nebula_code_service
        from app.config.settings import settings
        
        # 1. 检查仓库是否存在
        repo = db.query(CodeRepository).filter(CodeRepository.id == repository_id).first()
        if not repo:
            return error_response("仓库不存在")
        if repo.is_deleted:
            return error_response("仓库正在删除或已删除，无法查询")
        
        # 2. 如果 NebulaGraph 未启用，返回提示
        if not settings.USE_NEBULA_GRAPH:
            return error_response("NebulaGraph 未启用，无法查询调用链")
        
        # 3. 从 NebulaGraph 查询调用链
        nebula_service = get_nebula_code_service(db)
        
        # 在异步函数中直接使用 await
        result = await nebula_service.query_call_chain(
            repository_id=repository_id,
            source=source,
            target=target,
            max_hops=max_hops
        )
        return success_response(result)
    
    except Exception as e:
        logger.error(f"查询调用链失败: {e}", exc_info=True)
        return error_response(f"查询调用链失败: {str(e)}")


@router.get("/query/dependency-path")
async def query_dependency_path(
    repository_id: int,
    source: str,
    target: str,
    max_hops: int = 3,
    db: Session = Depends(get_db)
):
    """
    查询依赖路径（从源文件到目标文件的依赖路径）
    
    Args:
        repository_id: 仓库ID
        source: 源文件路径
        target: 目标文件路径
        max_hops: 最大跳数
        
    Returns:
        依赖路径列表
    """
    try:
        from app.models.code_repository import CodeRepository
        from app.services.nebula_code_service import get_nebula_code_service
        from app.config.settings import settings
        
        # 1. 检查仓库是否存在
        repo = db.query(CodeRepository).filter(CodeRepository.id == repository_id).first()
        if not repo:
            return error_response("仓库不存在")
        if repo.is_deleted:
            return error_response("仓库正在删除或已删除，无法查询")
        
        # 2. 如果 NebulaGraph 未启用，返回提示
        if not settings.USE_NEBULA_GRAPH:
            return error_response("NebulaGraph 未启用，无法查询依赖路径")
        
        # 3. 从 NebulaGraph 查询依赖路径
        nebula_service = get_nebula_code_service(db)
        
        # 在异步函数中直接使用 await
        result = await nebula_service.query_dependency_path(
            repository_id=repository_id,
            source=source,
            target=target,
            max_hops=max_hops
        )
        return success_response(result)
    
    except Exception as e:
        logger.error(f"查询依赖路径失败: {e}", exc_info=True)
        return error_response(f"查询依赖路径失败: {str(e)}")


# =============================================
# 12. 知识库关联 API
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
