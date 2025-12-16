"""
Operation Status Management Service
根据文档修改功能设计实现操作状态管理
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import redis
import json
from app.config.settings import settings
from app.core.logging import logger
from app.core.exceptions import CustomException, ErrorCode

class OperationStatusService:
    """操作状态管理服务 - 严格按照文档修改功能设计实现"""
    
    def __init__(self, db: Session):
        self.db = db
        # Redis连接 - 根据设计文档要求
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        
        # 设计文档要求的状态类型
        self.STATUS_TYPES = {
            "idle": "空闲状态",
            "editing": "编辑状态", 
            "saving": "保存状态",
            "processing": "处理状态",
            "completed": "完成状态",
            "failed": "失败状态",
            "rollback": "回退状态"
        }
        
        # 状态过期时间（秒）
        self.STATUS_EXPIRE_TIME = 3600  # 1小时
    
    def set_operation_status(self, operation_id: str, status: str, data: Dict[str, Any]) -> bool:
        """设置操作状态 - 根据设计文档实现"""
        try:
            logger.debug(f"设置操作状态: operation_id={operation_id}, status={status}")
            
            if status not in self.STATUS_TYPES:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"无效的状态类型: {status}"
                )
            
            # 构建状态数据
            status_data = {
                "operation_id": operation_id,
                "status": status,
                "status_description": self.STATUS_TYPES[status],
                "data": data,
                "timestamp": datetime.now().isoformat(),
                "expire_at": (datetime.now() + timedelta(seconds=self.STATUS_EXPIRE_TIME)).isoformat()
            }
            
            # 存储到Redis
            key = f"operation_status:{operation_id}"
            self.redis_client.setex(
                key,
                self.STATUS_EXPIRE_TIME,
                json.dumps(status_data, ensure_ascii=False)
            )
            
            logger.debug(f"操作状态设置成功: operation_id={operation_id}, status={status}")
            return True
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"设置操作状态错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"设置操作状态失败: {str(e)}"
            )
    
    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """获取操作状态 - 根据设计文档实现"""
        try:
            logger.debug(f"获取操作状态: operation_id={operation_id}")
            
            key = f"operation_status:{operation_id}"
            status_data = self.redis_client.get(key)
            
            if not status_data:
                logger.debug(f"操作状态不存在: operation_id={operation_id}")
                return None
            
            status_info = json.loads(status_data)
            logger.debug(f"操作状态获取成功: operation_id={operation_id}, status={status_info.get('status')}")
            return status_info
            
        except Exception as e:
            logger.error(f"获取操作状态错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"获取操作状态失败: {str(e)}"
            )
    
    def update_operation_progress(self, operation_id: str, progress: float, message: str = "") -> bool:
        """更新操作进度 - 根据设计文档实现"""
        try:
            logger.debug(f"更新操作进度: operation_id={operation_id}, progress={progress}")
            
            # 获取当前状态
            current_status = self.get_operation_status(operation_id)
            if not current_status:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"操作状态不存在: {operation_id}"
                )
            
            # 更新进度信息
            current_status["data"]["progress"] = progress
            current_status["data"]["message"] = message
            current_status["data"]["updated_at"] = datetime.now().isoformat()
            
            # 保存更新后的状态
            key = f"operation_status:{operation_id}"
            self.redis_client.setex(
                key,
                self.STATUS_EXPIRE_TIME,
                json.dumps(current_status, ensure_ascii=False)
            )
            
            logger.debug(f"操作进度更新成功: operation_id={operation_id}, progress={progress}")
            return True
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"更新操作进度错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"更新操作进度失败: {str(e)}"
            )
    
    def clear_operation_status(self, operation_id: str) -> bool:
        """清除操作状态 - 根据设计文档实现"""
        try:
            logger.debug(f"清除操作状态: operation_id={operation_id}")
            
            key = f"operation_status:{operation_id}"
            result = self.redis_client.delete(key)
            
            logger.debug(f"操作状态清除成功: operation_id={operation_id}, result={result}")
            return result > 0
            
        except Exception as e:
            logger.error(f"清除操作状态错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"清除操作状态失败: {str(e)}"
            )
    
    def get_active_operations(self) -> List[Dict[str, Any]]:
        """获取活跃操作 - 根据设计文档实现"""
        try:
            logger.debug("获取活跃操作列表")
            
            # 获取所有操作状态键
            pattern = "operation_status:*"
            keys = self.redis_client.keys(pattern)
            
            active_operations = []
            
            for key in keys:
                try:
                    status_data = self.redis_client.get(key)
                    if status_data:
                        status_info = json.loads(status_data)
                        active_operations.append(status_info)
                except Exception as e:
                    logger.warning(f"解析操作状态失败: {key}, error={e}")
                    continue
            
            logger.debug(f"获取活跃操作成功: {len(active_operations)} 个操作")
            return active_operations
            
        except Exception as e:
            logger.error(f"获取活跃操作错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"获取活跃操作失败: {str(e)}"
            )
    
    def check_operation_conflict(self, operation_id: str, required_status: str = "idle") -> bool:
        """检查操作冲突 - 根据设计文档实现"""
        try:
            logger.debug(f"检查操作冲突: operation_id={operation_id}, required_status={required_status}")
            
            current_status = self.get_operation_status(operation_id)
            
            if not current_status:
                # 没有状态，可以操作
                return False
            
            current_status_type = current_status.get("status", "idle")
            
            # 检查状态冲突
            if current_status_type != required_status:
                logger.warning(f"操作冲突: operation_id={operation_id}, current={current_status_type}, required={required_status}")
                return True
            
            logger.debug(f"无操作冲突: operation_id={operation_id}")
            return False
            
        except Exception as e:
            logger.error(f"检查操作冲突错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"检查操作冲突失败: {str(e)}"
            )
    
    def start_modification_operation(self, document_id: int, chunk_id: int, user_id: str = "user") -> str:
        """开始修改操作 - 根据设计文档实现"""
        try:
            logger.info(f"开始修改操作: document_id={document_id}, chunk_id={chunk_id}")
            
            operation_id = f"modify_{document_id}_{chunk_id}_{datetime.now().timestamp()}"
            
            # 检查操作冲突
            if self.check_operation_conflict(operation_id, "idle"):
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="存在正在进行的修改操作"
                )
            
            # 设置编辑状态
            operation_data = {
                "document_id": document_id,
                "chunk_id": chunk_id,
                "user_id": user_id,
                "progress": 0.0,
                "message": "开始编辑",
                "started_at": datetime.now().isoformat()
            }
            
            self.set_operation_status(operation_id, "editing", operation_data)
            
            logger.info(f"修改操作开始成功: operation_id={operation_id}")
            return operation_id
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"开始修改操作错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"开始修改操作失败: {str(e)}"
            )
    
    def complete_modification_operation(self, operation_id: str, success: bool = True, message: str = "") -> bool:
        """完成修改操作 - 根据设计文档实现"""
        try:
            logger.info(f"完成修改操作: operation_id={operation_id}, success={success}")
            
            # 获取当前状态
            current_status = self.get_operation_status(operation_id)
            if not current_status:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"操作状态不存在: {operation_id}"
                )
            
            # 更新状态
            final_status = "completed" if success else "failed"
            current_status["data"]["progress"] = 100.0 if success else 0.0
            current_status["data"]["message"] = message
            current_status["data"]["completed_at"] = datetime.now().isoformat()
            
            self.set_operation_status(operation_id, final_status, current_status["data"])
            
            logger.info(f"修改操作完成: operation_id={operation_id}, status={final_status}")
            return True
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"完成修改操作错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"完成修改操作失败: {str(e)}"
            )
