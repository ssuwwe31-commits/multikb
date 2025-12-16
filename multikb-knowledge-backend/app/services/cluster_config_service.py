"""
Service for cluster configuration management and connectivity checks.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List, Set
from urllib.parse import urljoin

import httpx
from httpx import Timeout
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from app.core.logging import logger
from app.core.exceptions import CustomException, ErrorCode
from app.models.cluster_config import ClusterConfig
from app.models.diagnosis_record import DiagnosisRecord
from app.models.diagnosis_iteration import DiagnosisIteration
from app.models.diagnosis_memory import DiagnosisMemory
from app.models.resource_snapshot import ResourceSnapshot
from app.models.system import OperationLog
from app.schemas.observability import (
    ClusterConfigCreate,
    ClusterConfigUpdate,
    ClusterConnectivityRequest,
    ClusterConnectivityResult,
    ClusterHealthResult,
)
from app.services.base import BaseService
from app.utils.crypto import crypto_manager
from app.services.resource_event_service import ResourceEventService, ResourceSyncStateService

DEFAULT_TIMEOUT = Timeout(10.0, connect=5.0)


class ClusterConfigService(BaseService[ClusterConfig]):
    """集群配置服务"""

    SENSITIVE_FIELDS = [
        "auth_token",
        "kubeconfig",
        "client_cert",
        "client_key",
        "ca_cert",
        "prometheus_password",
        "log_password",
    ]

    def __init__(self, db: Session):
        super().__init__(db, ClusterConfig)

    async def create_config(self, data: ClusterConfigCreate) -> ClusterConfig:
        # 检查名称唯一性（只检查未删除的记录）
        existing = (
            self.db.query(self.model)
            .filter(
                self.model.name == data.name,
                self.model.is_deleted == False  # noqa: E712
            )
            .first()
        )
        if existing:
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"集群名称 '{data.name}' 已存在"
            )
        
        payload = data.dict()
        self._encrypt_sensitive_fields(payload)
        try:
            config = await self.create(payload)
            self._log_operation("create", config.id, f"创建集群配置 {config.name}")
            # 自动执行健康检查
            try:
                await self.run_health_check(config)
                logger.info("集群配置 %s 创建后自动健康检查完成", config.name)
            except Exception as exc:  # pylint: disable=broad-except
                # 健康检查失败不影响配置创建，只记录日志
                logger.warning("集群配置 %s 创建后自动健康检查失败: %s", config.name, exc, exc_info=True)
            return config
        except Exception as exc:  # pylint: disable=broad-except
            # 捕获数据库完整性错误（如唯一约束违反）
            if "Duplicate entry" in str(exc) or "uk_cluster_name" in str(exc):
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"集群名称 '{data.name}' 已存在"
                ) from exc
            # 其他错误重新抛出
            raise

    async def update_config(self, config_id: int, data: ClusterConfigUpdate) -> Optional[ClusterConfig]:
        # 如果修改了名称，进行唯一性校验
        if data.name is not None:
            conflict = (
                self.db.query(self.model)
                .filter(
                    self.model.name == data.name,
                    self.model.id != config_id,
                    self.model.is_deleted == False  # noqa: E712
                )
                .first()
            )
            if conflict:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"集群名称 '{data.name}' 已存在"
                )
        
        payload = data.dict(exclude_unset=True, exclude_none=True)
        # 过滤掉空字符串的敏感字段（避免保存未加密的空值）
        for field in self.SENSITIVE_FIELDS:
            if field in payload and payload[field] == "":
                del payload[field]
        self._encrypt_sensitive_fields(payload)
        try:
            updated = await self.update(config_id, payload)
            if updated:
                self._log_operation("update", config_id, f"更新集群配置 {updated.name}")
                # 自动执行健康检查（特别是当API地址等关键配置改变时）
                try:
                    await self.run_health_check(updated)
                    logger.info("集群配置 %s 更新后自动健康检查完成", updated.name)
                except Exception as exc:  # pylint: disable=broad-except
                    # 健康检查失败不影响配置更新，只记录日志
                    logger.warning("集群配置 %s 更新后自动健康检查失败: %s", updated.name, exc, exc_info=True)
            return updated
        except Exception as exc:  # pylint: disable=broad-except
            # 捕获数据库完整性错误（如唯一约束违反）
            if "Duplicate entry" in str(exc) or "uk_cluster_name" in str(exc):
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"集群名称 '{data.name or '已存在'}' 已存在"
                ) from exc
            # 其他错误重新抛出
            raise

    async def list_configs(self, skip: int = 0, limit: int = 20) -> Tuple[List[ClusterConfig], int]:
        query = self.db.query(self.model).filter(self.model.is_deleted == False)  # noqa: E712
        total = query.count()
        items = query.order_by(self.model.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    async def delete_config(self, config_id: int, hard: bool = False) -> bool:
        """
        删除集群配置
        
        Args:
            config_id: 集群配置ID
            hard: 是否硬删除。True=物理删除，False=软删除（默认）
        
        Returns:
            bool: 删除是否成功
        """
        config = await self.get(config_id)
        if not config:
            # 如果硬删除，尝试从数据库直接查询（包括已软删除的记录）
            if hard:
                config = self.db.query(self.model).filter(self.model.id == config_id).first()
                if not config:
                    return False
            else:
                return False
        
        if hard:
            # 硬删除：物理删除记录（由于外键 CASCADE，关联的 resource_snapshots 和 diagnosis_records 会自动删除）
            cluster_name = config.name
            self.db.delete(config)
            self.db.commit()
            self._log_operation("delete", config_id, f"硬删除集群配置 {cluster_name} (ID: {config_id})")
            logger.info("硬删除集群配置: %s (ID: %s)", cluster_name, config_id)
        else:
            # 软删除：只标记为已删除
            config.is_deleted = True
            self.db.commit()
            self.db.refresh(config)
            self._log_operation("delete", config_id, f"软删除集群配置 {config.name} (ID: {config_id})")
            logger.info("软删除集群配置: %s (ID: %s)", config.name, config_id)
        
        return True

    async def run_health_check(self, config: ClusterConfig) -> ClusterConnectivityResult:
        """执行健康检查并更新数据库状态"""
        try:
            result = await self.test_connectivity(config, None)
            # 更新 API Server 状态（主要状态）
            config.last_health_status = result.api_server.status
            
            # 构建完整的健康检查消息（包含所有组件状态）
            health_messages = [f"API: {result.api_server.status} - {result.api_server.message}"]
            if result.prometheus:
                health_messages.append(f"Prometheus: {result.prometheus.status} - {result.prometheus.message}")
            if result.logging:
                health_messages.append(f"Logging: {result.logging.status} - {result.logging.message}")
            
            # 更新完整的健康检查消息（包含所有组件状态）
            config.last_health_message = " | ".join(health_messages)
            config.last_health_checked_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(config)
            logger.info("集群配置 %s 健康检查完成，状态: %s", config.name, result.api_server.status)
            return result
        except Exception as exc:  # pylint: disable=broad-except
            # 即使健康检查失败，也要更新数据库状态
            config.last_health_status = "error"
            config.last_health_message = f"健康检查失败: {str(exc)}"
            config.last_health_checked_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(config)
            logger.error("集群配置 %s 健康检查失败: %s", config.name, exc, exc_info=True)
            # 重新抛出异常，让调用者知道检查失败
            raise

    async def test_connectivity(
        self, config: Optional[ClusterConfig], overrides: Optional[ClusterConnectivityRequest]
    ) -> ClusterConnectivityResult:
        payload: Dict[str, Any] = {}
        if config:
            payload.update(self.build_runtime_payload(config))
        if overrides:
            payload.update(overrides.dict(exclude_unset=True, exclude_none=True))

        api_status = await self._check_api_server(payload)
        prometheus_status = await self._check_prometheus(payload)
        logging_status = await self._check_log_system(payload)

        return ClusterConnectivityResult(
            api_server=api_status,
            prometheus=prometheus_status,
            logging=logging_status,
        )

    def build_runtime_payload(self, config: ClusterConfig) -> Dict[str, Any]:
        """返回包含解密凭证的运行时配置，用于外部系统通信。"""
        payload: Dict[str, Any] = {
            "api_server": config.api_server,
            "auth_type": config.auth_type,
            "auth_token": crypto_manager.decrypt_text(config.auth_token),
            "kubeconfig": crypto_manager.decrypt_text(config.kubeconfig),
            "client_cert": crypto_manager.decrypt_text(config.client_cert),
            "client_key": crypto_manager.decrypt_text(config.client_key),
            "ca_cert": crypto_manager.decrypt_text(config.ca_cert),
            "verify_ssl": config.verify_ssl,
            "prometheus_url": config.prometheus_url,
            "prometheus_auth_type": config.prometheus_auth_type,
            "prometheus_username": config.prometheus_username,
            "prometheus_password": crypto_manager.decrypt_text(config.prometheus_password),
            "log_system": config.log_system,
            "log_endpoint": config.log_endpoint,
            "log_auth_type": config.log_auth_type,
            "log_username": config.log_username,
            "log_password": crypto_manager.decrypt_text(config.log_password),
        }
        return payload

    def serialize_config(self, config: ClusterConfig) -> Dict[str, Any]:
        """序列化集群配置，自动剔除敏感字段。"""
        data = {
            "id": config.id,
            "name": config.name,
            "description": config.description,
            "api_server": config.api_server,
            "auth_type": config.auth_type,
            "verify_ssl": config.verify_ssl,
            "prometheus_url": config.prometheus_url,
            "prometheus_auth_type": config.prometheus_auth_type,
            "prometheus_username": config.prometheus_username,
            "log_system": config.log_system,
            "log_endpoint": config.log_endpoint,
            "log_auth_type": config.log_auth_type,
            "log_username": config.log_username,
            "is_active": config.is_active,
            "last_health_status": config.last_health_status,
            "last_health_message": config.last_health_message,
            "last_health_checked_at": config.last_health_checked_at,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }
        for field in self.SENSITIVE_FIELDS:
            data[field] = None
        return data

    def get_active_configs(self) -> List[ClusterConfig]:
        return (
            self.db.query(self.model)
            .filter(self.model.is_deleted == False, self.model.is_active == True)  # noqa: E712
            .all()
        )

    async def _check_api_server(self, payload: Dict[str, Any]) -> ClusterHealthResult:
        url = payload.get("api_server")
        if not url:
            return ClusterHealthResult(name="api_server", status="missing", message="未提供 API Server")

        headers = {}
        auth_type = payload.get("auth_type", "token")
        if auth_type == "token" and payload.get("auth_token"):
            headers["Authorization"] = f"Bearer {payload['auth_token']}"
        elif auth_type == "basic" and payload.get("auth_token"):
            headers["Authorization"] = payload["auth_token"]

        verify_option: Any = payload.get("verify_ssl", True)

        target = urljoin(url, "/version")
        try:
            # 对于 K8s API Server，通常在内网环境，不应该使用代理
            # 使用 NO_PROXY 环境变量来禁用代理
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            target_host = parsed_url.hostname or ""
            
            original_no_proxy = os.environ.get("NO_PROXY", "")
            original_no_proxy_lower = os.environ.get("no_proxy", "")
            
            try:
                # 将目标主机添加到 NO_PROXY
                no_proxy_list = []
                if original_no_proxy:
                    no_proxy_list.extend(original_no_proxy.split(","))
                if target_host and target_host not in no_proxy_list:
                    no_proxy_list.append(target_host)
                # 也可以添加通配符来禁用所有代理
                if "*" not in no_proxy_list:
                    no_proxy_list.append("*")
                
                os.environ["NO_PROXY"] = ",".join(no_proxy_list)
                os.environ["no_proxy"] = ",".join(no_proxy_list)
                
                # 同时清除代理环境变量（双重保险）
                original_proxy = os.environ.pop("HTTP_PROXY", None)
                original_https_proxy = os.environ.pop("HTTPS_PROXY", None)
                original_http_proxy = os.environ.pop("http_proxy", None)
                original_https_proxy_lower = os.environ.pop("https_proxy", None)
                
                async with httpx.AsyncClient(
                    timeout=DEFAULT_TIMEOUT,
                    verify=verify_option
                ) as client:
                    response = await client.get(target, headers=headers)
                    response.raise_for_status()
                    data = response.json()
            finally:
                # 恢复原始环境变量
                if original_no_proxy:
                    os.environ["NO_PROXY"] = original_no_proxy
                elif "NO_PROXY" in os.environ:
                    del os.environ["NO_PROXY"]
                    
                if original_no_proxy_lower:
                    os.environ["no_proxy"] = original_no_proxy_lower
                elif "no_proxy" in os.environ:
                    del os.environ["no_proxy"]
                
                if original_proxy is not None:
                    os.environ["HTTP_PROXY"] = original_proxy
                if original_https_proxy is not None:
                    os.environ["HTTPS_PROXY"] = original_https_proxy
                if original_http_proxy is not None:
                    os.environ["http_proxy"] = original_http_proxy
                if original_https_proxy_lower is not None:
                    os.environ["https_proxy"] = original_https_proxy_lower
            message = f"Kubernetes {data.get('gitVersion', '')} ({data.get('platform', '')})"
            return ClusterHealthResult(name="api_server", status="ok", message=message)
        except httpx.ConnectError as exc:
            # httpx.ConnectError 可能没有详细的错误信息，需要从异常对象中提取
            # 尝试从多个来源获取错误详情（包括异常链和堆栈跟踪）
            error_detail = ""
            error_type = type(exc).__name__
            stack_hints = []  # 从堆栈跟踪中提取的关键信息
            
            # 1. 尝试从 __cause__ 获取底层异常信息
            if hasattr(exc, '__cause__') and exc.__cause__:
                cause = exc.__cause__
                error_detail = str(cause)
                error_type = f"{type(exc).__name__} -> {type(cause).__name__}"
                # 如果底层异常也有 __cause__，继续深入
                if hasattr(cause, '__cause__') and cause.__cause__:
                    deeper_cause = cause.__cause__
                    deeper_detail = str(deeper_cause)
                    if deeper_detail:
                        error_detail = f"{error_detail} ({deeper_detail})"
            
            # 2. 尝试从 message 属性获取
            if not error_detail and hasattr(exc, 'message') and exc.message:
                error_detail = str(exc.message)
            
            # 3. 尝试从字符串表示获取
            if not error_detail:
                exc_str = str(exc)
                if exc_str and exc_str != type(exc).__name__:
                    error_detail = exc_str
            
            # 4. 从堆栈跟踪中提取关键信息（通过 traceback）
            import traceback
            try:
                tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
                tb_text = ''.join(tb_lines)
                
                # 检测关键信息
                if 'http_proxy.py' in tb_text or 'http_proxy' in tb_text:
                    stack_hints.append("检测到代理连接")
                if 'start_tls' in tb_text:
                    stack_hints.append("TLS/SSL 握手阶段")
                if 'connection_pool' in tb_text:
                    stack_hints.append("连接池问题")
            except Exception:
                pass  # 如果无法提取堆栈信息，忽略
            
            # 获取目标 URL
            target_url = url
            if hasattr(exc, 'request') and exc.request:
                target_url = str(exc.request.url)
            
            # 构建用户友好的错误消息
            error_msg = f"连接失败: 无法连接到 {target_url}"
            
            # 根据堆栈提示和错误详情判断错误类型
            is_proxy_issue = any('proxy' in hint.lower() for hint in stack_hints) or 'proxy' in str(error_detail).lower()
            is_tls_issue = any('tls' in hint.lower() or 'ssl' in hint.lower() for hint in stack_hints) or any(keyword in str(error_detail).lower() for keyword in ["ssl", "tls", "certificate", "cert", "start_tls"])
            
            if error_detail:
                error_detail_lower = error_detail.lower()
                # 根据错误类型提供具体的诊断建议
                if any(keyword in error_detail_lower for keyword in ["name or service not known", "nodename", "servname", "dns"]):
                    error_msg += "，DNS 解析失败，请检查地址是否正确"
                elif any(keyword in error_detail_lower for keyword in ["connection refused", "refused"]):
                    error_msg += "，连接被拒绝，请检查服务是否运行或端口是否正确"
                elif any(keyword in error_detail_lower for keyword in ["timed out", "timeout", "timedout"]):
                    error_msg += "，连接超时，请检查网络或防火墙设置"
                elif is_tls_issue:
                    error_msg += "，TLS/SSL 握手失败"
                    if is_proxy_issue:
                        error_msg += "（可能涉及代理），请检查代理配置和证书设置"
                    else:
                        error_msg += "，请检查证书配置或关闭证书验证"
                elif is_proxy_issue:
                    error_msg += "，代理连接失败，请检查代理配置或环境变量（HTTP_PROXY/HTTPS_PROXY）"
                elif "network is unreachable" in error_detail_lower:
                    error_msg += "，网络不可达，请检查网络连接"
                else:
                    # 对于其他错误，提供通用提示
                    error_msg += "，请检查网络连接、防火墙和地址配置"
            else:
                # 即使没有详细错误信息，也根据堆栈提示提供建议
                if is_tls_issue:
                    error_msg += "，TLS/SSL 握手失败"
                    if is_proxy_issue:
                        error_msg += "（可能涉及代理），请检查代理配置和证书设置"
                    else:
                        error_msg += "，请检查证书配置或关闭证书验证"
                elif is_proxy_issue:
                    error_msg += "，代理连接失败，请检查代理配置或环境变量（HTTP_PROXY/HTTPS_PROXY）"
                else:
                    error_msg += "，请检查网络连接、防火墙和地址配置"
            
            # 记录详细的错误信息（包含异常类型、详情和堆栈提示）
            logger.warning(
                "API server health check failed (%s): %s - URL: %s%s",
                error_type,
                error_detail or "无详细错误信息",
                target_url,
                f" [堆栈提示: {', '.join(stack_hints)}]" if stack_hints else "",
                exc_info=True
            )
            return ClusterHealthResult(name="api_server", status="error", message=error_msg)
        except httpx.TimeoutException as exc:
            error_detail = str(exc) or getattr(exc, 'message', '') or type(exc).__name__
            if hasattr(exc, 'request') and exc.request:
                target_url = str(exc.request.url)
                error_msg = f"连接超时: 请求 {target_url} 超时（超过 {DEFAULT_TIMEOUT.connect} 秒），请检查网络或增加超时时间"
            else:
                error_msg = f"连接超时: 请求 {url} 超时，请检查网络或增加超时时间"
            if error_detail and error_detail != type(exc).__name__:
                error_msg += f" (详情: {error_detail})"
            logger.warning("API server health check failed (Timeout): %s - %s", error_detail, error_msg, exc_info=True)
            return ClusterHealthResult(name="api_server", status="error", message=error_msg)
        except httpx.HTTPStatusError as exc:
            error_msg = f"HTTP 错误: {exc.response.status_code} - {exc.response.text[:100]}"
            logger.warning("API server health check failed (HTTP %s): %s", exc.response.status_code, str(exc))
            return ClusterHealthResult(name="api_server", status="error", message=error_msg)
        except Exception as exc:  # pylint: disable=broad-except
            error_msg = f"未知错误: {str(exc) or type(exc).__name__}"
            logger.warning("API server health check failed: %s", exc, exc_info=True)
            return ClusterHealthResult(name="api_server", status="error", message=error_msg)

    async def _check_prometheus(self, payload: Dict[str, Any]) -> Optional[ClusterHealthResult]:
        url = payload.get("prometheus_url")
        if not url:
            return None

        headers = {}
        auth_type = payload.get("prometheus_auth_type", "none")
        if auth_type == "basic" and payload.get("prometheus_username") and payload.get("prometheus_password"):
            import base64

            token = base64.b64encode(
                f"{payload['prometheus_username']}:{payload['prometheus_password']}".encode("utf-8")
            ).decode("utf-8")
            headers["Authorization"] = f"Basic {token}"
        elif auth_type == "token" and payload.get("prometheus_password"):
            headers["Authorization"] = f"Bearer {payload['prometheus_password']}"

        target = urljoin(url, "/api/v1/status/runtimeinfo")
        try:
            # Prometheus 通常也在内网环境，禁用代理
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            target_host = parsed_url.hostname or ""
            
            original_no_proxy = os.environ.get("NO_PROXY", "")
            original_no_proxy_lower = os.environ.get("no_proxy", "")
            
            try:
                # 将目标主机添加到 NO_PROXY
                no_proxy_list = []
                if original_no_proxy:
                    no_proxy_list.extend(original_no_proxy.split(","))
                if target_host and target_host not in no_proxy_list:
                    no_proxy_list.append(target_host)
                if "*" not in no_proxy_list:
                    no_proxy_list.append("*")
                
                os.environ["NO_PROXY"] = ",".join(no_proxy_list)
                os.environ["no_proxy"] = ",".join(no_proxy_list)
                
                # 同时清除代理环境变量
                original_proxy = os.environ.pop("HTTP_PROXY", None)
                original_https_proxy = os.environ.pop("HTTPS_PROXY", None)
                original_http_proxy = os.environ.pop("http_proxy", None)
                original_https_proxy_lower = os.environ.pop("https_proxy", None)
                
                async with httpx.AsyncClient(
                    timeout=DEFAULT_TIMEOUT
                ) as client:
                    response = await client.get(target, headers=headers)
                    response.raise_for_status()
                    data = response.json()
            finally:
                # 恢复原始环境变量
                if original_no_proxy:
                    os.environ["NO_PROXY"] = original_no_proxy
                elif "NO_PROXY" in os.environ:
                    del os.environ["NO_PROXY"]
                if original_no_proxy_lower:
                    os.environ["no_proxy"] = original_no_proxy_lower
                elif "no_proxy" in os.environ:
                    del os.environ["no_proxy"]
                if original_proxy is not None:
                    os.environ["HTTP_PROXY"] = original_proxy
                if original_https_proxy is not None:
                    os.environ["HTTPS_PROXY"] = original_https_proxy
                if original_http_proxy is not None:
                    os.environ["http_proxy"] = original_http_proxy
                if original_https_proxy_lower is not None:
                    os.environ["https_proxy"] = original_https_proxy_lower
            status = data.get("status", "success")
            message = f"Prometheus 运行正常 (版本: {data.get('data', {}).get('versionInfo', {}).get('version', 'unknown')})"
            return ClusterHealthResult(name="prometheus", status="ok" if status == "success" else status, message=message)
        except httpx.ConnectError as exc:
            error_msg = f"连接失败: 无法连接到 {url}，请检查网络连接和地址是否正确"
            logger.warning("Prometheus health check failed (ConnectError): %s", str(exc))
            return ClusterHealthResult(name="prometheus", status="error", message=error_msg)
        except httpx.TimeoutException as exc:
            error_msg = f"连接超时: 请求 {url} 超时，请检查网络或增加超时时间"
            logger.warning("Prometheus health check failed (Timeout): %s", str(exc))
            return ClusterHealthResult(name="prometheus", status="error", message=error_msg)
        except httpx.HTTPStatusError as exc:
            error_msg = f"HTTP 错误: {exc.response.status_code} - {exc.response.text[:100]}"
            logger.warning("Prometheus health check failed (HTTP %s): %s", exc.response.status_code, str(exc))
            return ClusterHealthResult(name="prometheus", status="error", message=error_msg)
        except Exception as exc:  # pylint: disable=broad-except
            error_msg = f"未知错误: {str(exc) or type(exc).__name__}"
            logger.warning("Prometheus health check failed: %s", exc, exc_info=True)
            return ClusterHealthResult(name="prometheus", status="error", message=error_msg)

    async def _check_log_system(self, payload: Dict[str, Any]) -> Optional[ClusterHealthResult]:
        endpoint = payload.get("log_endpoint")
        if not endpoint:
            return None

        system = (payload.get("log_system") or "custom").lower()
        auth_type = payload.get("log_auth_type", "none")
        headers = {}

        if auth_type == "basic" and payload.get("log_username") and payload.get("log_password"):
            import base64

            token = base64.b64encode(
                f"{payload['log_username']}:{payload['log_password']}".encode("utf-8")
            ).decode("utf-8")
            headers["Authorization"] = f"Basic {token}"
        elif auth_type == "token" and payload.get("log_password"):
            headers["Authorization"] = f"Bearer {payload['log_password']}"

        path_map = {
            "elk": "/_cluster/health",
            "elasticsearch": "/_cluster/health",
            "loki": "/ready",
            "custom": "/health",
        }
        target = urljoin(endpoint, path_map.get(system, "/"))
        try:
            # 日志系统通常也在内网环境，禁用代理
            from urllib.parse import urlparse
            parsed_url = urlparse(endpoint)
            target_host = parsed_url.hostname or ""
            
            original_no_proxy = os.environ.get("NO_PROXY", "")
            original_no_proxy_lower = os.environ.get("no_proxy", "")
            
            try:
                # 将目标主机添加到 NO_PROXY
                no_proxy_list = []
                if original_no_proxy:
                    no_proxy_list.extend(original_no_proxy.split(","))
                if target_host and target_host not in no_proxy_list:
                    no_proxy_list.append(target_host)
                if "*" not in no_proxy_list:
                    no_proxy_list.append("*")
                
                os.environ["NO_PROXY"] = ",".join(no_proxy_list)
                os.environ["no_proxy"] = ",".join(no_proxy_list)
                
                # 同时清除代理环境变量
                original_proxy = os.environ.pop("HTTP_PROXY", None)
                original_https_proxy = os.environ.pop("HTTPS_PROXY", None)
                original_http_proxy = os.environ.pop("http_proxy", None)
                original_https_proxy_lower = os.environ.pop("https_proxy", None)
                
                async with httpx.AsyncClient(
                    timeout=DEFAULT_TIMEOUT
                ) as client:
                    response = await client.get(target, headers=headers)
                    response.raise_for_status()
            finally:
                # 恢复原始环境变量
                if original_no_proxy:
                    os.environ["NO_PROXY"] = original_no_proxy
                elif "NO_PROXY" in os.environ:
                    del os.environ["NO_PROXY"]
                if original_no_proxy_lower:
                    os.environ["no_proxy"] = original_no_proxy_lower
                elif "no_proxy" in os.environ:
                    del os.environ["no_proxy"]
                if original_proxy is not None:
                    os.environ["HTTP_PROXY"] = original_proxy
                if original_https_proxy is not None:
                    os.environ["HTTPS_PROXY"] = original_https_proxy
                if original_http_proxy is not None:
                    os.environ["http_proxy"] = original_http_proxy
                if original_https_proxy_lower is not None:
                    os.environ["https_proxy"] = original_https_proxy_lower
            message = f"{system.upper()} 运行正常"
            if system in ["elk", "elasticsearch"]:
                try:
                    data = response.json()
                    cluster_status = data.get("status", "unknown")
                    message = f"Elasticsearch 集群状态: {cluster_status}"
                except Exception:
                    pass  # 如果 JSON 解析失败，使用默认消息
            return ClusterHealthResult(name="logging", status="ok", message=message)
        except httpx.ConnectError as exc:
            error_msg = f"连接失败: 无法连接到 {endpoint}，请检查网络连接和地址是否正确"
            logger.warning("Logging system health check failed (ConnectError): %s", str(exc))
            return ClusterHealthResult(name="logging", status="error", message=error_msg)
        except httpx.TimeoutException as exc:
            error_msg = f"连接超时: 请求 {endpoint} 超时，请检查网络或增加超时时间"
            logger.warning("Logging system health check failed (Timeout): %s", str(exc))
            return ClusterHealthResult(name="logging", status="error", message=error_msg)
        except httpx.HTTPStatusError as exc:
            error_msg = f"HTTP 错误: {exc.response.status_code} - {exc.response.text[:100]}"
            logger.warning("Logging system health check failed (HTTP %s): %s", exc.response.status_code, str(exc))
            return ClusterHealthResult(name="logging", status="error", message=error_msg)
        except Exception as exc:  # pylint: disable=broad-except
            error_msg = f"未知错误: {str(exc) or type(exc).__name__}"
            logger.warning("Logging system health check failed: %s", exc, exc_info=True)
            return ClusterHealthResult(name="logging", status="error", message=error_msg)

    def _encrypt_sensitive_fields(self, payload: Dict[str, Any]) -> None:
        for field in self.SENSITIVE_FIELDS:
            if field in payload and payload[field]:
                payload[field] = crypto_manager.encrypt_text(payload[field])

    def _log_operation(self, operation_type: str, resource_id: int, description: str) -> None:
        try:
            log = OperationLog(
                operation_type=operation_type,
                operation_description=description,
                resource_type="cluster_config",
                resource_id=resource_id,
            )
            self.db.add(log)
            self.db.commit()
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("记录操作日志失败: %s", exc)


class DiagnosisRecordService(BaseService[DiagnosisRecord]):
    """诊断记录服务"""

    def __init__(self, db: Session):
        super().__init__(db, DiagnosisRecord)

    async def create_record(self, data: Dict[str, Any]) -> DiagnosisRecord:
        if "events" not in data:
            data["events"] = []
        return await self.create(data)

    async def update_status(self, record_id: int, status: str) -> Optional[DiagnosisRecord]:
        record = await self.get(record_id)
        if not record:
            return None
        record.status = status
        if status in ("completed", "failed"):
            record.completed_at = datetime.utcnow()  # type: ignore[name-defined]
        self.db.commit()
        self.db.refresh(record)
        return record

    async def append_event(self, record_id: int, event: Dict[str, Any]) -> Optional[DiagnosisRecord]:
        record = await self.get(record_id)
        if not record:
            return None
        events = record.events or []
        events.append(event)
        record.events = events
        self.db.commit()
        self.db.refresh(record)
        return record

    async def save_feedback(
        self,
        record_id: int,
        feedback_entry: Dict[str, Any],
        state_updates: Optional[Dict[str, Any]] = None,
        record: Optional[DiagnosisRecord] = None,
    ) -> Optional[DiagnosisRecord]:
        record_obj = record or await self.get(record_id)
        if not record_obj:
            return None
        existing = record_obj.feedback or {}
        history = existing.get("history", [])
        history.append(feedback_entry)
        # 只保留最近 20 条历史记录，避免无限增长
        existing["history"] = history[-20:]
        existing["latest"] = feedback_entry
        if state_updates:
            state = existing.get("state", {})
            # 只更新非空字段
            for key, value in state_updates.items():
                if value is not None:
                    state[key] = value
            existing["state"] = state
        record_obj.feedback = existing
        self.db.commit()
        self.db.refresh(record_obj)
        return record_obj

    async def get_with_relations(self, record_id: int) -> Optional[DiagnosisRecord]:
        return (
            self.db.query(self.model)
            .options(
                joinedload(self.model.iterations).joinedload(DiagnosisIteration.memories),
                joinedload(self.model.memories),
            )
            .filter(self.model.id == record_id, self.model.is_deleted == False)  # noqa: E712
            .first()
        )

    async def list_records(self, skip: int = 0, limit: int = 20) -> Tuple[List[DiagnosisRecord], int]:
        query = (
            self.db.query(self.model)
            .options(
                joinedload(self.model.iterations).joinedload(DiagnosisIteration.memories),
                joinedload(self.model.memories),
            )
            .filter(self.model.is_deleted == False)  # noqa: E712
        )
        total = query.count()
        items = query.order_by(self.model.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    async def delete_record(self, record_id: int) -> bool:
        record = (
            self.db.query(self.model)
            .filter(self.model.id == record_id)
            .first()
        )
        if not record:
            return False

        # 检查是否已沉淀到知识库，如果是则删除 OpenSearch 中的索引
        symptoms = record.symptoms or {}
        if symptoms.get("knowledge_sedimented"):
            try:
                from app.services.opensearch_service import OpenSearchService
                opensearch_service = OpenSearchService()
                # 诊断记录使用 record.id 作为 chunk_id 存储到 OpenSearch
                await opensearch_service.delete_document_chunk(record.id)
                logger.info(f"已删除诊断记录在 OpenSearch 中的索引: diagnosis_id={record.id}, chunk_id={record.id}")
            except Exception as e:
                logger.warning(f"删除诊断记录 OpenSearch 索引失败: {e}，但继续执行数据库删除")

        if not record.is_deleted:
            record.is_deleted = True
            record.deleted_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(record)

        # 硬删除（级联删除相关迭代、记忆等数据）
        self.db.delete(record)
        self.db.commit()
        return True


class ResourceSnapshotService(BaseService[ResourceSnapshot]):
    """资源快照服务"""

    def __init__(self, db: Session):
        super().__init__(db, ResourceSnapshot)

    async def upsert_snapshot(self, payload: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """插入或更新快照，处理并发冲突"""
        # 先尝试查询现有记录（包括已删除的，因为唯一约束包含 cluster_id 和 resource_uid）
        # 注意：唯一约束 uk_snapshot_uid 只包含 cluster_id 和 resource_uid，不包括 is_deleted
        # 所以即使记录是已删除的（is_deleted=True），也不能插入新记录，需要恢复已删除的记录
        query = (
            self.db.query(self.model)
            .filter(
                self.model.cluster_id == payload["cluster_id"],
                self.model.resource_uid == payload["resource_uid"],
            )
            .order_by(self.model.created_at.desc())
        )
        existing = query.first()
        change_type = "created"
        diff: Dict[str, Any] = {}

        if existing:
            # 记录已存在，更新（包括恢复已删除的记录）
            if existing.is_deleted:
                # 记录是已删除的，恢复它
                change_type = "created"  # 恢复操作视为创建
                logger.debug(
                    f"恢复已删除的快照: 集群={payload['cluster_id']}, "
                    f"资源UID={payload['resource_uid']}"
                )
            else:
                # 记录未删除，检查是否有变更
                change_type = "none"
                if self._is_snapshot_changed(existing, payload):
                    change_type = "updated"
                    diff = self._build_diff(existing, payload)
            
            # 更新所有字段（包括恢复 is_deleted = False）
            for key, value in payload.items():
                setattr(existing, key, value)
            # 确保 is_deleted = False（恢复已删除的记录）
            existing.is_deleted = False
            try:
                self.db.commit()
                self.db.refresh(existing)
                return change_type, diff
            except IntegrityError as exc:
                # 并发更新冲突，回滚并重新查询
                self.db.rollback()
                logger.warning(
                    f"快照更新并发冲突，重新查询: 集群={payload['cluster_id']}, "
                    f"资源UID={payload['resource_uid']}, 错误={exc}"
                )
                # 重新构建查询并查询（包括已删除的，可能已被其他事务更新）
                existing = (
                    self.db.query(self.model)
                    .filter(
                        self.model.cluster_id == payload["cluster_id"],
                        self.model.resource_uid == payload["resource_uid"],
                    )
                    .order_by(self.model.created_at.desc())
                    .first()
                )
                if existing:
                    if existing.is_deleted:
                        change_type = "created"  # 恢复操作视为创建
                    else:
                        change_type = "none"
                        if self._is_snapshot_changed(existing, payload):
                            change_type = "updated"
                            diff = self._build_diff(existing, payload)
                    for key, value in payload.items():
                        setattr(existing, key, value)
                    # 确保 is_deleted = False（恢复已删除的记录）
                    existing.is_deleted = False
                    self.db.commit()
                    self.db.refresh(existing)
                    return change_type, diff
                # 如果重新查询后仍不存在，继续下面的插入逻辑

        # 记录不存在，尝试插入
        try:
            await self.create(payload)
            return "created", {}
        except IntegrityError as exc:
            # 并发插入冲突（两个请求同时插入），回滚并重新查询
            self.db.rollback()
            logger.warning(
                f"快照插入并发冲突，重新查询并更新: 集群={payload['cluster_id']}, "
                f"资源UID={payload['resource_uid']}, 错误={exc}"
            )
            # 重新构建查询并查询（包括已删除的，可能已被其他事务插入）
            existing = (
                self.db.query(self.model)
                .filter(
                    self.model.cluster_id == payload["cluster_id"],
                    self.model.resource_uid == payload["resource_uid"],
                )
                .order_by(self.model.created_at.desc())
                .first()
            )
            if existing:
                # 已存在（可能是已删除的记录），恢复并更新
                if existing.is_deleted:
                    change_type = "created"  # 恢复操作视为创建
                    logger.debug(
                        f"恢复已删除的快照（并发冲突后）: 集群={payload['cluster_id']}, "
                        f"资源UID={payload['resource_uid']}"
                    )
                else:
                    change_type = "none"
                    if self._is_snapshot_changed(existing, payload):
                        change_type = "updated"
                        diff = self._build_diff(existing, payload)
                for key, value in payload.items():
                    setattr(existing, key, value)
                # 确保 is_deleted = False（恢复已删除的记录）
                existing.is_deleted = False
                self.db.commit()
                self.db.refresh(existing)
                return change_type, diff
            else:
                # 仍然不存在（异常情况），重新抛出异常
                logger.error(
                    f"快照插入失败且重新查询后仍不存在: 集群={payload['cluster_id']}, "
                    f"资源UID={payload['resource_uid']}"
                )
                raise

    async def mark_absent(
        self,
        cluster_id: int,
        resource_type: str,
        namespace: Optional[str],
        existing_uids: Set[str],
    ) -> List[Dict[str, Any]]:
        query = (
            self.db.query(self.model)
            .filter(
                self.model.cluster_id == cluster_id,
                self.model.resource_type == resource_type,
                self.model.namespace == namespace,
                self.model.is_deleted == False,  # noqa: E712
            )
        )
        deleted_records: List[Dict[str, Any]] = []
        for snapshot in query.all():
            if snapshot.resource_uid not in existing_uids:
                snapshot.is_deleted = True
                deleted_records.append(
                    {
                        "resource_uid": snapshot.resource_uid,
                        "diff": {"previous_version": snapshot.resource_version, "status": snapshot.status},
                    }
                )
        if deleted_records:
            self.db.commit()
        return deleted_records

    async def delete_snapshot(self, cluster_id: int, resource_uid: str) -> Optional[Dict[str, Any]]:
        snapshot = (
            self.db.query(self.model)
            .filter(
                self.model.cluster_id == cluster_id,
                self.model.resource_uid == resource_uid,
                self.model.is_deleted == False,  # noqa: E712
            )
            .first()
        )
        if not snapshot:
            return None
        snapshot.is_deleted = True
        self.db.commit()
        self.db.refresh(snapshot)
        return {
            "resource_uid": snapshot.resource_uid,
            "diff": {"status": snapshot.status, "resource_version": snapshot.resource_version},
        }

    @staticmethod
    def _is_snapshot_changed(existing: ResourceSnapshot, payload: Dict[str, Any]) -> bool:
        tracked_fields = ["resource_version", "spec", "status", "labels", "annotations"]
        for field in tracked_fields:
            if getattr(existing, field) != payload.get(field):
                return True
        if existing.snapshot != payload.get("snapshot"):
            return True
        return False

    @staticmethod
    def _build_diff(existing: ResourceSnapshot, payload: Dict[str, Any]) -> Dict[str, Any]:
        diff: Dict[str, Any] = {}
        if existing.spec != payload.get("spec"):
            diff["spec"] = {"before": existing.spec, "after": payload.get("spec")}
        if existing.status != payload.get("status"):
            diff["status"] = {"before": existing.status, "after": payload.get("status")}
        if existing.labels != payload.get("labels"):
            diff["labels"] = {"before": existing.labels, "after": payload.get("labels")}
        if existing.annotations != payload.get("annotations"):
            diff["annotations"] = {"before": existing.annotations, "after": payload.get("annotations")}
        if existing.resource_version != payload.get("resource_version"):
            diff["resource_version"] = {"before": existing.resource_version, "after": payload.get("resource_version")}
        return diff
