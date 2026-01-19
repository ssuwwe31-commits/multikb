"""
LLM Function Calling 工具定义
用于结构化任务（API 端点检测、存储系统检测等）
"""

# API 端点检测工具
API_ENDPOINTS_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_api_endpoints",
        "description": "从代码文件中提取 HTTP API 端点（路由）。支持 FastAPI、Flask、Django、Gradio、Streamlit、Tornado、Sanic 等框架。",
        "parameters": {
            "type": "object",
            "properties": {
                "endpoints": {
                    "type": "array",
                    "description": "API 端点列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "method": {
                                "type": "string",
                                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
                                "description": "HTTP 方法"
                            },
                            "path": {
                                "type": "string",
                                "description": "路由路径（完整路径，包括路径参数，如 /api/users/{id}）"
                            },
                            "function_name": {
                                "type": "string",
                                "description": "处理函数名"
                            },
                            "line": {
                                "type": "integer",
                                "description": "行号（如果可能）"
                            },
                            "description": {
                                "type": "string",
                                "description": "端点描述（可选）"
                            }
                        },
                        "required": ["method", "path", "function_name"]
                    }
                }
            },
            "required": ["endpoints"]
        }
    }
}

# 存储系统检测工具
STORAGE_SYSTEMS_TOOL = {
    "type": "function",
    "function": {
        "name": "detect_storage_systems",
        "description": "检测代码中使用的存储系统。包括：数据库（MySQL、PostgreSQL、MongoDB等）、缓存（Redis、Memcached等）、消息队列（Kafka、RabbitMQ等）、文件系统、对象存储（S3、MinIO等）。",
        "parameters": {
            "type": "object",
            "properties": {
                "storage_systems": {
                    "type": "array",
                    "description": "存储系统列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "存储系统名称（如 MySQL、Redis、文件系统）"
                            },
                            "type": {
                                "type": "string",
                                "enum": ["database", "cache", "message_queue", "file_system", "object_storage"],
                                "description": "存储系统类型"
                            },
                            "description": {
                                "type": "string",
                                "description": "使用场景描述（可选）"
                            }
                        },
                        "required": ["name", "type"]
                    }
                }
            },
            "required": ["storage_systems"]
        }
    }
}

# 外部服务检测工具
EXTERNAL_SERVICES_TOOL = {
    "type": "function",
    "function": {
        "name": "detect_external_services",
        "description": "检测代码中使用的外部服务。包括：云服务（AWS、Azure、GCP）、API 服务、第三方库服务等。",
        "parameters": {
            "type": "object",
            "properties": {
                "services": {
                    "type": "array",
                    "description": "外部服务列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "服务名称（如 vllm、OpenAI、AWS S3）"
                            },
                            "type": {
                                "type": "string",
                                "description": "服务类型（如 LLM、云存储、API）"
                            },
                            "description": {
                                "type": "string",
                                "description": "使用场景描述（可选）"
                            }
                        },
                        "required": ["name"]
                    }
                }
            },
            "required": ["services"]
        }
    }
}

# 组件匹配工具
COMPONENT_MATCHING_TOOL = {
    "type": "function",
    "function": {
        "name": "match_components",
        "description": "将核心组件名称匹配到实际代码文件路径。",
        "parameters": {
            "type": "object",
            "properties": {
                "matches": {
                    "type": "array",
                    "description": "组件匹配列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "component_name": {
                                "type": "string",
                                "description": "组件名称"
                            },
                            "file_paths": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "匹配的文件路径列表"
                            },
                            "confidence": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                                "description": "匹配置信度（0-1）"
                            }
                        },
                        "required": ["component_name", "file_paths"]
                    }
                }
            },
            "required": ["matches"]
        }
    }
}
