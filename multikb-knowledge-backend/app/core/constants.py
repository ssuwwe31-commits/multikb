"""
Constants Module
"""

# 文件类型常量
ALLOWED_FILE_TYPES = [
    ".pdf", ".docx", ".txt", ".md", ".html", ".rtf", ".odt"
]

# 图片类型常量
ALLOWED_IMAGE_TYPES = [
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"
]

# 文档状态常量
DOCUMENT_STATUS = {
    "UPLOADED": "uploaded",
    "PROCESSING": "processing",
    "COMPLETED": "completed",
    "FAILED": "failed",
    "REPROCESSING": "reprocessing"
}

# 任务状态常量
TASK_STATUS = {
    "PENDING": "pending",
    "STARTED": "started",
    "SUCCESS": "success",
    "FAILURE": "failure",
    "RETRY": "retry",
    "REVOKED": "revoked"
}

# 知识库状态常量
KNOWLEDGE_BASE_STATUS = {
    "ACTIVE": "active",
    "INACTIVE": "inactive",
    "ARCHIVED": "archived"
}

# 分页常量
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# 向量维度常量
VECTOR_DIMENSION = 512

# 缓存键前缀
CACHE_PREFIXES = {
    "KNOWLEDGE_BASE": "kb:",
    "DOCUMENT": "doc:",
    "CHUNK": "chunk:",
    "IMAGE": "img:",
    "SEARCH": "search:",
    "QA": "qa:",
}

# 文档处理状态常量
DOC_STATUS_UPLOADED = "uploaded"
DOC_STATUS_PARSING = "parsing"
DOC_STATUS_CHUNKING = "chunking"
DOC_STATUS_VECTORIZING = "vectorizing"
DOC_STATUS_INDEXING = "indexing"
DOC_STATUS_COMPLETED = "completed"
DOC_STATUS_FAILED = "failed"
