"""
代码库异步任务
负责克隆、解析和分析
"""

import os
import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.tasks.celery_app import celery_app
from app.core.logging import logger
from app.services.git_service import GitService
from app.services.code_analyzer_service import CodeAnalyzerService
from app.services.code_analysis_agent_v2 import CodeAnalysisAgentV2  # V2（基于 Function Calling + Thinking 模型）


def _save_cache_with_retry(conn, repo_id: int, cache_type: str, cache_key: str, cache_data: str, expires_at: datetime, max_retries: int = 3):
    """
    保存缓存数据，带重试机制（处理 MySQL 连接超时问题）
    
    注意：此函数会修改传入的 conn 对象（在重试时）
    
    Args:
        conn: 数据库连接（可能被修改）
        repo_id: 仓库ID
        cache_type: 缓存类型
        cache_key: 缓存键
        cache_data: 缓存数据（JSON 字符串）
        expires_at: 过期时间
        max_retries: 最大重试次数
    """
    from app.config.database import engine
    
    for attempt in range(max_retries):
        try:
            # 检查数据大小
            data_size_mb = len(cache_data.encode('utf-8')) / (1024 * 1024)
            if data_size_mb > 50:
                logger.warning(f"缓存数据过大 ({data_size_mb:.2f} MB)，可能超过 MySQL max_allowed_packet")
            
            # 尝试执行插入
            conn.execute(
                text("""INSERT INTO code_analysis_cache 
                (repository_id, cache_type, cache_key, cache_data, expires_at)
                VALUES (:repo_id, :cache_type, :cache_key, :cache_data, :expires_at)
                ON DUPLICATE KEY UPDATE cache_data = VALUES(cache_data), expires_at = VALUES(expires_at)"""),
                {
                    "repo_id": repo_id,
                    "cache_type": cache_type,
                    "cache_key": cache_key,
                    "cache_data": cache_data,
                    "expires_at": expires_at
                }
            )
            return  # 成功，退出
            
        except OperationalError as e:
            error_code = e.orig.args[0] if hasattr(e, 'orig') and hasattr(e.orig, 'args') and len(e.orig.args) > 0 else None
            
            # MySQL server has gone away (2006) 或连接被中止
            if error_code in (2006, 2013) or 'gone away' in str(e).lower() or 'ConnectionAbortedError' in str(e):
                if attempt < max_retries - 1:
                    logger.warning(f"数据库连接断开，重试 {attempt + 1}/{max_retries}: {e}")
                    time.sleep(1)  # 等待 1 秒后重试
                    
                    # 关闭旧连接并重新获取
                    try:
                        conn.close()
                    except:
                        pass
                    conn = engine.connect()
                    continue
                else:
                    logger.error(f"保存缓存失败，已重试 {max_retries} 次: {e}")
                    raise
            else:
                # 其他错误，直接抛出
                raise
        except Exception as e:
            logger.error(f"保存缓存时发生未知错误: {e}")
            raise


