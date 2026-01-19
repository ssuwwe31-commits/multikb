"""
代码库克隆任务的辅助函数
处理文件和符号的保存逻辑
"""

import os
import asyncio
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.core.logging import logger
from app.config.settings import settings
from app.tasks.code_repository_helpers import resolve_import_to_file_path as _resolve_import_to_file_path
from app.models.code_file import CodeFile
from app.models.code_symbol import CodeSymbol


# 批量插入配置（为未来性能优化准备）
# TODO: 实施批量插入优化时使用这些配置
BATCH_SIZE_FILES = 50  # 每批插入50个文件
BATCH_SIZE_SYMBOLS = 200  # 每批插入200个符号
VECTORIZATION_BATCH_SIZE = 100  # 向量化批处理大小


def _prepare_file_data_batch(
    file_data_list: List[Dict],
    repo_id: int,
    knowledge_base_id: Optional[int],
    repo_local_path: str
) -> List[Dict]:
    """
    准备批量插入的文件数据
    
    注意：此函数目前未使用，为未来批量插入性能优化准备
    实施计划见: PERFORMANCE_OPTIMIZATION_PLAN.md
    
    Args:
        file_data_list: 文件数据列表
        repo_id: 仓库ID
        knowledge_base_id: 知识库ID
        repo_local_path: 仓库本地路径
        
    Returns:
        准备好的文件数据列表
    """
    prepared_files = []
    
    def process_file(file_data: Dict) -> Optional[Dict]:
        """处理单个文件数据"""
        try:
            file_path = file_data.get('file_path', '')
            if not file_path:
                return None
            
            file_name = os.path.basename(file_path)
            language = file_data.get('language')
            lines = file_data.get('lines', 0)
            complexity = file_data.get('complexity', {})
            complexity_score = complexity.get('cyclomatic', 0) if isinstance(complexity, dict) else 0
            
            # 计算文件大小和哈希
            file_size = 0
            content_hash = None
            file_content = None
            
            if repo_local_path:
                full_path = os.path.join(repo_local_path, file_path)
                if os.path.exists(full_path):
                    try:
                        file_size = os.path.getsize(full_path)
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            file_content = f.read()
                            content_hash = hashlib.sha256(file_content.encode('utf-8')).hexdigest()
                    except Exception:
                        pass
            
            imports_count = len(file_data.get('imports', []))
            symbols_count = len(file_data.get('symbols', []))
            
            return {
                'repository_id': repo_id,
                'knowledge_base_id': knowledge_base_id,
                'file_path': file_path,
                'file_name': file_name,
                'file_type': None,
                'language': language,
                'content_hash': content_hash,
                'lines_of_code': lines,
                'file_size': file_size,
                'complexity_score': complexity_score if complexity_score > 0 else None,
                'symbols_count': symbols_count,
                'imports_count': imports_count,
                'vector_indexed': False,
                'is_deleted': False,
                '_file_data': file_data,  # 保存原始数据用于后续处理
                '_file_content': file_content  # 保存文件内容用于向量化
            }
        except Exception as e:
            logger.warning(f"准备文件数据失败: {file_data.get('file_path', 'unknown')}, 错误: {e}")
            return None
    
    # 使用线程池并行处理文件读取
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_file, fd): fd for fd in file_data_list}
        for future in as_completed(futures):
            result = future.result()
            if result:
                prepared_files.append(result)
    
    return prepared_files


