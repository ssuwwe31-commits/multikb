"""
WebSocket Endpoints
根据文档修改功能设计实现WebSocket实时通知端点
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from typing import Optional
import json
from app.services.websocket_notification_service import websocket_notification_service
from app.core.logging import logger
from app.core.security import verify_token
from app.dependencies.auth import get_current_user

router = APIRouter()

@router.websocket("/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: Optional[str] = Query(None)):
    """WebSocket连接端点 - 根据设计文档实现，需要认证"""
    try:
        # 验证Token
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="缺少认证令牌")
            return
        
        payload = verify_token(token)
        if not payload:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="认证令牌无效")
            return
        
        # 验证user_id是否与token中的用户ID一致
        token_user_id = payload.get("sub")
        if token_user_id != user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="用户ID不匹配")
            return
        
        logger.info(f"WebSocket连接请求: user_id={user_id}")
        
        # 建立连接
        await websocket_notification_service.connect(websocket, user_id)
        
        try:
            while True:
                # 接收客户端消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 处理客户端消息
                await handle_client_message(websocket, user_id, message)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket连接断开: user_id={user_id}")
        except Exception as e:
            logger.error(f"WebSocket处理错误: {e}", exc_info=True)
        finally:
            # 断开连接
            websocket_notification_service.disconnect(websocket, user_id)
            
    except Exception as e:
        logger.error(f"WebSocket端点错误: {e}", exc_info=True)


# 文档状态推送：需要认证
@router.websocket("/documents/status")
async def documents_status_socket(websocket: WebSocket, token: Optional[str] = Query(None)):
    """文档状态WebSocket端点 - 需要认证"""
    try:
        # 先接受连接，然后再验证Token（确保前端能收到onclose事件）
        await websocket.accept()
        
        # 验证Token
        if not token:
            logger.warning("WebSocket连接失败: 缺少认证令牌")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="缺少认证令牌")
            return
        
        payload = verify_token(token)
        if not payload:
            logger.warning("WebSocket连接失败: 认证令牌无效")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="认证令牌无效")
            return
        
        # Token验证通过
        user_id = payload.get("sub")
        logger.info(f"WebSocket连接成功: 文档状态推送, user_id={user_id}")
        
        try:
            await websocket.send_json({"type": "connected", "message": "ok"})
        except WebSocketDisconnect:
            logger.info("文档状态WebSocket在发送欢迎包前断开")
            return

        while True:
            try:
                data = await websocket.receive_text()
                await websocket.send_json({"type": "pong", "echo": data})
            except WebSocketDisconnect:
                logger.info("文档状态WebSocket断开连接")
                break
    except WebSocketDisconnect:
        logger.info("文档状态WebSocket在握手阶段断开")
    except Exception as e:
        logger.error(f"文档状态WebSocket错误: {e}", exc_info=True)
        # 如果还没有accept，尝试关闭连接
        try:
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="服务器错误")
        except:
            pass

async def handle_client_message(websocket: WebSocket, user_id: str, message: dict):
    """处理客户端消息 - 根据设计文档实现"""
    try:
        message_type = message.get("type", "")
        
        if message_type == "ping":
            # 心跳检测
            await websocket_notification_service.send_personal_message({
                "type": "pong",
                "timestamp": "2024-01-01T10:00:00Z"
            }, websocket)
            
        elif message_type == "subscribe":
            # 订阅特定类型的通知
            subscription_type = message.get("subscription_type", "")
            await websocket_notification_service.send_personal_message({
                "type": "subscription_confirmed",
                "subscription_type": subscription_type,
                "message": f"已订阅 {subscription_type} 通知"
            }, websocket)
            
        elif message_type == "unsubscribe":
            # 取消订阅
            subscription_type = message.get("subscription_type", "")
            await websocket_notification_service.send_personal_message({
                "type": "unsubscription_confirmed",
                "subscription_type": subscription_type,
                "message": f"已取消订阅 {subscription_type} 通知"
            }, websocket)
            
        else:
            # 未知消息类型
            await websocket_notification_service.send_personal_message({
                "type": "error",
                "message": f"未知的消息类型: {message_type}"
            }, websocket)
            
    except Exception as e:
        logger.error(f"处理客户端消息错误: {e}", exc_info=True)
        await websocket_notification_service.send_personal_message({
            "type": "error",
            "message": f"处理消息失败: {str(e)}"
        }, websocket)

@router.get("/ws/stats", dependencies=[Depends(get_current_user)])
async def get_websocket_stats():
    """获取WebSocket连接统计 - 根据设计文档实现，需要认证"""
    try:
        stats = websocket_notification_service.get_connection_stats()
        return stats
    except Exception as e:
        logger.error(f"获取WebSocket统计错误: {e}", exc_info=True)
        return {"error": str(e)}