@celery_app.task(bind=True, name='tasks.code_repository_tasks.clone_and_analyze')
def clone_and_analyze(self, repo_id: int, repo_url: str, branch: str = 'main'):
    """
    异步克隆并解析仓库
    
    Args:
        repo_id: 仓库ID
        repo_url: 仓库URL
        branch: 分支名称
    """
    from app.config.database import engine
    
    try:
        logger.info(f"[Task {self.request.id}] ========== 开始克隆和分析仓库 ==========")
        logger.info(f"[Task {self.request.id}] 📦 仓库信息: repo_id={repo_id}, repo_url={repo_url}, branch={branch}")
        
        # 1. 更新状态：克隆中
        with engine.connect() as conn:
            conn.execute(
                text("""UPDATE code_repositories 
                SET clone_status = 'cloning', clone_progress = 0.0, updated_at = NOW()
                WHERE id = :repo_id"""),
                {"repo_id": repo_id}
            )
            conn.commit()
        
        # 2. 克隆仓库
        logger.info(f"[Task {self.request.id}] 🔄 开始克隆仓库: {repo_url} (分支: {branch})")
        git_service = GitService()
        
        def progress_callback(progress: float):
            """进度回调"""
            with engine.connect() as conn:
                conn.execute(
                    text("""UPDATE code_repositories 
                    SET clone_progress = :progress, updated_at = NOW()
                    WHERE id = :repo_id"""),
                    {"progress": progress, "repo_id": repo_id}
                )
                conn.commit()
            
            # 更新任务进度
            self.update_state(
                state='PROGRESS',
                meta={'progress': progress * 0.5, 'stage': 'cloning'}
            )
        
        local_path = git_service.clone_repository(
            repo_id=repo_id,
            repo_url=repo_url,
            branch=branch,
            shallow=True,
            progress_callback=progress_callback
        )
        
        # 3. 获取仓库信息
        repo_info = git_service.get_repo_info(repo_id)
        
        # 4. 更新克隆状态
        with engine.connect() as conn:
            conn.execute(
                text("""UPDATE code_repositories 
                SET clone_status = 'completed', clone_progress = 1.0,
                    local_path = :local_path,
                    last_commit_hash = :commit_hash,
                    last_commit_date = :commit_date,
                    updated_at = NOW()
                WHERE id = :repo_id"""),
                {
                    "local_path": repo_info['local_path'],
                    "commit_hash": repo_info['last_commit_hash'],
                    "commit_date": repo_info['last_commit_date'],
                    "repo_id": repo_id
                }
            )
            conn.commit()
        
        logger.info(f"[Task {self.request.id}] ✅ 克隆完成: local_path={local_path}")
        logger.info(f"[Task {self.request.id}] 📋 仓库信息: commit_hash={repo_info.get('last_commit_hash', 'N/A')[:7]}, "
                   f"commit_date={repo_info.get('last_commit_date', 'N/A')}")
        logger.info(f"[Task {self.request.id}] 🔄 开始代码解析")
        
        # 5. 更新状态：解析中
        with engine.connect() as conn:
            conn.execute(
                text("""UPDATE code_repositories 
                SET parse_status = 'parsing', parse_progress = 0.0, updated_at = NOW()
                WHERE id = :repo_id"""),
                {"repo_id": repo_id}
            )
            conn.commit()
        
        self.update_state(
            state='PROGRESS',
            meta={'progress': 0.5, 'stage': 'parsing'}
        )
        
        # 6. 分析代码（使用 Agent）
        logger.info(f"[Task {self.request.id}] ========== 开始代码分析 ==========")
        logger.info(f"[Task {self.request.id}] 🤖 使用 Agent V2 进行智能分析")
        self.update_state(
            state='PROGRESS',
            meta={'progress': 0.6, 'stage': 'agent_analysis'}
        )
        
        # ============================================
        # ✅ 新方法：使用 Agent 进行智能分析
        # ============================================
        from app.config.database import engine
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        try:
            # ✅ 使用 Agent V2（基于 Function Calling + Thinking 模型）
            agent = CodeAnalysisAgentV2(db=db)
            agent_result = agent.analyze_repository(local_path)
            
            # Agent V2 返回结构: {'static_analysis': {...}, 'call_chain': {...}, 'agent_metadata': {...}}
            # 从 static_analysis 中提取分析结果
            static_analysis = agent_result.get('static_analysis', {})
            agent_metadata = agent_result.get('agent_metadata', {})
            
            # 如果 static_analysis 存在，使用它；否则降级到基础分析
            if static_analysis and isinstance(static_analysis, dict):
                analysis = static_analysis
                stats = analysis.get('statistics', {})
                logger.info(f"[Task {self.request.id}] ========== ✅ Agent V2 分析完成 ==========")
                logger.info(f"[Task {self.request.id}] 📊 Agent 分析统计:")
                logger.info(f"[Task {self.request.id}]   - 迭代次数: {len(agent_metadata.get('iterations', []))}")
                logger.info(f"[Task {self.request.id}]   - LLM调用: {agent_metadata.get('total_llm_calls', 0)}")
                logger.info(f"[Task {self.request.id}]   - 工具调用: {agent_metadata.get('total_tool_calls', 0)}")
                logger.info(f"[Task {self.request.id}] 📊 代码分析统计:")
                logger.info(f"[Task {self.request.id}]   - 文件数: {stats.get('total_files', 0)}")
                logger.info(f"[Task {self.request.id}]   - 总行数: {stats.get('total_lines', 0)}")
                logger.info(f"[Task {self.request.id}]   - 函数数: {stats.get('total_functions', 0)}")
                logger.info(f"[Task {self.request.id}]   - 类数: {stats.get('total_classes', 0)}")
                logger.info(f"[Task {self.request.id}]   - 语言分布: {stats.get('languages', {})}")
            else:
                # Agent V2 没有返回 static_analysis，降级到基础分析
                logger.warning(f"[Task {self.request.id}] ⚠️ Agent V2 未返回 static_analysis，降级到基础分析")
                raise ValueError("Agent V2 未返回 static_analysis")
        except Exception as agent_error:
            logger.warning(f"[Task {self.request.id}] ⚠️ Agent V2 分析失败，降级到基础分析: {agent_error}", exc_info=True)
            # 降级：使用基础分析服务
            logger.info(f"[Task {self.request.id}] 🔄 使用基础分析服务 (CodeAnalyzerService)")
            analyzer = CodeAnalyzerService()
            analysis = analyzer.analyze_repository(local_path)
            stats = analysis.get('statistics', {})
            logger.info(f"[Task {self.request.id}] ✅ 基础分析完成: "
                       f"文件数={stats.get('total_files', 0)}, "
                       f"总行数={stats.get('total_lines', 0)}, "
                       f"函数数={stats.get('total_functions', 0)}, "
                       f"类数={stats.get('total_classes', 0)}")
        finally:
            db.close()
        
        # ============================================
        # ❌ 旧方法：已废弃，不再使用
        # ============================================
        # # 6. 分析代码（旧方法 - 已废弃）
        # analyzer = CodeAnalyzerService()
        # analysis = analyzer.analyze_repository(local_path)
        # 
        # 说明：
        # - 旧方法直接使用 CodeAnalyzerService，没有智能决策和迭代优化
        # - Agent V1（已废弃）: 基于规则的简单判断
        # - Agent V2（新版本）: 基于 Function Calling + Thinking 模型，支持：
        #   1. 真正的 LLM 推理（而非规则判断）
        #   2. Function Calling（工具调用）
        #   3. Thinking 模式（记录思考过程）
        #   4. 智能迭代（基于质量评估）
        #   5. 语义理解（理解代码语义）
        # ============================================
        
        # 7. 更新分析结果
        logger.info(f"[Task {self.request.id}] ========== 开始更新分析结果 ==========")
        stats = analysis.get('statistics', {})
        logger.info(f"[Task {self.request.id}] 📊 分析统计: "
                   f"文件数={stats.get('total_files', 0)}, "
                   f"总行数={stats.get('total_lines', 0)}, "
                   f"函数数={stats.get('total_functions', 0)}, "
                   f"类数={stats.get('total_classes', 0)}, "
                   f"语言={list(stats.get('languages', {}).keys())}")
        
        with engine.connect() as conn:
            # 更新统计信息
            logger.info(f"[Task {self.request.id}] 💾 更新仓库统计信息到 code_repositories 表")
            conn.execute(
                text("""UPDATE code_repositories 
                SET parse_status = 'completed', parse_progress = 1.0,
                    total_files = :total_files,
                    total_lines = :total_lines,
                    language_stats = :language_stats,
                    updated_at = NOW()
                WHERE id = :repo_id"""),
                {
                    "total_files": stats.get('total_files', 0),
                    "total_lines": stats.get('total_lines', 0),
                    "language_stats": json.dumps(stats.get('languages', {})),
                    "repo_id": repo_id
                }
            )
            logger.info(f"[Task {self.request.id}] ✅ 仓库统计信息更新成功")
            
            # 保存分析结果到缓存（24小时）
            expires_at = datetime.now() + timedelta(hours=24)
            
            # 优化缓存数据：不存储完整的文件列表，只存储统计信息和关键信息
            # 完整文件列表太大（可能超过 72MB），会导致 MySQL "max_allowed_packet" 错误
            cache_data = {
                'statistics': analysis['statistics'],
                'file_count': len(analysis['files']),
                # 只存储前 100 个文件作为示例（如果需要）
                'sample_files': analysis['files'][:100] if len(analysis['files']) > 100 else analysis['files']
            }
            
            cache_json = json.dumps(cache_data)
            cache_size_mb = len(cache_json.encode('utf-8')) / (1024 * 1024)
            logger.info(f"[Task {self.request.id}] 缓存数据大小: {cache_size_mb:.2f} MB")
            
            # 如果数据仍然太大（> 50MB），只存储统计信息
            if cache_size_mb > 50:
                logger.warning(f"[Task {self.request.id}] 缓存数据过大，只存储统计信息")
                cache_data = {
                    'statistics': analysis['statistics'],
                    'file_count': len(analysis['files'])
                }
                cache_json = json.dumps(cache_data)
            
            # 保存代码结构（使用重试机制）
            logger.info(f"[Task {self.request.id}] 💾 保存代码结构到缓存 (大小: {len(cache_json.encode('utf-8'))/1024:.1f} KB)")
            _save_cache_with_retry(conn, repo_id, 'structure', 'full', cache_json, expires_at, max_retries=3)
            logger.info(f"[Task {self.request.id}] ✅ 代码结构缓存保存成功")
            
            # 单独保存统计信息到缓存（方便快速查询）
            statistics_cache = json.dumps(analysis['statistics'])
            _save_cache_with_retry(conn, repo_id, 'statistics', 'full', statistics_cache, expires_at, max_retries=3)
            logger.info(f"[Task {self.request.id}] ✅ 统计信息缓存保存成功")
            
            # 保存依赖图（使用重试机制）
            dependencies_json = json.dumps(analysis['dependencies'])
            deps_size_kb = len(dependencies_json.encode('utf-8')) / 1024
            logger.info(f"[Task {self.request.id}] 💾 保存依赖图到缓存 (大小: {deps_size_kb:.1f} KB)")
            _save_cache_with_retry(conn, repo_id, 'dependencies', 'graph', dependencies_json, expires_at, max_retries=3)
            logger.info(f"[Task {self.request.id}] ✅ 依赖图缓存保存成功")
            
            # 保存摘要（使用重试机制）
            summary_data = {
                'summary': analysis['summary'],
                'statistics': analysis['statistics']
            }
            summary_json = json.dumps(summary_data)
            summary_size_kb = len(summary_json.encode('utf-8')) / 1024
            logger.info(f"[Task {self.request.id}] 💾 保存摘要到缓存 (大小: {summary_size_kb:.1f} KB)")
            _save_cache_with_retry(conn, repo_id, 'summary', 'full', summary_json, expires_at, max_retries=3)
            logger.info(f"[Task {self.request.id}] ✅ 摘要缓存保存成功")
            
            conn.commit()
            logger.info(f"[Task {self.request.id}] ✅ 所有缓存数据提交成功")
        
        # 8. 保存详细数据到数据库表（code_files 和 code_symbols）
        logger.info(f"[Task {self.request.id}] ========== 开始保存文件和符号到数据库表 ==========")
        logger.info(f"[Task {self.request.id}] 分析结果统计: 文件数={len(analysis.get('files', []))}, "
                   f"总行数={analysis.get('statistics', {}).get('total_lines', 0)}, "
                   f"总函数数={analysis.get('statistics', {}).get('total_functions', 0)}, "
                   f"总类数={analysis.get('statistics', {}).get('total_classes', 0)}")
        
        from app.config.database import engine
        from sqlalchemy.orm import sessionmaker
        from app.services.code_file_service import CodeFileService
        from app.services.code_symbol_service import CodeSymbolService
        from app.services.code_vectorization_service import CodeVectorizationService
        
        SessionLocal = sessionmaker(bind=engine)
        db_session = SessionLocal()
        
        files_saved = 0
        files_vectorized = 0  # 文件向量化计数
        symbols_saved = 0
        symbols_vectorized = 0
        files_errors = 0
        symbols_errors = 0
        vectorization_errors = 0
        file_vectorization_errors = 0  # 文件向量化错误计数
        
        try:
            file_service = CodeFileService(db_session)
            symbol_service = CodeSymbolService(db_session)
            vectorization_service = CodeVectorizationService(db_session)
            
            # 确保 OpenSearch 索引存在（在向量化之前）
            try:
                from opensearch_schemas.code_indices import init_code_indices
                import asyncio
                opensearch = vectorization_service.opensearch
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(init_code_indices(opensearch.client))
                    logger.info(f"[Task {self.request.id}] ✅ 代码索引初始化完成")
                finally:
                    loop.close()
            except Exception as index_init_error:
                logger.warning(f"[Task {self.request.id}] ⚠️ 索引初始化失败（将尝试自动创建）: {index_init_error}")
            
            logger.info(f"[Task {self.request.id}] ✅ 服务初始化完成: CodeFileService, CodeSymbolService, CodeVectorizationService")
            
            # 获取仓库本地路径
            repo_local_path = None
            # 从数据库查询（最可靠的方式）
            from app.models.code_repository import CodeRepository
            repo = db_session.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
            if repo:
                repo_local_path = repo.local_path
                logger.info(f"[Task {self.request.id}] ✅ 获取仓库路径: {repo_local_path}")
            else:
                logger.warning(f"[Task {self.request.id}] ⚠️ 仓库不存在: repo_id={repo_id}")
            
            # 批量保存文件
            total_files = len(analysis.get('files', []))
            logger.info(f"[Task {self.request.id}] 📦 准备保存 {total_files} 个文件到 code_files 表")
            
            for idx, file_data in enumerate(analysis.get('files', []), 1):
                try:
                    file_path = file_data.get('file_path', '')
                    if not file_path:
                        continue
                    
                    # 准备文件数据
                    file_name = os.path.basename(file_path)
                    language = file_data.get('language')
                    lines = file_data.get('lines', 0)
                    complexity = file_data.get('complexity', {})
                    complexity_score = complexity.get('cyclomatic', 0) if isinstance(complexity, dict) else 0
                    
                    # 计算文件大小（如果可能）
                    file_size = 0
                    try:
                        if repo_local_path:
                            full_path = os.path.join(repo_local_path, file_path)
                            if os.path.exists(full_path):
                                file_size = os.path.getsize(full_path)
                    except Exception as size_error:
                        pass
                    
                    # 统计导入数量
                    imports_count = len(file_data.get('imports', []))
                    
                    # 保存文件
                    try:
                        file_symbols_count_before = len(file_data.get('symbols', []))
                        code_file = file_service.create_file(
                            repository_id=repo_id,
                            file_path=file_path,
                            file_name=file_name,
                            language=language,
                            lines_of_code=lines,
                            file_size=file_size,
                            complexity_score=complexity_score,
                            symbols_count=file_symbols_count_before,
                            imports_count=imports_count
                        )
                        files_saved += 1
                        
                        # 向量化文件并写入 OpenSearch
                        try:
                            import asyncio
                            # 获取文件内容
                            file_content = None
                            if repo_local_path:
                                full_path = os.path.join(repo_local_path, file_path)
                                if os.path.exists(full_path):
                                    try:
                                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                            file_content = f.read()
                                    except Exception:
                                        pass
                            
                            # 在同步上下文中运行异步函数
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(
                                    vectorization_service.vectorize_code_file(
                                        file_id=code_file.id,
                                        content=file_content
                                    )
                                )
                                files_vectorized += 1
                            finally:
                                loop.close()
                        except Exception as vectorize_file_error:
                            file_vectorization_errors += 1
                            if file_vectorization_errors <= 5:  # 只记录前5个错误
                                logger.warning(f"[Task {self.request.id}] 向量化文件失败: {file_path}, 错误: {vectorize_file_error}")
                            # 不中断流程，继续处理下一个文件
                        
                        # 每10个文件记录一次进度
                        if files_saved % 10 == 0:
                            logger.debug(f"[Task {self.request.id}] 📄 已保存 {files_saved}/{total_files} 个文件: {file_name} (符号数={file_symbols_count_before})")
                    except Exception as create_file_error:
                        files_errors += 1
                        if files_errors <= 5:
                            logger.warning(f"[Task {self.request.id}] ❌ 创建文件记录失败: {file_path}, 错误: {create_file_error}")
                        continue
                    
                    # 保存符号
                    file_symbols_count = 0
                    for symbol in file_data.get('symbols', []):
                        try:
                            symbol_name = symbol.get('name', '')
                            if not symbol_name:
                                continue
                            
                            symbol_type = symbol.get('type', 'unknown')
                            start_line = symbol.get('line', 0)
                            end_line = symbol.get('end_line', start_line)
                            
                            # 构建 qualified_name
                            qualified_name = symbol_name
                            # 如果是方法，尝试从类名构建完整名称
                            if symbol_type == 'method':
                                # 查找父类（在同一文件中的类）
                                for cls in file_data.get('symbols', []):
                                    if cls.get('type') == 'class':
                                        cls_start = cls.get('line', 0)
                                        cls_end = cls.get('end_line', cls_start)
                                        if cls_start <= start_line <= cls_end:
                                            qualified_name = f"{cls.get('name', '')}.{symbol_name}"
                                            break
                            
                            # 准备参数和返回值信息
                            parameters = symbol.get('parameters', [])
                            return_type = symbol.get('return_type')
                            
                            # 构建 signature
                            signature_parts = []
                            if parameters:
                                if isinstance(parameters[0], dict):
                                    # 新格式：包含类型信息
                                    param_strs = []
                                    for p in parameters:
                                        if isinstance(p, dict):
                                            param_name = p.get('name', '')
                                            param_type = p.get('type', 'Any')
                                            param_strs.append(f"{param_name}: {param_type}" if param_name else param_type)
                                        else:
                                            param_strs.append(str(p))
                                    signature_parts = param_strs
                                else:
                                    # 旧格式：只有名称
                                    signature_parts = [str(p) for p in parameters]
                            
                            signature = f"({', '.join(signature_parts)})" if signature_parts else "()"
                            if return_type:
                                signature += f" -> {return_type}"
                            
                            # 计算符号行数
                            lines_count = max(1, end_line - start_line + 1) if end_line > start_line else 1
                            
                            # 符号复杂度（如果有）
                            symbol_complexity = symbol.get('complexity', {}).get('cyclomatic', 0) if isinstance(symbol.get('complexity'), dict) else 0
                            
                            # 保存符号到MySQL（只保存基本信息）
                            try:
                                code_symbol = symbol_service.create_symbol(
                                    file_id=code_file.id,
                                    symbol_name=symbol_name,
                                    symbol_type=symbol_type,
                                    qualified_name=qualified_name,
                                    start_line=start_line,
                                    end_line=end_line,
                                    complexity_score=symbol_complexity if symbol_complexity > 0 else None,
                                    lines_count=lines_count
                                )
                                symbols_saved += 1
                                file_symbols_count += 1
                                
                                # 立即将详细数据写入OpenSearch
                                # 获取代码内容（如果需要）
                                code_content = None
                                if repo_local_path:
                                    full_path = os.path.join(repo_local_path, file_path)
                                    if os.path.exists(full_path) and start_line and end_line:
                                        try:
                                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                                lines = f.readlines()
                                                if start_line <= len(lines) and end_line <= len(lines):
                                                    code_content = ''.join(lines[start_line-1:end_line])
                                        except Exception:
                                            pass
                                
                                # 直接向量化并写入OpenSearch
                                try:
                                    import asyncio
                                    # 在同步上下文中运行异步函数
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    try:
                                        loop.run_until_complete(
                                            vectorization_service.vectorize_symbol_direct(
                                                symbol_id=code_symbol.id,
                                                file_id=code_file.id,
                                                repository_id=repo_id,
                                                knowledge_base_id=code_file.knowledge_base_id,
                                                symbol_name=symbol_name,
                                                symbol_type=symbol_type,
                                                qualified_name=qualified_name,
                                                signature=signature,
                                                docstring=symbol.get('docstring', '') if symbol.get('docstring') else None,  # 完整docstring，不截断
                                                parameters=parameters if parameters else None,
                                                return_type=return_type,
                                                file_path=file_path,
                                                start_line=start_line,
                                                end_line=end_line,
                                                complexity_score=symbol_complexity if symbol_complexity > 0 else None,
                                                lines_count=lines_count,
                                                code_content=code_content
                                            )
                                        )
                                        symbols_vectorized += 1
                                    finally:
                                        loop.close()
                                except Exception as vectorize_error:
                                    vectorization_errors += 1
                                    if vectorization_errors <= 5:
                                        logger.warning(f"[Task {self.request.id}] 向量化符号失败: {file_path}:{symbol_name}, 错误: {vectorize_error}")
                                    # 不中断流程，继续处理下一个符号
                                
                            except Exception as create_symbol_error:
                                symbols_errors += 1
                                if symbols_errors <= 5:
                                    logger.warning(f"[Task {self.request.id}] 创建符号失败: {file_path}:{symbol_name}, 错误: {create_symbol_error}")
                                continue
                            
                        except Exception as sym_error:
                            symbols_errors += 1
                            if symbols_errors <= 5:  # 只记录前5个错误
                                logger.warning(f"[Task {self.request.id}] 保存符号失败: {file_path}:{symbol.get('name', 'unknown')}, 错误: {sym_error}")
                            continue
                    
                    # 每100个文件提交一次，避免事务过大
                    if files_saved % 100 == 0:
                        db_session.commit()
                        logger.info(f"[Task {self.request.id}] 💾 批量提交 (每100个文件): "
                                   f"文件={files_saved}/{total_files} (向量化={files_vectorized}), "
                                   f"符号={symbols_saved} (向量化={symbols_vectorized}), "
                                   f"错误(文件={files_errors}, 符号={symbols_errors}, 文件向量化={file_vectorization_errors}, 符号向量化={vectorization_errors})")
                    
                    # 每1000个符号记录一次
                    if symbols_saved > 0 and symbols_saved % 1000 == 0:
                        logger.info(f"[Task {self.request.id}] 📊 符号保存进度: "
                                   f"已保存={symbols_saved}, 已向量化={symbols_vectorized}, "
                                   f"向量化错误={vectorization_errors}")
                    
                    # 记录每个文件的符号保存情况（仅前10个文件，用于调试）
                    if files_saved <= 10 and file_symbols_count > 0:
                        logger.debug(f"[Task {self.request.id}]   - 文件 {file_name}: {file_symbols_count} 个符号已保存")
                    
                except Exception as file_error:
                    files_errors += 1
                    if files_errors <= 5:  # 只记录前5个错误
                        logger.warning(f"[Task {self.request.id}] 保存文件失败: {file_data.get('file_path', 'unknown')}, 错误: {file_error}")
                    continue
            
            # 最终提交
            db_session.commit()
            logger.info(f"[Task {self.request.id}] 💾 数据库提交完成")
            
            logger.info(f"[Task {self.request.id}] ========== ✅ 数据保存完成 ==========")
            logger.info(f"[Task {self.request.id}] 📈 保存统计:")
            success_rate = (files_saved / total_files * 100) if total_files > 0 else 0
            logger.info(f"[Task {self.request.id}]   - 文件: {files_saved}/{total_files} (成功率: {success_rate:.1f}%)")
            logger.info(f"[Task {self.request.id}]   - 文件向量化: {files_vectorized}/{files_saved} 个 (OpenSearch code_files)")
            file_vectorization_rate = (files_vectorized / files_saved * 100) if files_saved > 0 else 0
            logger.info(f"[Task {self.request.id}]   - 文件向量化率: {file_vectorization_rate:.1f}%")
            logger.info(f"[Task {self.request.id}]   - 符号: {symbols_saved} 个 (MySQL)")
            logger.info(f"[Task {self.request.id}]   - 符号向量化: {symbols_vectorized} 个 (OpenSearch code_symbols)")
            symbol_vectorization_rate = (symbols_vectorized / symbols_saved * 100) if symbols_saved > 0 else 0
            logger.info(f"[Task {self.request.id}]   - 符号向量化率: {symbol_vectorization_rate:.1f}%")
            logger.info(f"[Task {self.request.id}]   - 错误: 文件={files_errors}, 文件向量化={file_vectorization_errors}, 符号={symbols_errors}, 符号向量化={vectorization_errors}")
            file_vectorization_rate = (files_vectorized / files_saved * 100) if files_saved > 0 else 0
            logger.info(f"[Task {self.request.id}]   - 文件向量化率: {file_vectorization_rate:.1f}%")
            logger.info(f"[Task {self.request.id}]   - 符号: {symbols_saved} 个 (MySQL)")
            logger.info(f"[Task {self.request.id}]   - 符号向量化: {symbols_vectorized} 个 (OpenSearch code_symbols)")
            symbol_vectorization_rate = (symbols_vectorized / symbols_saved * 100) if symbols_saved > 0 else 0
            logger.info(f"[Task {self.request.id}]   - 符号向量化率: {symbol_vectorization_rate:.1f}%")
            logger.info(f"[Task {self.request.id}]   - 错误: 文件={files_errors}, 文件向量化={file_vectorization_errors}, 符号={symbols_errors}, 符号向量化={vectorization_errors}")
            
            # 计算平均每个文件的符号数
            if files_saved > 0:
                avg_symbols = symbols_saved / files_saved
                logger.info(f"[Task {self.request.id}]   - 平均每个文件符号数: {avg_symbols:.1f}")
            
        except Exception as save_error:
            db_session.rollback()
            logger.error(f"[Task {self.request.id}] ❌ 保存文件和符号到数据库表失败: {save_error}", exc_info=True)
            logger.error(f"[Task {self.request.id}]   已保存: 文件={files_saved}, 符号={symbols_saved}")
            logger.error(f"[Task {self.request.id}]   错误: 文件={files_errors}, 符号={symbols_errors}")
            # 不抛出异常，因为缓存已经保存成功
        finally:
            db_session.close()
            logger.info(f"[Task {self.request.id}] 🔒 数据库会话已关闭")
        
        logger.info(f"[Task {self.request.id}] ========== ✅ 分析任务完成 ==========")
        logger.info(f"[Task {self.request.id}] 📊 最终统计:")
        logger.info(f"[Task {self.request.id}]   - 文件保存: {files_saved if 'files_saved' in locals() else 0}")
        logger.info(f"[Task {self.request.id}]   - 符号保存: {symbols_saved if 'symbols_saved' in locals() else 0}")
        logger.info(f"[Task {self.request.id}]   - 代码统计: {analysis.get('statistics', {})}")
        
        return {
            'status': 'completed',
            'repository_id': repo_id,
            'statistics': analysis['statistics'],
            'files_saved': files_saved if 'files_saved' in locals() else 0,
            'symbols_saved': symbols_saved if 'symbols_saved' in locals() else 0
        }
    
    except Exception as e:
        logger.error(f"[Task {self.request.id}] ========== ❌ 克隆/解析失败 ==========")
        logger.error(f"[Task {self.request.id}] 错误详情: {e}", exc_info=True)
        
        # 清理失败的克隆目录（处理权限问题）
        try:
            git_service = GitService()
            local_path = git_service.get_repo_path(repo_id)
            if local_path and os.path.exists(local_path):
                import stat
                import shutil
                
                def handle_remove_readonly(func, path, exc):
                    """处理只读文件删除"""
                    try:
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    except Exception:
                        pass
                
                shutil.rmtree(local_path, onerror=handle_remove_readonly)
                logger.info(f"已清理失败的克隆目录: {local_path}")
        except Exception as cleanup_error:
            logger.warning(f"清理失败的克隆目录时出错: {cleanup_error}")
        
        # 更新失败状态
        with engine.connect() as conn:
            conn.execute(
                text("""UPDATE code_repositories 
                SET clone_status = 'failed', parse_status = 'failed', updated_at = NOW()
                WHERE id = :repo_id"""),
                {"repo_id": repo_id}
            )
            conn.commit()
        
        raise


