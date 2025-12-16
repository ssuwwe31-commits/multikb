"""
Schemas for Kubernetes observability integration.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.schemas.base import BaseResponseSchema


class ClusterConfigBase(BaseModel):
    name: str = Field(..., description="集群名称")
    description: Optional[str] = Field(None, description="集群描述")
    api_server: HttpUrl = Field(..., description="Kubernetes API Server 地址")
    auth_type: str = Field("token", description="认证方式: token|kubeconfig|basic")
    auth_token: Optional[str] = Field(None, description="Bearer Token")
    kubeconfig: Optional[str] = Field(None, description="kubeconfig 内容")
    client_cert: Optional[str] = Field(None, description="客户端证书 (PEM)")
    client_key: Optional[str] = Field(None, description="客户端私钥 (PEM)")
    ca_cert: Optional[str] = Field(None, description="CA 证书 (PEM)")
    verify_ssl: bool = Field(True, description="是否校验证书")
    prometheus_url: Optional[HttpUrl] = Field(None, description="Prometheus 地址")
    prometheus_auth_type: str = Field("none", description="Prometheus 认证方式")
    prometheus_username: Optional[str] = Field(None, description="Prometheus 用户名")
    prometheus_password: Optional[str] = Field(None, description="Prometheus 密码/Token")
    log_system: Optional[str] = Field(None, description="日志系统类型: elk|loki|custom")
    log_endpoint: Optional[HttpUrl] = Field(None, description="日志系统入口地址")
    log_auth_type: str = Field("none", description="日志系统认证方式")
    log_username: Optional[str] = Field(None, description="日志系统用户名")
    log_password: Optional[str] = Field(None, description="日志系统密码/Token")
    is_active: bool = Field(True, description="是否启用")


class ClusterConfigCreate(ClusterConfigBase):
    pass


class ClusterConfigUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    api_server: Optional[HttpUrl] = None
    auth_type: Optional[str] = None
    auth_token: Optional[str] = None
    kubeconfig: Optional[str] = None
    client_cert: Optional[str] = None
    client_key: Optional[str] = None
    ca_cert: Optional[str] = None
    verify_ssl: Optional[bool] = None
    prometheus_url: Optional[HttpUrl] = None
    prometheus_auth_type: Optional[str] = None
    prometheus_username: Optional[str] = None
    prometheus_password: Optional[str] = None
    log_system: Optional[str] = None
    log_endpoint: Optional[HttpUrl] = None
    log_auth_type: Optional[str] = None
    log_username: Optional[str] = None
    log_password: Optional[str] = None
    is_active: Optional[bool] = None


class ClusterConfigResponse(BaseResponseSchema, ClusterConfigBase):
    last_health_status: str = Field("unknown", description="最近一次健康检查状态")
    last_health_message: Optional[str] = Field(None, description="健康检查信息")
    last_health_checked_at: Optional[datetime] = Field(None, description="健康检查时间")


class ClusterConfigListResponse(BaseModel):
    list: List[ClusterConfigResponse]
    total: int
    page: int
    size: int


class ClusterHealthResult(BaseModel):
    name: str
    status: str
    message: Optional[str] = None


class ClusterConnectivityResult(BaseModel):
    api_server: ClusterHealthResult
    prometheus: Optional[ClusterHealthResult] = None
    logging: Optional[ClusterHealthResult] = None


class ClusterConnectivityRequest(BaseModel):
    api_server: Optional[str] = None
    auth_type: Optional[str] = None
    auth_token: Optional[str] = None
    kubeconfig: Optional[str] = None
    client_cert: Optional[str] = None
    client_key: Optional[str] = None
    ca_cert: Optional[str] = None
    verify_ssl: Optional[bool] = None
    prometheus_url: Optional[str] = None
    prometheus_auth_type: Optional[str] = None
    prometheus_username: Optional[str] = None
    prometheus_password: Optional[str] = None
    log_system: Optional[str] = None
    log_endpoint: Optional[str] = None
    log_auth_type: Optional[str] = None
    log_username: Optional[str] = None
    log_password: Optional[str] = None


class DiagnosisRecordBase(BaseModel):
    cluster_id: int
    namespace: Optional[str] = None
    resource_type: Optional[str] = None
    resource_name: Optional[str] = None
    trigger_source: str = "manual"
    trigger_payload: Optional[Dict[str, Any]] = None
    symptoms: Optional[Dict[str, Any]] = None
    status: str = "pending"
    summary: Optional[str] = None
    conclusion: Optional[str] = None
    confidence: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None
    logs: Optional[Dict[str, Any]] = None
    recommendations: Optional[Dict[str, Any]] = None
    knowledge_refs: Optional[List[int]] = None
    knowledge_source: Optional[str] = None
    events: Optional[List[Dict[str, Any]]] = None
    feedback: Optional[Dict[str, Any]] = None


class DiagnosisRecordCreate(DiagnosisRecordBase):
    pass


class DiagnosisRecordUpdate(BaseModel):
    status: Optional[str] = None
    summary: Optional[str] = None
    conclusion: Optional[str] = None
    confidence: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None
    logs: Optional[Dict[str, Any]] = None
    recommendations: Optional[Dict[str, Any]] = None
    knowledge_refs: Optional[List[int]] = None
    knowledge_source: Optional[str] = None
    events: Optional[List[Dict[str, Any]]] = None
    feedback: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None


class DiagnosisIterationResponse(BaseResponseSchema):
    diagnosis_id: int
    iteration_no: int
    stage: Optional[str] = None
    status: str
    reasoning_prompt: Optional[str] = None
    reasoning_summary: Optional[str] = None
    reasoning_output: Optional[Any] = None
    action_plan: Optional[Any] = None
    action_result: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="扩展信息",
        validation_alias="meta",
        serialization_alias="meta",
    )


class DiagnosisMemoryResponse(BaseResponseSchema):
    diagnosis_id: int
    iteration_id: Optional[int] = None
    iteration_no: Optional[int] = None
    memory_type: str
    summary: Optional[str] = None
    content: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="附加信息",
        validation_alias="meta",
        serialization_alias="meta",
    )


class DiagnosisRecordResponse(BaseResponseSchema, DiagnosisRecordBase):
    started_at: datetime
    completed_at: Optional[datetime] = None
    iterations: List[DiagnosisIterationResponse] = Field(default_factory=list)
    memories: List[DiagnosisMemoryResponse] = Field(default_factory=list)


class DiagnosisRecordListResponse(BaseModel):
    list: List[DiagnosisRecordResponse]
    total: int
    page: int
    size: int


class DiagnosisIterationListResponse(BaseModel):
    list: List[DiagnosisIterationResponse]
    total: int


class DiagnosisMemoryListResponse(BaseModel):
    list: List[DiagnosisMemoryResponse]
    total: int


class ResourceSyncRequest(BaseModel):
    namespace: Optional[str] = Field(None, description="命名空间，为空则默认命名空间")
    resource_types: List[str] = Field(default_factory=lambda: ["pods", "deployments"])
    limit: Optional[int] = Field(None, description="每种资源拉取数量限制")


class ResourceSnapshotResponse(BaseModel):
    id: int
    cluster_id: int
    resource_type: str
    namespace: Optional[str]
    resource_uid: str
    resource_name: Optional[str]
    labels: Optional[Dict[str, Any]]
    annotations: Optional[Dict[str, Any]]
    spec: Optional[Dict[str, Any]]
    status: Optional[Dict[str, Any]]
    resource_version: Optional[str]
    snapshot: Dict[str, Any]
    collected_at: Optional[datetime]
    updated_at: datetime


class ResourceSnapshotListResponse(BaseModel):
    list: List[ResourceSnapshotResponse]
    total: int
    page: int
    size: int


class MetricsQueryRequest(BaseModel):
    cluster_id: int
    promql: Optional[str] = None
    template_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    step_seconds: Optional[int] = Field(None, description="步长，单位秒")


class MetricsQueryResponse(BaseModel):
    status: str
    data: Dict[str, Any]


class LogQueryRequest(BaseModel):
    cluster_id: int
    query: str
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    limit: int = 100
    page: int = 1
    page_size: Optional[int] = None
    highlight: bool = False
    stats: bool = False


class LogQueryResponse(BaseModel):
    backend: str
    results: List[Dict[str, Any]]
    pagination: Dict[str, Any]
    stats: Optional[Dict[str, Any]] = None
    raw: Dict[str, Any]


class DiagnosisTriggerRequest(BaseModel):
    cluster_id: int
    namespace: Optional[str] = None
    resource_type: str = "pods"
    resource_name: str
    trigger_source: str = "manual"
    trigger_payload: Optional[Dict[str, Any]] = None
    time_range_hours: Optional[float] = Field(2.0, ge=0.1, le=168, description="监控数据时间范围（小时），默认2小时，范围0.1-168小时（7天）")


class DiagnosisFeedbackRequest(BaseModel):
    feedback_type: Literal["confirmed", "continue_investigation", "custom"] = Field(
        ..., description="反馈类型：已确认 / 继续排查 / 其他"
    )
    feedback_notes: Optional[str] = Field(None, description="反馈备注或说明")
    action_taken: Optional[str] = Field(None, description="已采取的行动")
    iteration_no: Optional[int] = Field(
        None, ge=1, description="关联的迭代序号（为空时默认取最后一轮）"
    )

    @model_validator(mode="after")
    def validate_notes(cls, values: "DiagnosisFeedbackRequest") -> "DiagnosisFeedbackRequest":
        if values.feedback_type in {"continue_investigation", "custom"}:
            if not values.feedback_notes or not values.feedback_notes.strip():
                raise ValueError("continue_investigation/custom 反馈必须填写备注")
        return values
