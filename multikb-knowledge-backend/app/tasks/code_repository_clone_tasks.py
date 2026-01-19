"""
代码库克隆相关任务
包含克隆、更新等操作
"""

import os
import json
from datetime import datetime, timedelta
from sqlalchemy import text

from app.tasks.celery_app import celery_app
from app.core.logging import logger
from app.services.git_service import GitService
from app.services.code_analyzer_service import CodeAnalyzerService
from app.services.code_analysis_agent_v2 import CodeAnalysisAgentV2
from app.config.settings import settings
from app.tasks.code_repository_helpers import (
    save_cache_with_retry as _save_cache_with_retry,
    resolve_import_to_file_path as _resolve_import_to_file_path,
    delete_cache as _delete_cache
)
from app.tasks.code_repository_clone_helpers import (
    save_files_and_symbols_to_db,
    create_dependency_edges
)


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
        
        from app.config.database import engine
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        try:
            # ✅ 使用 Agent V2（基于 Function Calling + Thinking 模型）
            agent = CodeAnalysisAgentV2(db=db)
            agent_result = agent.analyze_repository(local_path)
            
            # Agent V2 返回结构: {'static_analysis': {...}, 'call_chain': {...}, 'agent_metadata': {...}}
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
            cache_data = {
                'statistics': analysis['statistics'],
                'file_count': len(analysis['files']),
                # 只存储前 100 个文件作为示例（如果需要）
                'sample_files': analysis['files'][:100] if len(analysis['files']) > 100 else analysis['files']
            }
            
            cache_json = json.dumps(cache_data)
            cache_size_mb = len(cache_json.encode('utf-8')) / (1024 * 1024)
            logger.info(f"[Task {self.request.id}] 缓存数据大小: {cache_size_mb:.2f} MB")
            
            # 如果数据超过 3MB（MySQL max_allowed_packet 通常默认 4MB，留安全余量），精简数据
            if cache_size_mb > 3:
                logger.warning(f"[Task {self.request.id}] ⚠️ 缓存数据过大 ({cache_size_mb:.2f} MB)，超过 MySQL max_allowed_packet 限制，精简数据")
                # 精简策略：只保存文件路径和基本统计信息，移除详细的符号列表
                simplified_files = []
                for file_data in analysis['files']:
                    simplified_file = {
                        'path': file_data.get('path', ''),
                        'language': file_data.get('language', ''),
                        'lines': file_data.get('lines', 0),
                        'symbol_count': len(file_data.get('symbols', []))  # 只保存符号数量，不保存详细列表
                    }
                    simplified_files.append(simplified_file)
                
                cache_data = {
                    'statistics': analysis['statistics'],
                    'file_count': len(analysis['files']),
                    'files': simplified_files,  # 精简后的文件列表
                    'note': '数据已精简：移除了详细的符号列表以符合 MySQL max_allowed_packet 限制'
                }
                cache_json = json.dumps(cache_data)
                new_size_mb = len(cache_json.encode('utf-8')) / (1024 * 1024)
                logger.info(f"[Task {self.request.id}] ✅ 数据精简完成: {cache_size_mb:.2f} MB -> {new_size_mb:.2f} MB")
            
            # 如果精简后仍然太大（> 50MB），只存储统计信息
            cache_size_mb = len(cache_json.encode('utf-8')) / (1024 * 1024)
            if cache_size_mb > 50:
                logger.warning(f"[Task {self.request.id}] 缓存数据仍然过大 ({cache_size_mb:.2f} MB)，只存储统计信息")
                cache_data = {
                    'statistics': analysis['statistics'],
                    'file_count': len(analysis['files']),
                    'note': '数据过大，仅保存统计信息'
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
                'summary': analysis['summary'],  # LLM 生成的项目摘要
                'statistics': analysis['statistics']
            }
            summary_json = json.dumps(summary_data)
            summary_size_kb = len(summary_json.encode('utf-8')) / 1024
            summary_length = len(analysis.get('summary', ''))
            logger.info(f"[Task {self.request.id}] 💾 保存 LLM 摘要到数据库: "
                       f"表=code_analysis_cache, cache_type=summary, cache_key=full, "
                       f"repo_id={repo_id}, summary长度={summary_length}字符, 大小={summary_size_kb:.1f}KB")
            _save_cache_with_retry(conn, repo_id, 'summary', 'full', summary_json, expires_at, max_retries=3)
            logger.info(f"[Task {self.request.id}] ✅ LLM 摘要已保存到数据库: "
                       f"repo_id={repo_id}, 表=code_analysis_cache, cache_type=summary")
            
            conn.commit()
            logger.info(f"[Task {self.request.id}] ✅ 所有缓存数据提交成功")
        
        # 8. 保存详细数据到数据库表（code_files 和 code_symbols）
        logger.info(f"[Task {self.request.id}] ========== 开始保存文件和符号到数据库表 ==========")
        logger.info(f"[Task {self.request.id}] 分析结果统计: 文件数={len(analysis.get('files', []))}, "
                   f"总行数={analysis.get('statistics', {}).get('total_lines', 0)}, "
                   f"总函数数={analysis.get('statistics', {}).get('total_functions', 0)}, "
                   f"总类数={analysis.get('statistics', {}).get('total_classes', 0)}")
        
        # 使用辅助函数保存文件和符号
        save_result = save_files_and_symbols_to_db(
            task_id=self.request.id,
            repo_id=repo_id,
            analysis=analysis,
            repo_local_path=local_path
        )
        
        files_saved = save_result.get('files_saved', 0)
        symbols_saved = save_result.get('symbols_saved', 0)
        files_vectorized = save_result.get('files_vectorized', 0)
        symbols_vectorized = save_result.get('symbols_vectorized', 0)
        file_path_to_vid_map = save_result.get('file_path_to_vid_map', {})
        file_imports_data = save_result.get('file_imports_data', [])
        
        # 9. 创建文件之间的依赖关系边
        if settings.USE_NEBULA_GRAPH and file_imports_data and file_path_to_vid_map:
            create_dependency_edges(
                task_id=self.request.id,
                repo_id=repo_id,
                file_imports_data=file_imports_data,
                file_path_to_vid_map=file_path_to_vid_map,
                repo_local_path=local_path
            )
        
        logger.info(f"[Task {self.request.id}] ========== ✅ 分析任务完成 ==========")
        files_count = files_saved
        symbols_count = symbols_saved
        files_vectorized_count = files_vectorized
        symbols_vectorized_count = symbols_vectorized
        
        logger.info(f"[Task {self.request.id}] 📊 最终统计: "
                   f"文件={files_count} (MySQL={files_count}), "
                   f"符号={symbols_count}, "
                   f"文件向量化={files_vectorized_count}/{files_count}, "
                   f"符号向量化={symbols_vectorized_count}/{symbols_count}, "
                   f"统计={analysis.get('statistics', {})}")
        
        # 如果 NebulaGraph 启用但文件数为0，记录警告
        if settings.USE_NEBULA_GRAPH and files_count == 0:
            logger.warning(f"[Task {self.request.id}] ⚠️ NebulaGraph 已启用但未创建任何文件节点，请检查错误日志")
        
        # 自动触发 Wiki 内容生成任务
        try:
            logger.info(f"[Task {self.request.id}] 🚀 自动触发 Wiki 内容生成任务: repo_id={repo_id}")
            wiki_task = celery_app.send_task(
                'tasks.code_repository_tasks.generate_wiki_content',
                args=[repo_id],
                queue='code'
            )
            logger.info(f"[Task {self.request.id}] ✅ Wiki 生成任务已发送: task_id={wiki_task.id}")
        except Exception as wiki_task_error:
            logger.warning(f"[Task {self.request.id}] ⚠️ 自动触发 Wiki 生成任务失败: {wiki_task_error}")
        
        return {
            'status': 'completed',
            'repository_id': repo_id,
            'statistics': analysis['statistics'],
            'files_saved': files_count,
            'symbols_saved': symbols_count,
            'files_vectorized': files_vectorized_count,
            'symbols_vectorized': symbols_vectorized_count,
            'vectorization_status': {
                'files': {
                    'total': files_count,
                    'vectorized': files_vectorized_count,
                    'rate': (files_vectorized_count / files_count * 100) if files_count > 0 else 0
                },
                'symbols': {
                    'total': symbols_count,
                    'vectorized': symbols_vectorized_count,
                    'rate': (symbols_vectorized_count / symbols_count * 100) if symbols_count > 0 else 0
                }
            }
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
                analyzer = CodeAnalyzerService()
                analysis = analyzer.analyze_repository(local_path)
            finally:
                db.close()
            
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
                
                # 清除旧缓存（使用辅助函数删除缓存，包括 MinIO 文件）
                _delete_cache(conn, repo_id)
                
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
