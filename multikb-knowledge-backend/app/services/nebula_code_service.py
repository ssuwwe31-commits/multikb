"""
NebulaGraph Code Service
代码实体同步服务 - 将代码数据同步到知识图谱
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime
import hashlib

from app.core.logging import logger
from app.config.settings import settings
from app.services.graph_storage_service import get_graph_storage


class NebulaCodeService:
    """代码库到 NebulaGraph 的同步服务"""
    
    # 类级别的标志，用于跟踪 schema 是否已创建
    _schema_initialized = False
    
    def __init__(self, db: Session):
        self.db = db
        self.graph = get_graph_storage()
        self.space = "multikb_knowledge"  # 使用现有的图谱空间
    
    async def sync_repository(self, repository_id: int) -> Dict[str, Any]:
        """
        同步代码仓库到图谱
        
        Args:
            repository_id: 仓库ID
            
        Returns:
            同步结果统计
        """
        try:
            from app.models.code_repository import CodeRepository
            
            # 1. 查询仓库信息
            repo = self.db.query(CodeRepository).filter(
                CodeRepository.id == repository_id
            ).first()
            
            if not repo:
                raise ValueError(f"Repository {repository_id} not found")
            
            logger.info(f"开始同步代码仓库到图谱: {repo.repo_name}")
            
            # 2. 创建仓库节点
            repo_vid = await self._create_repository_node(repo)
            
            # 3. 如果关联了知识库，创建关联关系
            if repo.knowledge_base_id:
                await self._link_repository_to_kb(repo_vid, repo.knowledge_base_id)
            
            stats = {
                "repository_id": repository_id,
                "repository_vid": repo_vid,
                "status": "success",
                "synced_at": datetime.now().isoformat()
            }
            
            logger.info(f"代码仓库同步完成: {repo.repo_name}")
            return stats
            
        except Exception as e:
            logger.error(f"同步代码仓库失败: {e}")
            raise
    
    async def sync_code_file(self, file_id: int) -> Dict[str, Any]:
        """
        同步代码文件到图谱
        
        Args:
            file_id: 文件ID
            
        Returns:
            同步结果
        """
        try:
            from app.models.code_file import CodeFile
            
            # 1. 查询文件信息
            file = self.db.query(CodeFile).filter(
                CodeFile.id == file_id
            ).first()
            
            if not file:
                raise ValueError(f"Code file {file_id} not found")
            
            logger.info(f"开始同步代码文件到图谱: {file.file_path}")
            
            # 2. 创建文件节点
            file_vid = await self._create_file_node(file)
            
            # 3. 创建文件与仓库的包含关系
            repo_vid = f"code_repository_{file.repository_id}"
            await self._create_contains_edge(repo_vid, file_vid, "repository")
            
            # 4. 如果关联了知识库，创建关联关系
            if file.knowledge_base_id:
                kb_vid = f"knowledge_base_{file.knowledge_base_id}"
                await self._create_references_edge(kb_vid, file_vid, "contains")
            
            return {
                "file_id": file_id,
                "file_vid": file_vid,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"同步代码文件失败: {e}")
            raise
    
    async def sync_code_symbol(self, symbol_id: int) -> Dict[str, Any]:
        """
        同步代码符号到图谱
        
        Args:
            symbol_id: 符号ID
            
        Returns:
            同步结果
        """
        try:
            from app.models.code_symbol import CodeSymbol
            
            # 1. 查询符号信息
            symbol = self.db.query(CodeSymbol).filter(
                CodeSymbol.id == symbol_id
            ).first()
            
            if not symbol:
                raise ValueError(f"Code symbol {symbol_id} not found")
            
            logger.info(f"开始同步代码符号到图谱: {symbol.qualified_name}")
            
            # 2. 创建符号节点
            symbol_vid = await self._create_symbol_node(symbol)
            
            # 3. 创建符号与文件的包含关系
            file_vid = f"code_file_{symbol.file_id}"
            await self._create_contains_edge(
                file_vid, 
                symbol_vid, 
                "file",
                start_line=symbol.start_line,
                end_line=symbol.end_line
            )
            
            # 4. 如果有父符号，创建包含关系
            if symbol.parent_symbol_id:
                parent_vid = f"code_symbol_{symbol.parent_symbol_id}"
                await self._create_contains_edge(
                    parent_vid,
                    symbol_vid,
                    "symbol",
                    start_line=symbol.start_line,
                    end_line=symbol.end_line
                )
            
            return {
                "symbol_id": symbol_id,
                "symbol_vid": symbol_vid,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"同步代码符号失败: {e}")
            raise
    
    async def sync_dependency(self, dependency_id: int) -> Dict[str, Any]:
        """
        同步代码依赖关系到图谱
        
        Args:
            dependency_id: 依赖ID
            
        Returns:
            同步结果
        """
        try:
            from app.models.code_dependency import CodeDependency
            
            # 1. 查询依赖信息
            dep = self.db.query(CodeDependency).filter(
                CodeDependency.id == dependency_id
            ).first()
            
            if not dep:
                raise ValueError(f"Dependency {dependency_id} not found")
            
            logger.info(f"开始同步代码依赖关系到图谱: {dep.dependency_type}")
            
            # 2. 确定源和目标 VID
            if dep.source_symbol_id:
                source_vid = f"code_symbol_{dep.source_symbol_id}"
            else:
                source_vid = f"code_file_{dep.source_file_id}"
            
            if dep.target_symbol_id:
                target_vid = f"code_symbol_{dep.target_symbol_id}"
            else:
                target_vid = f"code_file_{dep.target_file_id}"
            
            # 3. 根据依赖类型创建不同的边
            if dep.dependency_type == "import":
                await self._create_imports_edge(
                    source_vid, 
                    target_vid,
                    import_statement=dep.import_statement,
                    line_number=dep.line_number
                )
            elif dep.dependency_type == "call":
                await self._create_calls_edge(
                    source_vid,
                    target_vid,
                    line_number=dep.line_number
                )
            elif dep.dependency_type == "inherit":
                await self._create_inherits_edge(
                    source_vid,
                    target_vid
                )
            elif dep.dependency_type == "implement":
                await self._create_implements_edge(
                    source_vid,
                    target_vid
                )
            else:
                # 通用依赖关系
                await self._create_depends_on_edge(
                    source_vid,
                    target_vid,
                    dependency_type=dep.dependency_type
                )
            
            return {
                "dependency_id": dependency_id,
                "source_vid": source_vid,
                "target_vid": target_vid,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"同步代码依赖关系失败: {e}")
            raise
    
    async def link_code_to_document(
        self, 
        code_file_id: Optional[int] = None,
        code_symbol_id: Optional[int] = None,
        document_id: Optional[int] = None,
        mapping_type: str = "reference",
        context: str = "",
        confidence: float = 1.0
    ) -> Dict[str, Any]:
        """
        创建代码与文档的关联关系
        
        Args:
            code_file_id: 代码文件ID
            code_symbol_id: 代码符号ID
            document_id: 文档ID
            mapping_type: 映射类型
            context: 映射上下文
            confidence: 置信度
            
        Returns:
            创建结果
        """
        try:
            # 确定代码节点 VID
            if code_symbol_id:
                code_vid = f"code_symbol_{code_symbol_id}"
            elif code_file_id:
                code_vid = f"code_file_{code_file_id}"
            else:
                raise ValueError("Must provide either code_file_id or code_symbol_id")
            
            # 文档节点 VID
            doc_vid = f"document_{document_id}"
            
            # 创建引用关系
            await self._create_references_edge(
                doc_vid,
                code_vid,
                reference_type=mapping_type,
                context=context,
                confidence=confidence
            )
            
            return {
                "document_vid": doc_vid,
                "code_vid": code_vid,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"创建代码-文档关联失败: {e}")
            raise
    
    # ============================================
    # 私有方法：VID 生成（基于哈希，不依赖 MySQL ID）
    # ============================================
    
    def _generate_file_vid(self, repository_id: int, file_path: str) -> str:
        """
        生成文件节点的 VID（基于仓库ID和文件路径哈希）
        
        Args:
            repository_id: 仓库ID
            file_path: 文件路径
            
        Returns:
            VID 字符串
        """
        # 使用仓库ID和文件路径生成唯一哈希
        vid_key = f"{repository_id}:{file_path}"
        vid_hash = hashlib.md5(vid_key.encode('utf-8')).hexdigest()[:16]  # 取前16位
        return f"code_file_{vid_hash}"
    
    def _generate_symbol_vid(self, repository_id: int, qualified_name: str, file_path: str, start_line: int) -> str:
        """
        生成符号节点的 VID（基于仓库ID、限定名、文件路径和行号哈希）
        
        Args:
            repository_id: 仓库ID
            qualified_name: 符号限定名
            file_path: 文件路径
            start_line: 起始行号
            
        Returns:
            VID 字符串
        """
        # 使用仓库ID、限定名、文件路径和行号生成唯一哈希
        vid_key = f"{repository_id}:{qualified_name}:{file_path}:{start_line}"
        vid_hash = hashlib.md5(vid_key.encode('utf-8')).hexdigest()[:16]  # 取前16位
        return f"code_symbol_{vid_hash}"
    
    # ============================================
    # 私有方法：创建节点
    # ============================================
    
    async def _create_repository_node(self, repo) -> str:
        """创建代码仓库节点（直接使用 nGQL，不使用 create_entity）"""
        # 确保 schema 已创建
        await self._ensure_code_schema()
        
        vid = f"code_repository_{repo.id}"
        
        # 转义字符串中的特殊字符
        def escape_string(s: str) -> str:
            if s is None:
                return ""
            s = str(s)
            # 先转义反斜杠，再转义其他字符
            s = s.replace('\\', '\\\\')
            s = s.replace('"', '\\"')
            # 处理换行符、制表符等，替换为空格
            s = s.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            # 移除可能导致问题的其他控制字符
            s = ''.join(char for char in s if ord(char) >= 32 or char in ['\n', '\r', '\t'])
            return s
        
        # 准备属性值
        repo_name_escaped = escape_string(repo.repo_name)
        repo_url_escaped = escape_string(repo.repo_url)
        description_escaped = escape_string(repo.description or "")
        default_branch_escaped = escape_string(repo.default_branch or "main")
        last_commit_hash_escaped = escape_string(repo.last_commit_hash or "")
        created_at = int(repo.created_at.timestamp()) if repo.created_at else int(datetime.now().timestamp())
        updated_at = int(repo.updated_at.timestamp()) if repo.updated_at else int(datetime.now().timestamp())
        
        # 构建 INSERT VERTEX 语句
        nGQL = (
            f'INSERT VERTEX code_repository('
            f'repo_name, repo_url, description, mysql_id, knowledge_base_id, '
            f'default_branch, last_commit_hash, total_files, total_lines, '
            f'created_at, updated_at'
            f') VALUES "{vid}":('
            f'"{repo_name_escaped}", "{repo_url_escaped}", "{description_escaped}", '
            f'{repo.id}, {repo.knowledge_base_id or 0}, '
            f'"{default_branch_escaped}", "{last_commit_hash_escaped}", '
            f'{repo.total_files or 0}, {repo.total_lines or 0}, '
            f'{created_at}, {updated_at}'
            f');'
        )
        
        try:
            await self.graph._execute(nGQL, space=self.space)
            logger.debug(f"创建代码仓库节点成功: vid={vid}, repo_name={repo.repo_name}")
            return vid
        except Exception as e:
            logger.error(f"创建代码仓库节点失败: {repo.repo_name}, VID={vid}, 错误={e}", exc_info=True)
            raise
    
    async def _create_file_node(self, file) -> str:
        """创建代码文件节点（使用 MySQL ID）"""
        # 确保 schema 已创建
        await self._ensure_code_schema()
        
        vid = f"code_file_{file.id}"
        
        # 转义字符串中的特殊字符
        def escape_string(s: str) -> str:
            if s is None:
                return ""
            s = str(s)
            # 先转义反斜杠，再转义其他字符
            s = s.replace('\\', '\\\\')
            s = s.replace('"', '\\"')
            # 处理换行符、制表符等，替换为空格
            s = s.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            # 移除可能导致问题的其他控制字符
            s = ''.join(char for char in s if ord(char) >= 32 or char in ['\n', '\r', '\t'])
            return s
        
        # 准备属性值
        file_path_escaped = escape_string(file.file_path)
        file_name_escaped = escape_string(file.file_name)
        language_escaped = escape_string(file.language or "")
        content_hash_escaped = escape_string(file.content_hash or "")
        created_at = int(file.created_at.timestamp()) if file.created_at else int(datetime.now().timestamp())
        updated_at = int(file.updated_at.timestamp()) if file.updated_at else int(datetime.now().timestamp())
        
        # 构建 INSERT VERTEX 语句
        nGQL = (
            f'INSERT VERTEX code_file('
            f'file_path, file_name, language, mysql_id, repository_id, knowledge_base_id, '
            f'content_hash, lines_of_code, file_size, symbols_count, imports_count, '
            f'complexity_score, created_at, updated_at'
            f') VALUES "{vid}":('
            f'"{file_path_escaped}", "{file_name_escaped}", "{language_escaped}", '
            f'{file.id}, {file.repository_id}, {file.knowledge_base_id or 0}, '
            f'"{content_hash_escaped}", {file.lines_of_code or 0}, {file.file_size or 0}, '
            f'{file.symbols_count or 0}, {file.imports_count or 0}, {file.complexity_score or 0.0}, '
            f'{created_at}, {updated_at}'
            f');'
        )
        
        try:
            await self.graph._execute(nGQL, space=self.space)
            return vid
        except Exception as e:
            logger.error(f"创建文件节点失败: {file.file_path}, VID={vid}, 错误={e}", exc_info=True)
            raise
    
    async def _create_symbol_node(self, symbol) -> str:
        """创建代码符号节点（使用 MySQL ID）"""
        # 确保 schema 已创建
        await self._ensure_code_schema()
        
        vid = f"code_symbol_{symbol.id}"
        
        # 转义字符串中的特殊字符
        def escape_string(s: str) -> str:
            if s is None:
                return ""
            s = str(s)
            # 先转义反斜杠，再转义其他字符
            s = s.replace('\\', '\\\\')
            s = s.replace('"', '\\"')
            # 处理换行符、制表符等，替换为空格
            s = s.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            # 移除可能导致问题的其他控制字符
            s = ''.join(char for char in s if ord(char) >= 32 or char in ['\n', '\r', '\t'])
            return s
        
        # 准备属性值
        symbol_name_escaped = escape_string(symbol.symbol_name)
        symbol_type_escaped = escape_string(symbol.symbol_type)
        qualified_name_escaped = escape_string(symbol.qualified_name or "")
        signature_escaped = escape_string(symbol.signature or "")
        docstring_escaped = escape_string(symbol.docstring or "")
        return_type_escaped = escape_string(symbol.return_type or "")
        created_at = int(symbol.created_at.timestamp()) if symbol.created_at else int(datetime.now().timestamp())
        updated_at = int(symbol.updated_at.timestamp()) if symbol.updated_at else int(datetime.now().timestamp())
        
        # 构建 INSERT VERTEX 语句
        nGQL = (
            f'INSERT VERTEX code_symbol('
            f'symbol_name, symbol_type, qualified_name, signature, mysql_id, file_id, '
            f'repository_id, knowledge_base_id, start_line, end_line, docstring, '
            f'return_type, complexity_score, lines_count, created_at, updated_at'
            f') VALUES "{vid}":('
            f'"{symbol_name_escaped}", "{symbol_type_escaped}", "{qualified_name_escaped}", '
            f'"{signature_escaped}", {symbol.id}, {symbol.file_id}, '
            f'{symbol.repository_id}, {symbol.knowledge_base_id or 0}, '
            f'{symbol.start_line or 0}, {symbol.end_line or 0}, '
            f'"{docstring_escaped}", "{return_type_escaped}", {symbol.complexity_score or 0.0}, '
            f'{symbol.lines_count or 0}, {created_at}, {updated_at}'
            f');'
        )
        
        try:
            await self.graph._execute(nGQL, space=self.space)
            return vid
        except Exception as e:
            logger.error(f"创建符号节点失败: {symbol.qualified_name}, VID={vid}, 错误={e}", exc_info=True)
            raise
    
    # ============================================
    # 私有方法：确保 Schema 已创建
    # ============================================
    
    async def _ensure_code_schema(self):
        """确保代码相关的 schema 已创建"""
        if NebulaCodeService._schema_initialized:
            return
        
        try:
            # 创建 code_file 标签
            create_code_file_tag = """
            CREATE TAG IF NOT EXISTS code_file(
                file_path string,
                file_name string,
                language string,
                mysql_id int,
                repository_id int,
                knowledge_base_id int,
                content_hash string,
                lines_of_code int,
                file_size int,
                symbols_count int,
                imports_count int,
                complexity_score double,
                created_at timestamp,
                updated_at timestamp
            );
            """
            await self.graph._execute(create_code_file_tag, space=self.space)
            
            # 创建 code_symbol 标签
            create_code_symbol_tag = """
            CREATE TAG IF NOT EXISTS code_symbol(
                symbol_name string,
                symbol_type string,
                qualified_name string,
                signature string,
                mysql_id int,
                file_id int,
                repository_id int,
                knowledge_base_id int,
                start_line int,
                end_line int,
                docstring string,
                return_type string,
                complexity_score double,
                lines_count int,
                created_at timestamp,
                updated_at timestamp
            );
            """
            await self.graph._execute(create_code_symbol_tag, space=self.space)
            
            # 创建 code_repository 标签
            create_code_repository_tag = """
            CREATE TAG IF NOT EXISTS code_repository(
                repo_name string,
                repo_url string,
                description string,
                mysql_id int,
                knowledge_base_id int,
                default_branch string,
                last_commit_hash string,
                total_files int,
                total_lines int,
                created_at timestamp,
                updated_at timestamp
            );
            """
            await self.graph._execute(create_code_repository_tag, space=self.space)
            
            # 创建 contains 边
            create_contains_edge = """
            CREATE EDGE IF NOT EXISTS contains(
                container_type string,
                start_line int,
                end_line int,
                created_at timestamp
            );
            """
            await self.graph._execute(create_contains_edge, space=self.space)
            
            # 创建 imports 边
            create_imports_edge = """
            CREATE EDGE IF NOT EXISTS imports(
                import_statement string,
                line_number int,
                import_type string,
                created_at timestamp
            );
            """
            await self.graph._execute(create_imports_edge, space=self.space)
            
            # 创建 calls 边
            create_calls_edge = """
            CREATE EDGE IF NOT EXISTS calls(
                call_location string,
                line_number int,
                call_type string,
                created_at timestamp
            );
            """
            await self.graph._execute(create_calls_edge, space=self.space)
            
            # 创建 depends_on 边
            create_depends_on_edge = """
            CREATE EDGE IF NOT EXISTS depends_on(
                dependency_type string,
                strength double,
                created_at timestamp
            );
            """
            await self.graph._execute(create_depends_on_edge, space=self.space)
            
            NebulaCodeService._schema_initialized = True
            logger.info("代码相关的 NebulaGraph schema 已创建")
            
        except Exception as e:
            logger.warning(f"创建代码 schema 时出错（可能已存在）: {e}")
            # 即使出错也标记为已初始化，避免重复尝试
            NebulaCodeService._schema_initialized = True
    
    # ============================================
    # 私有方法：创建边
    # ============================================
    
    async def _create_contains_edge(
        self, 
        container_vid: str, 
        content_vid: str, 
        container_type: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None
    ):
        """创建包含关系（直接使用 nGQL，不使用 create_relationship）"""
        # 确保 schema 已创建
        await self._ensure_code_schema()
        
        # 转义字符串中的特殊字符
        def escape_string(s: str) -> str:
            if s is None:
                return ""
            s = str(s)
            # 先转义反斜杠，再转义其他字符
            s = s.replace('\\', '\\\\')
            s = s.replace('"', '\\"')
            # 处理换行符、制表符等，替换为空格
            s = s.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            # 移除可能导致问题的其他控制字符
            s = ''.join(char for char in s if ord(char) >= 32 or char in ['\n', '\r', '\t'])
            return s
        
        container_type_escaped = escape_string(container_type)
        start_line = start_line or 0
        end_line = end_line or 0
        created_at = int(datetime.now().timestamp())
        
        # 构建 INSERT EDGE 语句
        nGQL = (
            f'INSERT EDGE contains('
            f'container_type, start_line, end_line, created_at'
            f') VALUES "{container_vid}" -> "{content_vid}":('
            f'"{container_type_escaped}", {start_line}, {end_line}, {created_at}'
            f');'
        )
        
        try:
            await self.graph._execute(nGQL, space=self.space)
            # 不再记录每个边的创建日志，减少日志量
        except Exception as e:
            logger.error(f"创建 contains 边失败: container_vid={container_vid}, content_vid={content_vid}, 错误={e}", exc_info=True)
            raise
    
    async def _create_imports_edge(
        self, 
        source_vid: str, 
        target_vid: str,
        import_statement: str = "",
        line_number: Optional[int] = None
    ):
        """创建导入关系（直接使用 nGQL，不使用 create_relationship）"""
        # 确保 schema 已创建
        await self._ensure_code_schema()
        
        # 转义字符串中的特殊字符
        def escape_string(s: str) -> str:
            if s is None:
                return ""
            s = str(s)
            s = s.replace('\\', '\\\\')
            s = s.replace('"', '\\"')
            s = s.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            return s
        
        import_statement_escaped = escape_string(import_statement)
        import_type = "module"
        line_number = line_number or 0
        created_at = int(datetime.now().timestamp())
        
        # 转义 VID
        source_vid_escaped = source_vid.replace('"', '\\"')
        target_vid_escaped = target_vid.replace('"', '\\"')
        
        # 构建 INSERT EDGE 语句
        nGQL = (
            f'INSERT EDGE imports('
            f'import_statement, line_number, import_type, created_at'
            f') VALUES "{source_vid_escaped}" -> "{target_vid_escaped}":('
            f'"{import_statement_escaped}", {line_number}, "{import_type}", {created_at}'
            f');'
        )
        
        try:
            await self.graph._execute(nGQL, space=self.space)
        except Exception as e:
            error_msg = str(e).lower()
            # 如果边已存在，不抛出异常（静默处理）
            if 'existed' in error_msg or 'duplicate' in error_msg or 'already exists' in error_msg:
                return  # 边已存在，静默返回
            # 其他错误才记录和抛出
            logger.error(f"创建 imports 边失败: source_vid={source_vid}, target_vid={target_vid}, 错误={e}", exc_info=True)
            raise
    
    async def _create_calls_edge(
        self,
        caller_vid: str,
        callee_vid: str,
        line_number: Optional[int] = None
    ):
        """创建调用关系"""
        rel_data = {
            "edge_type": "calls",
            "properties": {
                "call_location": "",
                "line_number": line_number or 0,
                "call_type": "direct",
                "created_at": int(datetime.now().timestamp())
            }
        }
        await self.graph.create_relationship(
            self.space,
            caller_vid,
            callee_vid,
            rel_data
        )
    
    async def _create_inherits_edge(
        self,
        child_vid: str,
        parent_vid: str
    ):
        """创建继承关系"""
        rel_data = {
            "edge_type": "inherits",
            "properties": {
                "inheritance_type": "extends",
                "created_at": int(datetime.now().timestamp())
            }
        }
        await self.graph.create_relationship(
            self.space,
            child_vid,
            parent_vid,
            rel_data
        )
    
    async def _create_implements_edge(
        self,
        impl_vid: str,
        interface_vid: str,
        confidence: float = 1.0
    ):
        """创建实现关系"""
        rel_data = {
            "edge_type": "implements",
            "properties": {
                "confidence": confidence,
                "implementation_detail": "",
                "created_at": int(datetime.now().timestamp())
            }
        }
        await self.graph.create_relationship(
            self.space,
            impl_vid,
            interface_vid,
            rel_data
        )
    
    async def _create_references_edge(
        self,
        source_vid: str,
        target_vid: str,
        reference_type: str = "reference",
        context: str = "",
        confidence: float = 1.0
    ):
        """创建引用关系"""
        rel_data = {
            "edge_type": "references",
            "properties": {
                "context": context,
                "reference_type": reference_type,
                "confidence": confidence,
                "created_at": int(datetime.now().timestamp())
            }
        }
        await self.graph.create_relationship(
            self.space,
            source_vid,
            target_vid,
            rel_data
        )
    
    async def _create_depends_on_edge(
        self,
        source_vid: str,
        target_vid: str,
        dependency_type: str = "unknown",
        strength: float = 1.0
    ):
        """创建依赖关系"""
        rel_data = {
            "edge_type": "depends_on",
            "properties": {
                "dependency_type": dependency_type,
                "strength": strength,
                "created_at": int(datetime.now().timestamp())
            }
        }
        await self.graph.create_relationship(
            self.space,
            source_vid,
            target_vid,
            rel_data
        )
    
    async def _link_repository_to_kb(self, repo_vid: str, kb_id: int):
        """将仓库链接到知识库"""
        kb_vid = f"knowledge_base_{kb_id}"
        
        rel_data = {
            "edge_type": "contains",
            "properties": {
                "container_type": "knowledge_base",
                "created_at": int(datetime.now().timestamp())
            }
        }
        
        await self.graph.create_relationship(
            self.space,
            kb_vid,
            repo_vid,
            rel_data
        )


# ============================================
# 便捷函数
# ============================================

    async def delete_repository_from_graph(self, repository_id: int) -> Dict[str, Any]:
        """
        从图数据库中删除代码仓库及其所有关联数据
        
        清理范围：
        1. 代码仓库节点（code_repository）
        2. 代码文件节点（code_file）
        3. 代码符号节点（code_symbol）
        4. 所有相关的边（imports, calls, inherits, implements, contains, depends_on, references）
        
        Args:
            repository_id: 仓库ID
            
        Returns:
            删除结果统计
        """
        try:
            from app.models.code_repository import CodeRepository
            from app.models.code_file import CodeFile
            from app.models.code_symbol import CodeSymbol
            
            # 1. 查询仓库信息
            repo = self.db.query(CodeRepository).filter(
                CodeRepository.id == repository_id
            ).first()
            
            if not repo:
                logger.warning(f"仓库不存在: repository_id={repository_id}")
                return {"status": "not_found", "repository_id": repository_id}
            
            logger.info(f"开始从图数据库删除代码仓库: {repo.repo_name}")
            
            deleted_stats = {
                "repository_nodes": 0,
                "file_nodes": 0,
                "symbol_nodes": 0,
                "edges": 0
            }
            
            # 2. 删除仓库节点（会级联删除相关边）
            repo_vid = f"code_repository_{repository_id}"
            try:
                await self.graph.delete_entity(self.space, repo_vid)
                deleted_stats["repository_nodes"] += 1
                logger.info(f"[NebulaGraph删除] ✅ 已删除仓库节点: {repo_vid}")
            except Exception as e:
                logger.warning(f"删除仓库节点失败: {e}")
            
            # 3. 批量删除该仓库的所有代码文件节点（使用批量删除优化性能）
            files = self.db.query(CodeFile).filter(
                CodeFile.repository_id == repository_id
            ).all()
            
            if files:
                logger.info(f"[NebulaGraph删除] 开始批量删除 {len(files)} 个文件节点（将分 {(len(files) + 49) // 50} 批执行）")
                file_vids = [f"code_file_{file.id}" for file in files]
                
                # 使用批量删除方法（每批50个，由batch_delete_entities内部处理）
                try:
                    result = await self.graph.batch_delete_entities(self.space, file_vids)
                    deleted_stats["file_nodes"] = result.get("success", 0)
                    failed_count = result.get("failed", 0)
                    if failed_count > 0:
                        logger.warning(f"删除文件节点时 {failed_count} 个失败")
                except Exception as e:
                    logger.warning(f"批量删除文件节点失败: {e}")
                    # 回退到逐个删除
                    for vid in file_vids:
                        try:
                            await self.graph.delete_entity(self.space, vid)
                            deleted_stats["file_nodes"] += 1
                        except Exception:
                            pass
            
            logger.info(f"[NebulaGraph删除] ✅ 已删除 {deleted_stats['file_nodes']} 个文件节点")
            
            # 4. 批量删除该仓库的所有代码符号节点（使用批量删除优化性能）
            symbols = self.db.query(CodeSymbol).filter(
                CodeSymbol.repository_id == repository_id
            ).all()
            
            if symbols:
                logger.info(f"[NebulaGraph删除] 开始批量删除 {len(symbols)} 个符号节点（将分 {(len(symbols) + 49) // 50} 批执行）")
                symbol_vids = [f"code_symbol_{symbol.id}" for symbol in symbols]
                
                # 使用批量删除方法（每批50个，由batch_delete_entities内部处理）
                try:
                    result = await self.graph.batch_delete_entities(self.space, symbol_vids)
                    deleted_stats["symbol_nodes"] = result.get("success", 0)
                    failed_count = result.get("failed", 0)
                    if failed_count > 0:
                        logger.warning(f"删除符号节点时 {failed_count} 个失败")
                except Exception as e:
                    logger.warning(f"批量删除符号节点失败: {e}")
                    # 回退到逐个删除
                    for vid in symbol_vids:
                        try:
                            await self.graph.delete_entity(self.space, vid)
                            deleted_stats["symbol_nodes"] += 1
                        except Exception:
                            pass
            
            logger.info(f"[NebulaGraph删除] ✅ 已删除 {deleted_stats['symbol_nodes']} 个符号节点")
            
            # 5. 统计（边会在删除节点时自动级联删除）
            deleted_stats["edges"] = "auto_deleted"  # NebulaGraph 会自动删除孤立的边
            
            logger.info(f"[NebulaGraph删除] ✅ 图数据库清理完成: repository_id={repository_id}, 统计={deleted_stats}")
            
            return {
                "status": "success",
                "repository_id": repository_id,
                "deleted_stats": deleted_stats
            }
            
        except Exception as e:
            logger.error(f"从图数据库删除代码仓库失败: {e}")
            return {
                "status": "error",
                "repository_id": repository_id,
                "error": str(e)
            }
    
    async def get_dependency_graph(self, repository_id: int, max_nodes: int = 500) -> Dict[str, Any]:
        """
        从 NebulaGraph 获取依赖关系图
        
        Args:
            repository_id: 仓库ID
            max_nodes: 最大节点数
            
        Returns:
            依赖图数据: { nodes: [], edges: [] }
        """
        try:
            await self.graph.create_space_if_not_exists(self.space)
            
            # 1. 先找到仓库节点
            repo_vid = f"code_repository_{repository_id}"
            
            # 2. 查询仓库下的所有文件节点（使用 GO 查询，更可靠）
            # 先通过边找到所有文件 VID
            find_files_nGQL = f"""
            GO FROM "{repo_vid}" OVER contains
            YIELD dst(edge) as vid
            | LIMIT {max_nodes};
            """
            
            files_vids_result = await self.graph._execute(find_files_nGQL, space=self.space)
            
            # GO 查询返回的列名可能不同，需要适配
            file_vids = []
            if files_vids_result:
                for row in files_vids_result:
                    vid = None
                    if 'vid' in row:
                        vid = row['vid']
                    else:
                        # 尝试其他可能的字段名
                        for key in row.keys():
                            if 'vid' in key.lower() or key == 'dst(edge)' or 'dst' in key.lower():
                                vid = row[key]
                                break
                    if vid:
                        # 确保 VID 是字符串格式
                        vid = str(vid).strip().strip('"').strip("'")
                        file_vids.append(vid)
            
            if not file_vids:
                logger.info(f"仓库 {repository_id} 在 NebulaGraph 中没有文件节点")
                return {"nodes": [], "edges": []}
            
            if not file_vids:
                return {"nodes": [], "edges": []}
            
            # 3. 批量获取文件属性（使用 FETCH PROP）
            # 转义 VID 中的特殊字符，并限制批量大小（避免查询过长）
            def escape_vid(vid: str) -> str:
                """转义 VID 中的特殊字符"""
                vid = str(vid).strip()
                # 移除可能的引号
                vid = vid.strip('"').strip("'")
                # 转义反斜杠和引号
                vid = vid.replace('\\', '\\\\').replace('"', '\\"')
                return f'"{vid}"'
            
            # 限制批量大小，避免查询过长
            batch_size = 100
            all_files_data = []
            for i in range(0, len(file_vids), batch_size):
                batch_vids = file_vids[i:i+batch_size]
                vid_list_str = ", ".join([escape_vid(vid) for vid in batch_vids])
                fetch_files_nGQL = f"""
                FETCH PROP ON code_file {vid_list_str}
                YIELD id(vertex) as vid, properties(vertex) as props;
                """
                
                batch_result = await self.graph._execute(fetch_files_nGQL, space=self.space)
                if batch_result:
                    all_files_data.extend(batch_result)
            
            if not all_files_data:
                logger.info(f"仓库 {repository_id} 在 NebulaGraph 中没有文件节点")
                return {"nodes": [], "edges": []}
            
            # 4. 构建节点列表
            nodes = []
            for row in all_files_data:
                vid = row.get('vid', '')
                props = row.get('props', {})
                
                nodes.append({
                    "id": vid,
                    "name": props.get('file_path', ''),
                    "type": "file",
                    "language": props.get('language', ''),
                    "symbols_count": props.get('symbols_count', 0) or 0,
                    "lines": props.get('lines_of_code', 0) or 0,
                    "mysql_id": props.get('mysql_id', 0)
                })
            
            # 5. 查询文件之间的依赖关系（imports, depends_on, calls）
            # 使用 GO 查询，分批处理避免查询过长
            edges = []
            batch_size = 50  # 每批查询50个文件
            
            # 预先转换 file_vids 为字符串列表，用于后续比较
            file_vids_str = [str(vid) for vid in file_vids]
            
            for edge_type in ['imports', 'depends_on', 'calls']:
                # 分批查询
                for batch_start in range(0, min(len(file_vids), 200), batch_size):  # 限制最多200个文件
                    batch_vids = file_vids[batch_start:batch_start + batch_size]
                    try:
                        # 使用 GO 查询遍历文件节点的出边
                        vid_list_str = ", ".join([escape_vid(vid) for vid in batch_vids])
                        edges_nGQL = f"""
                        GO FROM {vid_list_str} OVER {edge_type}
                        YIELD src(edge) as source_vid, dst(edge) as target_vid, properties(edge) as edge_props;
                        """
                        
                        edges_result = await self.graph._execute(edges_nGQL, space=self.space)
                        
                        if edges_result:
                            for row in edges_result:
                                source_vid = row.get('source_vid', '')
                                target_vid = row.get('target_vid', '')
                                edge_props = row.get('edge_props', {})
                                
                                # 只保留目标也在文件列表中的边（统一转换为字符串比较）
                                source_vid_str = str(source_vid) if source_vid else ''
                                target_vid_str = str(target_vid) if target_vid else ''
                                
                                if source_vid_str and target_vid_str and target_vid_str in file_vids_str:
                                    edges.append({
                                        'source_vid': source_vid_str,
                                        'target_vid': target_vid_str,
                                        'edge_type': edge_type,
                                        'edge_props': edge_props
                                    })
                    except Exception as edge_query_error:
                        logger.debug(f"查询 {edge_type} 边失败（批次 {batch_start}）: {edge_query_error}")
                        # 如果 GO 查询失败，尝试使用 MATCH 查询（作为备选）
                        try:
                            vid_list_str = ", ".join([escape_vid(vid) for vid in batch_vids])
                            match_nGQL = f"""
                            MATCH (source:code_file)-[e:{edge_type}]->(target:code_file)
                            WHERE id(source) IN [{vid_list_str}] AND id(target) IN [{", ".join([escape_vid(vid) for vid in file_vids[:200]])}]
                            RETURN 
                                id(source) as source_vid,
                                id(target) as target_vid,
                                type(e) as edge_type,
                                properties(e) as edge_props
                            LIMIT 500;
                            """
                            match_result = await self.graph._execute(match_nGQL, space=self.space)
                            if match_result:
                                for row in match_result:
                                    source_vid = row.get('source_vid', '')
                                    target_vid = row.get('target_vid', '')
                                    edge_props = row.get('edge_props', {})
                                    
                                    if source_vid and target_vid:
                                        edges.append({
                                            'source_vid': str(source_vid),
                                            'target_vid': str(target_vid),
                                            'edge_type': edge_type,
                                            'edge_props': edge_props
                                        })
                        except Exception:
                            pass
            
            edges_result = edges
            
            # 6. 构建边列表（edges_result 已经是处理过的列表）
            final_edges = []
            for row in edges_result:
                source_vid = row.get('source_vid', '') if isinstance(row, dict) else str(row.get('source_vid', ''))
                target_vid = row.get('target_vid', '') if isinstance(row, dict) else str(row.get('target_vid', ''))
                edge_type = row.get('edge_type', 'depends_on') if isinstance(row, dict) else 'depends_on'
                edge_props = row.get('edge_props', {}) if isinstance(row, dict) else {}
                
                if not source_vid or not target_vid:
                    continue
                
                # 确定边的类型标签
                if edge_type == 'imports':
                    type_label = 'import'
                elif edge_type == 'depends_on':
                    type_label = edge_props.get('dependency_type', 'depends') if isinstance(edge_props, dict) else 'depends'
                elif edge_type == 'calls':
                    type_label = 'call'
                else:
                    type_label = edge_type
                
                final_edges.append({
                    "source": str(source_vid),
                    "target": str(target_vid),
                    "type": type_label
                })
            
            logger.info(f"[NebulaGraph查询] 仓库 {repository_id} 依赖图: {len(nodes)} 个节点, {len(final_edges)} 条边")
            
            return {
                "nodes": nodes,
                "edges": final_edges
            }
            
        except Exception as e:
            logger.error(f"从 NebulaGraph 获取依赖图失败: {e}", exc_info=True)
            # 如果 NebulaGraph 未启用或查询失败，返回空数据
            if not settings.USE_NEBULA_GRAPH:
                logger.warning("NebulaGraph 未启用，返回空依赖图")
                return {"nodes": [], "edges": []}
            raise
    
    async def create_file_node_direct(
        self,
        repository_id: int,
        file_path: str,
        file_name: str,
        language: Optional[str] = None,
        lines_of_code: int = 0,
        file_size: int = 0,
        complexity_score: float = 0.0,
        symbols_count: int = 0,
        imports_count: int = 0,
        knowledge_base_id: Optional[int] = None,
        content_hash: Optional[str] = None
    ) -> str:
        """
        直接创建文件节点到 NebulaGraph（不依赖 MySQL）
        
        Args:
            repository_id: 仓库ID
            file_path: 文件路径
            file_name: 文件名
            language: 编程语言
            lines_of_code: 代码行数
            file_size: 文件大小
            complexity_score: 复杂度分数
            symbols_count: 符号数量
            imports_count: 导入数量
            knowledge_base_id: 知识库ID
            content_hash: 内容哈希
            
        Returns:
            文件节点的 VID
        """
        # 确保 schema 已创建
        await self._ensure_code_schema()
        
        # 生成基于哈希的 VID
        vid = self._generate_file_vid(repository_id, file_path)
        
        # 转义字符串中的特殊字符
        def escape_string(s: str) -> str:
            if s is None:
                return ""
            s = str(s)
            # 先转义反斜杠，再转义其他字符
            s = s.replace('\\', '\\\\')
            s = s.replace('"', '\\"')
            # 处理换行符、制表符等，替换为空格
            s = s.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            # 移除可能导致问题的其他控制字符
            s = ''.join(char for char in s if ord(char) >= 32 or char in ['\n', '\r', '\t'])
            return s
        
        # 准备属性值
        file_path_escaped = escape_string(file_path)
        file_name_escaped = escape_string(file_name)
        language_escaped = escape_string(language or "")
        content_hash_escaped = escape_string(content_hash or "")
        created_at = int(datetime.now().timestamp())
        updated_at = int(datetime.now().timestamp())
        
        # 构建 INSERT VERTEX 语句
        nGQL = (
            f'INSERT VERTEX code_file('
            f'file_path, file_name, language, mysql_id, repository_id, knowledge_base_id, '
            f'content_hash, lines_of_code, file_size, symbols_count, imports_count, '
            f'complexity_score, created_at, updated_at'
            f') VALUES "{vid}":('
            f'"{file_path_escaped}", "{file_name_escaped}", "{language_escaped}", '
            f'0, {repository_id}, {knowledge_base_id or 0}, '
            f'"{content_hash_escaped}", {lines_of_code}, {file_size}, '
            f'{symbols_count}, {imports_count}, {complexity_score}, '
            f'{created_at}, {updated_at}'
            f');'
        )
        
        try:
            await self.graph._execute(nGQL, space=self.space)
            # 不再记录每个文件的创建日志，减少日志量（批量统计会在任务中统一输出）
            return vid
        except Exception as e:
            logger.error(f"创建文件节点失败: {file_path}, VID={vid}, 错误={e}", exc_info=True)
            raise
    
    async def create_symbol_node_direct(
        self,
        repository_id: int,
        file_path: str,
        symbol_name: str,
        symbol_type: str,
        qualified_name: str,
        start_line: int,
        end_line: int,
        signature: Optional[str] = None,
        docstring: Optional[str] = None,
        return_type: Optional[str] = None,
        complexity_score: float = 0.0,
        lines_count: int = 0,
        knowledge_base_id: Optional[int] = None,
        file_vid: Optional[str] = None
    ) -> str:
        """
        直接创建符号节点到 NebulaGraph（不依赖 MySQL）
        
        Args:
            repository_id: 仓库ID
            file_path: 文件路径
            symbol_name: 符号名称
            symbol_type: 符号类型
            qualified_name: 限定名
            start_line: 起始行号
            end_line: 结束行号
            signature: 函数签名
            docstring: 文档字符串
            return_type: 返回类型
            complexity_score: 复杂度分数
            lines_count: 代码行数
            knowledge_base_id: 知识库ID
            file_vid: 文件节点的 VID（用于创建包含关系）
            
        Returns:
            符号节点的 VID
        """
        # 确保 schema 已创建
        await self._ensure_code_schema()
        
        # 生成基于哈希的 VID
        vid = self._generate_symbol_vid(repository_id, qualified_name, file_path, start_line)
        
        # 转义字符串中的特殊字符
        def escape_string(s: str) -> str:
            if s is None:
                return ""
            s = str(s)
            # 先转义反斜杠，再转义其他字符
            s = s.replace('\\', '\\\\')
            s = s.replace('"', '\\"')
            # 处理换行符、制表符等，替换为空格
            s = s.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            # 移除可能导致问题的其他控制字符
            s = ''.join(char for char in s if ord(char) >= 32 or char in ['\n', '\r', '\t'])
            return s
        
        # 准备属性值
        symbol_name_escaped = escape_string(symbol_name)
        symbol_type_escaped = escape_string(symbol_type)
        qualified_name_escaped = escape_string(qualified_name)
        signature_escaped = escape_string(signature or "")
        docstring_escaped = escape_string(docstring or "")
        return_type_escaped = escape_string(return_type or "")
        created_at = int(datetime.now().timestamp())
        updated_at = int(datetime.now().timestamp())
        
        # 构建 INSERT VERTEX 语句
        nGQL = (
            f'INSERT VERTEX code_symbol('
            f'symbol_name, symbol_type, qualified_name, signature, mysql_id, file_id, '
            f'repository_id, knowledge_base_id, start_line, end_line, docstring, '
            f'return_type, complexity_score, lines_count, created_at, updated_at'
            f') VALUES "{vid}":('
            f'"{symbol_name_escaped}", "{symbol_type_escaped}", "{qualified_name_escaped}", '
            f'"{signature_escaped}", 0, 0, '
            f'{repository_id}, {knowledge_base_id or 0}, {start_line}, {end_line}, '
            f'"{docstring_escaped}", "{return_type_escaped}", {complexity_score}, '
            f'{lines_count}, {created_at}, {updated_at}'
            f');'
        )
        
        try:
            await self.graph._execute(nGQL, space=self.space)
            
            # 如果提供了文件 VID，创建包含关系
            if file_vid:
                await self._create_contains_edge(
                    file_vid,
                    vid,
                    "file",
                    start_line=start_line,
                    end_line=end_line
                )
            
            # 不再记录每个符号的创建日志，减少日志量（批量统计会在任务中统一输出）
            return vid
        except Exception as e:
            logger.error(f"创建符号节点失败: {qualified_name}, VID={vid}, 错误={e}", exc_info=True)
            raise
    
    async def get_repository_files(
        self,
        repository_id: int,
        language: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        从 NebulaGraph 查询仓库文件列表
        
        Args:
            repository_id: 仓库ID
            language: 语言筛选
            page: 页码
            page_size: 每页大小
            
        Returns:
            文件列表: { files: [], total: int, page: int, page_size: int }
        """
        try:
            await self.graph.create_space_if_not_exists(self.space)
            
            repo_vid = f"code_repository_{repository_id}"
            
            # 确保 page_size 是整数
            page_size = int(page_size) if page_size else 50
            page = int(page) if page else 1
            offset = (page - 1) * page_size
            
            # 构建查询条件（使用 GO 查询，更可靠）
            if language:
                # 使用 GO 查询，然后过滤语言
                find_files_nGQL = f"""
                GO FROM "{repo_vid}" OVER contains
                YIELD dst(edge) as vid, $$.code_file.language as language
                WHERE language == "{language}"
                | LIMIT {page_size} OFFSET {offset};
                """
            else:
                # 使用 GO 查询
                find_files_nGQL = f"""
                GO FROM "{repo_vid}" OVER contains
                YIELD dst(edge) as vid
                | LIMIT {page_size} OFFSET {offset};
                """
            
            files_vids_result = await self.graph._execute(find_files_nGQL, space=self.space)
            
            # GO 查询返回的列名可能不同，需要适配
            file_vids = []
            if files_vids_result:
                # 确保所有结果都有 'vid' 字段
                for row in files_vids_result:
                    vid = None
                    if 'vid' in row:
                        vid = row['vid']
                    else:
                        # 尝试其他可能的字段名
                        for key in row.keys():
                            if 'vid' in key.lower() or key == 'dst(edge)' or 'dst' in key.lower():
                                vid = row[key]
                                break
                    if vid:
                        # 确保 VID 是字符串格式
                        vid = str(vid).strip().strip('"').strip("'")
                        file_vids.append(vid)
            
            if not file_vids:
                return {"files": [], "total": 0, "page": page, "page_size": page_size}
            
            if not file_vids:
                return {"files": [], "total": 0, "page": page, "page_size": page_size}
            
            # 批量获取文件属性（分批处理，避免查询过长）
            def escape_vid(vid: str) -> str:
                """转义 VID 中的特殊字符"""
                vid = str(vid).strip()
                # 移除可能的引号
                vid = vid.strip('"').strip("'")
                # 转义反斜杠和引号
                vid = vid.replace('\\', '\\\\').replace('"', '\\"')
                return f'"{vid}"'
            
            # 限制批量大小，避免查询过长
            batch_size = 100
            all_files_data = []
            for i in range(0, len(file_vids), batch_size):
                batch_vids = file_vids[i:i+batch_size]
                vid_list_str = ", ".join([escape_vid(vid) for vid in batch_vids])
                fetch_files_nGQL = f"""
                FETCH PROP ON code_file {vid_list_str}
                YIELD id(vertex) as vid, properties(vertex) as props;
                """
                
                batch_result = await self.graph._execute(fetch_files_nGQL, space=self.space)
                if batch_result:
                    all_files_data.extend(batch_result)
            
            files_result = all_files_data
            
            # 构建文件列表
            files = []
            for row in files_result:
                vid = row.get('vid', '')
                props = row.get('props', {})
                files.append({
                    "id": vid,  # 使用 VID 作为 ID
                    "file_path": props.get('file_path', ''),
                    "file_name": props.get('file_name', ''),
                    "language": props.get('language', ''),
                    "lines_of_code": props.get('lines_of_code', 0) or 0,
                    "file_size": props.get('file_size', 0) or 0,
                    "symbols_count": props.get('symbols_count', 0) or 0,
                    "complexity_score": props.get('complexity_score', 0.0) or 0.0,
                    "imports_count": props.get('imports_count', 0) or 0
                })
            
            # 查询总数（使用 GO 查询，更可靠）
            if language:
                count_nGQL = f"""
                GO FROM "{repo_vid}" OVER contains
                YIELD dst(edge) as vid, $$.code_file.language as language
                WHERE language == "{language}"
                | YIELD count(*) as total;
                """
            else:
                count_nGQL = f"""
                GO FROM "{repo_vid}" OVER contains
                YIELD dst(edge) as vid
                | YIELD count(*) as total;
                """
            count_result = await self.graph._execute(count_nGQL, space=self.space)
            # GO 查询返回的格式可能不同，需要适配
            if count_result and len(count_result) > 0:
                total = count_result[0].get('total', 0) or count_result[0].get('count(*)', 0) or 0
            else:
                total = 0
            
            logger.info(f"[NebulaGraph查询] 仓库 {repository_id} 文件列表: 总数={total}, 当前页={len(files)}")
            
            return {
                "files": files,
                "total": total,
                "page": page,
                "page_size": page_size
            }
            
        except Exception as e:
            logger.error(f"从 NebulaGraph 查询文件列表失败: {e}", exc_info=True)
            raise
    
    async def get_file_by_vid(self, file_vid: str) -> Optional[Dict[str, Any]]:
        """
        从 NebulaGraph 根据 VID 查询文件详情
        
        Args:
            file_vid: 文件节点的 VID
            
        Returns:
            文件详情字典，如果不存在返回 None
        """
        try:
            await self.graph.create_space_if_not_exists(self.space)
            
            fetch_file_nGQL = f"""
            FETCH PROP ON code_file "{file_vid}"
            YIELD id(vertex) as vid, properties(vertex) as props;
            """
            
            result = await self.graph._execute(fetch_file_nGQL, space=self.space)
            
            if not result or len(result) == 0:
                return None
            
            row = result[0]
            vid = row.get('vid', '')
            props = row.get('props', {})
            
            return {
                "id": vid,
                "file_path": props.get('file_path', ''),
                "file_name": props.get('file_name', ''),
                "language": props.get('language', ''),
                "lines_of_code": props.get('lines_of_code', 0) or 0,
                "file_size": props.get('file_size', 0) or 0,
                "symbols_count": props.get('symbols_count', 0) or 0,
                "complexity_score": props.get('complexity_score', 0.0) or 0.0,
                "imports_count": props.get('imports_count', 0) or 0,
                "content_hash": props.get('content_hash', ''),
                "repository_id": props.get('repository_id', 0),
                "knowledge_base_id": props.get('knowledge_base_id', 0)
            }
            
        except Exception as e:
            logger.error(f"从 NebulaGraph 查询文件详情失败: {e}", exc_info=True)
            return None
    
    async def get_file_by_path(self, repository_id: int, file_path: str) -> Optional[Dict[str, Any]]:
        """
        从 NebulaGraph 根据文件路径查询文件详情
        
        Args:
            repository_id: 仓库ID
            file_path: 文件路径
            
        Returns:
            文件详情字典，如果不存在返回 None
        """
        # 生成 VID
        file_vid = self._generate_file_vid(repository_id, file_path)
        return await self.get_file_by_vid(file_vid)
    
    async def query_call_chain(
        self,
        repository_id: int,
        source: str,
        target: str,
        max_hops: int = 3
    ) -> Dict[str, Any]:
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
            await self.graph.create_space_if_not_exists(self.space)
            
            # 1. 查找源和目标节点
            # 先尝试作为符号查找
            source_vid = None
            target_vid = None
            
            # 查找源节点（先尝试符号，再尝试文件）
            source_vid = None
            # 尝试作为符号查找
            find_source_symbol_nGQL = f"""
            MATCH (s:code_symbol)
            WHERE s.repository_id == {repository_id}
            AND (s.symbol_name == "{source}" OR s.qualified_name == "{source}")
            RETURN id(s) as vid
            LIMIT 1;
            """
            source_result = await self.graph._execute(find_source_symbol_nGQL, space=self.space)
            if source_result and source_result[0].get('vid'):
                source_vid = source_result[0].get('vid')
            
            # 如果没找到符号，尝试作为文件查找
            if not source_vid:
                source_file_vid = self._generate_file_vid(repository_id, source)
                file_data = await self.get_file_by_vid(source_file_vid)
                if file_data:
                    source_vid = source_file_vid
            
            # 查找目标节点（先尝试符号，再尝试文件）
            target_vid = None
            # 尝试作为符号查找
            find_target_symbol_nGQL = f"""
            MATCH (t:code_symbol)
            WHERE t.repository_id == {repository_id}
            AND (t.symbol_name == "{target}" OR t.qualified_name == "{target}")
            RETURN id(t) as vid
            LIMIT 1;
            """
            target_result = await self.graph._execute(find_target_symbol_nGQL, space=self.space)
            if target_result and target_result[0].get('vid'):
                target_vid = target_result[0].get('vid')
            
            # 如果没找到符号，尝试作为文件查找
            if not target_vid:
                target_file_vid = self._generate_file_vid(repository_id, target)
                file_data = await self.get_file_by_vid(target_file_vid)
                if file_data:
                    target_vid = target_file_vid
            
            if not source_vid or not target_vid:
                return {"paths": [], "message": "未找到源或目标节点"}
            
            # 2. 查询调用链路径
            # 使用 FIND SHORTEST PATH 查找最短路径（支持多条路径）
            path_nGQL = f"""
            FIND SHORTEST PATH FROM "{source_vid}" TO "{target_vid}"
            OVER calls, imports
            UPTO {max_hops} STEPS
            YIELD path as p;
            """
            
            path_result = await self.graph._execute(path_nGQL, space=self.space)
            
            # 3. 解析路径结果并获取节点详情
            paths = []
            for row in path_result:
                path_data = row.get('p', {})
                # NebulaGraph 路径格式: Path(vertices=[...], edges=[...])
                # 需要提取 vertices 和 edges
                vertices = path_data.get('vertices', []) if isinstance(path_data, dict) else []
                edges = path_data.get('edges', []) if isinstance(path_data, dict) else []
                
                # 构建路径节点列表
                path_nodes = []
                for vertex in vertices:
                    if isinstance(vertex, dict):
                        vid = vertex.get('vid', '')
                        # 获取节点属性
                        if vid.startswith('code_symbol_'):
                            # 查询符号详情
                            fetch_symbol_nGQL = f"""
                            FETCH PROP ON code_symbol "{vid}"
                            YIELD properties(vertex) as props;
                            """
                            symbol_result = await self.graph._execute(fetch_symbol_nGQL, space=self.space)
                            if symbol_result:
                                props = symbol_result[0].get('props', {})
                                path_nodes.append({
                                    "vid": vid,
                                    "name": props.get('symbol_name', ''),
                                    "qualified_name": props.get('qualified_name', ''),
                                    "type": "symbol"
                                })
                        elif vid.startswith('code_file_'):
                            # 查询文件详情
                            file_data = await self.get_file_by_vid(vid)
                            if file_data:
                                path_nodes.append({
                                    "vid": vid,
                                    "name": file_data.get('file_path', ''),
                                    "file_path": file_data.get('file_path', ''),
                                    "type": "file"
                                })
                
                if path_nodes:
                    paths.append(path_nodes)
            
            logger.info(f"[调用链查询] 仓库 {repository_id}: {source} -> {target}, 找到 {len(paths)} 条路径")
            
            return {
                "paths": paths,
                "source": source,
                "target": target,
                "source_vid": source_vid,
                "target_vid": target_vid
            }
            
        except Exception as e:
            logger.error(f"查询调用链失败: {e}", exc_info=True)
            raise
    
    async def query_dependency_path(
        self,
        repository_id: int,
        source: str,
        target: str,
        max_hops: int = 3
    ) -> Dict[str, Any]:
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
            await self.graph.create_space_if_not_exists(self.space)
            
            # 1. 生成文件 VID
            source_vid = self._generate_file_vid(repository_id, source)
            target_vid = self._generate_file_vid(repository_id, target)
            
            # 验证文件是否存在
            source_file = await self.get_file_by_vid(source_vid)
            target_file = await self.get_file_by_vid(target_vid)
            
            if not source_file or not target_file:
                return {"paths": [], "message": "未找到源或目标文件"}
            
            # 2. 查询依赖路径
            path_nGQL = f"""
            FIND SHORTEST PATH FROM "{source_vid}" TO "{target_vid}"
            OVER imports, depends_on
            UPTO {max_hops} STEPS
            YIELD path as p;
            """
            
            path_result = await self.graph._execute(path_nGQL, space=self.space)
            
            # 3. 解析路径结果并获取节点详情
            paths = []
            for row in path_result:
                path_data = row.get('p', {})
                vertices = path_data.get('vertices', []) if isinstance(path_data, dict) else []
                
                # 构建路径节点列表
                path_nodes = []
                for vertex in vertices:
                    if isinstance(vertex, dict):
                        vid = vertex.get('vid', '')
                        # 文件节点
                        if vid.startswith('code_file_'):
                            file_data = await self.get_file_by_vid(vid)
                            if file_data:
                                path_nodes.append({
                                    "vid": vid,
                                    "name": file_data.get('file_path', ''),
                                    "file_path": file_data.get('file_path', ''),
                                    "type": "file"
                                })
                
                if path_nodes:
                    paths.append(path_nodes)
            
            logger.info(f"[依赖路径查询] 仓库 {repository_id}: {source} -> {target}, 找到 {len(paths)} 条路径")
            
            return {
                "paths": paths,
                "source": source,
                "target": target,
                "source_vid": source_vid,
                "target_vid": target_vid
            }
            
        except Exception as e:
            logger.error(f"查询依赖路径失败: {e}", exc_info=True)
            raise


def get_nebula_code_service(db: Session) -> NebulaCodeService:
    """获取 NebulaCode 服务实例"""
    return NebulaCodeService(db)
