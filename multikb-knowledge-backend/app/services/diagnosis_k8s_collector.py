"""
Diagnosis K8s resource collector service.
负责收集 K8s 相关资源信息：扩展诊断范围、深度诊断、历史对比分析
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from app.core.logging import logger
from app.models.cluster_config import ClusterConfig
from app.services.cluster_config_service import ResourceSnapshotService
from app.services.metrics_service import PrometheusMetricsService
from app.services.resource_sync_service import KubernetesResourceSyncService


class DiagnosisK8sCollector:
    """诊断 K8s 资源收集器"""

    def __init__(self, db, record_service, memory_service):
        self.db = db
        self.record_service = record_service
        self.memory_service = memory_service

    async def check_k8s_resources_collected(self, diagnosis_id: int) -> bool:
        """检查是否已经收集过相关 K8s 资源"""
        memories = await self.memory_service.list_by_diagnosis(diagnosis_id)
        for memory in memories:
            if memory.memory_type == "k8s_resource":
                return True
        return False

    async def collect_related_k8s_resources(
        self,
        record: Any,
        cluster: ClusterConfig,
        runtime: Dict[str, Any],
        context: Dict[str, Any],
        iteration: Any,
        make_event_func,
    ) -> None:
        """
        收集与 Pod 相关的 K8s 资源信息，用于扩展诊断范围
        
        收集的资源类型：
        - Deployment/StatefulSet (Pod 的控制器)
        - Service (服务发现)
        - ConfigMap/Secret (配置)
        - Node (节点状态)
        - ResourceQuota (资源配额)
        - NetworkPolicy (网络策略)
        - PVC (持久化存储)
        """
        namespace = context.get("namespace") or "default"
        pod_name = context.get("resource_name")
        iteration_no = iteration.iteration_no
        
        await self.record_service.append_event(
            record.id,
            make_event_func(
                "expand_scope",
                f"[迭代 {iteration_no}] 开始收集相关 K8s 资源信息",
                "info",
            ),
        )
        
        snapshot_service = ResourceSnapshotService(self.db)
        sync_service = KubernetesResourceSyncService(cluster, snapshot_service, runtime)
        
        collected_resources: Dict[str, Any] = {}
        
        try:
            # 1. 获取 Pod 详细信息，提取关联信息
            pod_detail = await sync_service.fetch_resource_detail("pods", namespace, pod_name)
            pod_metadata = pod_detail.get("metadata", {})
            pod_spec = pod_detail.get("spec", {})
            pod_status = pod_detail.get("status", {})
            
            # 提取 Pod 的标签和所有者引用
            labels = pod_metadata.get("labels", {})
            owner_refs = pod_metadata.get("ownerReferences", [])
            node_name = pod_spec.get("nodeName")
            
            collected_resources["pod"] = {
                "name": pod_name,
                "labels": labels,
                "node": node_name,
                "phase": pod_status.get("phase"),
                "conditions": pod_status.get("conditions", []),
            }
            
            # 2. 收集 Deployment/StatefulSet (通过 ownerReferences)
            for owner_ref in owner_refs:
                owner_kind = owner_ref.get("kind", "").lower()
                owner_name = owner_ref.get("name")
                
                if owner_kind in ["deployment", "statefulset", "daemonset"]:
                    resource_type = f"{owner_kind}s"
                    try:
                        resource_detail = await sync_service.fetch_resource_detail(
                            resource_type, namespace, owner_name
                        )
                        collected_resources[resource_type] = {
                            "name": owner_name,
                            "spec": resource_detail.get("spec", {}),
                            "status": resource_detail.get("status", {}),
                        }
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.warning("Failed to fetch %s %s: %s", resource_type, owner_name, exc)
            
            # 3. 收集 Service (通过标签选择器匹配)
            try:
                services = await sync_service._fetch_resource("services", namespace, None, None)
                matching_services = []
                for svc in services.get("items", []):
                    svc_spec = svc.get("spec", {})
                    selector = svc_spec.get("selector", {})
                    # 检查 Service 的 selector 是否匹配 Pod 的 labels
                    if selector and all(labels.get(k) == v for k, v in selector.items()):
                        matching_services.append({
                            "name": svc.get("metadata", {}).get("name"),
                            "spec": svc_spec,
                        })
                if matching_services:
                    collected_resources["services"] = matching_services
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Failed to fetch services: %s", exc)
            
            # 4. 收集 ConfigMap 和 Secret (从 Pod spec 中提取)
            configmaps = set()
            secrets = set()
            
            # 从 volumes 中提取
            volumes = pod_spec.get("volumes", [])
            for volume in volumes:
                cm_source = volume.get("configMap")
                if cm_source:
                    configmaps.add(cm_source.get("name"))
                secret_source = volume.get("secret")
                if secret_source:
                    secrets.add(secret_source.get("secretName"))
            
            # 从 containers 的 envFrom 中提取
            containers = pod_spec.get("containers", [])
            for container in containers:
                env_from = container.get("envFrom", [])
                for env in env_from:
                    if env.get("configMapRef"):
                        configmaps.add(env["configMapRef"].get("name"))
                    if env.get("secretRef"):
                        secrets.add(env["secretRef"].get("name"))
            
            # 获取 ConfigMap 详情
            if configmaps:
                collected_resources["configmaps"] = []
                for cm_name in configmaps:
                    try:
                        cm_detail = await sync_service.fetch_resource_detail("configmaps", namespace, cm_name)
                        collected_resources["configmaps"].append({
                            "name": cm_name,
                            "data": cm_detail.get("data", {}),
                        })
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.warning("Failed to fetch ConfigMap %s: %s", cm_name, exc)
            
            # 获取 Secret 详情（不包含敏感数据）
            if secrets:
                collected_resources["secrets"] = []
                for secret_name in secrets:
                    try:
                        secret_detail = await sync_service.fetch_resource_detail("secrets", namespace, secret_name)
                        # 不保存敏感数据，只保存元数据
                        collected_resources["secrets"].append({
                            "name": secret_name,
                            "type": secret_detail.get("type"),
                            "keys": list(secret_detail.get("data", {}).keys()) if secret_detail.get("data") else [],
                        })
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.warning("Failed to fetch Secret %s: %s", secret_name, exc)
            
            # 5. 收集 Node 信息
            if node_name:
                try:
                    node_detail = await sync_service.fetch_resource_detail("nodes", None, node_name)
                    collected_resources["node"] = {
                        "name": node_name,
                        "status": node_detail.get("status", {}),
                        "spec": {
                            "taints": node_detail.get("spec", {}).get("taints", []),
                            "unschedulable": node_detail.get("spec", {}).get("unschedulable", False),
                        },
                    }
                except Exception as exc:  # pylint: disable=broad-except
                    logger.warning("Failed to fetch Node %s: %s", node_name, exc)
            
            # 6. 收集 ResourceQuota (命名空间级别)
            try:
                quotas = await sync_service._fetch_resource("resourcequotas", namespace, None, None)
                if quotas.get("items"):
                    collected_resources["resourcequotas"] = [
                        {
                            "name": q.get("metadata", {}).get("name"),
                            "spec": q.get("spec", {}),
                            "status": q.get("status", {}),
                        }
                        for q in quotas.get("items", [])
                    ]
            except Exception as exc:  # pylint: disable=broad-except
                logger.debug("Failed to fetch ResourceQuota (may not exist): %s", exc)
            
            # 7. 收集 NetworkPolicy (命名空间级别)
            try:
                policies = await sync_service._fetch_resource("networkpolicies", namespace, None, None)
                if policies.get("items"):
                    collected_resources["networkpolicies"] = [
                        {
                            "name": p.get("metadata", {}).get("name"),
                            "spec": p.get("spec", {}),
                        }
                        for p in policies.get("items", [])
                    ]
            except Exception as exc:  # pylint: disable=broad-except
                logger.debug("Failed to fetch NetworkPolicy (may not exist): %s", exc)
            
            # 8. 收集 PVC (从 Pod volumes 中提取)
            pvc_names = set()
            for volume in volumes:
                pvc = volume.get("persistentVolumeClaim")
                if pvc:
                    pvc_names.add(pvc.get("claimName"))
            
            if pvc_names:
                collected_resources["persistentvolumeclaims"] = []
                for pvc_name in pvc_names:
                    try:
                        pvc_detail = await sync_service.fetch_resource_detail(
                            "persistentvolumeclaims", namespace, pvc_name
                        )
                        collected_resources["persistentvolumeclaims"].append({
                            "name": pvc_name,
                            "spec": pvc_detail.get("spec", {}),
                            "status": pvc_detail.get("status", {}),
                        })
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.warning("Failed to fetch PVC %s: %s", pvc_name, exc)
            
            # 保存收集的资源信息到记忆
            await self.memory_service.add_memory(
                record.id,
                memory_type="k8s_resource",
                summary=f"[迭代 {iteration_no}] 收集相关 K8s 资源信息",
                content=collected_resources,
                iteration_id=iteration.id,
                iteration_no=iteration_no,
            )
            
            await self.record_service.append_event(
                record.id,
                make_event_func(
                    "expand_scope",
                    f"[迭代 {iteration_no}] 已收集 {len(collected_resources)} 类相关 K8s 资源",
                    "success",
                ),
            )
            
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("收集相关 K8s 资源失败: %s", exc)
            await self.record_service.append_event(
                record.id,
                make_event_func(
                    "expand_scope",
                    f"[迭代 {iteration_no}] 收集相关 K8s 资源失败: {exc}",
                    "error",
                ),
            )

    async def check_deep_context_collected(self, diagnosis_id: int) -> bool:
        """检查是否已经收集过深度上下文信息"""
        memories = await self.memory_service.list_by_diagnosis(diagnosis_id)
        for memory in memories:
            if memory.memory_type == "deep_context":
                return True
        return False

    async def collect_deep_context(
        self,
        record: Any,
        cluster: ClusterConfig,
        runtime: Dict[str, Any],
        context: Dict[str, Any],
        iteration: Any,
        make_event_func,
        historical_analysis_func,
    ) -> None:
        """
        深度诊断：收集更多上下文信息
        
        当 K8s 资源信息仍无法判断问题时，收集：
        - K8s Events（集群事件）
        - 同一 Deployment 下的其他 Pod
        - 同一节点上的其他 Pod
        - 更长时间范围的指标和日志
        - 命名空间级别的统计信息
        """
        namespace = context.get("namespace") or "default"
        pod_name = context.get("resource_name")
        iteration_no = iteration.iteration_no
        
        await self.record_service.append_event(
            record.id,
            make_event_func(
                "deep_diagnosis",
                f"[迭代 {iteration_no}] 开始深度诊断：收集更多上下文信息",
                "info",
            ),
        )
        
        snapshot_service = ResourceSnapshotService(self.db)
        sync_service = KubernetesResourceSyncService(cluster, snapshot_service, runtime)
        
        deep_context: Dict[str, Any] = {}
        
        try:
            # 1. 收集 K8s Events（与 Pod 和相关资源相关的事件）
            try:
                events = await sync_service._fetch_resource("events", namespace, None, None)
                pod_events = []
                related_events = []
                
                for event in events.get("items", []):
                    involved_object = event.get("involvedObject", {})
                    obj_name = involved_object.get("name", "")
                    obj_kind = involved_object.get("kind", "")
                    
                    # 收集与 Pod 直接相关的事件
                    if obj_kind == "Pod" and obj_name == pod_name:
                        pod_events.append({
                            "type": event.get("type"),
                            "reason": event.get("reason"),
                            "message": event.get("message"),
                            "firstTimestamp": event.get("firstTimestamp"),
                            "lastTimestamp": event.get("lastTimestamp"),
                            "count": event.get("count"),
                        })
                    # 收集与相关资源的事件（Deployment、Node 等）
                    elif obj_kind in ["Deployment", "StatefulSet", "Node", "ReplicaSet"]:
                        related_events.append({
                            "kind": obj_kind,
                            "name": obj_name,
                            "type": event.get("type"),
                            "reason": event.get("reason"),
                            "message": event.get("message"),
                            "firstTimestamp": event.get("firstTimestamp"),
                        })
                
                deep_context["events"] = {
                    "pod_events": pod_events[-20:],  # 最近 20 条
                    "related_events": related_events[-20:],
                }
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Failed to fetch events: %s", exc)
            
            # 2. 获取 Pod 详细信息，提取 Deployment 和 Node 信息
            pod_detail = None
            try:
                pod_detail = await sync_service.fetch_resource_detail("pods", namespace, pod_name)
                pod_metadata = pod_detail.get("metadata", {})
                pod_spec = pod_detail.get("spec", {})
                labels = pod_metadata.get("labels", {})
                owner_refs = pod_metadata.get("ownerReferences", [])
                node_name = pod_spec.get("nodeName")
                
                # 3. 收集同一 Deployment/StatefulSet 下的其他 Pod
                for owner_ref in owner_refs:
                    owner_kind = owner_ref.get("kind", "").lower()
                    owner_name = owner_ref.get("name")
                    
                    if owner_kind in ["deployment", "statefulset"]:
                        resource_type = f"{owner_kind}s"
                        try:
                            # 获取所有 Pod
                            all_pods = await sync_service._fetch_resource("pods", namespace, None, None)
                            related_pods = []
                            
                            for pod in all_pods.get("items", []):
                                pod_meta = pod.get("metadata", {})
                                pod_owner_refs = pod_meta.get("ownerReferences", [])
                                
                                # 检查是否属于同一个控制器
                                for ref in pod_owner_refs:
                                    if ref.get("kind") == owner_ref.get("kind") and ref.get("name") == owner_name:
                                        pod_status = pod.get("status", {})
                                        related_pods.append({
                                            "name": pod_meta.get("name"),
                                            "phase": pod_status.get("phase"),
                                            "node": pod.get("spec", {}).get("nodeName"),
                                            "conditions": pod_status.get("conditions", []),
                                        })
                                        break
                            
                            if related_pods:
                                deep_context["related_pods"] = {
                                    "controller": f"{owner_kind}/{owner_name}",
                                    "pods": related_pods,
                                    "total": len(related_pods),
                                    "healthy": len([p for p in related_pods if p.get("phase") == "Running"]),
                                }
                        except Exception as exc:  # pylint: disable=broad-except
                            logger.warning("Failed to fetch related pods: %s", exc)
                
                # 4. 收集同一节点上的其他 Pod
                if node_name:
                    try:
                        all_pods = await sync_service._fetch_resource("pods", None, None, None)
                        node_pods = []
                        
                        for pod in all_pods.get("items", []):
                            if pod.get("spec", {}).get("nodeName") == node_name:
                                pod_meta = pod.get("metadata", {})
                                pod_status = pod.get("status", {})
                                node_pods.append({
                                    "name": pod_meta.get("name"),
                                    "namespace": pod_meta.get("namespace"),
                                    "phase": pod_status.get("phase"),
                                })
                        
                        if node_pods:
                            deep_context["node_pods"] = {
                                "node": node_name,
                                "pods": node_pods[:20],  # 最多 20 个
                                "total": len(node_pods),
                                "healthy": len([p for p in node_pods if p.get("phase") == "Running"]),
                            }
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.warning("Failed to fetch node pods: %s", exc)
                
                # 5. 收集命名空间级别的统计信息
                try:
                    all_pods = await sync_service._fetch_resource("pods", namespace, None, None)
                    ns_pods = all_pods.get("items", [])
                    
                    phases = {}
                    for pod in ns_pods:
                        phase = pod.get("status", {}).get("phase", "Unknown")
                        phases[phase] = phases.get(phase, 0) + 1
                    
                    deep_context["namespace_stats"] = {
                        "namespace": namespace,
                        "total_pods": len(ns_pods),
                        "pod_phases": phases,
                    }
                except Exception as exc:  # pylint: disable=broad-except
                    logger.warning("Failed to fetch namespace stats: %s", exc)
                
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Failed to collect deep context: %s", exc)
            
            # 6. 历史对比分析
            try:
                historical_analysis = await historical_analysis_func(
                    record, cluster, namespace, pod_name, pod_detail
                )
                if historical_analysis:
                    deep_context["historical_analysis"] = historical_analysis
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Failed to collect historical analysis: %s", exc)
            
            # 保存深度上下文信息到记忆
            if deep_context:
                await self.memory_service.add_memory(
                    record.id,
                    memory_type="deep_context",
                    summary=f"[迭代 {iteration_no}] 深度诊断：收集更多上下文信息",
                    content=deep_context,
                    iteration_id=iteration.id,
                    iteration_no=iteration_no,
                )
                
                await self.record_service.append_event(
                    record.id,
                    make_event_func(
                        "deep_diagnosis",
                        f"[迭代 {iteration_no}] 已收集深度上下文信息：{', '.join(deep_context.keys())}",
                        "success",
                    ),
                )
            
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("深度诊断失败: %s", exc)
            await self.record_service.append_event(
                record.id,
                make_event_func(
                    "deep_diagnosis",
                    f"[迭代 {iteration_no}] 深度诊断失败: {exc}",
                    "error",
                ),
            )

    async def collect_historical_analysis(
        self,
        record: Any,
        cluster: ClusterConfig,
        namespace: Optional[str],
        pod_name: str,
        current_pod_detail: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        历史对比分析：对比问题发生前后的配置和状态变化
        
        Returns:
            包含配置变化、指标对比、状态对比的字典
        """
        analysis: Dict[str, Any] = {}
        snapshot_service = ResourceSnapshotService(self.db)
        
        try:
            # 1. 配置变化对比
            # 获取问题发生前 24 小时的历史快照
            problem_start_time = record.started_at or datetime.utcnow()
            before_time = problem_start_time - timedelta(hours=24)
            
            # 查询 Pod 的历史快照
            historical_snapshots = (
                self.db.query(snapshot_service.model)
                .filter(
                    snapshot_service.model.cluster_id == cluster.id,
                    snapshot_service.model.resource_type == "pods",
                    snapshot_service.model.namespace == namespace,
                    snapshot_service.model.resource_name == pod_name,
                    snapshot_service.model.is_deleted == False,  # noqa: E712
                    snapshot_service.model.updated_at >= before_time,
                    snapshot_service.model.updated_at <= problem_start_time,
                )
                .order_by(snapshot_service.model.updated_at.desc())
                .limit(10)
                .all()
            )
            
            if historical_snapshots:
                # 对比最近的快照和当前快照
                latest_snapshot = historical_snapshots[0]
                config_changes = []
                
                # 对比 spec 变化
                if current_pod_detail:
                    current_spec = current_pod_detail.get("spec", {})
                    historical_spec = latest_snapshot.spec or {}
                    
                    # 对比资源限制
                    current_resources = current_spec.get("containers", [{}])[0].get("resources", {})
                    historical_resources = historical_spec.get("containers", [{}])[0].get("resources", {}) if historical_spec.get("containers") else {}
                    
                    if current_resources != historical_resources:
                        config_changes.append({
                            "field": "resources",
                            "before": historical_resources,
                            "after": current_resources,
                            "change_time": latest_snapshot.updated_at.isoformat() if latest_snapshot.updated_at else None,
                        })
                    
                    # 对比环境变量
                    current_env = current_spec.get("containers", [{}])[0].get("env", [])
                    historical_env = historical_spec.get("containers", [{}])[0].get("env", []) if historical_spec.get("containers") else []
                    
                    if current_env != historical_env:
                        config_changes.append({
                            "field": "env",
                            "before": historical_env,
                            "after": current_env,
                            "change_time": latest_snapshot.updated_at.isoformat() if latest_snapshot.updated_at else None,
                        })
                
                if config_changes:
                    analysis["config_changes"] = {
                        "pod": config_changes,
                        "summary": f"发现 {len(config_changes)} 项配置变更",
                    }
            
            # 2. 状态变化对比
            if historical_snapshots:
                status_changes = []
                for i, snapshot in enumerate(historical_snapshots[:5]):  # 最近 5 个快照
                    if snapshot.status:
                        status_changes.append({
                            "time": snapshot.updated_at.isoformat() if snapshot.updated_at else None,
                            "phase": snapshot.status.get("phase") if isinstance(snapshot.status, dict) else None,
                            "conditions": snapshot.status.get("conditions", []) if isinstance(snapshot.status, dict) else [],
                        })
                
                if status_changes:
                    analysis["status_changes"] = {
                        "timeline": status_changes,
                        "summary": f"记录了 {len(status_changes)} 个状态变化点",
                    }
            
            # 3. 查询 Deployment/StatefulSet 的历史快照（如果有）
            if current_pod_detail:
                owner_refs = current_pod_detail.get("metadata", {}).get("ownerReferences", [])
                for owner_ref in owner_refs:
                    owner_kind = owner_ref.get("kind", "").lower()
                    owner_name = owner_ref.get("name")
                    
                    if owner_kind in ["deployment", "statefulset"]:
                        resource_type = f"{owner_kind}s"
                        controller_snapshots = (
                            self.db.query(snapshot_service.model)
                            .filter(
                                snapshot_service.model.cluster_id == cluster.id,
                                snapshot_service.model.resource_type == resource_type,
                                snapshot_service.model.namespace == namespace,
                                snapshot_service.model.resource_name == owner_name,
                                snapshot_service.model.is_deleted == False,  # noqa: E712
                                snapshot_service.model.updated_at >= before_time,
                            )
                            .order_by(snapshot_service.model.updated_at.desc())
                            .limit(5)
                            .all()
                        )
                        
                        if controller_snapshots and len(controller_snapshots) > 1:
                            # 对比控制器配置变化
                            latest_controller = controller_snapshots[0]
                            previous_controller = controller_snapshots[1] if len(controller_snapshots) > 1 else None
                            
                            if previous_controller:
                                controller_changes = []
                                latest_spec = latest_controller.spec or {}
                                previous_spec = previous_controller.spec or {}
                                
                                # 对比副本数
                                latest_replicas = latest_spec.get("replicas")
                                previous_replicas = previous_spec.get("replicas")
                                if latest_replicas != previous_replicas:
                                    controller_changes.append({
                                        "field": "replicas",
                                        "before": previous_replicas,
                                        "after": latest_replicas,
                                        "change_time": latest_controller.updated_at.isoformat() if latest_controller.updated_at else None,
                                    })
                                
                                # 对比镜像
                                latest_image = latest_spec.get("template", {}).get("spec", {}).get("containers", [{}])[0].get("image")
                                previous_image = previous_spec.get("template", {}).get("spec", {}).get("containers", [{}])[0].get("image")
                                if latest_image != previous_image:
                                    controller_changes.append({
                                        "field": "image",
                                        "before": previous_image,
                                        "after": latest_image,
                                        "change_time": latest_controller.updated_at.isoformat() if latest_controller.updated_at else None,
                                    })
                                
                                if controller_changes:
                                    analysis["config_changes"] = analysis.get("config_changes", {})
                                    analysis["config_changes"][resource_type] = controller_changes
            
            # 4. 指标数据对比（通过 Prometheus 历史数据）
            if cluster.prometheus_url:
                try:
                    metrics_service = PrometheusMetricsService(cluster, {})
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(hours=24)
                    
                    # 获取 24 小时前的指标数据（历史同期）
                    historical_start = start_time - timedelta(days=1)  # 昨天同一时间
                    historical_end = start_time
                    
                    context = {"namespace": namespace or "default", "pod": pod_name, "window": "5m"}
                    step = timedelta(minutes=15)
                    
                    metrics_comparison = {}
                    
                    # 对比 CPU 使用率
                    try:
                        current_cpu = await metrics_service.run_template(
                            "pod_cpu_usage", context, start=start_time, end=end_time, step=step
                        )
                        historical_cpu = await metrics_service.run_template(
                            "pod_cpu_usage", context, start=historical_start, end=historical_end, step=step
                        )
                        
                        if current_cpu and historical_cpu:
                            current_values = [v for v in current_cpu.get("values", []) if v]
                            historical_values = [v for v in historical_cpu.get("values", []) if v]
                            
                            if current_values and historical_values:
                                current_avg = sum(current_values) / len(current_values) if current_values else 0
                                historical_avg = sum(historical_values) / len(historical_values) if historical_values else 0
                                
                                metrics_comparison["cpu_usage"] = {
                                    "current_avg": current_avg,
                                    "historical_avg": historical_avg,
                                    "difference": current_avg - historical_avg,
                                    "change_percent": ((current_avg - historical_avg) / historical_avg * 100) if historical_avg > 0 else 0,
                                }
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.debug("Failed to compare CPU usage: %s", exc)
                    
                    # 对比内存使用率
                    try:
                        current_memory = await metrics_service.run_template(
                            "pod_memory_usage", context, start=start_time, end=end_time, step=step
                        )
                        historical_memory = await metrics_service.run_template(
                            "pod_memory_usage", context, start=historical_start, end=historical_end, step=step
                        )
                        
                        if current_memory and historical_memory:
                            current_values = [v for v in current_memory.get("values", []) if v]
                            historical_values = [v for v in historical_memory.get("values", []) if v]
                            
                            if current_values and historical_values:
                                current_avg = sum(current_values) / len(current_values) if current_values else 0
                                historical_avg = sum(historical_values) / len(historical_values) if historical_values else 0
                                
                                metrics_comparison["memory_usage"] = {
                                    "current_avg": current_avg,
                                    "historical_avg": historical_avg,
                                    "difference": current_avg - historical_avg,
                                    "change_percent": ((current_avg - historical_avg) / historical_avg * 100) if historical_avg > 0 else 0,
                                    "unit": "bytes",
                                }
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.debug("Failed to compare memory usage: %s", exc)
                    
                    # 对比重启频率
                    try:
                        current_restart = await metrics_service.run_template(
                            "pod_restart_rate", context, start=start_time, end=end_time, step=step
                        )
                        historical_restart = await metrics_service.run_template(
                            "pod_restart_rate", context, start=historical_start, end=historical_end, step=step
                        )
                        
                        if current_restart and historical_restart:
                            current_values = [v for v in current_restart.get("values", []) if v]
                            historical_values = [v for v in historical_restart.get("values", []) if v]
                            
                            if current_values and historical_values:
                                current_avg = sum(current_values) / len(current_values) if current_values else 0
                                historical_avg = sum(historical_values) / len(historical_values) if historical_values else 0
                                
                                metrics_comparison["restart_rate"] = {
                                    "current_avg": current_avg,
                                    "historical_avg": historical_avg,
                                    "difference": current_avg - historical_avg,
                                    "change_percent": ((current_avg - historical_avg) / historical_avg * 100) if historical_avg > 0 else 0,
                                    "unit": "restarts/hour",
                                }
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.debug("Failed to compare restart rate: %s", exc)
                    
                    # 对比网络流量（如果 Prometheus 有相关指标）
                    try:
                        network_query = f'sum(rate(container_network_receive_bytes_total{{namespace="{namespace or "default"}",pod="{pod_name}"}}[5m])) by (pod)'
                        current_network_rx = await metrics_service.query_range(
                            network_query, start=start_time, end=end_time, step=step
                        )
                        historical_network_rx = await metrics_service.query_range(
                            network_query, start=historical_start, end=historical_end, step=step
                        )
                        
                        if current_network_rx and historical_network_rx:
                            current_values = []
                            historical_values = []
                            
                            for result in current_network_rx.get("data", {}).get("result", []):
                                values = result.get("values", [])
                                current_values.extend([float(v[1]) for v in values if len(v) > 1])
                            
                            for result in historical_network_rx.get("data", {}).get("result", []):
                                values = result.get("values", [])
                                historical_values.extend([float(v[1]) for v in values if len(v) > 1])
                            
                            if current_values and historical_values:
                                current_avg = sum(current_values) / len(current_values) if current_values else 0
                                historical_avg = sum(historical_values) / len(historical_values) if historical_values else 0
                                
                                metrics_comparison["network_rx"] = {
                                    "current_avg": current_avg,
                                    "historical_avg": historical_avg,
                                    "difference": current_avg - historical_avg,
                                    "change_percent": ((current_avg - historical_avg) / historical_avg * 100) if historical_avg > 0 else 0,
                                    "unit": "bytes/second",
                                }
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.debug("Failed to compare network traffic: %s", exc)
                    
                    if metrics_comparison:
                        analysis["metrics_comparison"] = metrics_comparison
                except Exception as exc:  # pylint: disable=broad-except
                    logger.debug("Failed to compare historical metrics: %s", exc)
            
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Historical analysis failed: %s", exc)
        
        return analysis if analysis else None
