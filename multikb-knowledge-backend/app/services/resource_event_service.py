"""
Services for resource events and sync states.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session

from app.services.base import BaseService
from app.models.resource_event import ResourceEvent
from app.models.resource_sync_state import ResourceSyncState
from app.services.opensearch_service import OpenSearchService
from app.core.logging import logger


class ResourceEventService(BaseService[ResourceEvent]):
    """资源事件记录服务"""

    def __init__(self, db: Session):
        super().__init__(db, ResourceEvent)
        self.opensearch_service = OpenSearchService()

    async def create_event(self, payload: Dict[str, Any]) -> ResourceEvent:
        """
        创建资源事件（双写：MySQL + OpenSearch）
        
        Args:
            payload: 事件数据
            
        Returns:
            ResourceEvent 对象
        """
        # 1. 写入 MySQL
        event = await self.create(payload)
        
        # 2. 写入 OpenSearch（异步，不阻塞）
        try:
            await self._index_to_opensearch(event)
        except Exception as exc:
            logger.warning("Failed to index event to OpenSearch: %s", exc)
            # 不抛出异常，MySQL 写入成功即可
        
        return event
    
    async def _index_to_opensearch(self, event: ResourceEvent) -> None:
        """将事件索引到 OpenSearch"""
        try:
            # 确保索引存在
            await self.opensearch_service.ensure_resource_events_index()
            
            # 构建文档数据
            doc = {
                "cluster_id": event.cluster_id,
                "resource_type": event.resource_type,
                "namespace": event.namespace,
                "resource_uid": event.resource_uid,
                "event_type": event.event_type,
                "diff": event.diff if event.diff else {},
                "created_at": event.created_at.isoformat() if event.created_at else datetime.utcnow().isoformat(),
            }
            
            # 索引到 OpenSearch
            await self.opensearch_service.index_resource_event(event.id, doc)
            logger.debug(f"资源事件已索引到 OpenSearch: event_id={event.id}, resource_uid={event.resource_uid}")
        except Exception as exc:
            logger.warning(f"索引资源事件到 OpenSearch 失败: {exc}")
            # 不抛出异常，允许继续执行

    async def query_events(
        self,
        cluster_id: int,
        resource_type: Optional[str] = None,
        namespace: Optional[str] = None,
        resource_uid: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        查询资源变更事件（优先使用 OpenSearch，回退到 MySQL）
        
        Args:
            cluster_id: 集群ID
            resource_type: 资源类型（可选）
            namespace: 命名空间（可选）
            resource_uid: 资源UID（可选）
            event_type: 事件类型（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            limit: 返回数量限制（默认 100）
            
        Returns:
            事件列表
        """
        # 优先使用 OpenSearch 查询
        try:
            start_time_str = start_time.isoformat() if start_time else None
            end_time_str = end_time.isoformat() if end_time else None
            
            result = await self.opensearch_service.search_resource_events(
                cluster_id=cluster_id,
                resource_type=resource_type,
                namespace=namespace,
                resource_uid=resource_uid,
                event_type=event_type,
                start_time=start_time_str,
                end_time=end_time_str,
                limit=limit,
            )
            return result.get("events", [])
        except Exception as exc:
            logger.warning(f"OpenSearch 查询失败，回退到 MySQL: {exc}")
            # 回退到 MySQL 查询
            return await self._query_from_mysql(
                cluster_id=cluster_id,
                resource_type=resource_type,
                namespace=namespace,
                resource_uid=resource_uid,
                event_type=event_type,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
    
    async def _query_from_mysql(
        self,
        cluster_id: int,
        resource_type: Optional[str] = None,
        namespace: Optional[str] = None,
        resource_uid: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """从 MySQL 查询资源事件（回退方案）"""
        query = (
            self.db.query(self.model)
            .filter(
                self.model.cluster_id == cluster_id,
                self.model.is_deleted == False,  # noqa: E712
            )
        )
        
        if resource_type:
            query = query.filter(self.model.resource_type == resource_type)
        if namespace:
            query = query.filter(self.model.namespace == namespace)
        if resource_uid:
            query = query.filter(self.model.resource_uid == resource_uid)
        if event_type:
            query = query.filter(self.model.event_type == event_type)
        if start_time:
            query = query.filter(self.model.created_at >= start_time)
        if end_time:
            query = query.filter(self.model.created_at <= end_time)
        
        events = query.order_by(self.model.created_at.desc()).limit(limit).all()
        
        return [
            {
                "id": event.id,
                "cluster_id": event.cluster_id,
                "resource_type": event.resource_type,
                "namespace": event.namespace,
                "resource_uid": event.resource_uid,
                "event_type": event.event_type,
                "diff": event.diff,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in events
        ]


class ResourceSyncStateService(BaseService[ResourceSyncState]):
    """资源同步状态服务"""

    def __init__(self, db: Session):
        super().__init__(db, ResourceSyncState)

    async def get_state(self, cluster_id: int, resource_type: str, namespace: Optional[str]) -> Optional[ResourceSyncState]:
        query = (
            self.db.query(self.model)
            .filter(
                self.model.cluster_id == cluster_id,
                self.model.resource_type == resource_type,
                self.model.namespace == namespace,
                self.model.is_deleted == False,  # noqa: E712
            )
        )
        return query.first()

    async def set_state(
        self,
        cluster_id: int,
        resource_type: str,
        namespace: Optional[str],
        resource_version: Optional[str],
    ) -> ResourceSyncState:
        state = await self.get_state(cluster_id, resource_type, namespace)
        payload = {
            "cluster_id": cluster_id,
            "resource_type": resource_type,
            "namespace": namespace,
            "resource_version": resource_version,
        }
        if state:
            for key, value in payload.items():
                setattr(state, key, value)
            self.db.commit()
            self.db.refresh(state)
            return state
        return await self.create(payload)