@celery_app.task(name='tasks.code_repository_tasks.update_repository')
def update_repository(repo_id: int):
    """
    更新仓库（增量 Pull）
    
    Args:
        repo_id: 仓库ID
    """
    from app.config.database import engine
    
    try:
        logger.info(f"开始更新仓库: {repo_id}")
        
        # 1. 获取仓库信息
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT local_path FROM code_repositories WHERE id = :repo_id"),
                {"repo_id": repo_id}
            )
            row = result.fetchone()
            
            if not row or not row[0]:
                raise ValueError(f"仓库 {repo_id} 不存在或未克隆")
            
            local_path = row[0]
        
        # 2. Pull 更新
        git_service = GitService()
        update_info = git_service.pull_repository(repo_id)
        
        # 3. 如果有更新，重新分析
        if update_info['changed']:
            logger.info(f"仓库 {repo_id} 有更新，重新分析")
            
            # 更新 commit 信息
            with engine.connect() as conn:
                conn.execute(
                    text("""UPDATE code_repositories 
                    SET last_commit_hash = :commit_hash, 
                        last_commit_date = NOW(),
                        parse_status = 'parsing',
                        updated_at = NOW()
                    WHERE id = :repo_id"""),
                    {"commit_hash": update_info['new_commit'], "repo_id": repo_id}
                )
                conn.commit()
            
            # 重新分析（使用 Agent V2）
            # ============================================
            # ✅ 新方法：使用 Agent V2 进行智能分析（基于 Function Calling）
            # ============================================
            from app.config.database import engine
            from sqlalchemy.orm import sessionmaker
            SessionLocal = sessionmaker(bind=engine)
            db = SessionLocal()
            try:
                agent = CodeAnalysisAgentV2(db=db)
                agent_result = agent.analyze_repository(local_path)
                static_analysis = agent_result.get('static_analysis', {})
                if static_analysis and isinstance(static_analysis, dict):
                    analysis = static_analysis
                    logger.info(f"✅ Agent V2 分析完成，迭代: {len(agent_result.get('agent_metadata', {}).get('iterations', []))}, "
                               f"LLM调用: {agent_result.get('agent_metadata', {}).get('total_llm_calls', 0)}")
                else:
                    raise ValueError("Agent V2 未返回 static_analysis")
            except Exception as agent_error:
                logger.warning(f"⚠️ Agent V2 分析失败，降级到基础分析: {agent_error}", exc_info=True)
                # 降级：使用基础分析服务
                analyzer = CodeAnalyzerService()
                analysis = analyzer.analyze_repository(local_path)
            finally:
                db.close()
            
            # ============================================
            # ❌ 旧方法：已废弃，不再使用
            # ============================================
            # Agent V1（基于规则，已删除）:
            # 原文件: app/services/code_analysis_agent.py
            # 
            # 基础分析（无智能决策）:
            # analyzer = CodeAnalyzerService()
            # analysis = analyzer.analyze_repository(local_path)
            # ============================================
            
            # 更新分析结果
            with engine.connect() as conn:
                conn.execute(
                    text("""UPDATE code_repositories 
                    SET parse_status = 'completed',
                        total_files = :total_files,
                        total_lines = :total_lines,
                        language_stats = :language_stats,
                        updated_at = NOW()
                    WHERE id = :repo_id"""),
                    {
                        "total_files": analysis['statistics']['total_files'],
                        "total_lines": analysis['statistics']['total_lines'],
                        "language_stats": json.dumps(analysis['statistics']['languages']),
                        "repo_id": repo_id
                    }
                )
                
                # 清除旧缓存（通过更新过期时间）
                conn.execute(
                    text("DELETE FROM code_analysis_cache WHERE repository_id = :repo_id"),
                    {"repo_id": repo_id}
                )
                
                conn.commit()
            
            logger.info(f"仓库 {repo_id} 更新完成")
            
            return {
                'status': 'updated',
                'changed_files': len(update_info['changed_files']),
                'statistics': analysis['statistics']
            }
        else:
            logger.info(f"仓库 {repo_id} 无更新")
            return {
                'status': 'no_changes'
            }
    
    except Exception as e:
        logger.error(f"更新仓库失败: {e}")
        raise


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
            result = db.execute(
                text("""SELECT cache_data FROM code_analysis_cache 
                WHERE repository_id = :repo_id AND cache_type = 'agent_analysis' AND cache_key = 'full'
                AND (expires_at IS NULL OR expires_at > NOW())"""),
                {"repo_id": repo_id}
            )
            cached = result.fetchone()
            
            if cached:
                logger.info(f"[Task {self.request.id}] 使用缓存的 Agent 分析结果: repo_id={repo_id}")
                return {
                    'status': 'completed',
                    'repository_id': repo_id,
                    'from_cache': True,
                    'result': json.loads(cached[0])
                }
        
        # 2. 获取仓库路径
        repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        
        if not repo or not repo.local_path:
            raise ValueError("仓库未克隆")
        
        # 3. 更新任务进度
        self.update_state(
            state='PROGRESS',
            meta={'progress': 0.1, 'stage': 'observing'}
        )
        
        # 4. 使用 Agent V2 分析（基于 Function Calling + Thinking 模型）
        logger.info(f"[Task {self.request.id}] 使用 Agent V2 分析代码库: repo_id={repo_id}, path={repo.local_path}")
        agent = CodeAnalysisAgentV2(db=db)
        
        # 更新进度：思考阶段
        self.update_state(
            state='PROGRESS',
            meta={'progress': 0.2, 'stage': 'thinking'}
        )
        
        agent_result = agent.analyze_repository(repo.local_path)
        
        # 更新进度：完成
        self.update_state(
            state='PROGRESS',
            meta={'progress': 1.0, 'stage': 'completed'}
        )
        
        # 5. 缓存结果（2小时）
        expires_at = datetime.now() + timedelta(hours=2)
        agent_result_json = json.dumps(agent_result)
        
        # 检查数据大小
        data_size_mb = len(agent_result_json.encode('utf-8')) / (1024 * 1024)
        if data_size_mb > 50:
            logger.warning(f"[Task {self.request.id}] Agent 结果数据过大 ({data_size_mb:.2f} MB)，只存储关键信息")
            # 只存储关键信息
            agent_result_json = json.dumps({
                'agent_metadata': agent_result.get('agent_metadata', {}),
                'summary': agent_result.get('summary', ''),
                'statistics': agent_result.get('statistics', {})
            })
        
        # 使用重试机制保存
        try:
            db.execute(
                text("""INSERT INTO code_analysis_cache 
                (repository_id, cache_type, cache_key, cache_data, expires_at)
                VALUES (:repo_id, 'agent_analysis', 'full', :cache_data, :expires_at)
                ON DUPLICATE KEY UPDATE cache_data = VALUES(cache_data), expires_at = VALUES(expires_at)"""),
                {"repo_id": repo_id, "cache_data": agent_result_json, "expires_at": expires_at}
            )
            db.commit()
        except OperationalError as e:
            error_code = e.orig.args[0] if hasattr(e, 'orig') and hasattr(e.orig, 'args') else None
            if error_code in (2006, 2013) or 'gone away' in str(e).lower():
                logger.warning(f"[Task {self.request.id}] 数据库连接断开，重新连接后重试")
                db.rollback()
                db.close()
                # 重新获取连接
                from app.config.database import engine
                from sqlalchemy.orm import sessionmaker
                SessionLocal = sessionmaker(bind=engine)
                db = SessionLocal()
                db.execute(
                    text("""INSERT INTO code_analysis_cache 
                    (repository_id, cache_type, cache_key, cache_data, expires_at)
                    VALUES (:repo_id, 'agent_analysis', 'full', :cache_data, :expires_at)
                    ON DUPLICATE KEY UPDATE cache_data = VALUES(cache_data), expires_at = VALUES(expires_at)"""),
                    {"repo_id": repo_id, "cache_data": agent_result_json, "expires_at": expires_at}
                )
                db.commit()
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


