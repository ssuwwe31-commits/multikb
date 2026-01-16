"""
代码问答服务
基于 RAG 的代码理解和问答
"""

import os
import hashlib
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.core.logging import logger
from app.services.code_parser_service import CodeParserService
from app.services.question_classifier import get_question_classifier
from app.services.rerank_service import RerankService
from app.config.settings import settings
from sqlalchemy.orm import Session


class CodeQAService:
    """代码问答服务（类似 DeepWiki 对话）"""
    
    # 代码理解 System Prompt
    CODE_QA_SYSTEM_PROMPT = """你是一个专业的代码分析助手，擅长理解和解释代码。

你的能力包括：
1. 理解代码的功能和设计意图
2. 分析代码的架构和模块划分
3. 识别代码中的设计模式和最佳实践
4. 发现潜在的问题和改进建议

在回答问题时，请：
- 基于提供的代码上下文给出准确的答案
- 引用具体的代码片段和行号
- 如果不确定，请明确说明
- 保持回答简洁专业
"""
    
    def __init__(self, db: Optional[Session] = None):
        """初始化问答服务"""
        self.db = db
        self.parser_service = CodeParserService()
        # 初始化问题分类器（如果启用）
        self.question_classifier = None
        if settings.QUESTION_CLASSIFIER_ENABLED:
            try:
                self.question_classifier = get_question_classifier()
                logger.info("代码问答服务初始化完成，已启用问题分类器")
            except Exception as e:
                logger.warning(f"问题分类器初始化失败: {e}")
        else:
            logger.info("代码问答服务初始化完成，问题分类器未启用")
        
        # 初始化 Rerank 服务（用于搜索结果精排）
        self.rerank_service = RerankService()
        logger.info("代码问答服务初始化完成，已启用 Rerank 服务")
    
    async def answer_question(
        self, 
        repo_path: str,
        question: str,
        context_files: Optional[List[str]] = None,
        max_context_files: int = 5,
        use_vector_search: bool = True,
        use_rerank: bool = True
    ) -> Dict:
        """
        回答关于代码的问题（支持向量搜索和 Rerank 精排）
        
        Args:
            repo_path: 仓库路径
            question: 用户问题
            context_files: 指定的上下文文件列表（相对路径）
            max_context_files: 最大上下文文件数
            use_vector_search: 是否使用向量搜索（默认 True）
            use_rerank: 是否使用 Rerank 精排（默认 True）
            
        Returns:
            回答结果，包含：
            - answer: 答案文本
            - sources: 引用的源文件
            - confidence: 置信度（可选）
        """
        logger.info(f"收到问题: {question}")
        
        # 1. 问题分类（如果启用）
        question_type = None
        classification_result = None
        if self.question_classifier:
            try:
                classification_result = self.question_classifier.classify(question)
                question_type = classification_result.get('category', 'general')
                logger.info(f"问题分类结果: {question_type} (方法: {classification_result.get('method')}, 置信度: {classification_result.get('confidence', 0)})")
            except Exception as e:
                logger.warning(f"问题分类失败: {e}")
                question_type = 'general'
        else:
            question_type = 'general'
        
        # 2. 选择相关文件（优先使用混合搜索：向量 + 关键词 + Rerank）
        if context_files is None:
            if use_vector_search and self.db:
                # 使用混合搜索（向量 + 关键词 BM25）+ Rerank（更精准）
                context_files = self._select_relevant_files_with_vector_search(
                    repo_path, question, max_context_files, use_rerank
                )
            else:
                # 降级到简单文件选择策略
                context_files = self._select_relevant_files(repo_path, question, max_context_files)
        
        logger.info(f"选择了 {len(context_files)} 个上下文文件")
        
        # 3. 读取并解析上下文文件
        context_data = []
        for file_path in context_files:
            full_path = os.path.join(repo_path, file_path)
            
            if not os.path.exists(full_path):
                logger.warning(f"文件不存在: {full_path}")
                continue
            
            try:
                # 读取文件内容
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 解析代码结构
                language = self.parser_service.detect_language(full_path)
                analysis = None
                if language:
                    analysis = self.parser_service.parse_file(full_path, language)
                
                context_data.append({
                    'path': file_path,
                    'content': content[:3000],  # 限制长度，避免 token 过多
                    'symbols': analysis.get('symbols', []) if analysis else [],
                    'language': language
                })
            
            except Exception as e:
                logger.error(f"读取文件失败 {full_path}: {e}")
                continue
        
        # 4. 如果是调用链问题，查询调用关系（从 NebulaGraph）
        call_chain_info = None
        if question_type == "call_chain" and self.db:
            call_chain_info = await self._get_call_chain_info(repo_path, question)
        
        # 5. 构建 Prompt（根据问题类型优化，包含调用链信息）
        prompt = self._build_qa_prompt(question, context_data, question_type, call_chain_info)
        
        # 6. 调用 LLM
        try:
            import requests
            from app.config.settings import settings
            
            # 构建完整的 prompt（包含系统提示）
            full_prompt = f"{self.CODE_QA_SYSTEM_PROMPT}\n\n{prompt}"
            
            # 直接调用 Ollama API
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.CODE_LLM_MODEL,
                    "prompt": full_prompt,
                    "stream": False
                },
                timeout=120  # 2分钟超时
            )
            response.raise_for_status()
            result = response.json()
            answer = result.get("response", "").strip()
            
            if not answer:
                answer = "抱歉，无法生成答案，请重新提问。"
            
            logger.info(f"LLM 生成答案成功，长度: {len(answer)} 字符")
            
            result = {
                'answer': answer,
                'sources': context_files,
                'question': question
            }
            
            # 添加问题分类信息
            if classification_result:
                result['question_type'] = question_type
                result['classification'] = {
                    'category': classification_result.get('category'),
                    'method': classification_result.get('method'),
                    'confidence': classification_result.get('confidence', 0)
                }
            
            # 如果是调用链问题，添加调用链信息
            if question_type == "call_chain" and call_chain_info:
                result['call_chain'] = {
                    'nodes': call_chain_info.get('nodes', []),
                    'edges': call_chain_info.get('edges', []),
                    'mermaid_diagram': call_chain_info.get('mermaid_diagram', '')
                }
            
            # 提取代码片段（从答案中提取代码引用）
            code_snippets = self._extract_code_snippets_from_answer(answer, context_data)
            if code_snippets:
                result['code_snippets'] = code_snippets
            
            return result
        
        except Exception as e:
            logger.error(f"生成答案失败: {e}")
            result = {
                'answer': f"抱歉，回答问题时出错：{str(e)}",
                'sources': [],
                'question': question
            }
            
            return result
    
    def _select_relevant_files(
        self, 
        repo_path: str, 
        question: str, 
        max_files: int = 5
    ) -> List[str]:
        """
        智能选择与问题相关的文件
        
        Args:
            repo_path: 仓库路径
            question: 用户问题
            max_files: 最大文件数
            
        Returns:
            相关文件列表（相对路径）
        """
        relevant_files = []
        
        # 策略1：优先选择 README
        for root, dirs, files in os.walk(repo_path):
            # 排除 .git 等目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if 'README' in file.upper():
                    relative_path = os.path.relpath(os.path.join(root, file), repo_path)
                    relevant_files.append(relative_path)
                    if len(relevant_files) >= max_files:
                        return relevant_files
        
        # 策略2：查找主入口文件
        main_patterns = ['main.py', 'app.py', '__init__.py', 'index.js', 'index.ts', 'server.js', 'app.js']
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__']]
            
            for file in files:
                if file in main_patterns:
                    relative_path = os.path.relpath(os.path.join(root, file), repo_path)
                    if relative_path not in relevant_files:
                        relevant_files.append(relative_path)
                        if len(relevant_files) >= max_files:
                            return relevant_files
        
        # 策略3：关键词匹配（简化版）
        question_lower = question.lower()
        keywords = self._extract_keywords(question_lower)
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__']]
            
            for file in files:
                # 检查文件名是否包含关键词
                file_lower = file.lower()
                if any(keyword in file_lower for keyword in keywords):
                    if self.parser_service.is_code_file(file):
                        relative_path = os.path.relpath(os.path.join(root, file), repo_path)
                        if relative_path not in relevant_files:
                            relevant_files.append(relative_path)
                            if len(relevant_files) >= max_files:
                                return relevant_files
        
        # 如果还没有足够的文件，随机选择一些代码文件
        if len(relevant_files) < max_files:
            for root, dirs, files in os.walk(repo_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__']]
                
                for file in files:
                    if self.parser_service.is_code_file(file):
                        relative_path = os.path.relpath(os.path.join(root, file), repo_path)
                        if relative_path not in relevant_files:
                            relevant_files.append(relative_path)
                            if len(relevant_files) >= max_files:
                                return relevant_files
        
        return relevant_files[:max_files]
    
    def _select_relevant_files_with_vector_search(
        self,
        repo_path: str,
        question: str,
        max_files: int = 5,
        use_rerank: bool = True
    ) -> List[str]:
        """
        使用混合搜索（向量 + 关键词 BM25）+ Rerank 选择相关文件（更精准）
        
        策略：
        1. 向量搜索（语义相似）
        2. 关键词搜索（BM25，精确匹配）
        3. 混合排序（结合两种结果）
        4. Rerank 精排（提升准确性）
        
        Args:
            repo_path: 仓库路径
            question: 用户问题
            max_files: 最大文件数
            use_rerank: 是否使用 Rerank 精排
            
        Returns:
            相关文件列表（相对路径）
        """
        try:
            # 获取仓库ID
            repository_id = self._get_repository_id_from_path(repo_path)
            if not repository_id:
                logger.warning(f"无法获取仓库ID，降级到简单文件选择: {repo_path}")
                return self._select_relevant_files(repo_path, question, max_files)
            
            # 使用向量搜索
            from app.services.opensearch_service import OpenSearchService
            from app.services.vector_service import VectorService
            from opensearch_schemas.code_indices import CODE_FILES_INDEX, CODE_SYMBOLS_INDEX
            
            opensearch = OpenSearchService()
            vector_service = VectorService(self.db)
            
            # 生成查询向量
            query_vector = vector_service.generate_embedding(question)
            if not query_vector:
                logger.warning("生成查询向量失败，降级到简单文件选择")
                return self._select_relevant_files(repo_path, question, max_files)
            
            # 使用混合搜索（向量 + 关键词 BM25），召回更多候选，供 rerank
            recall_limit = max_files * 3  # 召回3倍，供 rerank 精排
            
            results = []
            
            # 混合搜索代码文件（向量 + 关键词）
            file_results = opensearch.client.search(
                index=CODE_FILES_INDEX,
                body={
                    "size": recall_limit,
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"repository_id": repository_id}}
                            ],
                            "should": [
                                {
                                    "knn": {
                                        "content_vector": {
                                            "vector": query_vector,
                                            "k": recall_limit
                                        }
                                    }
                                },
                                {
                                    "multi_match": {
                                        "query": question,
                                        "fields": ["file_path^2", "file_name^3", "content_summary", "content"],
                                        "type": "best_fields"
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    },
                    "_source": ["file_path", "file_name", "content_summary", "content"]
                }
            )
            
            for hit in file_results['hits']['hits']:
                source = hit['_source']
                results.append({
                    'type': 'file',
                    'file_path': source.get('file_path'),
                    'file_name': source.get('file_name'),
                    'content': source.get('content_summary', '')[:500],  # 用于 rerank
                    'score': hit['_score']
                })
            
            # 混合搜索代码符号（向量 + 关键词）
            symbol_results = opensearch.client.search(
                index=CODE_SYMBOLS_INDEX,
                body={
                    "size": recall_limit,
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"repository_id": repository_id}}
                            ],
                            "should": [
                                {
                                    "knn": {
                                        "content_vector": {
                                            "vector": query_vector,
                                            "k": recall_limit
                                        }
                                    }
                                },
                                {
                                    "multi_match": {
                                        "query": question,
                                        "fields": ["symbol_name^3", "qualified_name^2", "signature^2", "docstring"],
                                        "type": "best_fields"
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    },
                    "_source": ["file_path", "symbol_name", "qualified_name", "signature", "docstring"]
                }
            )
            
            for hit in symbol_results['hits']['hits']:
                source = hit['_source']
                # 构建用于 rerank 的内容
                content_parts = []
                if source.get('qualified_name'):
                    content_parts.append(f"符号: {source['qualified_name']}")
                if source.get('signature'):
                    content_parts.append(f"签名: {source['signature']}")
                if source.get('docstring'):
                    content_parts.append(f"说明: {source['docstring'][:300]}")
                
                results.append({
                    'type': 'symbol',
                    'file_path': source.get('file_path'),
                    'symbol_name': source.get('symbol_name'),
                    'content': '\n'.join(content_parts),
                    'score': hit['_score']
                })
            
            # 使用 Rerank 精排
            if use_rerank and self.rerank_service.is_available() and len(results) > 1:
                try:
                    rerank_candidates = [
                        {
                            'content': r.get('content', ''),
                            'score': r.get('score', 0.0),
                            **r
                        }
                        for r in results
                    ]
                    
                    reranked_results = self.rerank_service.rerank(
                        query=question,
                        candidates=rerank_candidates,
                        top_k=max_files * 2  # 多取一些，后续去重
                    )
                    
                    logger.info(f"代码问答 Rerank 完成: 输入={len(rerank_candidates)}, 输出={len(reranked_results)}")
                    results = reranked_results
                except Exception as e:
                    logger.warning(f"Rerank 排序失败，使用原始排序: {e}")
                    # 降级：按原始分数排序
                    results.sort(key=lambda x: x.get('score', 0), reverse=True)
            else:
                # 没有 rerank，按原始分数排序
                results.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            # 提取文件路径（去重）
            file_paths = []
            seen_paths = set()
            for result in results[:max_files * 2]:  # 多取一些，用于去重
                file_path = result.get('file_path')
                if file_path and file_path not in seen_paths:
                    file_paths.append(file_path)
                    seen_paths.add(file_path)
                    if len(file_paths) >= max_files:
                        break
            
            logger.info(f"向量搜索 + Rerank 选择了 {len(file_paths)} 个相关文件")
            return file_paths[:max_files]
            
        except Exception as e:
            logger.error(f"向量搜索失败，降级到简单文件选择: {e}")
            return self._select_relevant_files(repo_path, question, max_files)
    
    def _get_repository_id_from_path(self, repo_path: str) -> Optional[int]:
        """从路径获取仓库ID"""
        if not self.db:
            return None
        
        try:
            # 从路径中提取仓库ID（路径格式：.../code_repositories/{id}/...）
            import re
            match = re.search(r'code_repositories[\\/](\d+)', repo_path)
            if match:
                return int(match.group(1))
            
            # 或者查询数据库
            from app.models.code_repository import CodeRepository
            repo = self.db.query(CodeRepository).filter(
                CodeRepository.local_path == repo_path
            ).first()
            
            return repo.id if repo else None
            
        except Exception as e:
            logger.warning(f"获取仓库ID失败: {e}")
            return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        从问题中提取关键词
        
        Args:
            text: 问题文本
            
        Returns:
            关键词列表
        """
        # 简化版：移除停用词后的单词
        stopwords = {
            '是', '的', '在', '了', '和', '有', '这', '个', '我', '你', '他',
            'is', 'the', 'in', 'of', 'and', 'a', 'to', 'how', 'what', 'where',
            '什么', '如何', '怎么', '哪里', '为什么'
        }
        
        # 简单分词（英文按空格，中文暂不处理）
        words = text.split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        return keywords[:5]  # 最多5个关键词
    
    async def _get_call_chain_info(
        self,
        repo_path: str,
        question: str
    ) -> Optional[Dict[str, Any]]:
        """
        从 NebulaGraph 查询调用链信息
        
        Args:
            repo_path: 仓库路径
            question: 用户问题
            
        Returns:
            调用链信息（如果可用）
        """
        try:
            if not settings.USE_NEBULA_GRAPH:
                return None
            
            # 从问题中提取函数/方法名
            # 简单策略：查找引号或反引号中的名称
            import re
            function_patterns = [
                r'["\']([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',  # "function_name("
                r'`([a-zA-Z_][a-zA-Z0-9_]*)`',  # `function_name`
                r'函数\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # 函数 function_name
                r'方法\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # 方法 method_name
            ]
            
            function_names = []
            for pattern in function_patterns:
                matches = re.findall(pattern, question)
                function_names.extend(matches)
            
            if not function_names:
                return None
            
            # 通过 MySQL 查询调用链（更可靠，因为依赖关系已存储在 MySQL）
            
            # 获取仓库ID
            repository_id = self._get_repository_id_from_path(repo_path)
            if not repository_id:
                return None
            
            # 查找函数/方法符号节点
            call_chain_nodes = []
            call_chain_edges = []
            
            for func_name in function_names[:3]:  # 最多查询3个函数
                # 1. 搜索符号节点（通过符号名）
                try:
                    # 查询符号节点（通过 MySQL）
                    symbols = self.db.query(CodeSymbol).filter(
                        CodeSymbol.repository_id == repository_id,
                        (CodeSymbol.symbol_name == func_name) | 
                        (CodeSymbol.qualified_name.contains(func_name))
                    ).limit(5).all()
                    
                    if not symbols:
                        continue
                    
                    for symbol in symbols:
                        # 构建 VID（格式：code_symbol_{id}）
                        vid = f"code_symbol_{symbol.id}"
                        
                        # 获取文件路径
                        file_path = ''
                        if symbol.file_id:
                            code_file = self.db.query(CodeFile).filter(CodeFile.id == symbol.file_id).first()
                            if code_file:
                                file_path = code_file.file_path
                        
                        # 构建符号节点
                        symbol_node = {
                            'vid': vid,
                            'symbol_name': symbol.symbol_name,
                            'qualified_name': symbol.qualified_name or symbol.symbol_name,
                            'file_path': file_path,
                            'start_line': symbol.start_line or 0,
                            'end_line': symbol.end_line or 0
                        }
                        call_chain_nodes.append(symbol_node)
                        
                        # 2. 查询调用关系（谁调用了这个函数）
                        # 查询谁调用了这个符号（入边）
                        incoming_calls = self.db.query(CodeDependency).filter(
                            CodeDependency.target_symbol_id == symbol.id,
                            CodeDependency.dependency_type == 'call'
                        ).limit(20).all()
                        
                        for dep in incoming_calls:
                            if dep.source_symbol_id:
                                # 获取调用者符号
                                caller_symbol = self.db.query(CodeSymbol).filter(
                                    CodeSymbol.id == dep.source_symbol_id
                                ).first()
                                
                                if caller_symbol:
                                    caller_vid = f"code_symbol_{caller_symbol.id}"
                                    
                                    # 获取调用者文件路径
                                    caller_file_path = ''
                                    if caller_symbol.file_id:
                                        caller_file = self.db.query(CodeFile).filter(
                                            CodeFile.id == caller_symbol.file_id
                                        ).first()
                                        if caller_file:
                                            caller_file_path = caller_file.file_path
                                    
                                    # 添加调用者节点
                                    caller_node = {
                                        'vid': caller_vid,
                                        'symbol_name': caller_symbol.symbol_name,
                                        'qualified_name': caller_symbol.qualified_name or caller_symbol.symbol_name,
                                        'file_path': caller_file_path,
                                        'start_line': caller_symbol.start_line or 0,
                                        'end_line': caller_symbol.end_line or 0
                                    }
                                    
                                    # 检查是否已存在
                                    if not any(n['vid'] == caller_vid for n in call_chain_nodes):
                                        call_chain_nodes.append(caller_node)
                                    
                                    # 添加调用边
                                    call_edge = {
                                        'from': caller_vid,
                                        'to': vid,
                                        'type': 'calls',
                                        'line_number': dep.line_number or 0
                                    }
                                    call_chain_edges.append(call_edge)
                        
                        # 3. 查询被调用关系（这个函数调用了谁）
                        # 查询这个符号调用了谁（出边）
                        outgoing_calls = self.db.query(CodeDependency).filter(
                            CodeDependency.source_symbol_id == symbol.id,
                            CodeDependency.dependency_type == 'call'
                        ).limit(20).all()
                        
                        for dep in outgoing_calls:
                            if dep.target_symbol_id:
                                # 获取被调用者符号
                                callee_symbol = self.db.query(CodeSymbol).filter(
                                    CodeSymbol.id == dep.target_symbol_id
                                ).first()
                                
                                if callee_symbol:
                                    callee_vid = f"code_symbol_{callee_symbol.id}"
                                    
                                    # 获取被调用者文件路径
                                    callee_file_path = ''
                                    if callee_symbol.file_id:
                                        callee_file = self.db.query(CodeFile).filter(
                                            CodeFile.id == callee_symbol.file_id
                                        ).first()
                                        if callee_file:
                                            callee_file_path = callee_file.file_path
                                    
                                    # 添加被调用者节点
                                    callee_node = {
                                        'vid': callee_vid,
                                        'symbol_name': callee_symbol.symbol_name,
                                        'qualified_name': callee_symbol.qualified_name or callee_symbol.symbol_name,
                                        'file_path': callee_file_path,
                                        'start_line': callee_symbol.start_line or 0,
                                        'end_line': callee_symbol.end_line or 0
                                    }
                                    
                                    # 检查是否已存在
                                    if not any(n['vid'] == callee_vid for n in call_chain_nodes):
                                        call_chain_nodes.append(callee_node)
                                    
                                    # 添加调用边
                                    call_edge = {
                                        'from': vid,
                                        'to': callee_vid,
                                        'type': 'calls',
                                        'line_number': dep.line_number or 0
                                    }
                                    call_chain_edges.append(call_edge)
                
                except Exception as e:
                    logger.warning(f"查询函数 {func_name} 的调用链失败: {e}")
                    continue
            
            if not call_chain_nodes:
                logger.debug(f"未找到函数 {function_names} 的调用链信息")
                return None
            
            # 生成 Mermaid 调用链图
            mermaid_diagram = self._generate_call_chain_mermaid(call_chain_nodes, call_chain_edges)
            
            return {
                'nodes': call_chain_nodes,
                'edges': call_chain_edges,
                'mermaid_diagram': mermaid_diagram,
                'function_names': function_names
            }
            
        except Exception as e:
            logger.warning(f"查询调用链失败: {e}")
            return None
    
    def _generate_call_chain_mermaid(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> str:
        """
        生成 Mermaid 调用链图
        
        Args:
            nodes: 节点列表
            edges: 边列表
            
        Returns:
            Mermaid 图表代码
        """
        try:
            if not nodes:
                return ""
            
            # 构建节点映射（vid -> 显示名称和节点ID）
            node_map = {}
            node_id_map = {}  # vid -> 简化的节点ID（用于 Mermaid）
            
            for idx, node in enumerate(nodes):
                vid = node.get('vid', '')
                display_name = node.get('qualified_name') or node.get('symbol_name', '')
                # 简化显示名称（只保留函数名）
                if '.' in display_name:
                    display_name = display_name.split('.')[-1]
                elif '::' in display_name:
                    display_name = display_name.split('::')[-1]
                
                node_map[vid] = display_name
                # 使用简化的节点ID（避免特殊字符问题）
                node_id = f"N{idx}"
                node_id_map[vid] = node_id
            
            # 生成 Mermaid 代码
            mermaid_lines = ["```mermaid", "graph TD"]
            
            # 添加节点（使用简化的节点ID和显示名称）
            for node in nodes:
                vid = node.get('vid', '')
                node_id = node_id_map.get(vid, vid)
                display_name = node_map.get(vid, vid)
                
                # 转义特殊字符和清理
                display_name = display_name.replace('"', "'").replace('\n', ' ').strip()
                if len(display_name) > 30:
                    display_name = display_name[:27] + "..."
                
                # 添加文件路径信息（如果有）
                file_path = node.get('file_path', '')
                if file_path:
                    file_name = file_path.split('/')[-1] if '/' in file_path else file_path
                    display_name += f"\\n({file_name})"
                
                mermaid_lines.append(f'    {node_id}["{display_name}"]')
            
            # 添加边
            for edge in edges:
                from_vid = edge.get('from', '')
                to_vid = edge.get('to', '')
                line_num = edge.get('line_number', 0)
                
                from_id = node_id_map.get(from_vid)
                to_id = node_id_map.get(to_vid)
                
                if from_id and to_id:
                    label = f"L{line_num}" if line_num > 0 else ""
                    mermaid_lines.append(f'    {from_id} -->|{label}| {to_id}')
            
            mermaid_lines.append("```")
            
            return "\n".join(mermaid_lines)
            
        except Exception as e:
            logger.error(f"生成调用链图失败: {e}", exc_info=True)
            return ""
    
    def _extract_code_snippets_from_answer(
        self,
        answer: str,
        context_data: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        从答案中提取代码片段引用
        
        Args:
            answer: LLM 生成的答案
            context_data: 上下文数据
            
        Returns:
            代码片段列表
        """
        import re
        
        code_snippets = []
        
        # 提取代码引用（格式：文件名:行号-行号 或 文件名:行号）
        pattern = r'([a-zA-Z0-9_/\\\.]+):(\d+)(?:-(\d+))?'
        matches = re.findall(pattern, answer)
        
        # 构建文件路径映射
        file_map = {item['path']: item for item in context_data}
        
        for match in matches:
            file_path = match[0]
            start_line = int(match[1])
            end_line = int(match[2]) if match[2] else start_line
            
            # 查找对应的文件
            for context_item in context_data:
                if file_path in context_item['path'] or context_item['path'].endswith(file_path):
                    content = context_item.get('content', '')
                    language = context_item.get('language', 'text')
                    
                    # 提取代码片段
                    lines = content.split('\n')
                    if start_line <= len(lines):
                        snippet_lines = lines[start_line-1:end_line]
                        code_snippet = '\n'.join(snippet_lines)
                        
                        code_snippets.append({
                            'file_path': context_item['path'],
                            'start_line': start_line,
                            'end_line': end_line,
                            'language': language,
                            'code': code_snippet
                        })
                    break
        
        return code_snippets
    
    def _build_qa_prompt(
        self, 
        question: str, 
        context_data: List[Dict], 
        question_type: str = 'general',
        call_chain_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        构建问答 Prompt
        
        Args:
            question: 用户问题
            context_data: 上下文数据
            
        Returns:
            完整的 Prompt
        """
        prompt = "## 代码上下文\n\n"
        
        # 添加每个文件的信息
        for item in context_data:
            prompt += f"### 文件：`{item['path']}`\n"
            prompt += f"语言：{item['language']}\n\n"
            
            # 添加符号信息
            symbols = item.get('symbols', [])
            if symbols:
                prompt += "主要符号：\n"
                for symbol in symbols[:5]:  # 最多5个
                    prompt += f"- {symbol['type']}: `{symbol['name']}` (line {symbol['line']})\n"
                prompt += "\n"
            
            # 添加代码内容（截断）
            content = item['content']
            if len(content) > 2000:
                content = content[:2000] + "\n... (代码已截断)"
            
            prompt += f"```{item['language']}\n{content}\n```\n\n"
        
        # 添加问题
        prompt += f"## 用户问题\n\n{question}\n\n"
        
        # 根据问题类型添加特定要求
        if question_type == "call_chain":
            prompt += """请详细说明调用链的每个环节，包括：
1. 函数的调用关系
2. 调用顺序和流程
3. 每个环节的作用

"""
            # 如果有调用链信息，添加到 prompt
            if call_chain_info:
                nodes = call_chain_info.get('nodes', [])
                edges = call_chain_info.get('edges', [])
                mermaid_diagram = call_chain_info.get('mermaid_diagram', '')
                
                if nodes:
                    prompt += "调用链节点信息：\n"
                    for node in nodes[:10]:  # 最多10个节点
                        prompt += f"- {node.get('qualified_name', node.get('symbol_name', ''))} "
                        prompt += f"({node.get('file_path', '')}:{node.get('start_line', 0)})\n"
                    prompt += "\n"
                
                if edges:
                    prompt += "调用关系：\n"
                    for edge in edges[:15]:  # 最多15条边
                        prompt += f"- {edge.get('from', '')} -> {edge.get('to', '')} "
                        prompt += f"(行号: {edge.get('line_number', 0)})\n"
                    prompt += "\n"
                
                if mermaid_diagram:
                    prompt += f"调用链图：\n{mermaid_diagram}\n\n"
            
            prompt += """请基于以上调用链信息，详细说明：
1. 函数的调用关系（谁调用了谁）
2. 调用顺序和流程
3. 每个环节的作用

如果需要引用代码，请标注文件名和行号（格式：文件名:行号-行号）。
如果调用链图已提供，请直接使用；如果没有，请生成 Mermaid 格式的调用链图（格式：```mermaid ... ```）。"""
        elif question_type == "architecture":
            prompt += """请详细说明系统架构，包括：
1. 模块划分和职责
2. 模块之间的关系
3. 数据流向

如果需要引用代码，请标注文件名和行号（格式：文件名:行号-行号）。"""
        elif question_type == "diagram":
            prompt += """请生成 Mermaid 格式的图表（格式：```mermaid ... ```），包括：
1. 清晰的图表结构
2. 准确的节点和关系

如果需要引用代码，请标注文件名和行号（格式：文件名:行号-行号）。"""
        elif question_type == "understanding":
            prompt += """请详细解释代码的功能和逻辑，包括：
1. 代码的作用
2. 关键逻辑说明
3. 参数和返回值说明

如果需要引用代码，请标注文件名和行号（格式：文件名:行号-行号）。"""
        elif question_type == "best_practice":
            prompt += """请分析代码质量和最佳实践，包括：
1. 潜在问题
2. 改进建议
3. 最佳实践建议

如果需要引用代码，请标注文件名和行号（格式：文件名:行号-行号）。"""
        else:
            prompt += "请基于以上代码上下文回答问题。如果需要引用代码，请标注文件名和行号（格式：文件名:行号-行号）。"
        
        return prompt
    
    def generate_code_documentation(
        self, 
        repo_path: str, 
        file_path: str
    ) -> Dict:
        """
        生成单个文件的详细文档
        
        Args:
            repo_path: 仓库路径
            file_path: 文件相对路径
            
        Returns:
            文档内容
        """
        full_path = os.path.join(repo_path, file_path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 解析文件
        language = self.parser_service.detect_language(full_path)
        if not language:
            raise ValueError(f"不支持的文件类型: {file_path}")
        
        analysis = self.parser_service.parse_file(full_path, language)
        if not analysis:
            raise ValueError(f"解析文件失败: {file_path}")
        
        # 读取文件内容
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 构建文档生成 Prompt
        prompt = f"""请为以下代码文件生成详细的技术文档：

文件：{file_path}
语言：{language}

代码内容：
```{language}
{content[:5000]}
```

请按以下格式生成文档：
1. 文件概述（这个文件的主要作用）
2. 主要功能（列出主要的函数/类及其作用）
3. 依赖关系（这个文件依赖哪些模块）
4. 使用示例（如何使用这个文件中的功能）

要求：
- 专业简洁
- 重点突出
- 包含代码示例
"""
        
        try:
            import requests
            from app.config.settings import settings
            
            # 构建完整的 prompt
            full_prompt = f"你是一个专业的技术文档撰写专家。\n\n{prompt}"
            
            # 直接调用 Ollama API
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.CODE_LLM_MODEL,
                    "prompt": full_prompt,
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            documentation = result.get("response", "").strip()
            
            if not documentation:
                documentation = "文档生成失败"
            
            logger.info(f"LLM 生成文档成功")
            
            return {
                'file_path': file_path,
                'language': language,
                'documentation': documentation,
                'symbols': analysis['symbols'],
                'imports': analysis['imports'],
                'lines': analysis['lines'],
                'complexity': analysis['complexity']
            }
        
        except Exception as e:
            logger.error(f"生成文档失败: {e}")
            return {
                'file_path': file_path,
                'language': language,
                'documentation': f"自动生成文档失败：{str(e)}",
                'symbols': analysis['symbols'],
                'imports': analysis['imports'],
                'lines': analysis['lines'],
                'complexity': analysis['complexity']
            }
