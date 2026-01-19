"""
Code Vectorization Service
代码向量化服务 - 将代码内容向量化并存入 OpenSearch
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime
import os
import hashlib
import asyncio
import json

from app.core.logging import logger
from app.config.settings import settings
from app.models.code_file import CodeFile
from app.models.code_symbol import CodeSymbol
from app.services.opensearch_service import OpenSearchService
from app.services.vector_service import VectorService
from opensearch_schemas.code_indices import CODE_FILES_INDEX, CODE_SYMBOLS_INDEX


class CodeVectorizationService:
    """代码向量化服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.opensearch = OpenSearchService()
        # 复用知识库的向量化服务（需要传入 db）
        self.vector_service = VectorService(db)
        # 向量缓存配置
        self.vector_cache: Dict[str, List[float]] = {}
        self.cache_enabled = settings.CODE_VECTORIZATION_CACHE_ENABLED
        # 记录使用的向量化模型（用于日志）
        self.embedding_model = settings.OLLAMA_EMBEDDING_MODEL
        logger.info(f"代码向量化服务初始化: 模型={self.embedding_model}, 缓存={self.cache_enabled}")
    
    async def vectorize_code_file(
        self,
        file_id: int,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        向量化代码文件
        
        Args:
            file_id: 文件ID
            content: 文件内容（可选，如果不提供则从本地读取）
            
        Returns:
            向量化结果
        """
        try:
            # 1. 获取文件信息
            code_file = self.db.query(CodeFile).filter(
                CodeFile.id == file_id
            ).first()
            
            if not code_file:
                logger.error(f"[文件向量化] ❌ 文件不存在: file_id={file_id}")
                raise ValueError(f"File {file_id} not found")
            
            # 2. 获取文件内容
            if not content:
                from app.models.code_repository import CodeRepository
                repo = self.db.query(CodeRepository).filter(
                    CodeRepository.id == code_file.repository_id
                ).first()
                
                if not repo or not repo.local_path:
                    raise ValueError("Repository not cloned locally")
                
                file_full_path = os.path.join(repo.local_path, code_file.file_path)
                
                if not os.path.exists(file_full_path):
                    raise ValueError(f"File not found: {file_full_path}")
                
                with open(file_full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            
            # 检查文件是否为空（空文件或只有空白字符）
            if not content or not content.strip():
                # 不再记录跳过空文件的日志，减少日志量
                return None  # 返回 None 表示跳过，而不是抛出错误
            
            # 3. 预处理代码内容（提取关键信息，针对 qwen3-embedding:4b 优化）
            processed_content = self._preprocess_code_content(content, code_file.language)
            
            # 检查预处理后的内容是否为空
            if not processed_content or not processed_content.strip():
                # 不再记录跳过预处理后为空文件的日志，减少日志量
                return None
            
            # 3.5. 计算预处理后的内容哈希（用于向量复用）
            # 注意：使用预处理后的内容计算哈希，确保相同预处理结果复用相同向量
            processed_content_hash = hashlib.md5(processed_content.encode('utf-8')).hexdigest()
            
            # 3.6. 检查 OpenSearch 中是否已有相同预处理内容哈希的文件向量（复用向量）
            # 查询时只按 content_hash（预处理后的），不涉及文件路径，所以不同目录但内容相同的文件可以复用
            vector = None
            existing_vector = await self._get_existing_vector_by_hash(processed_content_hash)
            if existing_vector:
                # 不再记录文件向量复用的日志，减少日志量
                vector = existing_vector
                # 将复用的向量加入内存缓存
                if self.cache_enabled:
                    cache_key = f"hash_{processed_content_hash}"
                    self.vector_cache[cache_key] = vector
            
            # 4. 如果未找到已存在的向量，生成新向量（使用 Ollama qwen3-embedding:4b，代码专用向量模型）
            if not vector:
                vector = await self._generate_embedding_with_retry(
                    processed_content, 
                    processed_content_hash  # 使用预处理后的内容哈希
                )
            
            if not vector:
                logger.warning(f"[文件向量化] ❌ 向量为空，跳过: file_id={file_id}")
                return None  # 返回 None 表示跳过，而不是抛出错误
            
            # 4. 准备索引文档
            doc = {
                "file_id": code_file.id,
                "repository_id": code_file.repository_id,
                "knowledge_base_id": code_file.knowledge_base_id,
                "file_path": code_file.file_path,
                "file_name": code_file.file_name,
                "language": code_file.language,
                "content": content[:10000],  # 限制内容长度
                "content_summary": self._extract_code_summary(content, code_file.language),  # 智能提取摘要
                "lines_of_code": code_file.lines_of_code,
                "file_size": code_file.file_size,
                "symbols_count": code_file.symbols_count,
                "imports_count": code_file.imports_count,
                "complexity_score": code_file.complexity_score,
                "content_vector": vector,
                "content_hash": code_file.content_hash,  # 原始内容哈希（用于文件变更检测）
                "processed_content_hash": processed_content_hash,  # 预处理后的内容哈希（用于向量复用）
                "created_at": code_file.created_at.isoformat() if code_file.created_at else None,
                "updated_at": code_file.updated_at.isoformat() if code_file.updated_at else None,
                "vector_updated_at": datetime.now().isoformat()
            }
            
            # 6. 索引到 OpenSearch
            doc_id = f"file_{code_file.id}"
            await self.opensearch.index_document(
                index=CODE_FILES_INDEX,
                doc_id=doc_id,
                document=doc
            )
            
            # 7. 更新数据库状态
            code_file.opensearch_doc_id = doc_id
            code_file.vector_indexed = True
            code_file.vector_updated_at = datetime.now()
            self.db.commit()
            # 不再记录单个文件的向量化完成日志，减少日志量（批量统计会在批量完成后统一输出）
            
            return {
                "file_id": file_id,
                "doc_id": doc_id,
                "vector_dimension": len(vector),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"向量化代码文件失败 (file_id={file_id}): {e}", exc_info=True)
            self.db.rollback()
            raise
    
    async def vectorize_code_file_by_vid(
        self,
        file_vid: str,
        file_path: str,
        repository_id: int,
        knowledge_base_id: Optional[int],
        language: Optional[str] = None,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        使用 VID 向量化代码文件（不依赖 MySQL）
        
        Args:
            file_vid: 文件节点的 VID
            file_path: 文件路径
            repository_id: 仓库ID
            knowledge_base_id: 知识库ID
            language: 编程语言
            content: 文件内容
            
        Returns:
            向量化结果
        """
        try:
            # 检查文件是否为空
            if not content or not content.strip():
                # 不再记录跳过空文件的日志，减少日志量
                return None
            
            # 预处理代码内容
            processed_content = self._preprocess_code_content(content, language)
            
            if not processed_content or not processed_content.strip():
                # 不再记录跳过预处理后为空文件的日志，减少日志量
                return None
            
            # 计算预处理后的内容哈希
            processed_content_hash = hashlib.md5(processed_content.encode('utf-8')).hexdigest()
            
            # 检查是否已有相同哈希的向量
            vector = None
            existing_vector = await self._get_existing_vector_by_hash(processed_content_hash)
            if existing_vector:
                # 不再记录文件向量复用的日志，减少日志量
                vector = existing_vector
                if self.cache_enabled:
                    cache_key = f"hash_{processed_content_hash}"
                    self.vector_cache[cache_key] = vector
            
            # 生成新向量
            if not vector:
                vector = await self._generate_embedding_with_retry(
                    processed_content,
                    processed_content_hash
                )
            
            if not vector:
                logger.warning(f"[文件向量化] ❌ 向量为空，跳过: file_vid={file_vid}")
                return None
            
            # 计算内容哈希
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # 准备索引文档
            doc = {
                "file_id": 0,  # 不再使用 MySQL ID，设置为 0
                "file_vid": file_vid,  # 添加 VID 字段
                "repository_id": repository_id,
                "knowledge_base_id": knowledge_base_id or 0,
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "language": language or "",
                "content": content[:10000],  # 限制内容长度
                "content_summary": self._extract_code_summary(content, language),  # 智能提取摘要
                "content_vector": vector,
                "content_hash": content_hash,
                "processed_content_hash": processed_content_hash,
                "vector_updated_at": datetime.now().isoformat()
            }
            
            # 索引到 OpenSearch（使用 VID 作为 doc_id）
            doc_id = file_vid  # 直接使用 VID 作为 doc_id
            await self.opensearch.index_document(
                index=CODE_FILES_INDEX,
                doc_id=doc_id,
                document=doc
            )
            
            # 不再记录单个文件的向量化完成日志，减少日志量（批量统计会在批量完成后统一输出）
            
            return {
                "file_vid": file_vid,
                "doc_id": doc_id,
                "vector_dimension": len(vector),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"向量化代码文件失败 (file_vid={file_vid}): {e}", exc_info=True)
            raise
    
    async def vectorize_code_symbol(
        self,
        symbol_id: int,
        code_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        向量化代码符号
        
        Args:
            symbol_id: 符号ID
            code_content: 符号代码内容（可选）
            
        Returns:
            向量化结果
        """
        try:
            # 1. 获取符号信息
            symbol = self.db.query(CodeSymbol).filter(
                CodeSymbol.id == symbol_id
            ).first()
            
            if not symbol:
                logger.error(f"[符号向量化] ❌ 符号不存在: symbol_id={symbol_id}")
                raise ValueError(f"Symbol {symbol_id} not found")
            
            # 2. 获取符号代码内容（如果未提供）
            if not code_content:
                from app.models.code_repository import CodeRepository
                from app.models.code_file import CodeFile
                
                code_file = self.db.query(CodeFile).filter(
                    CodeFile.id == symbol.file_id
                ).first()
                
                if not code_file:
                    raise ValueError("File not found")
                
                repo = self.db.query(CodeRepository).filter(
                    CodeRepository.id == code_file.repository_id
                ).first()
                
                if not repo or not repo.local_path:
                    raise ValueError("Repository not cloned locally")
                
                file_full_path = os.path.join(repo.local_path, code_file.file_path)
                
                if os.path.exists(file_full_path) and symbol.start_line and symbol.end_line:
                    with open(file_full_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        code_content = ''.join(lines[symbol.start_line-1:symbol.end_line])
                else:
                    # 使用签名作为内容
                    code_content = symbol.signature or symbol.symbol_name
            
            # 3. 构建向量化文本（智能提取关键信息）
            # 优先级：文档字符串 > 签名 > 代码内容
            vectorization_text = self._build_symbol_vectorization_text(
                symbol, code_content
            )
            
            # 检查向量化文本是否为空
            if not vectorization_text or not vectorization_text.strip():
                # 不再记录跳过空符号的日志，减少日志量
                return None
            
            # 3.5. 计算内容哈希
            content_hash = hashlib.md5(vectorization_text.encode()).hexdigest()
            
            # 3.6. 检查 OpenSearch 中是否已有相同 content_hash 的符号向量（复用向量）
            vector = None
            existing_vector = await self._get_existing_symbol_vector_by_hash(content_hash)
            if existing_vector:
                # 不再记录每个符号的向量复用日志，减少日志量（批量统计会在批量完成后统一输出）
                vector = existing_vector
                # 将复用的向量加入内存缓存
                if self.cache_enabled:
                    cache_key = f"hash_{content_hash}"
                    self.vector_cache[cache_key] = vector
            
            # 4. 如果未找到已存在的向量，生成新向量（使用 Ollama qwen3-embedding:4b，代码专用向量模型）
            # 支持缓存和重试机制
            if not vector:
                vector = await self._generate_embedding_with_retry(
                    vectorization_text,
                    content_hash
                )
            
            if not vector:
                logger.warning(f"[符号向量化] ❌ 向量为空，跳过: symbol_id={symbol_id}")
                return None  # 返回 None 表示跳过，而不是抛出错误（与文件向量化保持一致）
            
            # 6. 准备索引文档
            # 将 parameters 转换为字符串（因为索引 schema 定义为 text 类型）
            parameters_str = None
            if symbol.parameters:
                if isinstance(symbol.parameters, (list, dict)):
                    try:
                        parameters_str = json.dumps(symbol.parameters, ensure_ascii=False)
                    except (TypeError, ValueError) as e:
                        logger.warning(f"参数序列化失败，使用 str() 转换: {e}")
                        parameters_str = str(symbol.parameters)
                else:
                    parameters_str = str(symbol.parameters)
            
            doc = {
                "symbol_id": symbol.id,
                "file_id": symbol.file_id,
                "repository_id": symbol.repository_id,
                "knowledge_base_id": symbol.knowledge_base_id,
                "symbol_name": symbol.symbol_name,
                "symbol_type": symbol.symbol_type,
                "qualified_name": symbol.qualified_name,
                "signature": symbol.signature,
                "docstring": symbol.docstring,
                "parameters": parameters_str,  # 转换为字符串以匹配 text 类型
                "return_type": symbol.return_type,
                "file_path": code_file.file_path if code_file else None,
                "start_line": symbol.start_line,
                "end_line": symbol.end_line,
                "code_content": code_content[:5000],  # 限制代码长度
                "complexity_score": symbol.complexity_score,
                "lines_count": symbol.lines_count,
                "content_vector": vector,
                "content_hash": content_hash,  # 符号的预处理内容哈希，用于向量复用
                "created_at": symbol.created_at.isoformat() if symbol.created_at else None,
                "updated_at": symbol.updated_at.isoformat() if symbol.updated_at else None,
                "vector_updated_at": datetime.now().isoformat()
            }
            
            # 7. 索引到 OpenSearch
            doc_id = f"symbol_{symbol.id}"
            await self.opensearch.index_document(
                index=CODE_SYMBOLS_INDEX,
                doc_id=doc_id,
                document=doc
            )
            
            # 8. 更新数据库状态
            symbol.opensearch_doc_id = doc_id
            symbol.vector_indexed = True
            symbol.vector_updated_at = datetime.now()
            self.db.commit()
            # 不再记录单个符号的向量化完成日志，减少日志量（批量统计会在批量完成后统一输出）
            
            return {
                "symbol_id": symbol_id,
                "doc_id": doc_id,
                "vector_dimension": len(vector),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"向量化代码符号失败: {e}")
            raise
    
    async def vectorize_symbol_by_vid(
        self,
        symbol_vid: str,
        file_vid: str,
        repository_id: int,
        knowledge_base_id: Optional[int],
        symbol_name: str,
        symbol_type: str,
        qualified_name: Optional[str],
        signature: Optional[str],
        docstring: Optional[str],
        parameters: Optional[List],
        return_type: Optional[str],
        file_path: str,
        start_line: int,
        end_line: int,
        complexity_score: Optional[float] = None,
        lines_count: Optional[int] = None,
        code_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        使用 VID 向量化代码符号（不依赖 MySQL）
        
        Args:
            symbol_vid: 符号节点的 VID
            file_vid: 文件节点的 VID
            repository_id: 仓库ID
            knowledge_base_id: 知识库ID
            symbol_name: 符号名称
            symbol_type: 符号类型
            qualified_name: 限定名
            signature: 函数签名
            docstring: 文档字符串
            parameters: 参数列表
            return_type: 返回类型
            file_path: 文件路径
            start_line: 起始行号
            end_line: 结束行号
            complexity_score: 复杂度
            lines_count: 代码行数
            code_content: 代码内容
            
        Returns:
            向量化结果
        """
        try:
            # 1. 构建向量化文本
            vectorization_parts = []
            if docstring:
                vectorization_parts.append(docstring)
            if signature:
                vectorization_parts.append(signature)
            if code_content:
                vectorization_parts.append(code_content[:2000])
            if not vectorization_parts:
                vectorization_parts.append(f"{symbol_type} {symbol_name}")
            
            vectorization_text = "\n".join(vectorization_parts)
            
            if not vectorization_text or not vectorization_text.strip():
                logger.info(f"[符号向量化] ⚠️ 向量化文本为空，跳过: qualified_name={qualified_name}")
                return None
            
            # 2. 计算内容哈希
            content_hash = hashlib.md5(vectorization_text.encode()).hexdigest()
            
            # 3. 检查是否已有相同哈希的向量
            vector = None
            existing_vector = await self._get_existing_symbol_vector_by_hash(content_hash)
            if existing_vector:
                # 不再记录每个符号的向量复用日志，减少日志量
                vector = existing_vector
                if self.cache_enabled:
                    cache_key = f"hash_{content_hash}"
                    self.vector_cache[cache_key] = vector
            
            # 4. 生成新向量
            if not vector:
                vector = await self._generate_embedding_with_retry(
                    vectorization_text,
                    content_hash
                )
            
            if not vector:
                # 不再记录跳过空向量的日志，减少日志量
                return None
            
            # 5. 准备索引文档
            parameters_str = None
            if parameters:
                if isinstance(parameters, (list, dict)):
                    try:
                        parameters_str = json.dumps(parameters, ensure_ascii=False)
                    except (TypeError, ValueError) as e:
                        logger.warning(f"参数序列化失败，使用 str() 转换: {e}")
                        parameters_str = str(parameters)
                else:
                    parameters_str = str(parameters)
            
            doc = {
                "symbol_id": 0,  # 不再使用 MySQL ID，设置为 0
                "symbol_vid": symbol_vid,  # 添加 VID 字段
                "file_id": 0,  # 不再使用 MySQL ID，设置为 0
                "file_vid": file_vid,  # 添加 VID 字段
                "repository_id": repository_id,
                "knowledge_base_id": knowledge_base_id or 0,
                "symbol_name": symbol_name,
                "symbol_type": symbol_type,
                "qualified_name": qualified_name or symbol_name,
                "signature": signature or "",
                "docstring": docstring or "",
                "parameters": parameters_str,
                "return_type": return_type or "",
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "complexity_score": complexity_score or 0.0,
                "lines_count": lines_count or 0,
                "code_content": code_content[:2000] if code_content else "",
                "content_vector": vector,
                "content_hash": content_hash,
                "vector_updated_at": datetime.now().isoformat()
            }
            
            # 6. 索引到 OpenSearch（使用 VID 作为 doc_id）
            doc_id = symbol_vid  # 直接使用 VID 作为 doc_id
            await self.opensearch.index_document(
                index=CODE_SYMBOLS_INDEX,
                doc_id=doc_id,
                document=doc
            )
            
            # 不再记录单个符号的向量化完成日志，减少日志量（批量统计会在批量完成后统一输出）
            
            return {
                "symbol_vid": symbol_vid,
                "doc_id": doc_id,
                "vector_dimension": len(vector),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"向量化代码符号失败 (symbol_vid={symbol_vid}): {e}", exc_info=True)
            raise
    
    async def vectorize_symbol_direct(
        self,
        symbol_id: int,
        file_id: int,
        repository_id: int,
        knowledge_base_id: Optional[int],
        symbol_name: str,
        symbol_type: str,
        qualified_name: Optional[str],
        signature: Optional[str],
        docstring: Optional[str],
        parameters: Optional[List],
        return_type: Optional[str],
        file_path: str,
        start_line: int,
        end_line: int,
        complexity_score: Optional[float] = None,
        lines_count: Optional[int] = None,
        code_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        直接向量化代码符号（不依赖MySQL中的详细字段）
        
        Args:
            symbol_id: 符号ID
            file_id: 文件ID
            repository_id: 仓库ID
            knowledge_base_id: 知识库ID
            symbol_name: 符号名称
            symbol_type: 符号类型
            qualified_name: 完整限定名
            signature: 函数签名
            docstring: 文档字符串
            parameters: 参数列表
            return_type: 返回类型
            file_path: 文件路径
            start_line: 起始行号
            end_line: 结束行号
            complexity_score: 复杂度
            lines_count: 代码行数
            code_content: 代码内容（可选）
            
        Returns:
            向量化结果
        """
        try:
            # 1. 构建向量化文本（智能提取关键信息）
            # 优先级：文档字符串 > 签名 > 代码内容
            vectorization_parts = []
            if docstring:
                vectorization_parts.append(docstring)
            if signature:
                vectorization_parts.append(signature)
            if code_content:
                vectorization_parts.append(code_content[:2000])  # 限制代码长度
            if not vectorization_parts:
                vectorization_parts.append(f"{symbol_type} {symbol_name}")
            
            vectorization_text = "\n".join(vectorization_parts)
            
            # 检查向量化文本是否为空
            if not vectorization_text or not vectorization_text.strip():
                logger.info(f"[符号向量化] ⚠️ 向量化文本为空，跳过: qualified_name={qualified_name}")
                return None
            
            # 2. 计算内容哈希（用于向量复用）
            content_hash = hashlib.md5(vectorization_text.encode()).hexdigest()
            
            # 2.5. 检查 OpenSearch 中是否已有相同 content_hash 的符号向量（复用向量）
            vector = None
            existing_vector = await self._get_existing_symbol_vector_by_hash(content_hash)
            if existing_vector:
                # 不再记录每个符号的向量复用日志，减少日志量
                vector = existing_vector
                # 将复用的向量加入内存缓存
                if self.cache_enabled:
                    cache_key = f"hash_{content_hash}"
                    self.vector_cache[cache_key] = vector
            
            # 3. 如果未找到已存在的向量，生成新向量（使用 Ollama qwen3-embedding:4b，代码专用向量模型）
            if not vector:
                vector = await self._generate_embedding_with_retry(
                    vectorization_text,
                    content_hash
                )
            
            if not vector:
                # 不再记录跳过空向量的日志，减少日志量
                return None  # 返回 None 表示跳过，而不是抛出错误（与文件向量化保持一致）
            
            # 4. 准备索引文档（包含完整数据）
            # 将 parameters 转换为字符串（因为索引 schema 定义为 text 类型）
            parameters_str = None
            if parameters:
                if isinstance(parameters, (list, dict)):
                    try:
                        parameters_str = json.dumps(parameters, ensure_ascii=False)
                    except (TypeError, ValueError) as e:
                        logger.warning(f"参数序列化失败，使用 str() 转换: {e}")
                        parameters_str = str(parameters)
                else:
                    parameters_str = str(parameters)
            
            doc = {
                "symbol_id": symbol_id,
                "file_id": file_id,
                "repository_id": repository_id,
                "knowledge_base_id": knowledge_base_id,
                "symbol_name": symbol_name,
                "symbol_type": symbol_type,
                "qualified_name": qualified_name,
                "signature": signature,
                "docstring": docstring,
                "parameters": parameters_str,  # 转换为字符串以匹配 text 类型
                "return_type": return_type,
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "code_content": code_content[:5000] if code_content else None,  # 限制代码长度
                "complexity_score": complexity_score,
                "lines_count": lines_count,
                "content_vector": vector,
                "vector_updated_at": datetime.now().isoformat()
            }
            
            # 5. 索引到 OpenSearch
            doc_id = f"symbol_{symbol_id}"
            await self.opensearch.index_document(
                index=CODE_SYMBOLS_INDEX,
                doc_id=doc_id,
                document=doc
            )
            
            # 6. 更新数据库状态（只更新关联字段）
            symbol = self.db.query(CodeSymbol).filter(
                CodeSymbol.id == symbol_id
            ).first()
            
            if symbol:
                symbol.opensearch_doc_id = doc_id
                symbol.vector_indexed = True
                symbol.vector_updated_at = datetime.now()
                self.db.commit()
            
            return {
                "symbol_id": symbol_id,
                "doc_id": doc_id,
                "vector_dimension": len(vector),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"直接向量化代码符号失败: {symbol_name} ({symbol_id}): {e}")
            raise
    
    async def batch_vectorize_repository(
        self,
        repository_id: int,
        include_symbols: bool = True,
        max_concurrent: Optional[int] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        批量向量化仓库的所有文件和符号（支持并发控制和进度跟踪）
        
        Args:
            repository_id: 仓库ID
            include_symbols: 是否包含符号向量化
            max_concurrent: 最大并发数（默认使用配置值）
            progress_callback: 进度回调函数 callback(phase, current, total, stats)
            
        Returns:
            向量化统计
        """
        max_concurrent = max_concurrent or settings.CODE_VECTORIZATION_MAX_CONCURRENT
        
        try:
            stats = {
                "files": {"total": 0, "success": 0, "error": 0, "skipped": 0},
                "symbols": {"total": 0, "success": 0, "error": 0, "skipped": 0},
                "start_time": datetime.now().isoformat()
            }
            
            # 1. 向量化所有文件（并发控制）
            files = self.db.query(CodeFile).filter(
                CodeFile.repository_id == repository_id,
                CodeFile.is_deleted == False
            ).all()
            
            stats["files"]["total"] = len(files)
            # 批量处理开始日志：保留 info 级别（重要进度信息）
            logger.info(f"[批量向量化] 开始批量向量化文件: 总数={len(files)}, 并发数={max_concurrent}, 模型={settings.OLLAMA_EMBEDDING_MODEL}")
            
            # 使用信号量控制并发数
            semaphore = asyncio.Semaphore(max_concurrent)
            file_progress = {"current": 0}
            
            async def vectorize_file_with_semaphore(file_id: int, file_path: str, file_hash: Optional[str]):
                async with semaphore:
                    try:
                        # 检查是否已向量化（基于数据库中的 vector_indexed 字段）
                        # 注意：这里检查的是数据库状态，不是内存缓存（内存缓存在不同请求间会丢失）
                        file_obj = self.db.query(CodeFile).filter(CodeFile.id == file_id).first()
                        if file_obj and file_obj.vector_indexed and file_obj.opensearch_doc_id:
                            # 检查 OpenSearch 中是否真的存在（避免数据库和 OpenSearch 不一致）
                            try:
                                doc_exists = await self.opensearch.client.exists(
                                    index=CODE_FILES_INDEX,
                                    id=file_obj.opensearch_doc_id
                                )
                                if doc_exists:
                                    stats["files"]["skipped"] += 1
                                    # 移除详细日志，减少日志量（统计信息会在批量完成后统一输出）
                                    # logger.debug(f"跳过已向量化的文件: {file_path} (doc_id: {file_obj.opensearch_doc_id})")
                                    return
                                else:
                                    # OpenSearch 中不存在，但数据库标记为已向量化，需要重新向量化
                                    logger.warning(f"文件 {file_path} 数据库标记为已向量化，但 OpenSearch 中不存在，重新向量化")
                                    file_obj.vector_indexed = False
                                    file_obj.opensearch_doc_id = None
                                    self.db.commit()
                            except Exception as e:
                                # 如果检查失败，记录警告但继续向量化
                                logger.warning(f"检查 OpenSearch 文档存在性失败: {e}，继续向量化")
                        
                        # 执行向量化
                        result = await self.vectorize_code_file(file_id)
                        if result is None:
                            # 返回 None 表示跳过（空文件等），不算错误
                            stats["files"]["skipped"] += 1
                        else:
                            stats["files"]["success"] += 1
                    except Exception as e:
                        stats["files"]["error"] += 1
                        logger.error(f"向量化文件失败 {file_path}: {e}")
                    finally:
                        file_progress["current"] += 1
                        if progress_callback:
                            progress_callback("files", file_progress["current"], stats["files"]["total"], stats)
            
            # 并发执行文件向量化
            file_tasks = [
                vectorize_file_with_semaphore(file.id, file.file_path, file.content_hash)
                for file in files
            ]
            await asyncio.gather(*file_tasks, return_exceptions=True)
            
            # 文件向量化完成日志改为DEBUG，减少日志量（最终汇总会统一输出）
            logger.debug(f"[批量向量化] 文件向量化完成: 成功={stats['files']['success']}, 跳过={stats['files']['skipped']}, 错误={stats['files']['error']}")
            
            # 2. 向量化所有符号（如果启用，并发控制）
            if include_symbols:
                symbols = self.db.query(CodeSymbol).filter(
                    CodeSymbol.repository_id == repository_id,
                    CodeSymbol.is_deleted == False
                ).all()
                
                stats["symbols"]["total"] = len(symbols)
                # 批量处理开始日志：保留 info 级别（重要进度信息）
                logger.info(f"[批量向量化] 开始批量向量化符号: 总数={len(symbols)}, 并发数={max_concurrent}, 模型={settings.OLLAMA_EMBEDDING_MODEL}")
                
                symbol_progress = {"current": 0}
                
                async def vectorize_symbol_with_semaphore(symbol_id: int, symbol_name: str):
                    async with semaphore:
                        try:
                            result = await self.vectorize_code_symbol(symbol_id)
                            if result is None:
                                # 返回 None 表示跳过（空符号等），不算错误
                                stats["symbols"]["skipped"] += 1
                            else:
                                stats["symbols"]["success"] += 1
                        except Exception as e:
                            stats["symbols"]["error"] += 1
                            logger.error(f"向量化符号失败 {symbol_name}: {e}")
                        finally:
                            symbol_progress["current"] += 1
                            if progress_callback:
                                progress_callback("symbols", symbol_progress["current"], stats["symbols"]["total"], stats)
                
                # 并发执行符号向量化
                symbol_tasks = [
                    vectorize_symbol_with_semaphore(symbol.id, symbol.symbol_name)
                    for symbol in symbols
                ]
                await asyncio.gather(*symbol_tasks, return_exceptions=True)
                
                # 符号向量化完成日志改为DEBUG，减少日志量（最终汇总会统一输出）
                logger.debug(f"[批量向量化] 符号向量化完成: 成功={stats['symbols']['success']}, 跳过={stats['symbols']['skipped']}, 错误={stats['symbols']['error']}")

            stats["end_time"] = datetime.now().isoformat()
            logger.info(f"[批量向量化] ✅ 批量向量化完成: 文件成功={stats['files']['success']}, 文件跳过={stats['files']['skipped']}, 文件错误={stats['files']['error']}, 符号成功={stats['symbols']['success']}, 符号跳过={stats['symbols']['skipped']}, 符号错误={stats['symbols']['error']}")
            return stats
            
        except Exception as e:
            logger.error(f"批量向量化失败: {e}", exc_info=True)
            raise
    
    async def delete_file_vector(self, file_id: int) -> bool:
        """
        删除文件向量
        
        Args:
            file_id: 文件ID
            
        Returns:
            是否成功
        """
        try:
            doc_id = f"file_{file_id}"
            await self.opensearch.delete_document(CODE_FILES_INDEX, doc_id)
            
            # 更新数据库状态
            code_file = self.db.query(CodeFile).filter(
                CodeFile.id == file_id
            ).first()
            
            if code_file:
                code_file.vector_indexed = False
                code_file.opensearch_doc_id = None
                self.db.commit()
            
            # 不再记录删除文件向量的日志，减少日志量
            return True
            
        except Exception as e:
            logger.error(f"删除文件向量失败: {e}")
            return False
    
    async def delete_symbol_vector(self, symbol_id: int) -> bool:
        """
        删除符号向量
        
        Args:
            symbol_id: 符号ID
            
        Returns:
            是否成功
        """
        try:
            doc_id = f"symbol_{symbol_id}"
            await self.opensearch.delete_document(CODE_SYMBOLS_INDEX, doc_id)
            
            # 更新数据库状态
            symbol = self.db.query(CodeSymbol).filter(
                CodeSymbol.id == symbol_id
            ).first()
            
            if symbol:
                symbol.vector_indexed = False
                symbol.opensearch_doc_id = None
                self.db.commit()
            
            # 不再记录删除符号向量的日志，减少日志量
            return True
            
        except Exception as e:
            logger.error(f"删除符号向量失败: {e}")
            return False
    
    def _build_symbol_vectorization_text(
        self, 
        symbol: CodeSymbol, 
        code_content: str
    ) -> str:
        """
        构建符号向量化文本（智能提取关键信息）
        
        策略：
        1. 优先使用文档字符串（最语义化）
        2. 其次使用签名（包含参数和返回类型）
        3. 最后使用代码内容（提取关键部分）
        """
        parts = []
        
        # 1. 符号名称（完整限定名）
        if symbol.qualified_name:
            parts.append(f"符号: {symbol.qualified_name}")
        else:
            parts.append(f"符号: {symbol.symbol_name}")
        
        # 2. 文档字符串（优先级最高，语义最丰富）
        if symbol.docstring:
            # 清理文档字符串（移除 JSDoc 标记等）
            docstring = symbol.docstring.strip()
            # 限制长度，保留前 500 字符
            if len(docstring) > 500:
                docstring = docstring[:500] + "..."
            parts.append(f"说明: {docstring}")
        
        # 3. 签名（包含参数和返回类型信息）
        if symbol.signature:
            parts.append(f"签名: {symbol.signature}")
        
        # 4. 参数信息
        if symbol.parameters:
            params_str = str(symbol.parameters)
            if len(params_str) > 200:
                params_str = params_str[:200] + "..."
            parts.append(f"参数: {params_str}")
        
        # 5. 返回类型
        if symbol.return_type:
            parts.append(f"返回: {symbol.return_type}")
        
        # 6. 代码内容（提取关键部分）
        if code_content:
            # 提取代码的关键部分（函数体前 200 行，或前 2000 字符）
            code_lines = code_content.split('\n')
            if len(code_lines) > 200:
                code_content = '\n'.join(code_lines[:200]) + "\n..."
            if len(code_content) > 2000:
                code_content = code_content[:2000] + "..."
            parts.append(f"代码:\n{code_content}")
        
        # 7. 智能截断：如果总长度超过限制，按优先级保留
        result = "\n\n".join(parts)
        from app.config.settings import settings as _settings
        max_length = _settings.TEXT_EMBED_MAX_CHARS
        if len(result) > max_length:
            # 按优先级截断：parts 列表已经按优先级排序
            # 符号名 > 文档字符串 > 签名 > 参数 > 返回类型 > 代码
            truncated_parts = []
            current_length = 0
            separator_length = 2  # "\n\n" 的长度
            
            for i, part in enumerate(parts):
                # 计算添加当前部分后的总长度
                part_length = len(part)
                sep_length = separator_length if truncated_parts else 0
                total_if_added = current_length + sep_length + part_length
                
                if total_if_added <= max_length - 10:  # 留10字符余量
                    # 可以完整添加
                    truncated_parts.append(part)
                    current_length = total_if_added
                else:
                    # 无法完整添加，尝试添加部分内容
                    remaining = max_length - current_length - sep_length - 10
                    if remaining > 50:  # 至少保留50字符才有意义
                        # 对于代码部分（最后一个），尝试保留前部分
                        if i == len(parts) - 1 and part.startswith("代码:\n"):
                            code_part = part[5:]  # 移除 "代码:\n" 前缀
                            truncated_parts.append(f"代码:\n{code_part[:remaining]}...")
                        else:
                            truncated_parts.append(part[:remaining] + "...")
                    break
            
            result = '\n\n'.join(truncated_parts) if truncated_parts else result[:max_length]
        
        return result
    
    def _preprocess_code_content(self, content: str, language: Optional[str] = None) -> str:
        """
        预处理代码内容（提取关键信息用于向量化）
        
        策略：
        1. 提取注释和文档字符串
        2. 提取函数/类定义
        3. 提取导入语句
        4. 去除冗余空白和格式化
        """
        if not content:
            return ""
        
        lines = content.split('\n')
        key_parts = []
        
        # 1. 提取文档字符串和注释
        in_docstring = False
        docstring_lines = []
        comment_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Python docstring
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = not in_docstring
                if in_docstring:
                    docstring_lines.append(line)
                continue
            
            if in_docstring:
                docstring_lines.append(line)
                continue
            
            # 注释
            if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*'):
                comment_lines.append(line)
        
        if docstring_lines:
            key_parts.append('\n'.join(docstring_lines))
        if comment_lines:
            # 只保留前 20 行注释
            key_parts.append('\n'.join(comment_lines[:20]))
        
        # 2. 提取导入语句
        import_lines = [line for line in lines if line.strip().startswith(('import ', 'from ', 'require(', 'import('))]
        if import_lines:
            key_parts.append('\n'.join(import_lines[:30]))  # 最多 30 个导入
        
        # 3. 提取函数/类定义
        definition_lines = []
        for line in lines:
            stripped = line.strip()
            if (stripped.startswith(('def ', 'class ', 'function ', 'const ', 'let ', 'var ')) or
                stripped.startswith(('public ', 'private ', 'protected '))):
                definition_lines.append(line)
        
        if definition_lines:
            key_parts.append('\n'.join(definition_lines[:50]))  # 最多 50 个定义
        
        # 4. 如果提取的关键部分太少，使用原始内容的前 3000 字符
        if len('\n'.join(key_parts)) < 200:
            key_parts.append(content[:3000])
        
        result = '\n\n'.join(key_parts)
        
        # 5. 限制总长度（针对 qwen3-embedding:4b，支持 2048 字符）
        # 但为了保留更多信息，我们使用 2000 字符（留一些余量）
        from app.config.settings import settings as _settings
        max_length = min(_settings.TEXT_EMBED_MAX_CHARS, 2000)
        if len(result) > max_length:
            # 智能截断：优先保留关键信息
            # 策略：保留文档字符串、注释、导入、定义等关键部分
            # 如果关键部分已经超过限制，只保留关键部分
            key_parts_text = '\n\n'.join(key_parts)
            if len(key_parts_text) <= max_length:
                # 关键部分未超过限制，保留全部关键部分
                result = key_parts_text
            else:
                # 关键部分超过限制，按优先级截断
                truncated_parts = []
                current_length = 0
                for part in key_parts:
                    part_with_sep = part if not truncated_parts else '\n\n' + part
                    if current_length + len(part_with_sep) <= max_length - 10:  # 留10字符余量
                        truncated_parts.append(part)
                        current_length += len(part_with_sep)
                    else:
                        # 当前部分无法完整添加，尝试添加部分内容
                        remaining = max_length - current_length - 10
                        if remaining > 50:  # 至少保留50字符才有意义
                            truncated_parts.append(part[:remaining] + "...")
                        break
                result = '\n\n'.join(truncated_parts)
        
        return result
    
    async def _get_existing_vector_by_hash(self, processed_content_hash: str) -> Optional[List[float]]:
        """
        从 OpenSearch 中查询已存在的相同预处理内容哈希的文件向量
        
        Args:
            processed_content_hash: 预处理后的内容哈希（用于向量复用）
            
        Returns:
            向量列表，如果未找到则返回 None
            
        注意：
            - 查询只按 processed_content_hash，不涉及文件路径
            - 不同目录但预处理后内容相同的文件可以复用向量
        """
        try:
            # 查询 OpenSearch 中是否有相同预处理内容哈希的文件
            # 注意：使用 processed_content_hash 而不是 content_hash，确保相同预处理结果复用相同向量
            # 查询不涉及文件路径，所以不同目录但预处理后内容相同的文件可以复用
            query = {
                "size": 1,
                "query": {
                    "term": {
                        "processed_content_hash": processed_content_hash
                    }
                },
                "_source": ["content_vector", "file_id", "file_path", "processed_content_hash"]
            }
            
            # 使用 OpenSearchService 的异步 search 方法
            response = await self.opensearch.search(
                index=CODE_FILES_INDEX,
                query=query
            )
            
            hits = response.get("hits", {}).get("hits", [])
            if hits and len(hits) > 0:
                hit = hits[0]
                vector = hit.get("_source", {}).get("content_vector")
                if vector and isinstance(vector, list) and len(vector) > 0:
                    return vector
            
            return None
            
        except Exception as e:
            logger.error(f"[查询已存在文件向量] ❌ 查询失败: {e}", exc_info=True)
            return None
    
    async def _get_existing_symbol_vector_by_hash(self, content_hash: str) -> Optional[List[float]]:
        """
        从 OpenSearch 中查询已存在的相同 content_hash 的符号向量
        
        Args:
            content_hash: 符号内容哈希
            
        Returns:
            向量列表，如果未找到则返回 None
        """
        try:
            # 查询 OpenSearch 中是否有相同 content_hash 的符号
            query = {
                "size": 1,
                "query": {
                    "term": {
                        "content_hash": content_hash
                    }
                },
                "_source": ["content_vector", "symbol_id", "qualified_name"]
            }
            
            # 使用 OpenSearchService 的异步 search 方法
            response = await self.opensearch.search(
                index=CODE_SYMBOLS_INDEX,
                query=query
            )
            
            hits = response.get("hits", {}).get("hits", [])
            if hits and len(hits) > 0:
                hit = hits[0]
                vector = hit.get("_source", {}).get("content_vector")
                if vector and isinstance(vector, list) and len(vector) > 0:
                    return vector
            
            return None
            
        except Exception as e:
            logger.error(f"[查询已存在符号向量] ❌ 查询失败: {e}", exc_info=True)
            return None
    
    async def _generate_embedding_with_retry(
        self,
        text: str,
        content_hash: Optional[str] = None
    ) -> List[float]:
        """
        生成向量（带缓存和重试机制）
        
        Args:
            text: 要向量化的文本
            content_hash: 内容哈希（用于缓存）
            
        Returns:
            向量列表
        """
        # 1. 检查缓存
        if self.cache_enabled and content_hash:
            cache_key = f"hash_{content_hash}"
            if cache_key in self.vector_cache:
                return self.vector_cache[cache_key]
        
        # 2. 生成向量（带重试）
        retry_times = settings.CODE_VECTORIZATION_RETRY_TIMES
        retry_delay = settings.CODE_VECTORIZATION_RETRY_DELAY
        timeout = settings.CODE_VECTORIZATION_TIMEOUT
        
        last_error = None
        for attempt in range(retry_times):
            try:
                # 使用线程池执行同步的向量生成
                vector = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.vector_service.generate_embedding,
                        text
                    ),
                    timeout=timeout
                )
                
                if vector and isinstance(vector, list) and len(vector) > 0:
                    # 3. 缓存向量
                    if self.cache_enabled and content_hash and vector:
                        cache_key = f"hash_{content_hash}"
                        # 限制缓存大小（最多5000个，避免内存占用过大）
                        max_cache_size = 5000
                        if len(self.vector_cache) >= max_cache_size:
                            # 如果缓存满了，清除最旧的（简单策略：清除前500个）
                            keys_to_remove = list(self.vector_cache.keys())[:500]
                            for key in keys_to_remove:
                                del self.vector_cache[key]
                        self.vector_cache[cache_key] = vector
                    
                    return vector
                else:
                    last_error = "向量生成返回空向量"
                    if attempt < retry_times - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))  # 指数退避
                
            except asyncio.TimeoutError as e:
                last_error = f"向量化超时（{timeout}秒）"
                if attempt < retry_times - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))  # 指数退避
            except Exception as e:
                last_error = str(e)
                if attempt < retry_times - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))  # 指数退避
        
        # 所有重试都失败
        logger.error(f"[生成向量] ❌ 失败，已重试 {retry_times} 次: {last_error}")
        raise Exception(f"向量化失败: {last_error}")
    
    def _extract_code_summary(self, content: str, language: Optional[str] = None) -> str:
        """
        提取代码摘要（用于索引显示）
        
        策略：
        1. 优先提取文档字符串
        2. 其次提取文件开头的注释
        3. 最后提取前几行代码
        """
        if not content:
            return ""
        
        lines = content.split('\n')
        summary_parts = []
        
        # 1. 提取文档字符串（前 3 个）
        docstring_count = 0
        in_docstring = False
        current_docstring = []
        
        for line in lines[:100]:  # 只检查前 100 行
            stripped = line.strip()
            
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if in_docstring:
                    # 结束文档字符串
                    if current_docstring:
                        summary_parts.append('\n'.join(current_docstring))
                        docstring_count += 1
                        if docstring_count >= 3:
                            break
                    current_docstring = []
                in_docstring = not in_docstring
                continue
            
            if in_docstring:
                current_docstring.append(line)
        
        # 2. 提取文件开头的注释
        if len(summary_parts) < 2:
            comment_lines = []
            for line in lines[:30]:
                stripped = line.strip()
                if stripped.startswith('#') or stripped.startswith('//'):
                    comment_lines.append(line)
                    if len(comment_lines) >= 10:
                        break
            if comment_lines:
                summary_parts.append('\n'.join(comment_lines))
        
        # 3. 如果还没有摘要，使用前 10 行代码
        if not summary_parts:
            summary_parts.append('\n'.join(lines[:10]))
        
        result = '\n\n'.join(summary_parts)
        
        # 限制长度
        if len(result) > 500:
            result = result[:500] + "..."
        
        return result


# ============================================
# 便捷函数
# ============================================

def get_code_vectorization_service(db: Session) -> CodeVectorizationService:
    """获取代码向量化服务实例"""
    return CodeVectorizationService(db)