@celery_app.task(bind=True, name='tasks.code_repository_tasks.delete_repository')
def delete_repository(self, repo_id: int):
    """
    异步删除仓库（彻底删除所有相关数据）
    
    清理范围：
    1. 本地克隆的代码文件
    2. OpenSearch 向量索引（code_files, code_symbols）
    3. NebulaGraph 图数据库（节点和边）
    4. MySQL 数据库记录（所有关联表）
    
    Args:
        repo_id: 仓库ID
        
    Returns:
        删除结果
    """
    from app.config.database import engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        logger.info(f"[Task {self.request.id}] ========== 开始删除仓库 ==========")
        logger.info(f"[Task {self.request.id}] 📦 仓库ID: {repo_id}")
        
        from app.models.code_repository import CodeRepository
        
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
                # 先检查索引是否存在（安全处理）
                try:
                    index_exists = opensearch.client.indices.exists(index='code_files')
                except Exception as check_error:
                    # 检查索引时出错，可能是连接问题，记录警告但继续
                    logger.warning(f"[Task {self.request.id}] ⚠️ 检查代码文件索引失败: {check_error}")
                    index_exists = False
                
                if index_exists:
                    opensearch.client.delete_by_query(
                        index='code_files',
                        body={
                            'query': {
                                'term': {'repository_id': repo_id}
                            }
                        },
                        wait_for_completion=True,
                        timeout=60  # 超时时间（秒），必须是数字类型
                    )
                    deleted_items.append("代码文件向量索引")
                    logger.info(f"[Task {self.request.id}] ✅ 已删除代码文件索引: repo_id={repo_id}")
                else:
                    logger.info(f"[Task {self.request.id}] ℹ️ 代码文件索引不存在，跳过")
            except Exception as e:
                # 索引不存在时忽略错误
                error_str = str(e).lower()
                if 'index_not_found_exception' in error_str or 'not_found' in error_str or '404' in error_str:
                    logger.info(f"[Task {self.request.id}] ℹ️ 代码文件索引不存在，跳过")
                else:
                    logger.warning(f"[Task {self.request.id}] ⚠️ 删除代码文件索引失败: {e}")
            
            # 删除代码符号索引
            try:
                # 先检查索引是否存在（安全处理）
                try:
                    index_exists = opensearch.client.indices.exists(index='code_symbols')
                except Exception as check_error:
                    # 检查索引时出错，可能是连接问题，记录警告但继续
                    logger.warning(f"[Task {self.request.id}] ⚠️ 检查代码符号索引失败: {check_error}")
                    index_exists = False
                
                if index_exists:
                    opensearch.client.delete_by_query(
                        index='code_symbols',
                        body={
                            'query': {
                                'term': {'repository_id': repo_id}
                            }
                        },
                        wait_for_completion=True,
                        timeout=60  # 超时时间（秒），必须是数字类型
                    )
                    deleted_items.append("代码符号向量索引")
                    logger.info(f"[Task {self.request.id}] ✅ 已删除代码符号索引: repo_id={repo_id}")
                else:
                    logger.info(f"[Task {self.request.id}] ℹ️ 代码符号索引不存在，跳过")
            except Exception as e:
                # 索引不存在时忽略错误
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
                        body={
                            'query': {
                                'term': {'repository_id': repo_id}
                            }
                        },
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
        
        # 3. 删除 NebulaGraph 图数据库数据（异步执行，避免阻塞）
        try:
            logger.info(f"[Task {self.request.id}] 🗑️ 删除 NebulaGraph 数据")
            from app.services.nebula_code_service import get_nebula_code_service
            from app.config.settings import settings
            
            # 只有启用了图数据库才执行删除
            if settings.USE_NEBULA_GRAPH:
                import asyncio
                nebula_service = get_nebula_code_service(db)
                
                # 在同步上下文中运行异步函数
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
        
        # 4. 删除分析缓存（code_analysis_cache表）
        try:
            logger.info(f"[Task {self.request.id}] 🗑️ 删除分析缓存")
            db.execute(
                text("DELETE FROM code_analysis_cache WHERE repository_id = :repo_id"),
                {"repo_id": repo_id}
            )
            deleted_items.append("分析缓存数据")
            logger.info(f"[Task {self.request.id}] ✅ 已删除分析缓存: repo_id={repo_id}")
        except Exception as e:
            logger.warning(f"[Task {self.request.id}] ⚠️ 删除分析缓存失败: {e}")
        
        # 5. 删除关联映射（code_kb_mappings表）
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
        
        # 6. 删除代码文件记录（code_files表，级联删除）
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
        
        # 7. 删除代码符号记录（code_symbols表）
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
        
        # 8. 删除依赖关系记录（code_dependencies表）
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
        
        # 9. 最后删除仓库主记录（code_repositories表）
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


