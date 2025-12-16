"""
Base Service Class
"""

from typing import TypeVar, Generic, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)

class BaseService(Generic[ModelType]):
    """基础服务类"""
    
    def __init__(self, db: Session, model: type[ModelType]):
        self.db = db
        self.model = model
    
    async def get(self, id: int) -> Optional[ModelType]:
        """获取单个对象"""
        return self.db.query(self.model).filter(
            and_(self.model.id == id, self.model.is_deleted == False)
        ).first()
    
    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        **filters
    ) -> List[ModelType]:
        """获取多个对象"""
        query = self.db.query(self.model).filter(self.model.is_deleted == False)
        
        # 应用过滤条件
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    async def create(self, obj_in: dict) -> ModelType:
        """创建对象"""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    async def update(self, id: int, obj_in: dict) -> Optional[ModelType]:
        """更新对象"""
        db_obj = await self.get(id)
        if not db_obj:
            return None
        
        for key, value in obj_in.items():
            if hasattr(db_obj, key) and value is not None:
                setattr(db_obj, key, value)
        
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    async def delete(self, id: int) -> bool:
        """软删除对象"""
        db_obj = await self.get(id)
        if not db_obj:
            return False
        
        db_obj.is_deleted = True
        self.db.commit()
        return True
