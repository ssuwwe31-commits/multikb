"""
Configuration Management
"""

import os
from pathlib import Path
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings  # type: ignore

# 计算项目根目录，确保无论从哪里运行都能找到根目录下的 .env
_CURRENT_DIR = Path(__file__).resolve().parent
_APP_DIR = _CURRENT_DIR.parent
_PROJECT_ROOT = _APP_DIR.parent
_ENV_FILE = _PROJECT_ROOT / ".env"

class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    APP_NAME: str = "SPX Knowledge Base"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_HOSTS: List[str] = ["*"]
    # CORS配置
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"]
    
    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://user:password@localhost:3306/spx_knowledge"
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "user"
    MYSQL_PASSWORD: str = "password"
    MYSQL_DATABASE: str = "spx_knowledge"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    
    # OpenSearch配置
    OPENSEARCH_URL: str = "http://localhost:9200"
    OPENSEARCH_USERNAME: str = ""
    OPENSEARCH_PASSWORD: str = ""
    OPENSEARCH_USE_SSL: bool = False
    OPENSEARCH_VERIFY_CERTS: bool = False
    # OpenSearch 索引与参数（可配置，去除硬编码）
    DOCUMENT_INDEX_NAME: str = "documents"
    IMAGE_INDEX_NAME: str = "images"
    QA_INDEX_NAME: str = "qa_history"
    RESOURCE_EVENTS_INDEX_NAME: str = "resource_events"
    RESOURCE_EVENTS_RETENTION_DAYS: int = 30
    OPENSEARCH_NUMBER_OF_SHARDS: int = 3
    OPENSEARCH_NUMBER_OF_REPLICAS: int = 1
    TEXT_ANALYZER: str = "ik_max_word"
    HNSW_EF_CONSTRUCTION: int = 128
    HNSW_M: int = 24
    KNN_NUM_CANDIDATES_FACTOR: int = 2
    
    # MinIO配置
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "spx-knowledge-base"
    MINIO_SECURE: bool = False
    
    # 向量模型配置
    OLLAMA_BASE_URL: str = "http://192.168.131.158:11434"
    OLLAMA_MODEL: str = "llama2"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    IMAGE_EMBEDDING_MODEL: str = "clip_vit_b32"
    CLIP_MODEL_NAME: str = "ViT-B-32"
    CLIP_MODELS_DIR: str = str((_PROJECT_ROOT / "models" / "clip").resolve())
    CLIP_PRETRAINED_PATH: str = str((_PROJECT_ROOT / "models" / "clip" / "ViT-B-32-openclip.pt").resolve())
    CLIP_CACHE_DIR: str = str((_PROJECT_ROOT / "models" / "clip" / "cache").resolve())
    # Hugging Face 缓存目录（可选，默认使用项目 models/cache 目录）
    HF_HOME: Optional[str] = str((_PROJECT_ROOT / "models" / "cache").resolve())

    IMAGE_PIPELINE_MODE: str = "memory"  # memory|temp
    DEBUG_KEEP_TEMP_FILES: bool = False
    
    # OCR / Qwen VL 配置
    OCR_ENGINE: str = "qwen_vl"
    OCR_MAX_RETRIES: int = 1
    OCR_RETRY_DELAY_SECONDS: int = 0
    OCR_PREPROCESS_ENABLED: bool = True
    OCR_PREPROCESS_MAX_SIZE: int = 2048
    OCR_PREPROCESS_DENOISE: bool = False
    OLLAMA_OCR_MODEL: str = "qwen2-vl:7b"
    OLLAMA_OCR_BASE_URL: str | None = None
    OLLAMA_OCR_TIMEOUT: int = 600  # 增加到 600 秒（10分钟），适配大图片和复杂图片 OCR 处理
    OLLAMA_OCR_MAX_RETRIES: int = 2
    
    # QA系统配置
    QA_DEFAULT_PAGE_SIZE: int = 20
    QA_MAX_PAGE_SIZE: int = 100
    QA_DEFAULT_SIMILARITY_THRESHOLD: float = 0.7
    QA_DEFAULT_MAX_SOURCES: int = 10
    QA_DEFAULT_MAX_HISTORY: int = 5
    QA_DEFAULT_MAX_RESULTS: int = 10
    # QA对话历史总结模型（如果为 None 或空字符串，则使用问答模型）
    QA_SUMMARY_MODEL: Optional[str] = None
    
    # 多模态处理配置
    MULTIMODAL_TEXT_MAX_LENGTH: int = 10000
    MULTIMODAL_IMAGE_MAX_SIZE_MB: int = 10
    MULTIMODAL_IMAGE_MAX_DIMENSION: int = 1024
    MULTIMODAL_MAX_KEYWORDS: int = 10
    MULTIMODAL_DEFAULT_FUSION_SCORE: float = 0.8
    MULTIMODAL_DEFAULT_SEMANTIC_SIMILARITY: float = 0.7
    MULTIMODAL_DEFAULT_RELEVANCE_SCORE: float = 0.7
    MULTIMODAL_DEFAULT_CONSISTENCY_SCORE: float = 0.8
    
    # 降级策略配置
    FALLBACK_HIGH_RELEVANCE_THRESHOLD: float = 0.8
    FALLBACK_MEDIUM_RELEVANCE_THRESHOLD: float = 0.5
    FALLBACK_LOW_RELEVANCE_THRESHOLD: float = 0.3
    FALLBACK_SIMILARITY_WEIGHT: float = 0.4
    FALLBACK_MATCH_WEIGHT: float = 0.3
    FALLBACK_COMPLETENESS_WEIGHT: float = 0.2
    FALLBACK_ACCURACY_WEIGHT: float = 0.1
    
    # 历史存储配置
    QA_HISTORY_INDEX_NAME: str = "qa_history"
    QA_ANSWER_INDEX_NAME: str = "qa_answers"
    QA_HISTORY_CLEANUP_DAYS: int = 90
    QA_HISTORY_DEFAULT_PAGE_SIZE: int = 20
    QA_HISTORY_MAX_PAGE_SIZE: int = 100
    
    # 向量维度
    TEXT_EMBEDDING_DIMENSION: int = 1024
    IMAGE_EMBEDDING_DIMENSION: int = 512
    TEXT_EMBED_MAX_CHARS: int = 1024
    
    # Excel 解析配置
    EXCEL_ENABLE_FLATTENED_TEXT: bool = False
    
    # 预览生成配置
    ENABLE_PREVIEW_GENERATION: bool = True  # 是否在文档处理时预生成预览（PDF/HTML）
    
    # Rerank模型配置
    RERANK_ENABLED: bool = True  # 是否启用rerank模型
    # 推荐中英文支持较好的模型：bge-reranker-v2-m3（多语言支持）或 bge-reranker-large（中英文效果更好）
    RERANK_MODEL_NAME: str = "BAAI/bge-reranker-v2-m3"  # rerank模型名称（支持中英文，多语言）
    RERANK_MODEL_PATH: Optional[str] = str((_PROJECT_ROOT / "models" / "rerank").resolve())  # 本地模型目录，默认指向项目 models/rerank
    RERANK_TOP_K: int = 5  # rerank后返回的结果数量（默认5个）
    RERANK_DEVICE: str = "cpu"  # rerank模型运行设备（cpu/cuda，如果配置为cuda但GPU不可用，会自动降级到cpu）
    RERANK_MIN_SCORE: float = 0.5  # rerank 后端最小得分过滤（0-1），业界建议0.4-0.5，设置为0.5以提升结果质量
    # 混合搜索向量权重 α（关键词权重为 1-α）
    # 设置为0.5表示向量和BM25权重平衡，既考虑语义相似度，也重视精确匹配
    SEARCH_HYBRID_ALPHA: float = 0.5

    # 文本向量检索参数
    SEARCH_VECTOR_THRESHOLD: float = 0.6  # 向量相似度默认阈值
    SEARCH_VECTOR_TOPK: int = 5  # 向量检索默认返回数量（与 RERANK_TOP_K 保持一致）
    # 精确搜索字段列表（用于 multi_match type=phrase），为空则默认 content
    SEARCH_EXACT_FIELDS: List[str] = ["content"]
    # 搜索历史返回条数限制
    SEARCH_HISTORY_DEFAULT_LIMIT: int = 5
    SEARCH_HISTORY_MAX_LIMIT: int = 20
    
    # 实体/意图阈值
    ENTITY_PERSON_CONFIDENCE: float = 0.8
    ENTITY_PLACE_CONFIDENCE: float = 0.7
    INTENT_FACTUAL_CONFIDENCE: float = 0.8
    INTENT_OPERATION_CONFIDENCE: float = 0.8
    INTENT_COMPARISON_CONFIDENCE: float = 0.7
    INTENT_DEFAULT_CONFIDENCE: float = 0.5
    
    # 图片搜索阈值
    IMAGE_SEARCH_DEFAULT_CONFIDENCE: float = 0.8
    IMAGE_SEARCH_MULTIMODAL_CONFIDENCE: float = 0.7
    IMAGE_SEARCH_DEFAULT_CONFIDENCE_FALLBACK: float = 0.5

    # 图片定位/关联增强
    IMAGE_COORDS_NORMALIZE: bool = True  # 统一输出坐标为 0-1 归一化
    IMAGE_ASSOC_RERANK_ENABLED: bool = False  # 图片↔文本关联是否启用 cross-encoder 精排（默认关闭）

    # 内容预览
    CONTENT_PREVIEW_LENGTH: int = 100
    
    # 批量操作
    MAX_BATCH_OPERATION_SIZE: int = 10
    
    # 缓存
    CACHE_TTL_SECONDS: int = 3600
    CACHE_MAX_SIZE: int = 1000
    CACHE_CLEANUP_INTERVAL: int = 300
    
    # Celery Worker 配置
    # Celery worker 并发数（默认根据 CPU 数自动计算，建议 >= 4 以避免 k8s 同步任务占用）
    # 如果 CPU 核心数 >= 4，默认使用 4-8 个并发；否则使用 2-4 个并发
    # 设置为 None 表示自动计算，也可以手动指定（如 6、8 等）
    CELERY_CONCURRENCY: Optional[int] = None  # None 表示自动计算
    # Celery worker 监听的队列（默认包含所有队列）
    # 如果 OBSERVABILITY_ENABLE_SCHEDULE 为 False，默认排除 observability 队列
    # 设置为 None 表示使用默认值（根据 OBSERVABILITY_ENABLE_SCHEDULE 决定）
    # 也可以手动指定，如：document,vector,index,image,version,cleanup,notification,celery
    CELERY_QUEUES: Optional[str] = None  # None 表示使用默认值
    # Celery 日志级别
    CELERY_LOG_LEVEL: str = "INFO"
    # Celery 任务优先级配置（0-255，数字越大优先级越高）
    CELERY_TASK_PRIORITY_DOCUMENT: int = 10  # 文档处理任务（最高优先级）
    CELERY_TASK_PRIORITY_VECTOR: int = 8  # 向量化任务
    CELERY_TASK_PRIORITY_INDEX: int = 8  # 索引任务
    CELERY_TASK_PRIORITY_IMAGE: int = 7  # 图片处理任务
    CELERY_TASK_PRIORITY_VERSION: int = 6  # 版本任务
    CELERY_TASK_PRIORITY_NOTIFICATION: int = 5  # 通知任务
    CELERY_TASK_PRIORITY_OBSERVABILITY: int = 3  # K8s 同步任务（低优先级，后台任务）
    CELERY_TASK_PRIORITY_CLEANUP: int = 2  # 清理任务（最低优先级）
    CELERY_TASK_PRIORITY_DEFAULT: int = 5  # 默认优先级
    
    OBSERVABILITY_RESOURCE_TYPES: List[str] = [
        "pods",
        "deployments",
        "statefulsets",
        "configmaps",  # 支持追踪 ConfigMap 配置变更
        "secrets",     # 支持追踪 Secret 配置变更
        "daemonsets",  # 支持追踪 DaemonSet（如 kube-proxy）
    ]
    OBSERVABILITY_DEFAULT_NAMESPACE: Optional[str] = None  # None 表示全命名空间
    # 支持追踪多个命名空间（包含系统组件命名空间）；为空则表示全部
    OBSERVABILITY_TRACKED_NAMESPACES: Optional[List[str]] = None
    OBSERVABILITY_SYNC_INTERVAL_SECONDS: int = 300
    OBSERVABILITY_HEALTHCHECK_INTERVAL_SECONDS: int = 600
    OBSERVABILITY_METRICS_CACHE_SECONDS: int = 120
    OBSERVABILITY_LOG_CACHE_SECONDS: int = 60
    OBSERVABILITY_ENABLE_SCHEDULE: bool = True
    OBSERVABILITY_ALLOWED_ROLES: List[str] = ["admin"]
    OBSERVABILITY_WATCH_TIMEOUT_SECONDS: int = 30
    OBSERVABILITY_WATCH_MAX_ATTEMPTS: int = 3
    OBSERVABILITY_DIAGNOSIS_MAX_ITERATIONS: int = 5
    OBSERVABILITY_DIAGNOSIS_CONFIDENCE_THRESHOLD: float = 0.8
    OBSERVABILITY_DIAGNOSIS_MEMORY_RECENT_LIMIT: int = 10
    OBSERVABILITY_DIAGNOSIS_ITERATION_DELAY_SECONDS: int = 5
    OBSERVABILITY_KNOWLEDGE_BASE_ID: Optional[int] = None  # 诊断案例保存到的知识库ID（可选）
    OBSERVABILITY_KNOWLEDGE_EVAL_MAX_DOCS: int = 3  # 每轮知识库评估最多使用的文档数量
    # 日志收集配置
    OBSERVABILITY_LOG_INITIAL_TAIL_LINES: int = 500  # 第一次尝试获取日志时的 tail_lines
    OBSERVABILITY_LOG_FALLBACK_TAIL_LINES: int = 300  # 回退策略时的 tail_lines（时间范围内无日志时）
    OBSERVABILITY_LOG_MAX_LINES: int = 300  # 最终返回的最大日志行数（优先保留 ERROR/WARNING/FATAL 日志）
    OBSERVABILITY_LOG_CONTEXT_LINES: int = 3  # 错误日志上下文行数（前后各几行）
    OBSERVABILITY_LOG_MAX_LINE_LENGTH: int = 10000  # 单行日志最大长度（超过此长度将被截断，单位：字符）
    SEARXNG_URL: Optional[str] = None
    EXTERNAL_SEARCH_ENABLED: bool = True
    EXTERNAL_SEARCH_MIN_DOC_HITS: int = 2
    EXTERNAL_SEARCH_MIN_SCORE: float = 0.55
    EXTERNAL_SEARCH_MIN_CONFIDENCE: float = 0.6
    EXTERNAL_SEARCH_RESULT_LIMIT: int = 5
    EXTERNAL_SEARCH_CACHE_TTL: int = 600  # 秒
    EXTERNAL_SEARCH_RATE_LIMIT_PER_USER: int = 30
    EXTERNAL_SEARCH_RATE_LIMIT_WINDOW: int = 3600  # 秒
    EXTERNAL_SEARCH_TIMEOUT: int = 12
    EXTERNAL_SEARCH_SUMMARY_ENABLED: bool = True
    EXTERNAL_SEARCH_SUMMARY_MAX_ITEMS: int = 5
    EXTERNAL_SEARCH_SUMMARY_MODEL: Optional[str] = None
    EXTERNAL_SEARCH_INDEX_NAME: str = "external_searches"
    EXTERNAL_SEARCH_CATEGORIES: Optional[str] = None
    EXTERNAL_SEARCH_INTENT_MODEL: Optional[str] = None
    
    # 自动标签/摘要配置
    ENABLE_AUTO_TAGGING: bool = True
    AUTO_TAGGING_MODEL: Optional[str] = None  # 默认使用 OLLAMA_MODEL
    AUTO_TAGGING_MAX_CONTENT_LENGTH: int = 10000
    
    # 批量上传配置
    BATCH_UPLOAD_MAX_FILES: int = 100
    BATCH_UPLOAD_MAX_SIZE: int = 1024 * 1024 * 1024  # 1GB
    STRUCTURED_PREVIEW_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB
    ENABLE_BATCH_SECURITY_SCAN_QUEUE: bool = True  # 批量上传时是否使用专用扫描队列
    
    # 文本质量阈值
    MAX_NEWLINE_RATIO: float = 0.5
    MAX_SPECIAL_CHAR_RATIO: float = 0.1
    MIN_CHINESE_RATIO: float = 0.3
    MIN_ENGLISH_RATIO: float = 0.3
    
    # 降级策略置信度
    FALLBACK_CONFIDENCE_BOOST: float = 0.2
    FALLBACK_DEFAULT_CONFIDENCE: float = 0.5
    
    # 文件验证
    FILE_HEADER_READ_SIZE: int = 1024
    
    # 安全
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # 2小时，减少频繁刷新
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30天，延长会话有效期
    
    # 登录安全
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 30
    
    # 密码规则
    MIN_PASSWORD_LENGTH: int = 8
    MAX_PASSWORD_LENGTH: int = 50
    
    # 邮箱验证
    EMAIL_VERIFICATION_ENABLED: bool = False
    EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES: int = 10
    
    # 日志
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "logs/app.log"
    
    # 环境
    ENVIRONMENT: str = "development"
    
    # ClamAV
    CLAMAV_ENABLED: bool = True
    CLAMAV_REQUIRED: bool = False  # 如果为 true，ClamAV 不可用时拒绝上传
    CLAMAV_SOCKET_PATH: Optional[str] = None
    CLAMAV_TCP_HOST: Optional[str] = "localhost"
    CLAMAV_TCP_PORT: int = 3310
    CLAMAV_SCAN_TIMEOUT: int = 60
    CLAMAV_USE_TCP: bool = False
    
    # 上传
    MAX_FILE_SIZE: int = 100 * 1024 * 1024
    ALLOWED_FILE_TYPES: List[str] = [".docx", ".pdf", ".txt", ".log"]
    
    # 文档处理
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    # 最小分块大小：避免产生太多小块（默认 500 字符，约为 CHUNK_SIZE 的一半）
    # 如果分块小于此值，会尝试与相邻分块合并（合并后不超过 chunk_max）
    CHUNK_MIN_SIZE: int = 500
    MAX_CHUNKS_PER_DOCUMENT: int = 1000
    PARSING_TIMEOUT: int = 300
    VECTORIZATION_TIMEOUT: int = 600
    OLLAMA_TIMEOUT: int = 300
    
    # 实体提取相关配置
    ENTITY_EXTRACTION_CHUNK_SIZE: int = 8000  # 实体提取块大小（LLM上下文）
    ENTITY_EXTRACTION_CHUNK_OVERLAP_RATIO: float = 0.2  # 重叠比例（20%）
    ENTITY_EXTRACTION_MAX_CONCURRENT: int = 5  # 最大并发数
    ENTITY_EXTRACTION_CROSS_CHUNK_ENABLED: bool = True  # 是否启用跨块关系检测
    
    # 知识图谱置信度配置
    KG_ENTITY_DEFAULT_CONFIDENCE: float = 0.7  # 实体默认置信度
    KG_RELATIONSHIP_DEFAULT_CONFIDENCE: float = 0.7  # 关系默认置信度
    KG_HIGH_CONFIDENCE_THRESHOLD: float = 0.9  # 高置信度阈值（用于明确的关系/实体）
    KG_LOW_CONFIDENCE_THRESHOLD: float = 0.7  # 低置信度阈值（用于推测的关系/实体）
    KG_PENDING_VERIFICATION_CONFIDENCE: float = 0.6  # 待验证关系/实体的置信度
    # 知识图谱日志配置
    KG_VERBOSE_LOGGING: bool = True  # 是否输出详细的图存储操作日志（单个实体/关系的插入日志），默认true，可通过.env设置为false以减少日志量
    
    # 分块存储策略
    STORE_CHUNK_TEXT_IN_DB: bool = False
    
    # NebulaGraph配置
    USE_NEBULA_GRAPH: bool = False  # 是否启用NebulaGraph
    NEBULA_HOSTS: Union[str, List[tuple]] = [("127.0.0.1", 9669)]  # NebulaGraph地址列表，支持字符串格式 "host:port" 或 "host1:port1,host2:port2"
    NEBULA_USER: str = "root"  # NebulaGraph用户名
    NEBULA_PASSWORD: str = "password"  # NebulaGraph密码
    
    @field_validator('NEBULA_HOSTS', mode='before')
    @classmethod
    def parse_nebula_hosts(cls, v):
        """解析NEBULA_HOSTS环境变量
        
        支持格式：
        - List[tuple]: [("127.0.0.1", 9669)]
        - str: "host:port" 或 "host1:port1,host2:port2"
        """
        if isinstance(v, str):
            # 解析字符串格式 "host:port" 或 "host1:port1,host2:port2"
            hosts = []
            for host_str in v.split(','):
                host_str = host_str.strip()
                if ':' in host_str:
                    host, port = host_str.rsplit(':', 1)
                    try:
                        hosts.append((host.strip(), int(port.strip())))
                    except ValueError:
                        raise ValueError(f"Invalid NEBULA_HOSTS format: {host_str}. Expected 'host:port'")
                else:
                    raise ValueError(f"Invalid NEBULA_HOSTS format: {host_str}. Expected 'host:port'")
            return hosts
        return v

    # 兼容历史环境变量（忽略未使用但不报错）
    SOFFICE_PATH: Optional[str] = None  # 旧的 libreoffice 路径，当前未使用

    class Config:
        env_file = _ENV_FILE
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 忽略未声明的环境变量，避免启动失败

settings = Settings()