def save_files_and_symbols_to_db(
    task_id: str,
    repo_id: int,
    analysis: Dict[str, Any],
    repo_local_path: str
) -> Dict[str, Any]:
    """
    保存文件和符号到数据库（MySQL、NebulaGraph、OpenSearch）
    
    Args:
        task_id: 任务ID
        repo_id: 仓库ID
        analysis: 分析结果
        repo_local_path: 仓库本地路径
        
    Returns:
        保存结果统计
    """
    from app.config.database import engine
    from sqlalchemy.orm import sessionmaker
    from app.models.code_repository import CodeRepository
    from app.services.code_file_service import get_code_file_service
    from app.services.code_symbol_service import get_code_symbol_service
    from app.services.code_vectorization_service import CodeVectorizationService
    
    SessionLocal = sessionmaker(bind=engine)
    db_session = SessionLocal()
    
    files_saved = 0
    files_vectorized = 0
    symbols_saved = 0
    symbols_vectorized = 0
    files_errors = 0
    symbols_errors = 0
    vectorization_errors = 0
    file_vectorization_errors = 0
    
    file_path_to_vid_map = {}
    file_imports_data = []
    
    try:
        vectorization_service = CodeVectorizationService(db_session)
        
        # 确保 OpenSearch 索引存在
        try:
            from opensearch_schemas.code_indices import init_code_indices
            opensearch = vectorization_service.opensearch
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(init_code_indices(opensearch.client))
                logger.info(f"[Task {task_id}] ✅ 代码索引初始化完成")
            finally:
                loop.close()
        except Exception as index_init_error:
            logger.warning(f"[Task {task_id}] ⚠️ 索引初始化失败（将尝试自动创建）: {index_init_error}")
        
        # 获取仓库信息
        repo = db_session.query(CodeRepository).filter(CodeRepository.id == repo_id).first()
        if not repo:
            logger.warning(f"[Task {task_id}] ⚠️ 仓库不存在: repo_id={repo_id}")
            return {
                'files_saved': 0,
                'symbols_saved': 0,
                'files_vectorized': 0,
                'symbols_vectorized': 0,
                'file_path_to_vid_map': {},
                'file_imports_data': []
            }
        
        knowledge_base_id = repo.knowledge_base_id if repo else None
        
        # 先创建仓库节点到 NebulaGraph
        if settings.USE_NEBULA_GRAPH:
            try:
                from app.services.nebula_code_service import get_nebula_code_service
                nebula_service = get_nebula_code_service(db_session)
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    sync_result = loop.run_until_complete(nebula_service.sync_repository(repo_id))
                    repo_vid = sync_result.get('repository_vid') if isinstance(sync_result, dict) else sync_result
                    logger.info(f"[Task {task_id}] ✅ 仓库节点已同步到 NebulaGraph: repo_id={repo_id}, vid={repo_vid}")
                finally:
                    loop.close()
            except Exception as sync_repo_error:
                logger.error(f"[Task {task_id}] ❌ 同步仓库节点失败: {sync_repo_error}", exc_info=True)
        
        # 批量保存文件
        total_files = len(analysis.get('files', []))
        logger.info(f"[Task {task_id}] 📦 准备保存 {total_files} 个文件到 MySQL 和 NebulaGraph")
        
        file_service = get_code_file_service(db_session)
        symbol_service = get_code_symbol_service(db_session)
        
        for file_data in analysis.get('files', []):
            try:
                file_path = file_data.get('file_path', '')
                if not file_path:
                    continue
                
                file_name = os.path.basename(file_path)
                language = file_data.get('language')
                lines = file_data.get('lines', 0)
                complexity = file_data.get('complexity', {})
                complexity_score = complexity.get('cyclomatic', 0) if isinstance(complexity, dict) else 0
                
                # 计算文件大小
                file_size = 0
                try:
                    if repo_local_path:
                        full_path = os.path.join(repo_local_path, file_path)
                        if os.path.exists(full_path):
                            file_size = os.path.getsize(full_path)
                except Exception:
                    pass
                
                imports_count = len(file_data.get('imports', []))
                file_symbols_count_before = len(file_data.get('symbols', []))
                
                # 计算内容哈希
                content_hash = None
                file_content = None
                if repo_local_path:
                    full_path = os.path.join(repo_local_path, file_path)
                    if os.path.exists(full_path):
                        try:
                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                file_content = f.read()
                                import hashlib
                                content_hash = hashlib.sha256(file_content.encode('utf-8')).hexdigest()
                        except Exception:
                            pass
                
                file_vid = None
                file_id = None
                
                # 1. 保存到 MySQL
                try:
                    code_file = file_service.create_file(
                        repository_id=repo_id,
                        file_path=file_path,
                        file_name=file_name,
                        file_type=None,
                        language=language,
                        content=file_content,
                        lines_of_code=lines,
                        file_size=file_size,
                        complexity_score=complexity_score if complexity_score > 0 else None,
                        symbols_count=file_symbols_count_before,
                        imports_count=imports_count,
                        content_hash=content_hash
                    )
                    file_id = code_file.id
                    files_saved += 1
                except Exception as mysql_error:
                    logger.error(f"[Task {task_id}] ❌ 保存文件到 MySQL 失败: {file_path}, 错误: {mysql_error}")
                    file_id = None
                
                # 2. 保存到 NebulaGraph
                if settings.USE_NEBULA_GRAPH:
                    try:
                        from app.services.nebula_code_service import get_nebula_code_service
                        nebula_service = get_nebula_code_service(db_session)
                        
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            file_vid = loop.run_until_complete(
                                nebula_service.create_file_node_direct(
                                    repository_id=repo_id,
                                    file_path=file_path,
                                    file_name=file_name,
                                    language=language,
                                    lines_of_code=lines,
                                    file_size=file_size,
                                    complexity_score=complexity_score,
                                    symbols_count=file_symbols_count_before,
                                    imports_count=imports_count,
                                    knowledge_base_id=knowledge_base_id,
                                    content_hash=content_hash
                                )
                            )
                            
                            repo_vid = f"code_repository_{repo_id}"
                            loop.run_until_complete(
                                nebula_service._create_contains_edge(repo_vid, file_vid, "repository")
                            )
                            
                            file_path_to_vid_map[file_path] = file_vid
                            file_imports_data.append({
                                'file_path': file_path,
                                'file_vid': file_vid,
                                'imports': file_data.get('imports', [])
                            })
                        finally:
                            loop.close()
                    except Exception as nebula_error:
                        logger.error(f"[Task {task_id}] ❌ 创建文件到 NebulaGraph 失败: {file_path}, 错误: {nebula_error}")
                        files_errors += 1
                
                # 3. 向量化文件
                if settings.USE_NEBULA_GRAPH and file_vid:
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            result = loop.run_until_complete(
                                vectorization_service.vectorize_code_file_by_vid(
                                    file_vid=file_vid,
                                    file_path=file_path,
                                    repository_id=repo_id,
                                    knowledge_base_id=knowledge_base_id,
                                    language=language,
                                    content=file_content
                                )
                            )
                            if result is not None:
                                files_vectorized += 1
                        finally:
                            loop.close()
                    except Exception as vectorize_file_error:
                        file_vectorization_errors += 1
                        if file_vectorization_errors <= 5:
                            logger.warning(f"[Task {task_id}] 向量化文件失败: {file_path}, 错误: {vectorize_file_error}")
                
                # 4. 保存符号
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
                        if symbol_type == 'method':
                            for cls in file_data.get('symbols', []):
                                if cls.get('type') == 'class':
                                    cls_start = cls.get('line', 0)
                                    cls_end = cls.get('end_line', cls_start)
                                    if cls_start <= start_line <= cls_end:
                                        qualified_name = f"{cls.get('name', '')}.{symbol_name}"
                                        break
                        
                        if qualified_name and len(qualified_name) > 495:
                            qualified_name = qualified_name[:492] + "..."
                        
                        # 构建 signature
                        parameters = symbol.get('parameters', [])
                        return_type = symbol.get('return_type')
                        
                        signature_parts = []
                        if parameters:
                            if isinstance(parameters[0], dict):
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
                                signature_parts = [str(p) for p in parameters]
                        
                        signature = f"({', '.join(signature_parts)})" if signature_parts else "()"
                        
                        # 处理 return_type
                        return_type_clean = None
                        if return_type:
                            return_type_single_line = ' '.join(return_type.replace('\r\n', ' ').replace('\n', ' ').split())
                            if len(return_type_single_line) > 95:
                                return_type_clean = return_type_single_line[:92] + "..."
                            else:
                                return_type_clean = return_type_single_line
                            signature += f" -> {return_type}"
                        
                        lines_count = max(1, end_line - start_line + 1) if end_line > start_line else 1
                        symbol_complexity = symbol.get('complexity', {}).get('cyclomatic', 0) if isinstance(symbol.get('complexity'), dict) else 0
                        
                        symbol_vid = None
                        symbol_id = None
                        
                        # 保存到 MySQL
                        if file_id:
                            try:
                                code_symbol = symbol_service.create_symbol(
                                    file_id=file_id,
                                    repository_id=repo_id,
                                    symbol_type=symbol_type,
                                    symbol_name=symbol_name,
                                    qualified_name=qualified_name,
                                    signature=signature,
                                    start_line=start_line,
                                    end_line=end_line,
                                    docstring=symbol.get('docstring', '') if symbol.get('docstring') else None,
                                    parameters=parameters if parameters else None,
                                    return_type=return_type_clean,
                                    complexity_score=symbol_complexity if symbol_complexity > 0 else None,
                                    lines_count=lines_count
                                )
                                symbol_id = code_symbol.id
                                symbols_saved += 1
                                file_symbols_count += 1
                            except Exception as mysql_error:
                                logger.warning(f"[Task {task_id}] ⚠️ 保存符号到 MySQL 失败: {file_path}:{symbol_name}, 错误: {mysql_error}")
                        
                        # 保存到 NebulaGraph
                        if settings.USE_NEBULA_GRAPH and file_vid:
                            try:
                                from app.services.nebula_code_service import get_nebula_code_service
                                nebula_service = get_nebula_code_service(db_session)
                                
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    symbol_vid = loop.run_until_complete(
                                        nebula_service.create_symbol_node_direct(
                                            repository_id=repo_id,
                                            file_path=file_path,
                                            symbol_name=symbol_name,
                                            symbol_type=symbol_type,
                                            qualified_name=qualified_name,
                                            start_line=start_line,
                                            end_line=end_line,
                                            signature=signature,
                                            docstring=symbol.get('docstring', '') if symbol.get('docstring') else None,
                                            return_type=return_type,
                                            complexity_score=symbol_complexity if symbol_complexity > 0 else 0.0,
                                            lines_count=lines_count,
                                            knowledge_base_id=knowledge_base_id,
                                            file_vid=file_vid
                                        )
                                    )
                                    if not symbol_id:
                                        symbols_saved += 1
                                        file_symbols_count += 1
                                finally:
                                    loop.close()
                            except Exception as nebula_error:
                                logger.error(f"[Task {task_id}] ❌ 创建符号到 NebulaGraph 失败: {file_path}:{symbol_name}, 错误: {nebula_error}")
                                symbols_errors += 1
                        
                        # 向量化符号
                        if settings.USE_NEBULA_GRAPH and symbol_vid and file_vid:
                            try:
                                code_content = None
                                if repo_local_path:
                                    full_path = os.path.join(repo_local_path, file_path)
                                    if os.path.exists(full_path) and start_line and end_line:
                                        try:
                                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                                lines_list = f.readlines()
                                                if start_line <= len(lines_list) and end_line <= len(lines_list):
                                                    code_content = ''.join(lines_list[start_line-1:end_line])
                                        except Exception:
                                            pass
                                
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    loop.run_until_complete(
                                        vectorization_service.vectorize_symbol_by_vid(
                                            symbol_vid=symbol_vid,
                                            file_vid=file_vid,
                                            repository_id=repo_id,
                                            knowledge_base_id=knowledge_base_id,
                                            symbol_name=symbol_name,
                                            symbol_type=symbol_type,
                                            qualified_name=qualified_name,
                                            signature=signature,
                                            docstring=symbol.get('docstring', '') if symbol.get('docstring') else None,
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
                                    logger.warning(f"[Task {task_id}] 向量化符号失败: {file_path}:{symbol_name}, 错误: {vectorize_error}")
                    
                    except Exception as sym_error:
                        symbols_errors += 1
                        if symbols_errors <= 5:
                            logger.warning(f"[Task {task_id}] 保存符号失败: {file_path}:{symbol.get('name', 'unknown')}, 错误: {sym_error}")
                        continue
                
                # 每100个文件提交一次
                if files_saved % 100 == 0:
                    db_session.commit()
                    if files_saved % 200 == 0:
                        logger.info(f"[Task {task_id}] 💾 批量提交: "
                                   f"文件={files_saved}/{total_files} (向量化={files_vectorized}), "
                                   f"符号={symbols_saved} (向量化={symbols_vectorized})")
            
            except Exception as file_error:
                files_errors += 1
                if files_errors <= 5:
                    logger.warning(f"[Task {task_id}] 保存文件失败: {file_data.get('file_path', 'unknown')}, 错误: {file_error}")
                continue
        
        # 最终提交
        db_session.commit()
        logger.info(f"[Task {task_id}] 💾 数据库提交完成")
        
        logger.info(f"[Task {task_id}] 📈 保存统计: "
                   f"文件={files_saved}/{total_files}, "
                   f"文件向量化={files_vectorized}, "
                   f"符号={symbols_saved}, "
                   f"符号向量化={symbols_vectorized}")
        
        return {
            'files_saved': files_saved,
            'symbols_saved': symbols_saved,
            'files_vectorized': files_vectorized,
            'symbols_vectorized': symbols_vectorized,
            'file_path_to_vid_map': file_path_to_vid_map,
            'file_imports_data': file_imports_data
        }
    
    except Exception as save_error:
        db_session.rollback()
        logger.error(f"[Task {task_id}] ❌ 保存文件和符号失败: {save_error}", exc_info=True)
        return {
            'files_saved': files_saved,
            'symbols_saved': symbols_saved,
            'files_vectorized': files_vectorized,
            'symbols_vectorized': symbols_vectorized,
            'file_path_to_vid_map': file_path_to_vid_map,
            'file_imports_data': file_imports_data
        }
    finally:
        db_session.close()


def create_dependency_edges(
    task_id: str,
    repo_id: int,
    file_imports_data: List[Dict[str, Any]],
    file_path_to_vid_map: Dict[str, str],
    repo_local_path: str
):
    """
    创建文件之间的依赖关系边
    
    Args:
        task_id: 任务ID
        repo_id: 仓库ID
        file_imports_data: 文件导入数据列表
        file_path_to_vid_map: 文件路径到VID的映射
        repo_local_path: 仓库本地路径
    """
    if not settings.USE_NEBULA_GRAPH or not file_imports_data or not file_path_to_vid_map:
        return
    
    try:
        from app.config.database import engine
        from sqlalchemy.orm import sessionmaker
        from app.services.nebula_code_service import get_nebula_code_service
        
        SessionLocal = sessionmaker(bind=engine)
        db_session = SessionLocal()
        
        try:
            nebula_service = get_nebula_code_service(db_session)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                total_edges_created = 0
                for file_info in file_imports_data:
                    source_file_path = file_info['file_path']
                    source_file_vid = file_info['file_vid']
                    imports = file_info.get('imports', [])
                    
                    if not imports:
                        continue
                    
                    for imp in imports:
                        import_module = imp.get('module', '') or imp.get('name', '')
                        if not import_module:
                            continue
                        
                        target_file_path = _resolve_import_to_file_path(
                            import_module,
                            source_file_path,
                            list(file_path_to_vid_map.keys()),
                            repo_local_path
                        )
                        
                        if target_file_path and target_file_path in file_path_to_vid_map:
                            target_file_vid = file_path_to_vid_map[target_file_path]
                            try:
                                loop.run_until_complete(
                                    nebula_service._create_imports_edge(
                                        source_vid=source_file_vid,
                                        target_vid=target_file_vid,
                                        import_statement=import_module,
                                        line_number=imp.get('line', 0)
                                    )
                                )
                                total_edges_created += 1
                            except Exception as edge_error:
                                error_msg = str(edge_error).lower()
                                if 'existed' not in error_msg and 'duplicate' not in error_msg:
                                    if total_edges_created < 10:
                                        logger.debug(f"[Task {task_id}] 创建依赖边失败: {source_file_path} -> {target_file_path}, 错误: {edge_error}")
                
                if total_edges_created > 0:
                    logger.info(f"[Task {task_id}] ✅ 已创建 {total_edges_created} 条文件依赖关系边")
            finally:
                loop.close()
        finally:
            db_session.close()
    
    except Exception as edges_error:
        logger.warning(f"[Task {task_id}] ⚠️ 创建文件依赖关系边失败: {edges_error}")
