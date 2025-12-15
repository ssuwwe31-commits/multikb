"""
Entity Type Service
实体类型服务
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.entity_type import EntityType, KnowledgeBaseEntityType
from app.core.exceptions import CustomException, ErrorCode
from app.core.logging import logger


# 行业模板定义
INDUSTRY_TEMPLATES = {
    "technology": {
        "code": "technology",
        "name": "技术文档",
        "description": "适用于技术文档、开发文档、API文档等",
        "entity_types": [
            {"code": "person", "sort_order": 1},
            {"code": "technology", "sort_order": 2},
            {"code": "framework", "sort_order": 3},
            {"code": "standard", "sort_order": 4},
            {"code": "product", "sort_order": 5},
            {"code": "concept", "sort_order": 6},
            {"code": "method", "sort_order": 7},
            {"code": "document", "sort_order": 8},
            {"code": "organization", "sort_order": 9},
        ]
    },
    "medical": {
        "code": "medical",
        "name": "医疗健康",
        "description": "适用于医疗文档、健康知识等",
        "entity_types": [
            {"code": "person", "sort_order": 1},
            {"code": "organization", "sort_order": 2},
            {"code": "concept", "sort_order": 3},
            {"code": "method", "sort_order": 4},
            {"code": "disease", "sort_order": 5},
            {"code": "drug", "sort_order": 6},
            {"code": "treatment", "sort_order": 7},
            {"code": "location", "sort_order": 8},
        ]
    },
    "legal": {
        "code": "legal",
        "name": "法律",
        "description": "适用于法律文档、法规等",
        "entity_types": [
            {"code": "person", "sort_order": 1},
            {"code": "organization", "sort_order": 2},
            {"code": "location", "sort_order": 3},
            {"code": "event", "sort_order": 4},
            {"code": "document", "sort_order": 5},
            {"code": "law", "sort_order": 6},
            {"code": "case", "sort_order": 7},
        ]
    },
    "finance": {
        "code": "finance",
        "name": "金融",
        "description": "适用于金融文档、财务报告等",
        "entity_types": [
            {"code": "person", "sort_order": 1},
            {"code": "organization", "sort_order": 2},
            {"code": "product", "sort_order": 3},
            {"code": "concept", "sort_order": 4},
            {"code": "event", "sort_order": 5},
            {"code": "financial_product", "sort_order": 6},
            {"code": "market", "sort_order": 7},
            {"code": "location", "sort_order": 8},
        ]
    },
    "education": {
        "code": "education",
        "name": "教育",
        "description": "适用于教育文档、课程资料等",
        "entity_types": [
            {"code": "person", "sort_order": 1},
            {"code": "organization", "sort_order": 2},
            {"code": "location", "sort_order": 3},
            {"code": "concept", "sort_order": 4},
            {"code": "document", "sort_order": 5},
            {"code": "course", "sort_order": 6},
            {"code": "subject", "sort_order": 7},
            {"code": "event", "sort_order": 8},
        ]
    },
    "general": {
        "code": "general",
        "name": "通用",
        "description": "通用模板，包含基础实体类型",
        "entity_types": [
            {"code": "person", "sort_order": 1},
            {"code": "location", "sort_order": 2},
            {"code": "organization", "sort_order": 3},
            {"code": "concept", "sort_order": 4},
            {"code": "product", "sort_order": 5},
            {"code": "technology", "sort_order": 6},
            {"code": "event", "sort_order": 7},
            {"code": "other", "sort_order": 8},
        ]
    }
}


class EntityTypeService:
    """实体类型服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_types(
        self,
        is_enabled: Optional[bool] = None,
        is_system: Optional[bool] = None,
        knowledge_base_id: Optional[int] = None,
        level: Optional[int] = None,
        parent_id: Optional[int] = None,
        include_children: bool = False,
        user_id: Optional[int] = None
    ) -> List[EntityType]:
        """获取实体类型列表（支持层级查询）
        
        Args:
            is_enabled: 是否只返回启用的类型
            is_system: 是否只返回系统类型
            knowledge_base_id: 知识库ID（返回该知识库可用的类型）
            level: 层级（1=一级分类，2=二级分类，3=三级分类）
            parent_id: 父类型ID（返回该父类型下的子类型）
            include_children: 是否包含子类型
            user_id: 用户ID（如果提供，返回系统类型 + 该用户创建的类型）
        """
        # 如果指定了知识库ID，先查询该知识库配置的类型
        if knowledge_base_id:
            kb_types = self.db.query(EntityType).join(
                KnowledgeBaseEntityType,
                KnowledgeBaseEntityType.entity_type_id == EntityType.id
            ).filter(
                KnowledgeBaseEntityType.knowledge_base_id == knowledge_base_id,
                KnowledgeBaseEntityType.is_enabled == True,
                EntityType.is_deleted == False
            )
            
            # 应用额外的过滤条件
            if is_enabled is not None:
                kb_types = kb_types.filter(EntityType.is_enabled == is_enabled)
            if is_system is not None:
                kb_types = kb_types.filter(EntityType.is_system == is_system)
            if level is not None:
                kb_types = kb_types.filter(EntityType.level == level)
            if parent_id is not None:
                kb_types = kb_types.filter(EntityType.parent_id == parent_id)
            
            kb_types = kb_types.order_by(
                KnowledgeBaseEntityType.sort_order,
                EntityType.sort_order
            ).all()
            
            # 如果知识库没有配置类型，返回全局启用的类型
            if not kb_types:
                query = self.db.query(EntityType).filter(
                    EntityType.is_deleted == False
                )
                if is_enabled is not None:
                    query = query.filter(EntityType.is_enabled == is_enabled)
                elif is_enabled is None:
                    # 默认只返回启用的类型
                    query = query.filter(EntityType.is_enabled == True)
                if is_system is not None:
                    query = query.filter(EntityType.is_system == is_system)
                # 如果提供了 user_id，显示系统类型 + 该用户创建的类型
                if user_id is not None:
                    from sqlalchemy import or_
                    query = query.filter(
                        or_(
                            EntityType.is_system == True,  # 系统类型
                            EntityType.user_id == user_id  # 或当前用户创建的类型
                        )
                    )
                if level is not None:
                    query = query.filter(EntityType.level == level)
                if parent_id is not None:
                    query = query.filter(EntityType.parent_id == parent_id)
                return query.order_by(EntityType.sort_order, EntityType.id).all()
            
            # 如果需要包含子类型
            if include_children:
                result = []
                for entity_type in kb_types:
                    result.append(entity_type)
                    children = self.get_children_types(entity_type.id)
                    result.extend(children)
                return result
            
            return kb_types
        
        # 否则返回全局类型
        query = self.db.query(EntityType).filter(
            EntityType.is_deleted == False
        )
        
        if is_enabled is not None:
            query = query.filter(EntityType.is_enabled == is_enabled)
        
        if is_system is not None:
            query = query.filter(EntityType.is_system == is_system)
        
        # 如果提供了 user_id，显示系统类型 + 该用户创建的类型
        if user_id is not None:
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    EntityType.is_system == True,  # 系统类型
                    EntityType.user_id == user_id  # 或当前用户创建的类型
                )
            )
        
        if level is not None:
            query = query.filter(EntityType.level == level)
        
        if parent_id is not None:
            query = query.filter(EntityType.parent_id == parent_id)
        
        result = query.order_by(EntityType.sort_order, EntityType.id).all()
        
        # 如果需要包含子类型
        if include_children:
            final_result = []
            for entity_type in result:
                final_result.append(entity_type)
                children = self.get_children_types(entity_type.id)
                final_result.extend(children)
            return final_result
        
        return result
    
    def get_all_types_paginated(
        self,
        is_enabled: Optional[bool] = None,
        is_system: Optional[bool] = None,
        knowledge_base_id: Optional[int] = None,
        level: Optional[int] = None,
        parent_id: Optional[int] = None,
        include_children: bool = False,
        user_id: Optional[int] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> tuple:
        """获取实体类型列表（支持分页和关键词搜索）
        
        Returns:
            tuple: (类型列表, 总数)
        """
        from sqlalchemy import or_, func
        from app.core.pagination import get_offset
        
        # 构建基础查询
        if knowledge_base_id:
            # 如果指定了知识库ID，先查询该知识库配置的类型
            kb_query = self.db.query(EntityType).join(
                KnowledgeBaseEntityType,
                KnowledgeBaseEntityType.entity_type_id == EntityType.id
            ).filter(
                KnowledgeBaseEntityType.knowledge_base_id == knowledge_base_id,
                KnowledgeBaseEntityType.is_enabled == True,
                EntityType.is_deleted == False
            )
            
            # 检查知识库是否有配置的类型
            kb_types_count = kb_query.count()
            
            if kb_types_count > 0:
                # 如果知识库有配置的类型，使用知识库配置的类型
                query = kb_query
            else:
                # 如果知识库没有配置类型，回退到所有全局类型
                logger.info(f"知识库 {knowledge_base_id} 没有配置实体类型，返回所有全局类型")
                query = self.db.query(EntityType).filter(
                    EntityType.is_deleted == False
                )
        else:
            # 否则返回全局类型
            query = self.db.query(EntityType).filter(
                EntityType.is_deleted == False
            )
        
        # 应用过滤条件
        if is_enabled is not None:
            query = query.filter(EntityType.is_enabled == is_enabled)
        
        if is_system is not None:
            query = query.filter(EntityType.is_system == is_system)
        
        # 如果提供了 user_id，显示系统类型 + 该用户创建的类型
        if user_id is not None:
            query = query.filter(
                or_(
                    EntityType.is_system == True,  # 系统类型
                    EntityType.user_id == user_id  # 或当前用户创建的类型
                )
            )
        
        if level is not None:
            query = query.filter(EntityType.level == level)
        
        if parent_id is not None:
            query = query.filter(EntityType.parent_id == parent_id)
        
        # 关键词搜索（名称或代码）
        if keyword:
            keyword_like = f"%{keyword}%"
            query = query.filter(
                or_(
                    EntityType.name.like(keyword_like),
                    EntityType.code.like(keyword_like)
                )
            )
        
        # 如果需要包含子类型，先获取所有符合条件的类型
        if include_children:
            base_types = query.order_by(EntityType.sort_order, EntityType.id).all()
            final_result = []
            for entity_type in base_types:
                final_result.append(entity_type)
                children = self.get_children_types(entity_type.id)
                final_result.extend(children)
            
            # 计算总数
            total = len(final_result)
            
            # 手动分页
            offset = get_offset(page, size)
            paginated_result = final_result[offset:offset + size]
            
            return paginated_result, total
        
        # 获取总数
        total = query.count()
        
        # 分页查询
        offset = get_offset(page, size)
        result = query.order_by(EntityType.sort_order, EntityType.id).offset(offset).limit(size).all()
        
        return result, total
    
    def get_type_by_code(self, code: str) -> Optional[EntityType]:
        """根据代码获取实体类型"""
        return self.db.query(EntityType).filter(
            EntityType.code == code,
            EntityType.is_deleted == False
        ).first()
    
    def get_type_by_id(self, type_id: int) -> Optional[EntityType]:
        """根据ID获取实体类型"""
        return self.db.query(EntityType).filter(
            EntityType.id == type_id,
            EntityType.is_deleted == False
        ).first()
    
    # 最大层级限制
    MAX_LEVEL = 3
    
    def _calculate_level(self, parent_id: Optional[int]) -> int:
        """计算层级深度（最多支持3级分类）"""
        if not parent_id:
            return 1
        
        parent_type = self.get_type_by_id(parent_id)
        if not parent_type:
            return 1
        
        return parent_type.level + 1
    
    def _validate_level(self, level: int):
        """验证层级深度是否超过限制"""
        if level > self.MAX_LEVEL:
            raise CustomException(
                ErrorCode.BAD_REQUEST,
                f"实体类型最多支持{self.MAX_LEVEL}级分类，当前层级为{level}，超过限制"
            )
    
    def create_type(self, type_data: Dict[str, Any], user_id: Optional[int] = None) -> EntityType:
        """创建实体类型（最多支持3级分类，自动计算level）
        
        Args:
            type_data: 实体类型数据
            user_id: 创建用户ID（可选，如果提供则关联到该用户）
        """
        # 检查代码是否已存在
        existing = self.get_type_by_code(type_data["code"])
        if existing:
            raise CustomException(
                ErrorCode.BAD_REQUEST,
                f"实体类型代码 '{type_data['code']}' 已存在"
            )
        
        # 确保用户创建的类型不是系统类型
        type_data = type_data.copy()
        type_data["is_system"] = False
        # 关联创建用户
        if user_id:
            type_data["user_id"] = user_id
        
        # 自动计算层级（忽略用户传入的level，确保一致性）
        parent_id = type_data.get("parent_id")
        calculated_level = self._calculate_level(parent_id)
        
        # 验证层级深度不超过限制
        self._validate_level(calculated_level)
        
        type_data["level"] = calculated_level
        
        # 验证父类型存在（如果指定了parent_id）
        if parent_id:
            parent_type = self.get_type_by_id(parent_id)
            if not parent_type:
                raise CustomException(
                    ErrorCode.BAD_REQUEST,
                    f"父类型 ID {parent_id} 不存在"
                )
        
        entity_type = EntityType(**type_data)
        self.db.add(entity_type)
        self.db.commit()
        self.db.refresh(entity_type)
        
        logger.info(f"创建实体类型: {entity_type.code} ({entity_type.name}), level={entity_type.level}, parent_id={entity_type.parent_id}")
        return entity_type
    
    def update_type(self, type_id: int, update_data: Dict[str, Any], user_id: Optional[int] = None) -> EntityType:
        """更新实体类型（如果修改parent_id，自动重新计算level）
        
        Args:
            type_id: 实体类型ID
            update_data: 更新数据
            user_id: 当前用户ID（用于权限检查）
        """
        entity_type = self.get_type_by_id(type_id)
        
        if not entity_type:
            raise CustomException(
                ErrorCode.NOT_FOUND,
                "实体类型不存在"
            )
        
        # 权限检查：系统类型或用户只能更新自己创建的类型
        if entity_type.is_system:
            # 系统类型允许更新部分字段（但不允许修改 parent_id）
            if "parent_id" in update_data:
                raise CustomException(
                    ErrorCode.FORBIDDEN,
                    "系统类型不允许修改父类型"
                )
        elif user_id is not None:
            # 用户只能更新自己创建的类型
            if entity_type.user_id != user_id:
                raise CustomException(
                    ErrorCode.FORBIDDEN,
                    "只能更新自己创建的实体类型"
                )
        
        # 禁止修改的字段
        forbidden_fields = ["code", "is_system", "user_id", "id", "created_at", "updated_at", "is_deleted"]
        update_data = {k: v for k, v in update_data.items() if k not in forbidden_fields}
        
        # 系统类型只能更新部分字段
        if entity_type.is_system:
            allowed_fields = ["name", "description", "icon", "color", "tag_type", "sort_order", "meta_data", "is_enabled"]
            update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        # 如果修改了parent_id，需要重新计算level并更新所有子类型的level
        parent_id_changed = "parent_id" in update_data and update_data["parent_id"] != entity_type.parent_id
        
        for key, value in update_data.items():
            if value is not None:
                setattr(entity_type, key, value)
        
        # 如果parent_id改变，重新计算level并验证
        if parent_id_changed:
            new_level = self._calculate_level(entity_type.parent_id)
            # 验证新层级不超过限制
            self._validate_level(new_level)
            entity_type.level = new_level
            # 递归更新所有子类型的level（并验证）
            self._recalculate_children_levels(type_id)
        
        self.db.commit()
        self.db.refresh(entity_type)
        
        logger.info(f"更新实体类型: {entity_type.code} ({entity_type.name}), level={entity_type.level}")
        return entity_type
    
    def _recalculate_children_levels(self, parent_id: int):
        """递归重新计算所有子类型的level（最多3级）"""
        children = self.get_children_types(parent_id, include_disabled=True)
        parent_type = self.get_type_by_id(parent_id)
        
        if not parent_type:
            return
        
        for child in children:
            new_level = parent_type.level + 1
            # 验证层级不超过限制
            self._validate_level(new_level)
            child.level = new_level
            self.db.flush()
            # 递归处理子类型的子类型
            self._recalculate_children_levels(child.id)
    
    def delete_type(self, type_id: int, user_id: Optional[int] = None) -> None:
        """删除实体类型
        
        Args:
            type_id: 实体类型ID
            user_id: 当前用户ID（用于权限检查）
        """
        entity_type = self.get_type_by_id(type_id)
        
        if not entity_type:
            raise CustomException(
                ErrorCode.NOT_FOUND,
                "实体类型不存在"
            )
        
        # 系统类型不可删除
        if entity_type.is_system:
            raise CustomException(
                ErrorCode.FORBIDDEN,
                "系统内置类型不可删除"
            )
        
        # 权限检查：用户只能删除自己创建的类型
        if user_id is not None and entity_type.user_id != user_id:
            raise CustomException(
                ErrorCode.FORBIDDEN,
                "只能删除自己创建的实体类型"
            )
        
        # 检查是否有子类型
        children_count = self.db.query(EntityType).filter(
            EntityType.parent_id == type_id,
            EntityType.is_deleted == False
        ).count()
        
        if children_count > 0:
            raise CustomException(
                ErrorCode.BAD_REQUEST,
                f"无法删除：此类型下还有 {children_count} 个子类型，请先删除子类型"
            )
        
        # 检查是否有实体使用该类型
        from app.models.knowledge_graph import KnowledgeGraphEntity
        entity_count = self.db.query(KnowledgeGraphEntity).filter(
            KnowledgeGraphEntity.type == entity_type.code,
            KnowledgeGraphEntity.is_deleted == False
        ).count()
        
        if entity_count > 0:
            raise CustomException(
                ErrorCode.BAD_REQUEST,
                f"无法删除：有 {entity_count} 个实体正在使用此类型"
            )
        
        # 软删除
        entity_type.is_deleted = True
        self.db.commit()
        
        logger.info(f"删除实体类型: {entity_type.code} ({entity_type.name})")
    
    def toggle_type(self, type_id: int, is_enabled: bool) -> EntityType:
        """启用/禁用实体类型"""
        entity_type = self.get_type_by_id(type_id)
        
        if not entity_type:
            raise CustomException(
                ErrorCode.NOT_FOUND,
                "实体类型不存在"
            )
        
        entity_type.is_enabled = is_enabled
        self.db.commit()
        self.db.refresh(entity_type)
        
        logger.info(f"{'启用' if is_enabled else '禁用'}实体类型: {entity_type.code} ({entity_type.name})")
        return entity_type
    
    def get_knowledge_base_types(self, knowledge_base_id: int) -> List[EntityType]:
        """获取知识库的实体类型列表"""
        # 先查询知识库配置的类型
        kb_types = self.db.query(EntityType).join(
            KnowledgeBaseEntityType,
            KnowledgeBaseEntityType.entity_type_id == EntityType.id
        ).filter(
            KnowledgeBaseEntityType.knowledge_base_id == knowledge_base_id,
            KnowledgeBaseEntityType.is_enabled == True,
            EntityType.is_enabled == True,
            EntityType.is_deleted == False
        ).order_by(
            KnowledgeBaseEntityType.sort_order,
            EntityType.sort_order
        ).all()
        
        # 如果知识库没有配置，返回全局启用的类型
        if not kb_types:
            kb_types = self.get_all_types(is_enabled=True)
        
        return kb_types
    
    def configure_knowledge_base_types(
        self,
        knowledge_base_id: int,
        entity_type_ids: List[int],
        configs: Optional[List[Dict[str, Any]]] = None
    ) -> List[KnowledgeBaseEntityType]:
        """配置知识库的实体类型"""
        # 删除现有配置
        self.db.query(KnowledgeBaseEntityType).filter(
            KnowledgeBaseEntityType.knowledge_base_id == knowledge_base_id
        ).delete()
        
        # 创建新配置
        kb_entity_types = []
        for idx, entity_type_id in enumerate(entity_type_ids):
            # 查找详细配置
            config = None
            if configs:
                config = next((c for c in configs if c.get("entity_type_id") == entity_type_id), None)
            
            kb_entity_type = KnowledgeBaseEntityType(
                knowledge_base_id=knowledge_base_id,
                entity_type_id=entity_type_id,
                is_enabled=config.get("is_enabled", True) if config else True,
                sort_order=config.get("sort_order", idx + 1) if config else idx + 1
            )
            self.db.add(kb_entity_type)
            kb_entity_types.append(kb_entity_type)
        
        self.db.commit()
        
        logger.info(f"配置知识库 {knowledge_base_id} 的实体类型: {len(entity_type_ids)} 个")
        return kb_entity_types
    
    def get_industry_templates(self) -> List[Dict[str, Any]]:
        """获取所有行业模板列表"""
        templates = []
        for template_code, template_data in INDUSTRY_TEMPLATES.items():
            templates.append({
                "code": template_data["code"],
                "name": template_data["name"],
                "description": template_data["description"],
                "entity_type_count": len(template_data["entity_types"])
            })
        return templates
    
    def get_industry_template(self, template_code: str) -> Optional[Dict[str, Any]]:
        """获取指定行业模板"""
        return INDUSTRY_TEMPLATES.get(template_code)
    
    def apply_industry_template(
        self,
        knowledge_base_id: int,
        template_code: str
    ) -> List[KnowledgeBaseEntityType]:
        """
        应用行业模板到知识库
        
        流程：
        1. 获取模板定义
        2. 查找或创建模板中的实体类型
        3. 配置知识库的实体类型（启用模板中的类型）
        4. 返回配置结果
        """
        template = INDUSTRY_TEMPLATES.get(template_code)
        if not template:
            raise CustomException(
                ErrorCode.BAD_REQUEST,
                f"模板 '{template_code}' 不存在"
            )
        
        entity_type_ids = []
        entity_type_codes = [et["code"] for et in template["entity_types"]]
        
        # 查找模板中的实体类型
        for type_code in entity_type_codes:
            entity_type = self.get_type_by_code(type_code)
            if entity_type:
                entity_type_ids.append(entity_type.id)
            else:
                # 如果类型不存在，尝试创建（仅限非系统类型）
                # 系统类型（person, location等）应该已经存在
                logger.warning(f"实体类型 '{type_code}' 不存在，跳过")
        
        if not entity_type_ids:
            raise CustomException(
                ErrorCode.BAD_REQUEST,
                f"模板 '{template_code}' 中没有可用的实体类型"
            )
        
        # 配置知识库的实体类型
        configs = []
        for et_def in template["entity_types"]:
            entity_type = self.get_type_by_code(et_def["code"])
            if entity_type:
                configs.append({
                    "entity_type_id": entity_type.id,
                    "is_enabled": True,
                    "sort_order": et_def.get("sort_order", 0)
                })
        
        kb_entity_types = []
        # 删除现有配置
        self.db.query(KnowledgeBaseEntityType).filter(
            KnowledgeBaseEntityType.knowledge_base_id == knowledge_base_id
        ).delete()
        
        # 创建新配置
        for config in configs:
            kb_entity_type = KnowledgeBaseEntityType(
                knowledge_base_id=knowledge_base_id,
                entity_type_id=config["entity_type_id"],
                is_enabled=config["is_enabled"],
                sort_order=config["sort_order"]
            )
            self.db.add(kb_entity_type)
            kb_entity_types.append(kb_entity_type)
        
        self.db.commit()
        
        logger.info(f"应用行业模板 '{template_code}' 到知识库 {knowledge_base_id}: {len(kb_entity_types)} 个类型")
        return kb_entity_types
    
    def get_children_types(self, parent_id: int, include_disabled: bool = False) -> List[EntityType]:
        """获取指定父类型的所有直接子类型（一级子类型）"""
        query = self.db.query(EntityType).filter(
            EntityType.parent_id == parent_id,
            EntityType.is_deleted == False
        )
        
        if not include_disabled:
            query = query.filter(EntityType.is_enabled == True)
        
        return query.order_by(EntityType.sort_order, EntityType.id).all()
    
    def get_all_descendants(self, parent_id: int, include_disabled: bool = False) -> List[EntityType]:
        """获取指定父类型的所有后代类型（递归查询所有子类型、孙类型等）"""
        descendants = []
        children = self.get_children_types(parent_id, include_disabled=include_disabled)
        
        for child in children:
            descendants.append(child)
            # 递归获取子类型的后代
            descendants.extend(self.get_all_descendants(child.id, include_disabled=include_disabled))
        
        return descendants
    
    def get_all_ancestors(self, type_id: int) -> List[EntityType]:
        """获取指定类型的所有祖先类型（从根到父类型的路径）"""
        ancestors = []
        entity_type = self.get_type_by_id(type_id)
        
        if not entity_type:
            return ancestors
        
        current = entity_type
        while current.parent_id:
            parent = self.get_type_by_id(current.parent_id)
            if not parent:
                break
            ancestors.insert(0, parent)  # 插入到开头，保持从根到父的顺序
            current = parent
        
        return ancestors
    
    def get_parent_type(self, type_id: int) -> Optional[EntityType]:
        """获取指定类型的父类型"""
        entity_type = self.get_type_by_id(type_id)
        if not entity_type or not entity_type.parent_id:
            return None
        return self.get_type_by_id(entity_type.parent_id)
    
    def get_type_tree(self, root_id: Optional[int] = None, knowledge_base_id: Optional[int] = None, max_depth: Optional[int] = None, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取实体类型树（递归包含所有子类型，最多3级）
        
        Args:
            root_id: 根类型ID（可选）
            knowledge_base_id: 知识库ID（可选）
            max_depth: 最大深度（可选）
            user_id: 用户ID（如果提供，返回系统类型 + 该用户创建的类型）
        """
        # 获取根类型（一级分类）
        if root_id:
            root_type = self.get_type_by_id(root_id)
            root_types = [root_type] if root_type else []
        else:
            root_types = self.get_all_types(
                level=1,
                knowledge_base_id=knowledge_base_id,
                is_enabled=True,
                user_id=user_id
            )
        
        def build_tree(entity_type: EntityType, current_depth: int = 1) -> Dict[str, Any]:
            """递归构建树结构"""
            # 如果设置了最大深度限制，检查是否超过
            if max_depth is not None and current_depth >= max_depth:
                return {
                    "id": entity_type.id,
                    "code": entity_type.code,
                    "name": entity_type.name,
                    "description": entity_type.description,
                    "icon": entity_type.icon,
                    "color": entity_type.color,
                    "tag_type": entity_type.tag_type,
                    "sort_order": entity_type.sort_order,
                    "is_system": entity_type.is_system,
                    "is_enabled": entity_type.is_enabled,
                    "parent_id": entity_type.parent_id,
                    "level": entity_type.level,
                    "children": []  # 超过深度限制，不加载子类型
                }
            
            children = self.get_children_types(entity_type.id)
            return {
                "id": entity_type.id,
                "code": entity_type.code,
                "name": entity_type.name,
                "description": entity_type.description,
                "icon": entity_type.icon,
                "color": entity_type.color,
                "tag_type": entity_type.tag_type,
                "sort_order": entity_type.sort_order,
                "is_system": entity_type.is_system,
                "is_enabled": entity_type.is_enabled,
                "parent_id": entity_type.parent_id,
                "level": entity_type.level,
                "children": [build_tree(child, current_depth + 1) for child in children] if children else []
            }
        
        return [build_tree(root_type) for root_type in root_types if root_type]
    
    def recalculate_all_levels(self) -> int:
        """重新计算所有实体类型的level（用于数据修复，最多3级）"""
        # 获取所有一级分类
        root_types = self.get_all_types(level=1)
        updated_count = 0
        
        def update_level_recursive(entity_type: EntityType):
            """递归更新level（最多3级）"""
            nonlocal updated_count
            
            children = self.get_children_types(entity_type.id, include_disabled=True)
            for child in children:
                expected_level = entity_type.level + 1
                # 验证层级不超过限制
                if expected_level > self.MAX_LEVEL:
                    logger.warning(f"实体类型 {child.code} 的层级超过限制，跳过更新")
                    continue
                if child.level != expected_level:
                    child.level = expected_level
                    updated_count += 1
                # 递归处理子类型
                update_level_recursive(child)
        
        for root_type in root_types:
            # 确保一级分类的level为1
            if root_type.level != 1:
                root_type.level = 1
                updated_count += 1
            # 递归更新所有子类型
            update_level_recursive(root_type)
        
        self.db.commit()
        logger.info(f"重新计算了 {updated_count} 个实体类型的level")
        return updated_count
    
    def create_template_entity_types(self, template_code: str) -> List[EntityType]:
        """
        创建模板中定义的实体类型（如果不存在）
        
        用于初始化时创建行业特定的实体类型
        """
        template = INDUSTRY_TEMPLATES.get(template_code)
        if not template:
            raise CustomException(
                ErrorCode.BAD_REQUEST,
                f"模板 '{template_code}' 不存在"
            )
        
        created_types = []
        
        # 行业特定类型的定义
        industry_type_definitions = {
            "technology": [
                {"code": "framework", "name": "框架", "description": "软件开发框架", "icon": "grid", "color": "#4ECDC4", "tag_type": "success"},
                {"code": "standard", "name": "标准", "description": "技术标准、规范", "icon": "document", "color": "#45B7D1", "tag_type": "primary"},
                {"code": "method", "name": "方法", "description": "技术方法、算法", "icon": "tools", "color": "#FFA07A", "tag_type": "warning"},
                {"code": "document", "name": "文档", "description": "技术文档、规范文档", "icon": "document", "color": "#95A5A6", "tag_type": "info"},
            ],
            "medical": [
                {"code": "disease", "name": "疾病", "description": "疾病、病症", "icon": "warning", "color": "#FF6B6B", "tag_type": "danger", "parent_type": "concept"},
                {"code": "drug", "name": "药物", "description": "药品、药物", "icon": "medicine-box", "color": "#4ECDC4", "tag_type": "success", "parent_type": "product"},
                {"code": "treatment", "name": "治疗方法", "description": "治疗方案、治疗方法", "icon": "first-aid-kit", "color": "#45B7D1", "tag_type": "primary", "parent_type": "method"},
            ],
            "legal": [
                {"code": "law", "name": "法律", "description": "法律法规、法律条文", "icon": "document", "color": "#4ECDC4", "tag_type": "success", "parent_type": "document"},
                {"code": "case", "name": "案例", "description": "法律案例、判例", "icon": "folder-opened", "color": "#45B7D1", "tag_type": "primary", "parent_type": "event"},
            ],
            "finance": [
                {"code": "financial_product", "name": "金融产品", "description": "金融产品、理财产品", "icon": "wallet", "color": "#4ECDC4", "tag_type": "success", "parent_type": "product"},
                {"code": "market", "name": "市场", "description": "金融市场、市场", "icon": "trend-charts", "color": "#45B7D1", "tag_type": "primary", "parent_type": "concept"},
            ],
            "education": [
                {"code": "course", "name": "课程", "description": "课程、课程内容", "icon": "reading", "color": "#4ECDC4", "tag_type": "success", "parent_type": "concept"},
                {"code": "subject", "name": "学科", "description": "学科、专业", "icon": "notebook", "color": "#45B7D1", "tag_type": "primary", "parent_type": "concept"},
            ],
        }
        
        type_definitions = industry_type_definitions.get(template_code, [])
        
        for type_def in type_definitions:
            # 检查是否已存在
            existing = self.get_type_by_code(type_def["code"])
            if not existing:
                # 创建新类型
                entity_type = EntityType(
                    code=type_def["code"],
                    name=type_def["name"],
                    description=type_def.get("description", ""),
                    icon=type_def.get("icon", ""),
                    color=type_def.get("color", ""),
                    tag_type=type_def.get("tag_type", "info"),
                    sort_order=type_def.get("sort_order", 0),
                    is_system=False,  # 行业特定类型不是系统类型
                    is_enabled=True,
                    meta_data={
                        "parent_type": type_def.get("parent_type"),
                        "template": template_code,
                        "prompt_hint": type_def.get("description", "")
                    }
                )
                self.db.add(entity_type)
                created_types.append(entity_type)
        
        if created_types:
            self.db.commit()
            for entity_type in created_types:
                self.db.refresh(entity_type)
            logger.info(f"为模板 '{template_code}' 创建了 {len(created_types)} 个实体类型")
        
        return created_types

