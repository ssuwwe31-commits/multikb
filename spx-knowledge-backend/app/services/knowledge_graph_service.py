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


class KnowledgeGraphService:
    """知识图谱服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.extraction_service = EntityExtractionService(db)
        self.permission_service = KnowledgeBasePermissionService(db)
        self.graph_storage = get_graph_storage()  # 初始化图存储实例
    
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
            confidence=entity_data.confidence or 0.7,
            metadata=entity_data.metadata,
        )
        
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        
        # 同步到NebulaGraph（异步，不阻塞）
        try:
            import asyncio
            space = f"kb_{kb_id}"
            vid = self.entity_id_to_vid(entity.id)
            # 在同步方法中运行异步函数
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行，创建任务
                asyncio.create_task(self._sync_entity_to_nebula(space, entity, vid))
            else:
                loop.run_until_complete(self._sync_entity_to_nebula(space, entity, vid))
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
            entity.metadata = entity_data.metadata
        
        self.db.commit()
        self.db.refresh(entity)
        
        # 同步到NebulaGraph（异步，不阻塞）
        try:
            import asyncio
            space = f"kb_{entity.knowledge_base_id}"
            vid = self.entity_id_to_vid(entity.id)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._sync_entity_to_nebula(space, entity, vid))
            else:
                loop.run_until_complete(self._sync_entity_to_nebula(space, entity, vid))
        except Exception as e:
            logger.warning(f"同步实体到NebulaGraph失败（异步）: {e}, entity_id={entity.id}")
        
        return entity
    
    def delete_entity(self, entity_id: int, user_id: int) -> bool:
        """删除实体（逻辑删除）"""
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
        
        entity.is_deleted = True
        self.db.commit()
        
        # 从NebulaGraph删除（异步，不阻塞）
        try:
            import asyncio
            space = f"kb_{entity.knowledge_base_id}"
            vid = self.entity_id_to_vid(entity.id)
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self.graph_storage.delete_entity(space, vid))
            except RuntimeError:
                asyncio.run(self.graph_storage.delete_entity(space, vid))
        except Exception as e:
            logger.warning(f"从NebulaGraph删除实体失败: {e}, entity_id={entity.id}")
        
        return True
    
    def get_entities(
        self, 
        kb_id: int, 
        filters: Dict[str, Any], 
        page: int = 1, 
        size: int = 20,
        user_id: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """获取实体列表"""
        # 检查权限
        if user_id:
            self.permission_service.ensure_permission(kb_id, user_id, "kg:view")
        
        query = self.db.query(KnowledgeGraphEntity).filter(
            and_(
                KnowledgeGraphEntity.knowledge_base_id == kb_id,
                KnowledgeGraphEntity.is_deleted == False
            )
        )
        
        # 应用筛选条件
        if filters.get("type"):
            query = query.filter(KnowledgeGraphEntity.type == filters["type"])
        
        if filters.get("keyword"):
            keyword = f"%{filters['keyword']}%"
            query = query.filter(
                or_(
                    KnowledgeGraphEntity.name.like(keyword),
                    KnowledgeGraphEntity.description.like(keyword)
                )
            )
        
        # 总数
        total = query.count()
        
        # 分页
        skip = (page - 1) * size
        entities = query.order_by(desc(KnowledgeGraphEntity.created_at)).offset(skip).limit(size).all()
        
        # 转换为字典并添加统计信息
        result = []
        for entity in entities:
            # 统计相关文档数量
            doc_count = self.db.query(KnowledgeGraphEntityDocument).filter(
                and_(
                    KnowledgeGraphEntityDocument.entity_id == entity.id,
                    KnowledgeGraphEntityDocument.is_deleted == False
                )
            ).count()
            
            # 统计相关实体数量
            entity_count = self.db.query(KnowledgeGraphRelationship).filter(
                and_(
                    or_(
                        KnowledgeGraphRelationship.source_entity_id == entity.id,
                        KnowledgeGraphRelationship.target_entity_id == entity.id
                    ),
                    KnowledgeGraphRelationship.is_deleted == False
                )
            ).count()
            
            result.append({
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "description": entity.description,
                "aliases": entity.aliases,
                "confidence": entity.confidence,
                "related_documents_count": doc_count,
                "related_entities_count": entity_count,
            })
        
        return result, total
    
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
                "title": doc.title,
                "mentions_count": mapping.mentions_count,
            })
        
        return {
            "entity": {
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "description": entity.description,
                "aliases": entity.aliases,
                "metadata": entity.metadata,
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
            confidence=relationship_data.confidence or 0.7,
            metadata=relationship_data.metadata,
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
        """搜索实体（模糊匹配）"""
        if kb_id and user_id:
            self.permission_service.ensure_permission(kb_id, user_id, "kg:view")
        
        db_query = self.db.query(KnowledgeGraphEntity).filter(
            KnowledgeGraphEntity.is_deleted == False
        )
        
        if kb_id:
            db_query = db_query.filter(KnowledgeGraphEntity.knowledge_base_id == kb_id)
        
        if entity_type:
            db_query = db_query.filter(KnowledgeGraphEntity.type == entity_type)
        
        # 模糊匹配名称或描述
        keyword = f"%{query}%"
        db_query = db_query.filter(
            or_(
                KnowledgeGraphEntity.name.like(keyword),
                KnowledgeGraphEntity.description.like(keyword)
            )
        )
        
        entities = db_query.limit(limit).all()
        
        result = []
        for entity in entities:
            # 计算匹配得分（简单实现：名称完全匹配得分最高）
            score = 1.0 if query.lower() in entity.name.lower() else 0.8
            matched_field = "name" if query.lower() in entity.name.lower() else "description"
            
            result.append({
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "description": entity.description,
                "score": score,
                "matched_field": matched_field,
            })
        
        # 按得分排序
        result.sort(key=lambda x: x["score"], reverse=True)
        return result
    
    def get_visualization_data(
        self,
        kb_id: int,
        entity_ids: Optional[List[int]] = None,
        relation_types: Optional[List[str]] = None,
        max_nodes: int = 100,
        layout: str = "force",
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """获取可视化数据"""
        if user_id:
            self.permission_service.ensure_permission(kb_id, user_id, "kg:view")
        
        # 获取节点
        query = self.db.query(KnowledgeGraphEntity).filter(
            and_(
                KnowledgeGraphEntity.knowledge_base_id == kb_id,
                KnowledgeGraphEntity.is_deleted == False
            )
        )
        
        if entity_ids:
            query = query.filter(KnowledgeGraphEntity.id.in_(entity_ids))
        
        entities = query.limit(max_nodes).all()
        
        # 获取边
        rel_query = self.db.query(KnowledgeGraphRelationship).filter(
            and_(
                KnowledgeGraphRelationship.knowledge_base_id == kb_id,
                KnowledgeGraphRelationship.is_deleted == False
            )
        )
        
        if entity_ids:
            rel_query = rel_query.filter(
                or_(
                    KnowledgeGraphRelationship.source_entity_id.in_(entity_ids),
                    KnowledgeGraphRelationship.target_entity_id.in_(entity_ids)
                )
            )
        
        if relation_types:
            rel_query = rel_query.filter(
                KnowledgeGraphRelationship.relation_type.in_(relation_types)
            )
        
        relationships = rel_query.limit(max_nodes * 2).all()
        
        # 构建节点列表
        nodes = []
        entity_id_set = set()
        
        for entity in entities:
            entity_id_set.add(entity.id)
            # 统计关联文档数量（用于节点大小）
            doc_count = self.db.query(KnowledgeGraphEntityDocument).filter(
                and_(
                    KnowledgeGraphEntityDocument.entity_id == entity.id,
                    KnowledgeGraphEntityDocument.is_deleted == False
                )
            ).count()
            
            nodes.append({
                "id": entity.id,
                "label": entity.name,
                "type": entity.type,
                "group": entity.type,  # 用于分组着色
                "value": max(5, min(50, doc_count)),  # 节点大小（5-50）
                "title": entity.description or entity.name,  # 悬停提示
            })
        
        # 构建边列表
        edges = []
        for rel in relationships:
            # 确保源和目标节点都在节点列表中
            if rel.source_entity_id in entity_id_set and rel.target_entity_id in entity_id_set:
                edges.append({
                    "from": rel.source_entity_id,
                    "to": rel.target_entity_id,
                    "label": rel.relation_type,
                    "value": rel.weight,  # 边的粗细
                    "title": rel.description or rel.relation_type,  # 悬停提示
                })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "layout": layout,
        }
    
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
            relationship.metadata = relationship_data.metadata
        
        self.db.commit()
        self.db.refresh(relationship)
        
        # 同步到NebulaGraph（需要先删除旧关系，再创建新关系）
        try:
            import asyncio
            space = f"kb_{relationship.knowledge_base_id}"
            source_vid = self.entity_id_to_vid(relationship.source_entity_id)
            target_vid = self.entity_id_to_vid(relationship.target_entity_id)
            
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._update_relationship_in_nebula(space, relationship, source_vid, target_vid))
            else:
                loop.run_until_complete(self._update_relationship_in_nebula(space, relationship, source_vid, target_vid))
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
        """删除关系（逻辑删除）"""
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
        
        relationship.is_deleted = True
        self.db.commit()
        
        # 从NebulaGraph删除
        try:
            import asyncio
            space = f"kb_{relationship.knowledge_base_id}"
            source_vid = self.entity_id_to_vid(relationship.source_entity_id)
            target_vid = self.entity_id_to_vid(relationship.target_entity_id)
            
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self.graph_storage.delete_relationship(space, source_vid, target_vid))
            except RuntimeError:
                asyncio.run(self.graph_storage.delete_relationship(space, source_vid, target_vid))
        except Exception as e:
            logger.warning(f"从NebulaGraph删除关系失败: {e}, relationship_id={relationship.id}")
        
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
            "metadata": relationship.metadata,
            "created_at": relationship.created_at,
            "updated_at": relationship.updated_at,
        }

