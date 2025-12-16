"""
Knowledge Graph Service
知识图谱服务
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from datetime import datetime
import json
from collections import deque

from app.models.knowledge_graph import (
    KnowledgeGraphEntity,
    KnowledgeGraphRelationship,
    KnowledgeGraphEntityDocument,
    KnowledgeGraphExtractionTask,
)
from app.models.document import Document
from app.schemas.knowledge_graph import (
    EntityCreate,
    EntityUpdate,
    RelationshipCreate,
    RelationshipUpdate,
    PathQueryRequest,
    NeighborQueryRequest,
)
from app.core.exceptions import CustomException, ErrorCode
from app.core.logging import logger
from app.services.entity_extraction_service import EntityExtractionService
from app.services.permission_service import KnowledgeBasePermissionService
from app.services.graph_storage_service import get_graph_storage
from app.config.settings import settings


class KnowledgeGraphService:
    """知识图谱服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.extraction_service = EntityExtractionService(db)
        self.permission_service = KnowledgeBasePermissionService(db)
        self.graph_storage = get_graph_storage()  # 初始化图存储实例
    
    def _run_async(self, coro):
        """在同步上下文中运行异步代码的辅助方法"""
        import asyncio
        try:
            # 尝试获取当前运行的事件循环
            loop = asyncio.get_running_loop()
            # 如果有运行的事件循环，在新线程中运行
            import concurrent.futures
            
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()
        except RuntimeError:
            # 如果没有运行的事件循环，直接使用asyncio.run()
            return asyncio.run(coro)
    
    # ============================================
    # 实体相关方法
    # ============================================
    
    def create_entity(
        self, 
        kb_id: int, 
        entity_data: EntityCreate, 
        user_id: int
    ) -> KnowledgeGraphEntity:
        """创建实体"""
        # 检查权限
        self.permission_service.ensure_permission(kb_id, user_id, "kg:edit")
        
        # 检查是否已存在同名实体
        existing = self.db.query(KnowledgeGraphEntity).filter(
            and_(
                KnowledgeGraphEntity.knowledge_base_id == kb_id,
                KnowledgeGraphEntity.name == entity_data.name,
                KnowledgeGraphEntity.type == entity_data.type,
                KnowledgeGraphEntity.is_deleted == False
            )
        ).first()
        
        if existing:
            raise CustomException(
                ErrorCode.BAD_REQUEST,
                f"实体 '{entity_data.name}' (类型: {entity_data.type}) 已存在"
            )
        
        entity = KnowledgeGraphEntity(
            knowledge_base_id=kb_id,
            user_id=user_id,
            name=entity_data.name,
            type=entity_data.type,
            description=entity_data.description,
            aliases=entity_data.aliases,
            confidence=entity_data.confidence or settings.KG_ENTITY_DEFAULT_CONFIDENCE,
            extra_metadata=entity_data.metadata,
        )
        
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        
        # 同步到NebulaGraph（异步，不阻塞）
        try:
            import asyncio
            space = f"kb_{kb_id}"
            vid = self.entity_id_to_vid(entity.id)
            # 使用asyncio.run()在同步上下文中运行异步函数
            try:
                # 如果已有事件循环，使用create_task
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._sync_entity_to_nebula(space, entity, vid))
            except RuntimeError:
                # 如果没有事件循环，使用asyncio.run()
                asyncio.run(self._sync_entity_to_nebula(space, entity, vid))
        except Exception as e:
            logger.warning(f"同步实体到NebulaGraph失败（异步）: {e}, entity_id={entity.id}")
            entity.nebula_synced = False
            entity.nebula_sync_error = str(e)
            self.db.commit()
        
        return entity
    
    def update_entity(
        self, 
        entity_id: int, 
        entity_data: EntityUpdate, 
        user_id: int
    ) -> KnowledgeGraphEntity:
        """更新实体"""
        entity = self.db.query(KnowledgeGraphEntity).filter(
            KnowledgeGraphEntity.id == entity_id,
            KnowledgeGraphEntity.is_deleted == False
        ).first()
        
        if not entity:
            raise CustomException(ErrorCode.NOT_FOUND, "实体不存在")
        
        # 检查权限
        self.permission_service.ensure_permission(
            entity.knowledge_base_id, user_id, "kg:edit"
        )
        
        # 更新字段
        if entity_data.name is not None:
            entity.name = entity_data.name
        if entity_data.type is not None:
            entity.type = entity_data.type
        if entity_data.description is not None:
            entity.description = entity_data.description
        if entity_data.aliases is not None:
            entity.aliases = entity_data.aliases
        if entity_data.confidence is not None:
            entity.confidence = entity_data.confidence
        if entity_data.metadata is not None:
            entity.extra_metadata = entity_data.metadata
        
        self.db.commit()
        self.db.refresh(entity)
        
        # 同步到NebulaGraph（异步，不阻塞）
        try:
            import asyncio
            space = f"kb_{entity.knowledge_base_id}"
            vid = self.entity_id_to_vid(entity.id)
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._sync_entity_to_nebula(space, entity, vid))
            except RuntimeError:
                asyncio.run(self._sync_entity_to_nebula(space, entity, vid))
        except Exception as e:
            logger.warning(f"同步实体到NebulaGraph失败（异步）: {e}, entity_id={entity.id}")
        
        return entity
    
    def delete_entity(self, entity_id: int, user_id: int) -> bool:
        """删除实体（物理删除）"""
        entity = self.db.query(KnowledgeGraphEntity).filter(
            KnowledgeGraphEntity.id == entity_id,
            KnowledgeGraphEntity.is_deleted == False
        ).first()
        
        if not entity:
            raise CustomException(ErrorCode.NOT_FOUND, "实体不存在")
        
        # 检查权限
        self.permission_service.ensure_permission(
            entity.knowledge_base_id, user_id, "kg:delete"
        )
        
        kb_id = entity.knowledge_base_id
        vid = self.entity_id_to_vid(entity.id)
        
        # 先删除关联数据
        # 1. 删除实体-文档关联（物理删除）
        self.db.query(KnowledgeGraphEntityDocument).filter(
            KnowledgeGraphEntityDocument.entity_id == entity_id
        ).delete(synchronize_session=False)
        
        # 2. 删除相关关系（物理删除，只删除未删除的关系）
        self.db.query(KnowledgeGraphRelationship).filter(
            (KnowledgeGraphRelationship.source_entity_id == entity_id) |
            (KnowledgeGraphRelationship.target_entity_id == entity_id),
            KnowledgeGraphRelationship.is_deleted == False
        ).delete(synchronize_session=False)
        
        # 3. 删除实体（物理删除）
        self.db.delete(entity)
        self.db.commit()
        
        # 从NebulaGraph删除（异步，不阻塞）
        try:
            import asyncio
            space = f"kb_{kb_id}"
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self.graph_storage.delete_entity(space, vid))
            except RuntimeError:
                self._run_async(self.graph_storage.delete_entity(space, vid))
        except Exception as e:
            logger.warning(f"从NebulaGraph删除实体失败: {e}, entity_id={entity_id}")
        
        return True
    
    def get_entities(
        self, 
        kb_id: int, 
        filters: Dict[str, Any], 
        page: int = 1, 
        size: int = 20,
        user_id: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """获取实体列表（必须从NebulaGraph查询）"""
        # 检查权限
        if user_id:
            self.permission_service.ensure_permission(kb_id, user_id, "kg:view")
        
        # 必须使用NebulaGraph，不允许回退到MySQL
        if not settings.USE_NEBULA_GRAPH:
            raise CustomException(
                ErrorCode.INTERNAL_ERROR,
                "NebulaGraph未启用，无法查询实体。请启用NebulaGraph后再试。"
            )
        
        try:
            import asyncio
            space = f"kb_{kb_id}"
            nebula_result = self._run_async(self.graph_storage.list_entities(
                space=space,
                entity_type=filters.get("type"),
                keyword=filters.get("keyword"),
                page=page,
                size=size
            ))
            
            entities_list = nebula_result.get('entities', [])
            total = nebula_result.get('total', 0)
            
            # 添加相关文档数量统计（从MySQL查询索引信息）
            result = []
            for entity_data in entities_list:
                entity_id = entity_data.get('id')
                if entity_id:
                    doc_count = self.db.query(KnowledgeGraphEntityDocument).filter(
                        and_(
                            KnowledgeGraphEntityDocument.entity_id == entity_id,
                            KnowledgeGraphEntityDocument.is_deleted == False
                        )
                    ).count()
                else:
                    doc_count = 0
                
                entity_data['related_documents_count'] = doc_count
                result.append(entity_data)
            
            return result, total
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"从NebulaGraph查询实体失败: {e}")
            raise CustomException(
                ErrorCode.INTERNAL_ERROR,
                f"NebulaGraph查询失败: {str(e)}"
            )
    
    def get_entity_detail(
        self, 
        entity_id: int, 
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """获取实体详情（包含关系和文档）"""
        entity = self.db.query(KnowledgeGraphEntity).filter(
            KnowledgeGraphEntity.id == entity_id,
            KnowledgeGraphEntity.is_deleted == False
        ).first()
        
        if not entity:
            raise CustomException(ErrorCode.NOT_FOUND, "实体不存在")
        
        # 检查权限
        if user_id:
            self.permission_service.ensure_permission(
                entity.knowledge_base_id, user_id, "kg:view"
            )
        
        # 获取关系
        relationships = self.db.query(KnowledgeGraphRelationship).filter(
            and_(
                or_(
                    KnowledgeGraphRelationship.source_entity_id == entity_id,
                    KnowledgeGraphRelationship.target_entity_id == entity_id
                ),
                KnowledgeGraphRelationship.is_deleted == False
            )
        ).all()
        
        relationship_list = []
        for rel in relationships:
            target_entity = rel.target_entity if rel.source_entity_id == entity_id else rel.source_entity
            relationship_list.append({
                "id": rel.id,
                "target_entity": {
                    "id": target_entity.id,
                    "name": target_entity.name,
                    "type": target_entity.type,
                },
                "relation_type": rel.relation_type,
                "description": rel.description,
                "weight": rel.weight,
            })
        
        # 获取相关文档
        doc_mappings = self.db.query(KnowledgeGraphEntityDocument).filter(
            and_(
                KnowledgeGraphEntityDocument.entity_id == entity_id,
                KnowledgeGraphEntityDocument.is_deleted == False
            )
        ).all()
        
        related_documents = []
        for mapping in doc_mappings:
            doc = mapping.document
            related_documents.append({
                "document_id": doc.id,
                "title": doc.original_filename,  # 使用original_filename而不是title
                "mentions_count": mapping.mentions_count,
            })
        
        return {
            "entity": {
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "description": entity.description,
                "aliases": entity.aliases,
                "metadata": entity.extra_metadata,
                "confidence": entity.confidence,
            },
            "relationships": relationship_list,
            "related_documents": related_documents,
        }
    
    # ============================================
    # 关系相关方法
    # ============================================
    
    def create_relationship(
        self, 
        kb_id: int, 
        relationship_data: RelationshipCreate, 
        user_id: int
    ) -> KnowledgeGraphRelationship:
        """创建关系"""
        # 检查权限
        self.permission_service.ensure_permission(kb_id, user_id, "kg:edit")
        
        # 验证实体存在
        source_entity = self.db.query(KnowledgeGraphEntity).filter(
            KnowledgeGraphEntity.id == relationship_data.source_entity_id,
            KnowledgeGraphEntity.is_deleted == False
        ).first()
        
        target_entity = self.db.query(KnowledgeGraphEntity).filter(
            KnowledgeGraphEntity.id == relationship_data.target_entity_id,
            KnowledgeGraphEntity.is_deleted == False
        ).first()
        
        if not source_entity or not target_entity:
            raise CustomException(ErrorCode.NOT_FOUND, "源实体或目标实体不存在")
        
        if source_entity.knowledge_base_id != kb_id or target_entity.knowledge_base_id != kb_id:
            raise CustomException(ErrorCode.BAD_REQUEST, "实体不属于该知识库")
        
        # 检查是否已存在相同关系
        existing = self.db.query(KnowledgeGraphRelationship).filter(
            and_(
                KnowledgeGraphRelationship.source_entity_id == relationship_data.source_entity_id,
                KnowledgeGraphRelationship.target_entity_id == relationship_data.target_entity_id,
                KnowledgeGraphRelationship.relation_type == relationship_data.relation_type,
                KnowledgeGraphRelationship.is_deleted == False
            )
        ).first()
        
        if existing:
            raise CustomException(ErrorCode.BAD_REQUEST, "关系已存在")
        
        relationship = KnowledgeGraphRelationship(
            knowledge_base_id=kb_id,
            user_id=user_id,
            source_entity_id=relationship_data.source_entity_id,
            target_entity_id=relationship_data.target_entity_id,
            relation_type=relationship_data.relation_type,
            description=relationship_data.description,
            weight=relationship_data.weight or 0.5,
            confidence=relationship_data.confidence or settings.KG_RELATIONSHIP_DEFAULT_CONFIDENCE,
            extra_metadata=relationship_data.metadata,
        )
        
        self.db.add(relationship)
        self.db.commit()
        self.db.refresh(relationship)
        
        # 同步到NebulaGraph（异步，不阻塞）
        try:
            import asyncio
            space = f"kb_{kb_id}"
            source_vid = self.entity_id_to_vid(relationship.source_entity_id)
            target_vid = self.entity_id_to_vid(relationship.target_entity_id)
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._sync_relationship_to_nebula(space, relationship, source_vid, target_vid))
            except RuntimeError:
                asyncio.run(self._sync_relationship_to_nebula(space, relationship, source_vid, target_vid))
        except Exception as e:
            logger.warning(f"同步关系到NebulaGraph失败（异步）: {e}, relationship_id={relationship.id}")
        
        return relationship
    
    def get_relationships(
        self, 
        kb_id: int, 
        filters: Dict[str, Any], 
        page: int = 1, 
        size: int = 20,
        user_id: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """获取关系列表"""
        # 检查权限
        if user_id:
            self.permission_service.ensure_permission(kb_id, user_id, "kg:view")
        
        query = self.db.query(KnowledgeGraphRelationship).filter(
            and_(
                KnowledgeGraphRelationship.knowledge_base_id == kb_id,
                KnowledgeGraphRelationship.is_deleted == False
            )
        )
        
        # 应用筛选条件
        if filters.get("source_entity_id"):
            query = query.filter(
                KnowledgeGraphRelationship.source_entity_id == filters["source_entity_id"]
            )
        
        if filters.get("target_entity_id"):
            query = query.filter(
                KnowledgeGraphRelationship.target_entity_id == filters["target_entity_id"]
            )
        
        if filters.get("relation_type"):
            query = query.filter(
                KnowledgeGraphRelationship.relation_type == filters["relation_type"]
            )
        
        # 总数
        total = query.count()
        
        # 分页
        skip = (page - 1) * size
        relationships = query.order_by(desc(KnowledgeGraphRelationship.created_at)).offset(skip).limit(size).all()
        
        # 转换为字典
        result = []
        for rel in relationships:
            result.append({
                "id": rel.id,
                "source_entity_id": rel.source_entity_id,
                "target_entity_id": rel.target_entity_id,
                "source_entity": {
                    "id": rel.source_entity.id,
                    "name": rel.source_entity.name,
                    "type": rel.source_entity.type,
                },
                "target_entity": {
                    "id": rel.target_entity.id,
                    "name": rel.target_entity.name,
                    "type": rel.target_entity.type,
                },
                "relation_type": rel.relation_type,
                "description": rel.description,
                "weight": rel.weight,
                "confidence": rel.confidence,
            })
        
        return result, total
    
    # ============================================
    # 查询相关方法
    # ============================================
    
    def find_paths(
        self, 
        kb_id: int,
        source_entity_id: int, 
        target_entity_id: int, 
        max_hops: int = 3,
        relation_types: Optional[List[str]] = None,
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """查找两个实体间的路径（BFS算法）"""
        # 检查权限
        if user_id:
            self.permission_service.ensure_permission(kb_id, user_id, "kg:view")
        
        # TODO: 优先从NebulaGraph查询，如果失败则从MySQL查询
        # 这里先实现MySQL版本
        
        queue = deque([(source_entity_id, [source_entity_id], [])])
        visited = {(source_entity_id,): True}
        paths = []
        
        while queue:
            current_id, path, relationships = queue.popleft()
            
            if len(path) > max_hops + 1:
                continue
            
            if current_id == target_entity_id and len(path) > 1:
                paths.append({
                    "entities": path,
                    "relationships": relationships,
                    "path_length": len(path) - 1,
                    "total_weight": sum(r.get("weight", 1.0) for r in relationships)
                })
                continue
            
            # 获取当前实体的邻居
            neighbor_query = self.db.query(KnowledgeGraphRelationship).filter(
                and_(
                    KnowledgeGraphRelationship.source_entity_id == current_id,
                    KnowledgeGraphRelationship.is_deleted == False
                )
            )
            
            if relation_types:
                neighbor_query = neighbor_query.filter(
                    KnowledgeGraphRelationship.relation_type.in_(relation_types)
                )
            
            neighbors = neighbor_query.all()
            
            for neighbor_rel in neighbors:
                neighbor_id = neighbor_rel.target_entity_id
                
                # 避免循环
                if neighbor_id in path:
                    continue
                
                new_path = path + [neighbor_id]
                new_path_key = tuple(new_path)
                
                if new_path_key not in visited:
                    visited[new_path_key] = True
                    new_relationships = relationships + [{
                        "source": current_id,
                        "target": neighbor_id,
                        "type": neighbor_rel.relation_type,
                        "weight": neighbor_rel.weight,
                    }]
                    queue.append((neighbor_id, new_path, new_relationships))
        
        # 按路径长度和权重排序
        paths.sort(key=lambda x: (x["path_length"], -x["total_weight"]))
        return paths[:10]  # 返回前10条路径
    
    def get_entity_neighbors(
        self, 
        kb_id: int,
        entity_id: int, 
        relation_type: Optional[str] = None,
        max_depth: int = 1,
        limit: int = 50,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """获取实体邻居"""
        # 检查权限
        if user_id:
            self.permission_service.ensure_permission(kb_id, user_id, "kg:view")
        
        # TODO: 优先从NebulaGraph查询
        # 这里先实现MySQL版本（只支持1跳）
        
        query = self.db.query(KnowledgeGraphRelationship).filter(
            and_(
                KnowledgeGraphRelationship.source_entity_id == entity_id,
                KnowledgeGraphRelationship.is_deleted == False
            )
        )
        
        if relation_type:
            query = query.filter(KnowledgeGraphRelationship.relation_type == relation_type)
        
        relationships = query.limit(limit).all()
        
        neighbors = []
        for rel in relationships:
            target_entity = rel.target_entity
            neighbors.append({
                "entity_id": target_entity.id,
                "entity_name": target_entity.name,
                "entity_type": target_entity.type,
                "relationship": {
                    "id": rel.id,
                    "relation_type": rel.relation_type,
                    "description": rel.description,
                    "weight": rel.weight,
                }
            })
        
        return {
            "entity_id": entity_id,
            "neighbors": neighbors,
            "total": len(neighbors),
        }
    
    # ============================================
    # ID转换方法
    # ============================================
    
    def entity_id_to_vid(self, entity_id: int) -> str:
        """将MySQL实体ID转换为NebulaGraph VID"""
        return f"entity_{entity_id}"
    
    def vid_to_entity_id(self, vid: str) -> int:
        """将NebulaGraph VID转换为MySQL实体ID"""
        if vid.startswith("entity_"):
            return int(vid.replace("entity_", ""))
        raise ValueError(f"无效的VID格式: {vid}")
    
    def search_entities(
        self,
        query: str,
        kb_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        user_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """搜索实体（必须从NebulaGraph查询）"""
        if kb_id and user_id:
            self.permission_service.ensure_permission(kb_id, user_id, "kg:view")
        
        # 必须使用NebulaGraph，不允许回退到MySQL
        if not settings.USE_NEBULA_GRAPH:
            raise CustomException(
                ErrorCode.INTERNAL_ERROR,
                "NebulaGraph未启用，无法搜索实体。请启用NebulaGraph后再试。"
            )
        
        if not kb_id:
            raise CustomException(
                ErrorCode.BAD_REQUEST,
                "搜索实体需要指定知识库ID"
            )
        
        try:
            import asyncio
            space = f"kb_{kb_id}"
            # search_entities 内部已经会创建空间，不需要重复调用
            nebula_results = self._run_async(self.graph_storage.search_entities(
                space=space,
                keyword=query,
                entity_type=entity_type
            ))
            
            result = []
            for entity_data in nebula_results[:limit]:
                # 计算匹配得分
                name = entity_data.get('name', '')
                score = 1.0 if query.lower() in name.lower() else 0.8
                matched_field = "name" if query.lower() in name.lower() else "description"
                
                # 从MySQL获取ID（索引信息）
                mysql_id = entity_data.get('mysql_id', 0)
                if not mysql_id:
                    # 尝试从MySQL查找对应的实体ID（仅用于索引）
                    mysql_entity = self.db.query(KnowledgeGraphEntity).filter(
                        and_(
                            KnowledgeGraphEntity.knowledge_base_id == kb_id,
                            KnowledgeGraphEntity.name == name,
                            KnowledgeGraphEntity.is_deleted == False
                        )
                    ).first()
                    mysql_id = mysql_entity.id if mysql_entity else 0
                
                result.append({
                    "id": mysql_id,
                    "name": name,
                    "type": entity_data.get('type', ''),
                    "description": entity_data.get('description', ''),
                    "score": score,
                    "matched_field": matched_field,
                })
            
            # 按得分排序
            result.sort(key=lambda x: x["score"], reverse=True)
            return result
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"从NebulaGraph搜索实体失败: {e}")
            raise CustomException(
                ErrorCode.INTERNAL_ERROR,
                f"NebulaGraph搜索失败: {str(e)}"
            )
    
    def get_visualization_data(
        self,
        kb_id: int,
        entity_ids: Optional[List[int]] = None,
        relation_types: Optional[List[str]] = None,
        entity_type: Optional[str] = None,
        max_nodes: int = 100,
        layout: str = "force",
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """获取可视化数据（必须从NebulaGraph查询）"""
        if user_id:
            self.permission_service.ensure_permission(kb_id, user_id, "kg:view")
        
        # 必须使用NebulaGraph，不允许回退到MySQL
        if not settings.USE_NEBULA_GRAPH:
            raise CustomException(
                ErrorCode.INTERNAL_ERROR,
                "NebulaGraph未启用，无法获取可视化数据。请启用NebulaGraph后再试。"
            )
        
        try:
                import asyncio
                space = f"kb_{kb_id}"
                
                # 确保图空间存在（如果不存在则创建）
                self._run_async(self.graph_storage.create_space_if_not_exists(space))
                
                # 先查询MySQL中有效的实体ID列表（避免查询到无效数据）
                # 注意：清理孤立数据时需要查询所有实体，不受max_nodes限制
                query_all = self.db.query(KnowledgeGraphEntity.id).filter(
                    KnowledgeGraphEntity.knowledge_base_id == kb_id,
                    KnowledgeGraphEntity.is_deleted == False
                )
                
                # 用于清理孤立数据的完整实体ID列表（不受max_nodes限制）
                all_mysql_entity_ids = [row[0] for row in query_all.all()]
                mysql_entity_ids_set = set(all_mysql_entity_ids) if all_mysql_entity_ids else set()
                
                # 用于查询可视化的实体ID列表（受max_nodes限制）
                query = query_all
                if entity_type:
                    query = query.filter(KnowledgeGraphEntity.type == entity_type)
                
                if entity_ids:
                    query = query.filter(KnowledgeGraphEntity.id.in_(entity_ids))
                
                mysql_entity_ids = [row[0] for row in query.limit(max_nodes).all()]
                
                if not mysql_entity_ids:
                    logger.info(f"知识库 {kb_id} 中没有有效的实体，返回空结果")
                    return {
                        "nodes": [],
                        "edges": [],
                        "layout": layout
                    }
                
                logger.info(f"准备查询NebulaGraph实体: 知识库ID={kb_id}, MySQL中有效实体总数={len(all_mysql_entity_ids)}, 用于可视化的实体数量={len(mysql_entity_ids)}")
                
                # 步骤1：先查询NebulaGraph中所有实体，识别并清理孤立数据
                # 使用完整的实体ID列表进行清理判断
                
                # 查询NebulaGraph中所有实体
                query_all_entities_nGQL = """
                MATCH (n:entity)
                RETURN id(n) as vid, n.mysql_id as mysql_id, n.name as name
                LIMIT 10000;
                """
                logger.debug(f"[清理孤立数据] 查询所有实体的nGQL: {query_all_entities_nGQL}")
                all_entities = self._run_async(self.graph_storage._execute(query_all_entities_nGQL, space=space))
                logger.info(f"[清理孤立数据] NebulaGraph中实体总数: {len(all_entities)}")
                
                # 添加调试日志：查看前几个实体的原始数据
                if all_entities:
                    logger.debug(f"[清理孤立数据] 前3个实体的原始数据: {all_entities[:3]}")
                
                # 识别孤立实体（mysql_id不在有效列表中，或者mysql_id为0/NULL）
                orphaned_vids = []
                valid_vids = []
                
                # 添加调试日志：记录前几个实体的详细信息
                logger.debug(f"[清理孤立数据] MySQL有效实体ID集合（前10个）: {list(mysql_entity_ids_set)[:10]}")
                
                for entity in all_entities:
                    vid = str(entity.get('vid', '')).strip('"\'')
                    mysql_id_raw = entity.get('mysql_id', None)
                    
                    # 处理mysql_id（正确处理None、0、字符串等情况）
                    mysql_id = 0
                    if mysql_id_raw is not None:
                        if isinstance(mysql_id_raw, str):
                            mysql_id_str = mysql_id_raw.strip()
                            if mysql_id_str and mysql_id_str.upper() not in ('__NULL__', 'NULL', 'NONE', ''):
                                try:
                                    mysql_id = int(mysql_id_str)
                                except (ValueError, TypeError):
                                    mysql_id = 0
                        elif isinstance(mysql_id_raw, (int, float)):
                            mysql_id = int(mysql_id_raw)
                        elif mysql_id_raw == 0:
                            # 0 是有效值，但通常MySQL ID从1开始，所以0可能表示NULL
                            mysql_id = 0
                    
                    # 添加调试日志：记录前几个实体的匹配情况
                    if len(orphaned_vids) + len(valid_vids) < 5:
                        logger.debug(f"[清理孤立数据] 实体详情: vid={vid}, mysql_id_raw={mysql_id_raw} (type={type(mysql_id_raw)}), mysql_id={mysql_id}, 是否在集合中={mysql_id in mysql_entity_ids_set if mysql_id > 0 else False}")
                    
                    # 如果mysql_id为0或不在有效列表中，标记为孤立实体
                    if mysql_id == 0 or (mysql_entity_ids_set and mysql_id not in mysql_entity_ids_set):
                        orphaned_vids.append(vid)
                        if len(orphaned_vids) <= 5:  # 只记录前5个
                            logger.debug(f"[清理孤立数据] 发现孤立实体: vid={vid}, mysql_id={mysql_id}, name={entity.get('name', '')}, MySQL集合大小={len(mysql_entity_ids_set)}")
                    else:
                        valid_vids.append(vid)
                        if len(valid_vids) <= 5:  # 只记录前5个
                            logger.debug(f"[清理孤立数据] 有效实体: vid={vid}, mysql_id={mysql_id}, name={entity.get('name', '')}")
                
                # 安全检查：如果所有实体的mysql_id都是0，可能是数据问题，不应该删除
                all_mysql_ids_zero = all(
                    (entity.get('mysql_id', None) is None or 
                     entity.get('mysql_id', 0) == 0 or
                     (isinstance(entity.get('mysql_id'), str) and entity.get('mysql_id', '').strip() in ('', '0', '__NULL__', 'NULL', 'NONE')))
                    for entity in all_entities
                )
                
                if all_mysql_ids_zero and len(all_entities) > 0:
                    logger.error(f"[清理孤立数据] 警告：所有 {len(all_entities)} 个实体的mysql_id都是0或NULL，这可能是数据同步问题！跳过清理以避免误删数据。")
                    logger.error(f"[清理孤立数据] 请检查：1) 实体插入时是否正确设置了mysql_id；2) NebulaGraph中的mysql_id字段是否正确存储")
                elif orphaned_vids:
                    logger.warning(f"[清理孤立数据] 发现 {len(orphaned_vids)} 个孤立实体，开始自动清理")
                    deleted_count = 0
                    failed_count = 0
                    
                    for vid in orphaned_vids:
                        try:
                            self._run_async(self.graph_storage.delete_entity(space, vid))
                            deleted_count += 1
                            if deleted_count <= 5:  # 只记录前5个
                                logger.info(f"[清理孤立数据] 已删除孤立实体: vid={vid}")
                        except Exception as e:
                            failed_count += 1
                            logger.error(f"[清理孤立数据] 删除孤立实体失败: vid={vid}, 错误={e}")
                    
                    logger.info(f"[清理孤立数据] 清理完成: 成功删除={deleted_count}, 失败={failed_count}")
                
                # 步骤2：查询有效实体（只查询MySQL中存在的实体）
                if not mysql_entity_ids:
                    logger.info(f"MySQL中没有有效实体，返回空结果")
                    return {
                        "nodes": [],
                        "edges": [],
                        "layout": layout
                    }
                
                # 构建VID列表用于查询（VID格式：entity_{mysql_id}）
                vid_list = [f"entity_{eid}" for eid in mysql_entity_ids[:max_nodes]]  # 限制数量避免查询过长
                vid_quoted = [f"'{vid}'" for vid in vid_list]
                vid_list_str = ', '.join(vid_quoted)
                
                # 构建实体筛选条件
                entity_filter = [f"id(n) IN [{vid_list_str}]"]
                
                if entity_type:
                    entity_filter.append(f"n.type == '{entity_type}'")
                
                where_clause = "WHERE " + " AND ".join(entity_filter) if entity_filter else ""
                
                # 查询实体节点（使用FETCH PROP批量查询，因为MATCH查询字段返回NULL）
                # 注意：NebulaGraph的MATCH查询可能无法正确返回Tag属性，改用FETCH PROP批量查询
                entity_results = []
                
                # 将VID列表分批处理（每批最多50个，避免查询过长）
                batch_size = 50
                for i in range(0, len(vid_list), batch_size):
                    batch_vids = vid_list[i:i+batch_size]
                    vid_quoted_batch = [f'"{vid}"' for vid in batch_vids]
                    vid_str_batch = ', '.join(vid_quoted_batch)
                    
                    # 使用FETCH PROP批量查询
                    fetch_nGQL = f'FETCH PROP ON entity {vid_str_batch} YIELD id(vertex) as vid, properties(vertex) as props;'
                    logger.debug(f"实体批量查询nGQL (批次{i//batch_size + 1}, {len(batch_vids)}个实体): {fetch_nGQL[:200]}...")
                    
                    batch_results = self._run_async(self.graph_storage._execute(fetch_nGQL, space=space))
                    
                    # 解析FETCH PROP返回的Map结构
                    for row in batch_results:
                        vid = row.get('vid', '')
                        props = row.get('props', {})
                        
                        # props是Map，已经自动转换为字典
                        if isinstance(props, dict):
                            entity_results.append({
                                'vid': vid,
                                'name': props.get('name', ''),
                                'type': props.get('type', ''),
                                'description': props.get('description', ''),
                                'mysql_id': props.get('mysql_id', 0),
                                'confidence': props.get('confidence', settings.KG_ENTITY_DEFAULT_CONFIDENCE),
                                'aliases': props.get('aliases', '[]'),
                                'metadata': props.get('metadata', '{}'),
                                'user_id': props.get('user_id', 0),
                                'created_at': props.get('created_at', 0),
                                'updated_at': props.get('updated_at', 0),
                            })
                        else:
                            logger.warning(f"[警告] props不是字典类型: type={type(props)}, value={props}")
                
                logger.debug(f"实体查询nGQL (使用FETCH PROP批量查询, {len(vid_list)}个VID, 分{(len(vid_list)-1)//batch_size + 1}批)")
                logger.info(f"实体查询完成: 从NebulaGraph查询到 {len(entity_results)} 个实体（MySQL中有效实体数量: {len(mysql_entity_ids)}）")
                logger.info(f"从NebulaGraph查询到 {len(entity_results)} 个有效实体（MySQL中有效实体数量: {len(mysql_entity_ids)}）")
                
                # 添加调试日志：查看前3个实体的原始返回数据
                if entity_results:
                    logger.debug(f"[调试] 前3个实体的原始返回数据: {entity_results[:3]}")
                    logger.debug(f"[调试] 第一个实体的所有字段: {list(entity_results[0].keys()) if entity_results else []}")
                    if entity_results:
                        first_entity = entity_results[0]
                        logger.debug(f"[调试] 第一个实体详情: vid={first_entity.get('vid')}, name={repr(first_entity.get('name'))}, type={repr(first_entity.get('type'))}, mysql_id={repr(first_entity.get('mysql_id'))}")
                
                # 如果指定了entity_ids，过滤结果
                if entity_ids:
                    entity_id_set_filter = set(entity_ids)
                    entity_results = [e for e in entity_results if e.get('mysql_id', 0) in entity_id_set_filter]
                
                # 构建节点列表
                nodes = []
                entity_id_set = set()
                vid_to_id_map = {}
                skipped_entity_count = 0  # 统计跳过的无效实体数量
                
                logger.debug(f"开始处理 {len(entity_results)} 个实体查询结果")
                
                for entity_data in entity_results:
                    entity_id_raw = entity_data.get('mysql_id', 0)
                    vid = entity_data.get('vid')
                    name_raw = entity_data.get('name', '')
                    entity_type_raw = entity_data.get('type', '')
                    
                    # 处理 NULL 值：如果值是 '__NULL__' 字符串，转换为空值
                    entity_id = 0
                    if entity_id_raw:
                        if isinstance(entity_id_raw, str):
                            if entity_id_raw.upper() not in ('__NULL__', 'NULL', 'NONE', ''):
                                try:
                                    entity_id = int(entity_id_raw)
                                except (ValueError, TypeError):
                                    entity_id = 0
                        elif isinstance(entity_id_raw, (int, float)):
                            entity_id = int(entity_id_raw)
                    
                    # 如果mysql_id是0或NULL，尝试从VID提取（VID格式：entity_{mysql_id}）
                    vid_str = str(vid).strip('"\'') if vid else ''
                    if entity_id == 0 and vid_str.startswith('entity_'):
                        try:
                            entity_id = int(vid_str.replace('entity_', ''))
                            logger.debug(f"从VID提取entity_id: vid={vid_str}, entity_id={entity_id}")
                        except (ValueError, TypeError):
                            pass
                    
                    name = ''
                    if name_raw:
                        if isinstance(name_raw, str) and name_raw.upper() not in ('__NULL__', 'NULL', 'NONE', ''):
                            name = name_raw.strip()
                    
                    entity_type = ''
                    if entity_type_raw:
                        if isinstance(entity_type_raw, str) and entity_type_raw.upper() not in ('__NULL__', 'NULL', 'NONE', ''):
                            entity_type = entity_type_raw.strip()
                    
                    # 调试：记录前3个实体的原始数据和处理后数据
                    if len(vid_to_id_map) < 3:
                        logger.info("实体数据: 原始 entity_id=%s, name=%s, type=%s => 处理后 entity_id=%s, name=%s, type=%s", 
                                  entity_id_raw, name_raw, entity_type_raw, entity_id, name, entity_type)
                    
                    # 确保 entity_id 有效且 name 不为空
                    if entity_id and entity_id != 0 and name:
                        entity_id_set.add(entity_id)
                        # 确保VID是字符串，并去除可能的引号
                        vid_str = str(vid).strip('"\'') if vid else ''
                        if vid_str:
                            vid_to_id_map[vid_str] = entity_id
                        
                        # 统计关联文档数量（从MySQL查询）
                        doc_count = self.db.query(KnowledgeGraphEntityDocument).filter(
                            and_(
                                KnowledgeGraphEntityDocument.entity_id == entity_id,
                                KnowledgeGraphEntityDocument.is_deleted == False
                            )
                        ).count()
                        
                        nodes.append({
                            "id": entity_id,
                            "label": name.strip(),
                            "type": entity_type.strip() if entity_type else 'other',
                            "group": entity_type.strip() if entity_type else 'other',
                            "value": max(5, min(50, doc_count)),
                            "title": entity_data.get('description', '').strip() or name.strip(),
                        })
                    else:
                        # 记录跳过的无效实体（只记录前几个，避免日志过多）
                        skipped_entity_count += 1
                        if skipped_entity_count <= 3:
                            logger.warning("跳过无效实体[%d/%d]: entity_id=%s, name=%s", skipped_entity_count, len(entity_results), entity_id, name)
                        elif skipped_entity_count == 4:
                            logger.warning("跳过无效实体数量较多，后续不再详细记录（当前已跳过 %d 个）", skipped_entity_count)
                
                # 记录实体处理结果
                logger.info(f"实体处理完成: 查询到={len(entity_results)}, 有效={len(nodes)}, 跳过无效={skipped_entity_count}, vid映射数量={len(vid_to_id_map)}")
                
                # 查询关系边
                if vid_to_id_map:
                    # NebulaGraph的id()函数返回VID字符串，在IN子句中需要使用引号包裹
                    # 根据NebulaGraph文档，IN子句中的字符串应该使用单引号: WHERE id(v) IN ['vid1', 'vid2']
                    vid_keys = list(vid_to_id_map.keys())
                    # 确保VID是字符串格式，去除可能的引号，然后重新用单引号包裹
                    vid_quoted = []
                    for vid in vid_keys:
                        # 去除可能的引号，确保VID是纯字符串
                        vid_clean = str(vid).strip('"\'')
                        # 使用单引号包裹VID
                        vid_quoted.append("'" + vid_clean + "'")
                    vid_list_str = ', '.join(vid_quoted)
                    # 构建WHERE条件：WHERE id(v1) IN ['vid1', 'vid2'] AND id(v2) IN ['vid1', 'vid2']
                    rel_filter = 'WHERE id(v1) IN [' + vid_list_str + '] AND id(v2) IN [' + vid_list_str + ']'
                    
                    # 调试：记录VID列表构建过程
                    logger.debug("VID列表构建: vid_keys数量=%d, vid_list_str前100字符=%s", len(vid_keys), vid_list_str[:100] if len(vid_list_str) > 100 else vid_list_str)
                else:
                    rel_filter = ""
                
                if relation_types:
                    rel_type_list = ', '.join([f"'{rt}'" for rt in relation_types])
                    if rel_filter:
                        rel_filter += f" AND e.relation_type IN [{rel_type_list}]"
                    else:
                        rel_filter = f"WHERE e.relation_type IN [{rel_type_list}]"
                
                # 使用字符串拼接构建完整查询，避免f-string转义问题
                rel_nGQL = 'MATCH (v1:entity)-[e:relationship]->(v2:entity) ' + rel_filter + ' RETURN id(v1) as source_vid, id(v2) as target_vid, e.relation_type as relation_type, e.description as description, e.weight as weight LIMIT ' + str(max_nodes * 2) + ';'
                
                # 调试：记录实际生成的nGQL（直接显示和repr格式）
                logger.info("生成的nGQL查询（直接显示，前300字符）: %s", rel_nGQL[:300])
                logger.info("生成的nGQL查询（repr格式，前300字符）: %s", repr(rel_nGQL[:300]))
                
                # 在同步上下文中运行异步代码
                rel_results = self._run_async(self.graph_storage._execute(rel_nGQL, space=space))
                
                # 调试：记录查询结果
                logger.info("关系查询结果数量: %d", len(rel_results))
                if rel_results:
                    logger.debug("关系查询结果示例（前3条）: %s", rel_results[:3])
                    # 详细记录前3条的 VID 格式
                    for i, rel_data in enumerate(rel_results[:3]):
                        logger.info("关系 %d: source_vid=%s (type=%s, repr=%s), target_vid=%s (type=%s, repr=%s)", 
                                  i+1, 
                                  rel_data.get('source_vid'), type(rel_data.get('source_vid')), repr(rel_data.get('source_vid')),
                                  rel_data.get('target_vid'), type(rel_data.get('target_vid')), repr(rel_data.get('target_vid')))
                
                # 构建边列表
                edges = []
                matched_count = 0
                unmatched_count = 0
                for rel_data in rel_results:
                    source_vid = rel_data.get('source_vid')
                    target_vid = rel_data.get('target_vid')
                    
                    # 确保VID格式一致：去除可能的引号
                    source_vid_clean = str(source_vid).strip('"\'')
                    target_vid_clean = str(target_vid).strip('"\'')
                    
                    source_id = vid_to_id_map.get(source_vid_clean)
                    target_id = vid_to_id_map.get(target_vid_clean)
                    
                    # 调试：记录前几条的匹配情况
                    if unmatched_count < 5 and (not source_id or not target_id):
                        logger.info("关系VID匹配失败: source_vid=%s (clean=%s, found=%s), target_vid=%s (clean=%s, found=%s)", 
                                   source_vid, source_vid_clean, source_id is not None,
                                   target_vid, target_vid_clean, target_id is not None)
                        if unmatched_count == 0:
                            logger.info("vid_to_id_map keys sample (前10个): %s", list(vid_to_id_map.keys())[:10])
                        unmatched_count += 1
                    
                    if source_id and target_id and source_id in entity_id_set and target_id in entity_id_set:
                        edges.append({
                            "from": source_id,
                            "to": target_id,
                            "label": rel_data.get('relation_type', ''),
                            "value": float(rel_data.get('weight', 0.5)),
                            "title": rel_data.get('description') or rel_data.get('relation_type', ''),
                        })
                        matched_count += 1
                
                # 调试：记录匹配统计
                logger.info("关系匹配统计: 总数=%d, 匹配成功=%d, 匹配失败=%d", len(rel_results), matched_count, len(rel_results) - matched_count)
                
                # 如果发现大量匹配失败的关系，说明NebulaGraph中有孤立数据，记录警告
                if len(rel_results) > 0 and matched_count == 0 and len(vid_to_id_map) > 0:
                    logger.warning(f"检测到NebulaGraph中存在孤立的关系数据（MySQL中对应的实体不存在）: "
                                 f"关系总数={len(rel_results)}, 匹配成功=0, 有效实体VID数量={len(vid_to_id_map)}")
                    logger.warning("建议运行清理功能，删除NebulaGraph中的孤立数据")
                elif len(rel_results) > 0 and matched_count < len(rel_results) * 0.5:
                    # 如果匹配成功率低于50%，也记录警告
                    logger.warning(f"关系匹配成功率较低: 总数={len(rel_results)}, 匹配成功={matched_count}, "
                                 f"成功率={matched_count/len(rel_results)*100:.1f}%")
                    logger.warning("可能存在NebulaGraph中的孤立关系数据，建议运行清理功能")
                
                result = {
                    "nodes": nodes,
                    "edges": edges,
                    "layout": layout,
                }
                
                # 调试：记录返回结果
                logger.info("可视化数据返回: nodes数量=%d, edges数量=%d", len(nodes), len(edges))
                
                return result
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"从NebulaGraph查询可视化数据失败: {e}")
            raise CustomException(
                ErrorCode.INTERNAL_ERROR,
                f"NebulaGraph查询失败: {str(e)}"
            )
    
    def get_graph_stats(self, kb_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """获取知识图谱统计信息"""
        if user_id:
            self.permission_service.ensure_permission(kb_id, user_id, "kg:view")
        
        # 实体统计
        entities = self.db.query(KnowledgeGraphEntity).filter(
            and_(
                KnowledgeGraphEntity.knowledge_base_id == kb_id,
                KnowledgeGraphEntity.is_deleted == False
            )
        ).all()
        
        total_entities = len(entities)
        entity_type_distribution = {}
        for entity in entities:
            entity_type_distribution[entity.type] = entity_type_distribution.get(entity.type, 0) + 1
        
        # 关系统计
        relationships = self.db.query(KnowledgeGraphRelationship).filter(
            and_(
                KnowledgeGraphRelationship.knowledge_base_id == kb_id,
                KnowledgeGraphRelationship.is_deleted == False
            )
        ).all()
        
        total_relationships = len(relationships)
        relation_type_distribution = {}
        for rel in relationships:
            relation_type_distribution[rel.relation_type] = relation_type_distribution.get(rel.relation_type, 0) + 1
        
        # 计算图谱密度（实际边数 / 最大可能边数）
        max_possible_edges = total_entities * (total_entities - 1) if total_entities > 1 else 0
        graph_density = total_relationships / max_possible_edges if max_possible_edges > 0 else 0.0
        
        # 计算平均度数
        degree_sum = 0
        entity_degree = {}
        for rel in relationships:
            entity_degree[rel.source_entity_id] = entity_degree.get(rel.source_entity_id, 0) + 1
            entity_degree[rel.target_entity_id] = entity_degree.get(rel.target_entity_id, 0) + 1
        
        if entity_degree:
            degree_sum = sum(entity_degree.values())
            average_degree = degree_sum / len(entity_degree)
        else:
            average_degree = 0.0
        
        # 计算最大连通分量大小（简化实现：使用BFS）
        largest_component_size = self._calculate_largest_component_size(kb_id)
        
        return {
            "total_entities": total_entities,
            "total_relationships": total_relationships,
            "entity_type_distribution": entity_type_distribution,
            "relation_type_distribution": relation_type_distribution,
            "graph_density": round(graph_density, 4),
            "average_degree": round(average_degree, 2),
            "largest_component_size": largest_component_size,
        }
    
    def _calculate_largest_component_size(self, kb_id: int) -> int:
        """计算最大连通分量大小（使用BFS）"""
        # 获取所有实体
        entities = self.db.query(KnowledgeGraphEntity).filter(
            and_(
                KnowledgeGraphEntity.knowledge_base_id == kb_id,
                KnowledgeGraphEntity.is_deleted == False
            )
        ).all()
        
        if not entities:
            return 0
        
        entity_ids = [e.id for e in entities]
        
        # 构建邻接表
        adjacency = {eid: [] for eid in entity_ids}
        relationships = self.db.query(KnowledgeGraphRelationship).filter(
            and_(
                KnowledgeGraphRelationship.knowledge_base_id == kb_id,
                KnowledgeGraphRelationship.is_deleted == False
            )
        ).all()
        
        for rel in relationships:
            if rel.source_entity_id in adjacency and rel.target_entity_id in adjacency:
                adjacency[rel.source_entity_id].append(rel.target_entity_id)
                adjacency[rel.target_entity_id].append(rel.source_entity_id)
        
        # BFS查找最大连通分量
        visited = set()
        max_size = 0
        
        for start_id in entity_ids:
            if start_id in visited:
                continue
            
            queue = deque([start_id])
            component = set()
            
            while queue:
                current = queue.popleft()
                if current in visited:
                    continue
                
                visited.add(current)
                component.add(current)
                
                for neighbor in adjacency.get(current, []):
                    if neighbor not in visited:
                        queue.append(neighbor)
            
            max_size = max(max_size, len(component))
        
        return max_size
    
    def update_relationship(
        self,
        relationship_id: int,
        relationship_data: RelationshipUpdate,
        user_id: int
    ) -> KnowledgeGraphRelationship:
        """更新关系"""
        relationship = self.db.query(KnowledgeGraphRelationship).filter(
            KnowledgeGraphRelationship.id == relationship_id,
            KnowledgeGraphRelationship.is_deleted == False
        ).first()
        
        if not relationship:
            raise CustomException(ErrorCode.NOT_FOUND, "关系不存在")
        
        # 检查权限
        self.permission_service.ensure_permission(
            relationship.knowledge_base_id, user_id, "kg:edit"
        )
        
        # 更新字段
        if relationship_data.relation_type is not None:
            relationship.relation_type = relationship_data.relation_type
        if relationship_data.description is not None:
            relationship.description = relationship_data.description
        if relationship_data.weight is not None:
            relationship.weight = relationship_data.weight
        if relationship_data.confidence is not None:
            relationship.confidence = relationship_data.confidence
        if relationship_data.metadata is not None:
            relationship.extra_metadata = relationship_data.metadata
        
        self.db.commit()
        self.db.refresh(relationship)
        
        # 同步到NebulaGraph（需要先删除旧关系，再创建新关系）
        try:
            import asyncio
            space = f"kb_{relationship.knowledge_base_id}"
            source_vid = self.entity_id_to_vid(relationship.source_entity_id)
            target_vid = self.entity_id_to_vid(relationship.target_entity_id)
            
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._update_relationship_in_nebula(space, relationship, source_vid, target_vid))
            except RuntimeError:
                asyncio.run(self._update_relationship_in_nebula(space, relationship, source_vid, target_vid))
        except Exception as e:
            logger.warning(f"同步关系到NebulaGraph失败（异步）: {e}, relationship_id={relationship.id}")
        
        return relationship
    
    async def _update_relationship_in_nebula(
        self, space: str, relationship: KnowledgeGraphRelationship,
        source_vid: str, target_vid: str
    ):
        """更新NebulaGraph中的关系（先删除再创建）"""
        try:
            # 删除旧关系
            await self.graph_storage.delete_relationship(space, source_vid, target_vid)
            # 创建新关系
            await self._sync_relationship_to_nebula(space, relationship, source_vid, target_vid)
        except Exception as e:
            logger.error(f"更新NebulaGraph关系失败: {e}, relationship_id={relationship.id}")
    
    def delete_relationship(self, relationship_id: int, user_id: int) -> bool:
        """删除关系（物理删除）"""
        relationship = self.db.query(KnowledgeGraphRelationship).filter(
            KnowledgeGraphRelationship.id == relationship_id,
            KnowledgeGraphRelationship.is_deleted == False
        ).first()
        
        if not relationship:
            raise CustomException(ErrorCode.NOT_FOUND, "关系不存在")
        
        # 检查权限
        self.permission_service.ensure_permission(
            relationship.knowledge_base_id, user_id, "kg:delete"
        )
        
        kb_id = relationship.knowledge_base_id
        source_vid = self.entity_id_to_vid(relationship.source_entity_id)
        target_vid = self.entity_id_to_vid(relationship.target_entity_id)
        
        # 物理删除关系
        self.db.delete(relationship)
        self.db.commit()
        
        # 从NebulaGraph删除（异步，不阻塞）
        try:
            import asyncio
            space = f"kb_{kb_id}"
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self.graph_storage.delete_relationship(space, source_vid, target_vid))
            except RuntimeError:
                self._run_async(self.graph_storage.delete_relationship(space, source_vid, target_vid))
        except Exception as e:
            logger.warning(f"从NebulaGraph删除关系失败: {e}, relationship_id={relationship_id}")
        
        return True
    
    def get_relationship_detail(
        self,
        relationship_id: int,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """获取关系详情"""
        relationship = self.db.query(KnowledgeGraphRelationship).filter(
            KnowledgeGraphRelationship.id == relationship_id,
            KnowledgeGraphRelationship.is_deleted == False
        ).first()
        
        if not relationship:
            raise CustomException(ErrorCode.NOT_FOUND, "关系不存在")
        
        if user_id:
            self.permission_service.ensure_permission(
                relationship.knowledge_base_id, user_id, "kg:view"
            )
        
        return {
            "id": relationship.id,
            "source_entity": {
                "id": relationship.source_entity.id,
                "name": relationship.source_entity.name,
                "type": relationship.source_entity.type,
            },
            "target_entity": {
                "id": relationship.target_entity.id,
                "name": relationship.target_entity.name,
                "type": relationship.target_entity.type,
            },
            "relation_type": relationship.relation_type,
            "description": relationship.description,
            "weight": relationship.weight,
            "confidence": relationship.confidence,
            "metadata": relationship.extra_metadata,
            "created_at": relationship.created_at,
            "updated_at": relationship.updated_at,
        }
    
    # ============================================
    # NebulaGraph同步辅助方法
    # ============================================
    
    async def _sync_entity_to_nebula(
        self, space: str, entity: KnowledgeGraphEntity, vid: str
    ):
        """同步实体到NebulaGraph"""
        try:
            await self.graph_storage.create_entity(space, {
                "name": entity.name,
                "type": entity.type,
                "description": entity.description or "",
                "aliases": entity.aliases or [],
                "confidence": entity.confidence,
                "metadata": entity.extra_metadata or {},
                "mysql_id": entity.id,
                "user_id": entity.user_id,
                "id": vid
            })
            # 更新同步状态
            entity.nebula_synced = True
            entity.nebula_synced_at = datetime.now()
            entity.nebula_sync_error = None
            self.db.commit()
        except Exception as e:
            logger.error(f"同步实体到NebulaGraph失败: {e}, entity_id={entity.id}")
            entity.nebula_synced = False
            entity.nebula_sync_error = str(e)
            self.db.commit()
            raise
    
    async def _sync_relationship_to_nebula(
        self, space: str, relationship: KnowledgeGraphRelationship,
        source_vid: str, target_vid: str
    ):
        """同步关系到NebulaGraph"""
        try:
            await self.graph_storage.create_relationship(space, source_vid, target_vid, {
                "relation_type": relationship.relation_type,
                "description": relationship.description or "",
                "weight": relationship.weight,
                "confidence": relationship.confidence,
                "metadata": relationship.extra_metadata or {},
                "mysql_id": relationship.id,
                "user_id": relationship.user_id
            })
            # 更新同步状态
            relationship.nebula_synced = True
            relationship.nebula_synced_at = datetime.now()
            relationship.nebula_sync_error = None
            self.db.commit()
        except Exception as e:
            logger.error(f"同步关系到NebulaGraph失败: {e}, relationship_id={relationship.id}")
            relationship.nebula_synced = False
            relationship.nebula_sync_error = str(e)
            self.db.commit()
            raise

