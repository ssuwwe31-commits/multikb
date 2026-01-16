"""
NebulaGraph Code Service
代码实体同步服务 - 将代码数据同步到知识图谱
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.logging import logger
from app.config.settings import settings
from app.services.graph_storage_service import get_graph_storage


class NebulaCodeService:
    """代码库到 NebulaGraph 的同步服务"""
    
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
    # 私有方法：创建节点
    # ============================================
    
    async def _create_repository_node(self, repo) -> str:
        """创建代码仓库节点"""
        vid = f"code_repository_{repo.id}"
        
        entity_data = {
            "vid": vid,
            "tag": "code_repository",
            "properties": {
                "repo_name": repo.repo_name,
                "repo_url": repo.repo_url,
                "description": repo.description or "",
                "mysql_id": repo.id,
                "knowledge_base_id": repo.knowledge_base_id or 0,
                "default_branch": repo.default_branch,
                "last_commit_hash": repo.last_commit_hash or "",
                "total_files": repo.total_files,
                "total_lines": repo.total_lines,
                "created_at": int(repo.created_at.timestamp()) if repo.created_at else 0,
                "updated_at": int(repo.updated_at.timestamp()) if repo.updated_at else 0
            }
        }
        
        await self.graph.create_entity(self.space, entity_data)
        return vid
    
    async def _create_file_node(self, file) -> str:
        """创建代码文件节点"""
        vid = f"code_file_{file.id}"
        
        entity_data = {
            "vid": vid,
            "tag": "code_file",
            "properties": {
                "file_path": file.file_path,
                "file_name": file.file_name,
                "language": file.language or "",
                "mysql_id": file.id,
                "repository_id": file.repository_id,
                "knowledge_base_id": file.knowledge_base_id or 0,
                "content_hash": file.content_hash or "",
                "lines_of_code": file.lines_of_code or 0,
                "file_size": file.file_size or 0,
                "symbols_count": file.symbols_count,
                "imports_count": file.imports_count,
                "complexity_score": file.complexity_score or 0.0,
                "created_at": int(file.created_at.timestamp()) if file.created_at else 0,
                "updated_at": int(file.updated_at.timestamp()) if file.updated_at else 0
            }
        }
        
        await self.graph.create_entity(self.space, entity_data)
        return vid
    
    async def _create_symbol_node(self, symbol) -> str:
        """创建代码符号节点"""
        vid = f"code_symbol_{symbol.id}"
        
        entity_data = {
            "vid": vid,
            "tag": "code_symbol",
            "properties": {
                "symbol_name": symbol.symbol_name,
                "symbol_type": symbol.symbol_type,
                "qualified_name": symbol.qualified_name or "",
                "signature": symbol.signature or "",
                "mysql_id": symbol.id,
                "file_id": symbol.file_id,
                "repository_id": symbol.repository_id,
                "knowledge_base_id": symbol.knowledge_base_id or 0,
                "start_line": symbol.start_line or 0,
                "end_line": symbol.end_line or 0,
                "docstring": symbol.docstring or "",
                "return_type": symbol.return_type or "",
                "complexity_score": symbol.complexity_score or 0.0,
                "lines_count": symbol.lines_count or 0,
                "created_at": int(symbol.created_at.timestamp()) if symbol.created_at else 0,
                "updated_at": int(symbol.updated_at.timestamp()) if symbol.updated_at else 0
            }
        }
        
        await self.graph.create_entity(self.space, entity_data)
        return vid
    
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
        """创建包含关系"""
        rel_data = {
            "edge_type": "contains",
            "properties": {
                "container_type": container_type,
                "start_line": start_line or 0,
                "end_line": end_line or 0,
                "created_at": int(datetime.now().timestamp())
            }
        }
        await self.graph.create_relationship(
            self.space, 
            container_vid, 
            content_vid, 
            rel_data
        )
    
    async def _create_imports_edge(
        self, 
        source_vid: str, 
        target_vid: str,
        import_statement: str = "",
        line_number: Optional[int] = None
    ):
        """创建导入关系"""
        rel_data = {
            "edge_type": "imports",
            "properties": {
                "import_statement": import_statement,
                "line_number": line_number or 0,
                "import_type": "module",  # 默认为模块导入
                "created_at": int(datetime.now().timestamp())
            }
        }
        await self.graph.create_relationship(
            self.space,
            source_vid,
            target_vid,
            rel_data
        )
    
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
                logger.info(f"✓ 已删除仓库节点: {repo_vid}")
            except Exception as e:
                logger.warning(f"删除仓库节点失败: {e}")
            
            # 3. 批量删除该仓库的所有代码文件节点（使用批量删除优化性能）
            files = self.db.query(CodeFile).filter(
                CodeFile.repository_id == repository_id
            ).all()
            
            if files:
                logger.info(f"开始批量删除 {len(files)} 个文件节点")
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
            
            logger.info(f"✓ 已删除 {deleted_stats['file_nodes']} 个文件节点")
            
            # 4. 批量删除该仓库的所有代码符号节点（使用批量删除优化性能）
            symbols = self.db.query(CodeSymbol).filter(
                CodeSymbol.repository_id == repository_id
            ).all()
            
            if symbols:
                logger.info(f"开始批量删除 {len(symbols)} 个符号节点")
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
            
            logger.info(f"✓ 已删除 {deleted_stats['symbol_nodes']} 个符号节点")
            
            # 5. 统计（边会在删除节点时自动级联删除）
            deleted_stats["edges"] = "auto_deleted"  # NebulaGraph 会自动删除孤立的边
            
            logger.info(f"✓ 图数据库清理完成: repository_id={repository_id}, 统计={deleted_stats}")
            
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


def get_nebula_code_service(db: Session) -> NebulaCodeService:
    """获取 NebulaCode 服务实例"""
    return NebulaCodeService(db)
