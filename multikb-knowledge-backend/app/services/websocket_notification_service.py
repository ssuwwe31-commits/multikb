"""
WebSocket Notification Service
根据文档修改功能设计实现WebSocket实时通知
"""

from typing import Dict, Any, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
from datetime import datetime
from app.core.logging import logger

class WebSocketNotificationService:
    """WebSocket通知服务 - 严格按照文档修改功能设计实现"""
    
    def __init__(self):
        # 存储活跃连接
        self.active_connections: List[WebSocket] = []
        # 存储用户连接映射
        self.user_connections: Dict[str, List[WebSocket]] = {}
        
        # 设计文档要求的通知类型
        self.NOTIFICATION_TYPES = {
            "modification_started": "修改开始",
            "modification_progress": "修改进度",
            "modification_completed": "修改完成",
            "modification_failed": "修改失败",
            "error_occurred": "错误发生",
            "version_reverted": "版本回退",
            "consistency_check": "一致性检查",
            "performance_alert": "性能告警"
        }
    
    async def connect(self, websocket: WebSocket, user_id: str = "anonymous"):
        """接受WebSocket连接 - 根据设计文档实现"""
        try:
            await websocket.accept()
            self.active_connections.append(websocket)
            
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)
            
            logger.info(f"WebSocket连接建立: user_id={user_id}, 总连接数={len(self.active_connections)}")
            
            # 发送连接成功通知
            await self.send_personal_message({
                "type": "connection_established",
                "message": "WebSocket连接已建立",
                "timestamp": datetime.now().isoformat()
            }, websocket)
            
        except Exception as e:
            logger.error(f"WebSocket连接错误: {e}", exc_info=True)
    
    def disconnect(self, websocket: WebSocket, user_id: str = "anonymous"):
        """断开WebSocket连接 - 根据设计文档实现"""
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            
            if user_id in self.user_connections and websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            logger.info(f"WebSocket连接断开: user_id={user_id}, 剩余连接数={len(self.active_connections)}")
            
        except Exception as e:
            logger.error(f"WebSocket断开错误: {e}", exc_info=True)
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """发送个人消息 - 根据设计文档实现"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"发送个人消息错误: {e}", exc_info=True)
    
    async def send_to_user(self, message: Dict[str, Any], user_id: str):
        """发送给特定用户 - 根据设计文档实现"""
        try:
            if user_id in self.user_connections:
                for websocket in self.user_connections[user_id]:
                    try:
                        await websocket.send_text(json.dumps(message, ensure_ascii=False))
                    except Exception as e:
                        logger.error(f"发送用户消息错误: {e}", exc_info=True)
                        # 移除无效连接
                        self.disconnect(websocket, user_id)
        except Exception as e:
            logger.error(f"发送用户消息错误: {e}", exc_info=True)
    
    async def broadcast(self, message: Dict[str, Any]):
        """广播消息 - 根据设计文档实现"""
        try:
            for connection in self.active_connections:
                try:
                    await connection.send_text(json.dumps(message, ensure_ascii=False))
                except Exception as e:
                    logger.error(f"广播消息错误: {e}", exc_info=True)
                    # 移除无效连接
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)
        except Exception as e:
            logger.error(f"广播消息错误: {e}", exc_info=True)
    
    async def send_modification_notification(
        self,
        notification_type: str,
        document_id: int,
        chunk_id: int,
        user_id: str = "user",
        data: Optional[Dict[str, Any]] = None
    ):
        """发送修改通知 - 根据设计文档实现"""
        try:
            if notification_type not in self.NOTIFICATION_TYPES:
                logger.warning(f"未知的通知类型: {notification_type}")
                return
            
            message = {
                "type": notification_type,
                "title": self.NOTIFICATION_TYPES[notification_type],
                "document_id": document_id,
                "chunk_id": chunk_id,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "data": data or {}
            }
            
            # 发送给特定用户
            await self.send_to_user(message, user_id)
            
            logger.debug(f"修改通知已发送: type={notification_type}, doc_id={document_id}, chunk_id={chunk_id}")
            
        except Exception as e:
            logger.error(f"发送修改通知错误: {e}", exc_info=True)
    
    async def send_progress_notification(
        self,
        operation_id: str,
        progress: float,
        message: str,
        user_id: str = "user"
    ):
        """发送进度通知 - 根据设计文档实现"""
        try:
            notification_data = {
                "type": "modification_progress",
                "title": "修改进度",
                "operation_id": operation_id,
                "progress": progress,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.send_to_user(notification_data, user_id)
            
            logger.debug(f"进度通知已发送: operation_id={operation_id}, progress={progress}")
            
        except Exception as e:
            logger.error(f"发送进度通知错误: {e}", exc_info=True)
    
    async def send_error_notification(
        self,
        error_type: str,
        error_message: str,
        document_id: Optional[int] = None,
        chunk_id: Optional[int] = None,
        user_id: str = "user"
    ):
        """发送错误通知 - 根据设计文档实现"""
        try:
            notification_data = {
                "type": "error_occurred",
                "title": "错误发生",
                "error_type": error_type,
                "error_message": error_message,
                "document_id": document_id,
                "chunk_id": chunk_id,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.send_to_user(notification_data, user_id)
            
            logger.debug(f"错误通知已发送: error_type={error_type}, doc_id={document_id}")
            
        except Exception as e:
            logger.error(f"发送错误通知错误: {e}", exc_info=True)
    
    async def send_performance_alert(
        self,
        alert_type: str,
        alert_message: str,
        performance_data: Dict[str, Any],
        user_id: str = "admin"
    ):
        """发送性能告警 - 根据设计文档实现"""
        try:
            notification_data = {
                "type": "performance_alert",
                "title": "性能告警",
                "alert_type": alert_type,
                "alert_message": alert_message,
                "performance_data": performance_data,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.send_to_user(notification_data, user_id)
            
            logger.debug(f"性能告警已发送: alert_type={alert_type}")
            
        except Exception as e:
            logger.error(f"发送性能告警错误: {e}", exc_info=True)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计 - 根据设计文档实现"""
        try:
            stats = {
                "total_connections": len(self.active_connections),
                "user_connections": len(self.user_connections),
                "connections_by_user": {
                    user_id: len(connections) 
                    for user_id, connections in self.user_connections.items()
                },
                "timestamp": datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取连接统计错误: {e}", exc_info=True)
            return {"error": str(e)}

# 全局WebSocket通知服务实例
websocket_notification_service = WebSocketNotificationService()
