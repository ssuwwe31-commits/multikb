"""
Performance Monitoring Service
根据文档修改功能设计实现性能监控和状态跟踪
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import time
import psutil
import redis
import json
from app.config.settings import settings
from app.core.logging import logger
from app.core.exceptions import CustomException, ErrorCode

class PerformanceMonitoringService:
    """性能监控服务 - 严格按照文档修改功能设计实现"""
    
    def __init__(self, db: Session):
        self.db = db
        # Redis连接 - 根据设计文档要求
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        
        # 监控指标配置
        self.METRICS_RETENTION_DAYS = 7  # 指标保留天数
        self.METRICS_COLLECTION_INTERVAL = 60  # 指标收集间隔（秒）
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统指标 - 根据设计文档实现"""
        try:
            logger.debug("收集系统指标")
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            
            # 网络统计
            network = psutil.net_io_counters()
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": psutil.cpu_count(),
                    "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "usage_percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "usage_percent": (disk.used / disk.total) * 100
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            }
            
            logger.debug(f"系统指标收集完成: CPU={cpu_percent}%, Memory={memory.percent}%")
            return metrics
            
        except Exception as e:
            logger.error(f"收集系统指标错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"收集系统指标失败: {str(e)}"
            )
    
    def collect_application_metrics(self) -> Dict[str, Any]:
        """收集应用指标 - 根据设计文档实现"""
        try:
            logger.debug("收集应用指标")
            
            # 数据库连接数
            from sqlalchemy import text
            db_connections = self.db.execute(text("SELECT COUNT(*) FROM information_schema.processlist")).scalar()
            
            # Redis连接数
            redis_info = self.redis_client.info()
            
            # 文档处理统计
            from app.models.document import Document
            from app.models.chunk import DocumentChunk
            
            total_documents = self.db.query(Document).count()
            total_chunks = self.db.query(DocumentChunk).count()
            
            # 处理中的文档
            processing_documents = self.db.query(Document).filter(
                Document.status.in_(["uploaded", "parsing", "chunking", "vectorizing", "indexing"])
            ).count()
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "database": {
                    "connections": db_connections,
                    "total_documents": total_documents,
                    "total_chunks": total_chunks,
                    "processing_documents": processing_documents
                },
                "redis": {
                    "connected_clients": redis_info.get("connected_clients", 0),
                    "used_memory": redis_info.get("used_memory", 0),
                    "used_memory_percent": redis_info.get("used_memory_percent", 0),
                    "keyspace_hits": redis_info.get("keyspace_hits", 0),
                    "keyspace_misses": redis_info.get("keyspace_misses", 0)
                },
                "application": {
                    "uptime": time.time(),  # 简化版本
                    "active_operations": len(self.get_active_operations())
                }
            }
            
            logger.debug(f"应用指标收集完成: 文档={total_documents}, 块={total_chunks}")
            return metrics
            
        except Exception as e:
            logger.error(f"收集应用指标错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"收集应用指标失败: {str(e)}"
            )
    
    def get_active_operations(self) -> List[Dict[str, Any]]:
        """获取活跃操作 - 根据设计文档实现"""
        try:
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
            
            return active_operations
            
        except Exception as e:
            logger.error(f"获取活跃操作错误: {e}", exc_info=True)
            return []
    
    def store_metrics(self, metrics_type: str, metrics_data: Dict[str, Any]) -> bool:
        """存储指标数据 - 根据设计文档实现"""
        try:
            logger.debug(f"存储指标数据: type={metrics_type}")
            
            # 构建存储键
            timestamp = datetime.now()
            key = f"metrics:{metrics_type}:{timestamp.strftime('%Y%m%d_%H%M%S')}"
            
            # 存储到Redis
            self.redis_client.setex(
                key,
                self.METRICS_RETENTION_DAYS * 24 * 3600,  # 转换为秒
                json.dumps(metrics_data, ensure_ascii=False)
            )
            
            logger.debug(f"指标数据存储成功: key={key}")
            return True
            
        except Exception as e:
            logger.error(f"存储指标数据错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"存储指标数据失败: {str(e)}"
            )
    
    def get_metrics_history(self, metrics_type: str, hours: int = 24) -> List[Dict[str, Any]]:
        """获取指标历史 - 根据设计文档实现"""
        try:
            logger.debug(f"获取指标历史: type={metrics_type}, hours={hours}")
            
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            # 构建搜索模式
            pattern = f"metrics:{metrics_type}:*"
            keys = self.redis_client.keys(pattern)
            
            metrics_history = []
            
            for key in keys:
                try:
                    # 提取时间戳
                    key_parts = key.split(':')
                    if len(key_parts) >= 3:
                        time_str = key_parts[2]
                        metric_time = datetime.strptime(time_str, '%Y%m%d_%H%M%S')
                        
                        # 检查时间范围
                        if start_time <= metric_time <= end_time:
                            metrics_data = self.redis_client.get(key)
                            if metrics_data:
                                metric_info = json.loads(metrics_data)
                                metrics_history.append(metric_info)
                except Exception as e:
                    logger.warning(f"解析指标数据失败: {key}, error={e}")
                    continue
            
            # 按时间排序
            metrics_history.sort(key=lambda x: x.get('timestamp', ''))
            
            logger.debug(f"指标历史获取成功: {len(metrics_history)} 条记录")
            return metrics_history
            
        except Exception as e:
            logger.error(f"获取指标历史错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"获取指标历史失败: {str(e)}"
            )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要 - 根据设计文档实现"""
        try:
            logger.debug("获取性能摘要")
            
            # 获取最新系统指标
            system_metrics = self.collect_system_metrics()
            
            # 获取最新应用指标
            app_metrics = self.collect_application_metrics()
            
            # 获取活跃操作
            active_operations = self.get_active_operations()
            
            # 计算性能评分
            performance_score = self.calculate_performance_score(system_metrics, app_metrics)
            
            summary = {
                "timestamp": datetime.now().isoformat(),
                "performance_score": performance_score,
                "system_metrics": system_metrics,
                "application_metrics": app_metrics,
                "active_operations": {
                    "count": len(active_operations),
                    "operations": active_operations
                },
                "status": self.get_system_status(performance_score),
                "recommendations": self.get_performance_recommendations(system_metrics, app_metrics)
            }
            
            logger.debug(f"性能摘要生成成功: score={performance_score}")
            return summary
            
        except Exception as e:
            logger.error(f"获取性能摘要错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"获取性能摘要失败: {str(e)}"
            )
    
    def calculate_performance_score(self, system_metrics: Dict[str, Any], app_metrics: Dict[str, Any]) -> float:
        """计算性能评分 - 根据设计文档实现"""
        try:
            # CPU评分 (0-100)
            cpu_score = max(0, 100 - system_metrics["cpu"]["usage_percent"])
            
            # 内存评分 (0-100)
            memory_score = max(0, 100 - system_metrics["memory"]["usage_percent"])
            
            # 磁盘评分 (0-100)
            disk_score = max(0, 100 - system_metrics["disk"]["usage_percent"])
            
            # Redis评分 (0-100)
            redis_score = max(0, 100 - app_metrics["redis"]["used_memory_percent"])
            
            # 综合评分 (加权平均)
            performance_score = (
                cpu_score * 0.3 +
                memory_score * 0.3 +
                disk_score * 0.2 +
                redis_score * 0.2
            )
            
            return round(performance_score, 2)
            
        except Exception as e:
            logger.error(f"计算性能评分错误: {e}", exc_info=True)
            return 0.0
    
    def get_system_status(self, performance_score: float) -> str:
        """获取系统状态 - 根据设计文档实现"""
        if performance_score >= 80:
            return "excellent"
        elif performance_score >= 60:
            return "good"
        elif performance_score >= 40:
            return "warning"
        else:
            return "critical"
    
    def get_performance_recommendations(self, system_metrics: Dict[str, Any], app_metrics: Dict[str, Any]) -> List[str]:
        """获取性能建议 - 根据设计文档实现"""
        recommendations = []
        
        # CPU建议
        if system_metrics["cpu"]["usage_percent"] > 80:
            recommendations.append("CPU使用率过高，建议优化处理任务或增加CPU资源")
        
        # 内存建议
        if system_metrics["memory"]["usage_percent"] > 80:
            recommendations.append("内存使用率过高，建议清理缓存或增加内存资源")
        
        # 磁盘建议
        if system_metrics["disk"]["usage_percent"] > 80:
            recommendations.append("磁盘使用率过高，建议清理临时文件或增加存储空间")
        
        # Redis建议
        if app_metrics["redis"]["used_memory_percent"] > 80:
            recommendations.append("Redis内存使用率过高，建议清理过期数据或增加Redis内存")
        
        # 数据库建议
        if app_metrics["database"]["connections"] > 50:
            recommendations.append("数据库连接数过多，建议优化连接池配置")
        
        return recommendations