async def _index_wiki_content_to_opensearch(task_self, repo_id: int, repo_name: str, wiki_content: Dict):
    """
    将 Wiki 内容索引到 OpenSearch（用于语义搜索）
    
    Args:
        repo_id: 仓库ID
        repo_name: 仓库名称
        wiki_content: Wiki 内容字典
    """
    try:
        from app.services.opensearch_service import OpenSearchService
        from app.services.vector_service import VectorService
        from opensearch_schemas.code_indices import WIKI_CONTENT_INDEX, WIKI_CONTENT_INDEX_CONFIG
        import asyncio
        
        opensearch = OpenSearchService()
        vector_service = VectorService(db=None)  # Wiki 索引不需要 db
        
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
            # 三层架构说明
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
            
            # 架构模式
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
        
        # 6. 快速开始指南（摘要和安装步骤）
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
            
            # 安装步骤（合并所有步骤的文本）
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
        
        # 7. 核心组件（索引每个组件的描述）
        if wiki_content.get('core_components'):
            for idx, component in enumerate(wiki_content['core_components'][:10]):  # 最多索引前10个
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
        
        # 8. 价值主张（索引每个价值主张的描述）
        if wiki_content.get('value_propositions'):
            for idx, prop in enumerate(wiki_content['value_propositions'][:5]):  # 最多索引前5个
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
    
    # 使用 Redis 锁防止重复执行
    from app.core.cache import cache_manager
    import asyncio
    from typing import Dict
    
    lock_key = f"wiki_generation_lock:{repo_id}"
    lock_timeout = 300  # 5分钟超时
    lock_value = str(self.request.id)  # 使用任务ID作为锁值
    
    # 尝试获取锁
    lock_acquired = asyncio.run(cache_manager.acquire_lock(lock_key, timeout=lock_timeout, value=lock_value))
    
    if not lock_acquired:
        # 已有任务正在运行，跳过本次执行
        logger.warning(f"[Task {self.request.id}] Wiki 生成任务已在运行中，跳过: repo_id={repo_id}")
        return {
            'status': 'skipped',
            'repository_id': repo_id,
            'message': '已有任务正在运行，跳过本次执行'
        }
    
    try:
        logger.info(f"[Task {self.request.id}] 开始生成 Wiki 内容: repo_id={repo_id}")
        
        # 1. 获取仓库路径
        repo = db.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        
        if not repo or not repo.local_path:
            raise ValueError("仓库未克隆")
        
        # 2. 更新任务进度
        self.update_state(
            state='PROGRESS',
            meta={'progress': 0.1, 'stage': 'analyzing'}
        )
        
        # 3. 生成 Wiki 内容
        analyzer = CodeAnalyzerService()
        wiki_content = analyzer.generate_wiki_content(repo.local_path, repo.repo_name)
        
        # 4. 更新任务进度
        self.update_state(
            state='PROGRESS',
            meta={'progress': 1.0, 'stage': 'completed'}
        )
        
        # 5. 缓存结果（24小时）
        expires_at = datetime.now() + timedelta(hours=24)
        wiki_content_json = json.dumps(wiki_content)
        
        # 检查数据大小
        data_size_mb = len(wiki_content_json.encode('utf-8')) / (1024 * 1024)
        logger.info(f"[Task {self.request.id}] Wiki 内容大小: {data_size_mb:.2f} MB")
        
        if data_size_mb > 50:
            logger.warning(f"[Task {self.request.id}] Wiki 内容过大（{data_size_mb:.2f}MB），只存储关键信息")
            # 只存储关键信息（但保留重要部分）
            wiki_content_json = json.dumps({
                'project_overview': wiki_content.get('project_overview', ''),
                'what_is_project': wiki_content.get('what_is_project', ''),
                'core_components': wiki_content.get('core_components', []),
                'value_propositions': wiki_content.get('value_propositions', []),
                'key_features': wiki_content.get('key_features', []),
                'getting_started': wiki_content.get('getting_started', {}),  # 保留快速开始指南
                'system_architecture': {
                    'three_tier_architecture': wiki_content.get('system_architecture', {}).get('three_tier_architecture', ''),
                    'architectural_patterns': wiki_content.get('system_architecture', {}).get('architectural_patterns', ''),
                } if wiki_content.get('system_architecture') else {},
                'technology_stack': {
                    'core_technologies': wiki_content.get('technology_stack', {}).get('core_technologies', ''),
                } if wiki_content.get('technology_stack') else {},
                'statistics': wiki_content.get('statistics', {}) if 'statistics' in wiki_content else {}
            })
        
        # 使用重试机制保存
        try:
            db.execute(
                text("""INSERT INTO code_analysis_cache 
                (repository_id, cache_type, cache_key, cache_data, expires_at)
                VALUES (:repo_id, 'wiki_content', 'full', :cache_data, :expires_at)
                ON DUPLICATE KEY UPDATE cache_data = VALUES(cache_data), expires_at = VALUES(expires_at)"""),
                {"repo_id": repo_id, "cache_data": wiki_content_json, "expires_at": expires_at}
            )
            db.commit()
        except OperationalError as e:
            error_code = e.orig.args[0] if hasattr(e, 'orig') and hasattr(e.orig, 'args') else None
            if error_code in (2006, 2013) or 'gone away' in str(e).lower():
                logger.warning(f"[Task {self.request.id}] 数据库连接断开，重新连接后重试")
                db.rollback()
                db.close()
                # 重新获取连接
                from app.config.database import engine
                from sqlalchemy.orm import sessionmaker
                SessionLocal = sessionmaker(bind=engine)
                db = SessionLocal()
                db.execute(
                    text("""INSERT INTO code_analysis_cache 
                    (repository_id, cache_type, cache_key, cache_data, expires_at)
                    VALUES (:repo_id, 'wiki_content', 'full', :cache_data, :expires_at)
                    ON DUPLICATE KEY UPDATE cache_data = VALUES(cache_data), expires_at = VALUES(expires_at)"""),
                    {"repo_id": repo_id, "cache_data": wiki_content_json, "expires_at": expires_at}
                )
                db.commit()
            else:
                raise
        
        # 6. 索引 Wiki 内容到 OpenSearch（用于语义搜索）
        try:
            logger.info(f"[Task {self.request.id}] 开始索引 Wiki 内容到 OpenSearch: repo_id={repo_id}")
            # 在同步上下文中运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_index_wiki_content_to_opensearch(self, repo_id, repo.repo_name, wiki_content))
                logger.info(f"[Task {self.request.id}] ✅ Wiki 内容已索引到 OpenSearch: repo_id={repo_id}")
            finally:
                loop.close()
        except Exception as e:
            # 索引失败不影响主流程，只记录警告
            logger.warning(f"[Task {self.request.id}] ⚠️ Wiki 内容索引到 OpenSearch 失败: {e}", exc_info=True)
        
        logger.info(f"[Task {self.request.id}] Wiki 内容生成完成: repo_id={repo_id}")
        
        return {
            'status': 'completed',
            'repository_id': repo_id,
            'result': wiki_content
        }
    
    except Exception as e:
        logger.error(f"[Task {self.request.id}] Wiki 内容生成失败: {e}", exc_info=True)
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise
    finally:
        # 延迟释放锁（等待5秒，确保缓存已写入，并给前端时间处理结果）
        # 这样可以避免任务刚完成就立即触发新任务
        import time
        time.sleep(5)  # 等待5秒
        
        # 释放锁
        try:
            asyncio.run(cache_manager.release_lock(lock_key, value=lock_value))
            logger.debug(f"[Task {self.request.id}] 已释放 Wiki 生成锁: repo_id={repo_id}")
        except Exception as lock_err:
            logger.warning(f"[Task {self.request.id}] 释放锁失败: {lock_err}")
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
        
        if not repo or not repo.local_path:
            raise ValueError("仓库未克隆")
        
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
        
        # 优化缓存数据：不存储完整的文件列表
        cache_data = {
            'statistics': structure_data['statistics'],
            'file_count': len(structure_data['files']),
            'sample_files': structure_data['files'][:100] if len(structure_data['files']) > 100 else structure_data['files']
        }
        cache_json = json.dumps(cache_data)
        
        # 检查数据大小
        data_size_mb = len(cache_json.encode('utf-8')) / (1024 * 1024)
        logger.info(f"[Task {self.request.id}] 缓存数据大小: {data_size_mb:.2f} MB")
        
        if data_size_mb > 50:
            logger.warning(f"[Task {self.request.id}] 缓存数据过大，只存储统计信息")
            cache_data = {
                'statistics': structure_data['statistics'],
                'file_count': len(structure_data['files'])
            }
            cache_json = json.dumps(cache_data)
        
        # 使用重试机制保存
        try:
            db.execute(
                text("""INSERT INTO code_analysis_cache 
                (repository_id, cache_type, cache_key, cache_data, expires_at)
                VALUES (:repo_id, 'structure', 'full', :cache_data, :expires_at)
                ON DUPLICATE KEY UPDATE cache_data = VALUES(cache_data), expires_at = VALUES(expires_at)"""),
                {"repo_id": repo_id, "cache_data": cache_json, "expires_at": expires_at}
            )
            db.commit()
        except OperationalError as e:
            error_code = e.orig.args[0] if hasattr(e, 'orig') and hasattr(e.orig, 'args') else None
            if error_code in (2006, 2013) or 'gone away' in str(e).lower():
                logger.warning(f"[Task {self.request.id}] 数据库连接断开，重新连接后重试")
                db.rollback()
                db.close()
                # 重新获取连接
                from app.config.database import engine
                from sqlalchemy.orm import sessionmaker
                SessionLocal = sessionmaker(bind=engine)
                db = SessionLocal()
                db.execute(
                    text("""INSERT INTO code_analysis_cache 
                    (repository_id, cache_type, cache_key, cache_data, expires_at)
                    VALUES (:repo_id, 'structure', 'full', :cache_data, :expires_at)
                    ON DUPLICATE KEY UPDATE cache_data = VALUES(cache_data), expires_at = VALUES(expires_at)"""),
                    {"repo_id": repo_id, "cache_data": cache_json, "expires_at": expires_at}
                )
                db.commit()
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
