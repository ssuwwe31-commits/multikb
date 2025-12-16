"""
Routes for Kubernetes observability integration.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.dependencies.database import get_db
from app.dependencies.auth import require_observability_access
from app.schemas.observability import (
    ClusterConfigCreate,
    ClusterConfigUpdate,
    ClusterConnectivityRequest,
    DiagnosisRecordCreate,
    DiagnosisRecordUpdate,
    DiagnosisRecordResponse,
    DiagnosisRecordListResponse,
    DiagnosisIterationListResponse,
    DiagnosisIterationResponse,
    DiagnosisMemoryListResponse,
    DiagnosisMemoryResponse,
    ResourceSyncRequest,
    ResourceSnapshotListResponse,
    ResourceSnapshotResponse,
    MetricsQueryRequest,
    MetricsQueryResponse,
    LogQueryRequest,
    LogQueryResponse,
    DiagnosisTriggerRequest,
    DiagnosisFeedbackRequest,
)
from app.services.cluster_config_service import (
    ClusterConfigService,
    DiagnosisRecordService,
    ResourceSnapshotService,
)
from app.services.diagnosis_iteration_service import DiagnosisIterationService, DiagnosisMemoryService
from app.services.resource_sync_service import KubernetesResourceSyncService, list_snapshots
from app.services.metrics_service import PrometheusMetricsService
from app.services.log_query_service import LogQueryService
from app.services.diagnosis_service import DiagnosisService

router = APIRouter(dependencies=[Depends(require_observability_access)])


@router.get("/clusters", response_model=dict)
async def list_clusters(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """分页获取集群配置"""
    service = ClusterConfigService(db)
    skip = (page - 1) * size
    items, total = await service.list_configs(skip=skip, limit=size)
    payload = {
        "list": [service.serialize_config(item) for item in items],
        "total": total,
        "page": page,
        "size": size,
    }
    return {"code": 0, "message": "ok", "data": payload}


@router.post("/clusters", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_cluster(
    cluster: ClusterConfigCreate,
    db: Session = Depends(get_db),
):
    """创建新的集群配置"""
    service = ClusterConfigService(db)
    created = await service.create_config(cluster)
    logger.info("Created cluster config %s", created.name)
    return {"code": 0, "message": "ok", "data": service.serialize_config(created)}


@router.get("/clusters/{cluster_id}", response_model=dict)
async def get_cluster(
    cluster_id: int,
    db: Session = Depends(get_db),
):
    """获取集群配置详情"""
    service = ClusterConfigService(db)
    cluster = await service.get(cluster_id)
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="集群配置不存在")
    return {"code": 0, "message": "ok", "data": service.serialize_config(cluster)}


@router.put("/clusters/{cluster_id}", response_model=dict)
async def update_cluster(
    cluster_id: int,
    payload: ClusterConfigUpdate,
    db: Session = Depends(get_db),
):
    """更新集群配置"""
    service = ClusterConfigService(db)
    updated = await service.update_config(cluster_id, payload)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="集群配置不存在")
    logger.info("Updated cluster config %s", cluster_id)
    return {"code": 0, "message": "ok", "data": service.serialize_config(updated)}


@router.delete("/clusters/{cluster_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def delete_cluster(
    cluster_id: int,
    hard: bool = Query(True, description="是否硬删除（物理删除），默认True（硬删除）"),
    db: Session = Depends(get_db),
):
    """删除集群配置
    
    - hard=True: 硬删除（默认），物理删除记录，关联数据也会被删除（CASCADE）
    - hard=False: 软删除，只标记为已删除，数据保留
    """
    service = ClusterConfigService(db)
    deleted = await service.delete_config(cluster_id, hard=hard)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="集群配置不存在")
    delete_type = "硬删除" if hard else "软删除"
    logger.info("%s集群配置 %s", delete_type, cluster_id)
    return {"code": 0, "message": "ok", "data": {"id": cluster_id, "hard": hard}}


@router.post("/clusters/{cluster_id}/test", response_model=dict)
async def test_cluster_connectivity(
    cluster_id: int,
    request: Optional[ClusterConnectivityRequest] = Body(None),
    db: Session = Depends(get_db),
):
    """测试集群、Prometheus、日志系统的连通性"""
    service = ClusterConfigService(db)
    cluster = await service.get(cluster_id)
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="集群配置不存在")
    result = await service.test_connectivity(cluster, request)
    return {"code": 0, "message": "ok", "data": result.model_dump()}


@router.post("/clusters/{cluster_id}/health-check", response_model=dict)
async def run_health_check(
    cluster_id: int,
    db: Session = Depends(get_db),
):
    """执行一次健康检查并更新状态"""
    service = ClusterConfigService(db)
    cluster = await service.get(cluster_id)
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="集群配置不存在")
    result = await service.run_health_check(cluster)
    return {"code": 0, "message": "ok", "data": result.model_dump()}


# Diagnosis record endpoints
@router.get("/diagnosis", response_model=dict)
async def list_diagnosis(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """分页获取诊断记录"""
    service = DiagnosisRecordService(db)
    skip = (page - 1) * size
    items, total = await service.list_records(skip=skip, limit=size)
    payload = DiagnosisRecordListResponse(
        list=[DiagnosisRecordResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )
    return {"code": 0, "message": "ok", "data": payload.model_dump()}


@router.post("/diagnosis", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_diagnosis(
    payload: DiagnosisRecordCreate,
    db: Session = Depends(get_db),
):
    """创建诊断记录"""
    service = DiagnosisRecordService(db)
    created = await service.create_record(payload.dict())
    return {"code": 0, "message": "ok", "data": DiagnosisRecordResponse.model_validate(created).model_dump()}


@router.get("/diagnosis/{record_id}", response_model=dict)
async def get_diagnosis(
    record_id: int,
    db: Session = Depends(get_db),
):
    """获取诊断记录详情（包含迭代历史和上下文记忆）"""
    from app.core.logging import logger
    service = DiagnosisRecordService(db)
    record = await service.get_with_relations(record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="诊断记录不存在")
    
    # 调试日志：检查 symptoms 是否包含 config
    symptoms = record.symptoms
    symptoms_type = type(symptoms).__name__ if symptoms else None
    has_symptoms = bool(symptoms)
    symptoms_keys = list(symptoms.keys()) if isinstance(symptoms, dict) else []
    has_config = isinstance(symptoms, dict) and "config" in symptoms if symptoms else False
    config_keys_count = len(symptoms.get("config")) if isinstance(symptoms, dict) and isinstance(symptoms.get("config"), dict) else 0
    
    logger.warning(
        f"[API调试] GET /diagnosis/{record_id}: "
        f"has_symptoms={has_symptoms}, symptoms_type={symptoms_type}, "
        f"symptoms_keys={symptoms_keys[:15]}, has_config={has_config}, "
        f"config_keys_count={config_keys_count}"
    )
    
    response_data = DiagnosisRecordResponse.model_validate(record).model_dump()
    
    # 再次验证响应数据中的 symptoms
    response_symptoms = response_data.get("symptoms")
    response_has_config = isinstance(response_symptoms, dict) and "config" in response_symptoms if response_symptoms else False
    response_config_keys_count = len(response_symptoms.get("config")) if isinstance(response_symptoms, dict) and isinstance(response_symptoms.get("config"), dict) else 0
    
    logger.warning(
        f"[API调试] GET /diagnosis/{record_id} 响应数据: "
        f"response_has_symptoms={bool(response_symptoms)}, "
        f"response_has_config={response_has_config}, "
        f"response_config_keys_count={response_config_keys_count}"
    )
    
    return {"code": 0, "message": "ok", "data": response_data}


@router.put("/diagnosis/{record_id}", response_model=dict)
async def update_diagnosis(
    record_id: int,
    payload: DiagnosisRecordUpdate,
    db: Session = Depends(get_db),
):
    """更新诊断记录"""
    service = DiagnosisRecordService(db)
    updated = await service.update(record_id, payload.dict(exclude_unset=True, exclude_none=True))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="诊断记录不存在")
    return {"code": 0, "message": "ok", "data": DiagnosisRecordResponse.model_validate(updated).model_dump()}


@router.delete("/diagnosis/{record_id}", response_model=dict)
async def delete_diagnosis(
    record_id: int,
    db: Session = Depends(get_db),
):
    """删除诊断记录（软删除）"""
    service = DiagnosisRecordService(db)
    deleted = await service.delete_record(record_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="诊断记录不存在")
    logger.info("删除诊断记录: %s", record_id)
    return {"code": 0, "message": "删除成功"}


@router.post("/clusters/{cluster_id}/sync", response_model=dict)
async def sync_cluster_resources(
    cluster_id: int,
    payload: ResourceSyncRequest,
    db: Session = Depends(get_db),
):
    """手动触发集群资源同步"""
    cluster_service = ClusterConfigService(db)
    cluster = await cluster_service.get(cluster_id)
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="集群配置不存在")
    snapshot_service = ResourceSnapshotService(db)
    runtime = cluster_service.build_runtime_payload(cluster)
    sync_service = KubernetesResourceSyncService(cluster, snapshot_service, runtime)
    # 手动同步默认强制全量同步，确保数据完整性
    result = await sync_service.sync_resources(
        payload.namespace, 
        payload.resource_types, 
        payload.limit,
        force_full_sync=True  # 手动同步强制全量
    )
    return {"code": 0, "message": "ok", "data": result}


@router.get("/clusters/{cluster_id}/resources", response_model=dict)
async def get_cluster_resources(
    cluster_id: int,
    resource_type: Optional[str] = Query(None),
    namespace: Optional[str] = Query(None),
    resource_name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """查询资源快照"""
    snapshot_service = ResourceSnapshotService(db)
    skip = (page - 1) * size
    rows, total = await list_snapshots(
        snapshot_service,
        cluster_id=cluster_id,
        resource_type=resource_type,
        namespace=namespace,
        resource_name=resource_name,
        skip=skip,
        limit=size,
    )

    try:
        sample_names = [f"{item.get('namespace')}/{item.get('resource_name')}" for item in rows[:10]]
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("log cluster_resources failed: %s", exc)

    # 确保即使列表为空也正确创建响应对象
    resource_list = [ResourceSnapshotResponse.model_validate(item) for item in rows] if rows else []
    payload = ResourceSnapshotListResponse(
        list=resource_list,
        total=total or 0,
        page=page,
        size=size,
    )
    # 确保返回的data包含所有必要字段，即使列表为空
    data = payload.model_dump()
    # 再次确保字段存在
    if "list" not in data or data.get("list") is None:
        data["list"] = []
    if "total" not in data or data.get("total") is None:
        data["total"] = total or 0
    if "page" not in data:
        data["page"] = page
    if "size" not in data:
        data["size"] = size
    return {"code": 0, "message": "ok", "data": data}


@router.get("/clusters/{cluster_id}/namespaces", response_model=dict)
async def get_cluster_namespaces(
    cluster_id: int,
    db: Session = Depends(get_db),
):
    """实时获取集群的命名空间列表（直接查询 K8s API）"""
    cluster_service = ClusterConfigService(db)
    cluster = await cluster_service.get(cluster_id)
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="集群不存在")
    
    runtime = cluster_service.build_runtime_payload(cluster)
    sync_service = KubernetesResourceSyncService(cluster, ResourceSnapshotService(db), runtime)
    try:
        namespaces = await sync_service._get_all_namespaces()  # noqa: SLF001
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("获取命名空间失败: 集群=%s, 错误=%s", cluster.name, exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取命名空间失败")
    
    return {"code": 0, "message": "ok", "data": namespaces}


@router.get("/clusters/{cluster_id}/pods", response_model=dict)
async def get_cluster_pods(
    cluster_id: int,
    namespace: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """获取集群的 Pod 列表"""
    snapshot_service = ResourceSnapshotService(db)
    query = db.query(snapshot_service.model.resource_name).filter(
        snapshot_service.model.cluster_id == cluster_id,
        snapshot_service.model.resource_type == "pods",
        snapshot_service.model.is_deleted == False,  # noqa: E712
    )
    if namespace:
        query = query.filter(snapshot_service.model.namespace == namespace)
    
    pods = query.order_by(snapshot_service.model.resource_name).distinct().all()
    pod_list = [pod[0] for pod in pods if pod[0]]
    return {"code": 0, "message": "ok", "data": pod_list}


@router.post("/metrics/query", response_model=dict)
async def query_metrics(
    payload: MetricsQueryRequest,
    db: Session = Depends(get_db),
):
    """Prometheus 指标查询"""
    from app.core.exceptions import CustomException, ErrorCode
    
    cluster_service = ClusterConfigService(db)
    cluster = await cluster_service.get(payload.cluster_id)
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="集群配置不存在")
    runtime = cluster_service.build_runtime_payload(cluster)
    try:
        metrics_service = PrometheusMetricsService(cluster, runtime)
    except CustomException:
        # 重新抛出 CustomException（会被全局异常处理器处理）
        raise
    except ValueError as exc:
        # 捕获其他 ValueError 并转换为友好的错误消息
        raise CustomException(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"集群 '{cluster.name}' 未配置 Prometheus 监控地址，请先在集群配置中添加 Prometheus URL"
        ) from exc
    start = payload.start
    end = payload.end
    step = timedelta(seconds=payload.step_seconds) if payload.step_seconds else None

    if payload.template_id:
        context = payload.context or {}
        result = await metrics_service.run_template(payload.template_id, context, start=start, end=end, step=step)
    elif payload.promql:
        if start and end and step:
            result = await metrics_service.query_range(payload.promql, start=start, end=end, step=step)
        else:
            result = await metrics_service.query(payload.promql, time=end)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="必须提供 promql 或 template_id")
    response = MetricsQueryResponse(status=result.get("status", "success"), data=result.get("data", {}))
    return {"code": 0, "message": "ok", "data": response.model_dump()}


@router.post("/logs/query", response_model=dict)
async def query_logs(
    payload: LogQueryRequest,
    db: Session = Depends(get_db),
):
    """日志查询"""
    from app.core.exceptions import CustomException, ErrorCode
    
    cluster_service = ClusterConfigService(db)
    cluster = await cluster_service.get(payload.cluster_id)
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="集群配置不存在")
    runtime = cluster_service.build_runtime_payload(cluster)
    try:
        logs_service = LogQueryService(cluster, runtime)
    except CustomException:
        # 重新抛出 CustomException（会被全局异常处理器处理）
        raise
    except ValueError as exc:
        # 捕获其他 ValueError 并转换为友好的错误消息
        raise CustomException(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"集群 '{cluster.name}' 未配置日志系统地址，请先在集群配置中添加日志系统端点"
        ) from exc
    result = await logs_service.query_logs(
        payload.query,
        start=payload.start,
        end=payload.end,
        limit=payload.limit,
        page=payload.page,
        page_size=payload.page_size,
        highlight=payload.highlight,
        include_stats=payload.stats,
    )
    backend = runtime.get("log_system") or cluster.log_system or "custom"
    response = LogQueryResponse(
        backend=backend,
        results=result.get("results", []),
        pagination=result.get("pagination", {}),
        stats=result.get("stats"),
        raw=result.get("raw", result),
    )
    return {"code": 0, "message": "ok", "data": response.model_dump()}


@router.post("/diagnosis/run", response_model=dict)
async def run_diagnosis(
    payload: DiagnosisTriggerRequest,
    db: Session = Depends(get_db),
):
    """执行诊断流程"""
    service = DiagnosisService(db)
    result = await service.trigger_diagnosis(
        cluster_id=payload.cluster_id,
        namespace=payload.namespace,
        resource_type=payload.resource_type,
        resource_name=payload.resource_name,
        trigger_source=payload.trigger_source,
        trigger_payload=payload.trigger_payload,
        time_range_hours=payload.time_range_hours,
    )
    return {"code": 0, "message": "ok", "data": result.model_dump()}


@router.post("/diagnosis/{record_id}/feedback", response_model=dict)
async def diagnosis_feedback(
    record_id: int,
    payload: DiagnosisFeedbackRequest,
    db: Session = Depends(get_db),
):
    """提交诊断反馈（符合设计文档：feedback 和 action_taken）"""
    diagnosis_service = DiagnosisService(db)
    try:
        response = await diagnosis_service.process_feedback(record_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return {"code": 0, "message": "ok", "data": response.model_dump()}


@router.get("/diagnosis/{record_id}/iterations", response_model=dict)
async def list_diagnosis_iterations(
    record_id: int,
    db: Session = Depends(get_db),
):
    """获取诊断记录的迭代链路。"""
    service = DiagnosisIterationService(db)
    iterations = await service.list_by_diagnosis(record_id)
    response = DiagnosisIterationListResponse(
        list=[DiagnosisIterationResponse.model_validate(item) for item in iterations],
        total=len(iterations),
    )
    return {"code": 0, "message": "ok", "data": response.model_dump()}


@router.get("/diagnosis/{record_id}/memories", response_model=dict)
async def list_diagnosis_memories(
    record_id: int,
    memory_type: Optional[str] = Query(None, description="按记忆类型过滤"),
    db: Session = Depends(get_db),
):
    """获取诊断上下文记忆。"""
    service = DiagnosisMemoryService(db)
    memories = await service.list_by_diagnosis(record_id, memory_type=memory_type)
    response = DiagnosisMemoryListResponse(
        list=[DiagnosisMemoryResponse.model_validate(item) for item in memories],
        total=len(memories),
    )
    return {"code": 0, "message": "ok", "data": response.model_dump()}


@router.get("/diagnosis/{record_id}/report", response_model=dict)
async def get_diagnosis_report(
    record_id: int,
    db: Session = Depends(get_db),
):
    """获取诊断报告（当状态为 pending_human 时）"""
    record_service = DiagnosisRecordService(db)
    record = await record_service.get(record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="诊断记录不存在")
    
    # 从 recommendations 中提取诊断报告
    recommendations = record.recommendations or {}
    report = recommendations.get("diagnosis_report")
    
    if not report:
        # 如果没有报告，返回基本信息
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "has_report": False,
                "message": "该诊断记录尚未生成报告",
                "status": record.status,
            },
        }
    
    return {"code": 0, "message": "ok", "data": {"has_report": True, "report": report}}


@router.post("/alerts/webhook", response_model=dict)
async def alert_webhook(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """接收 Alertmanager 告警并触发诊断"""
    alerts = payload.get("alerts", [])
    diagnosis_service = DiagnosisService(db)
    processed = []
    for alert in alerts:
        labels = alert.get("labels", {})
        cluster_id = labels.get("cluster_id")
        namespace = labels.get("namespace")
        pod = labels.get("pod") or labels.get("pod_name")
        if not cluster_id or not pod:
            continue
        try:
            record = await diagnosis_service.trigger_diagnosis(
                cluster_id=int(cluster_id),
                namespace=namespace,
                resource_type="pods",
                resource_name=pod,
                trigger_source="alert",
                trigger_payload=alert,
            )
            processed.append(record.model_dump())
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Alert diagnosis failed: %s", exc)
    return {"code": 0, "message": "ok", "data": {"processed": processed, "count": len(processed)}}
