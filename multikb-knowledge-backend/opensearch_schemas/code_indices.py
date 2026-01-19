"""
OpenSearch Code Indices Configuration
代码索引配置 - 支持向量检索和全文搜索
"""

from typing import Dict, Any
from app.config.settings import settings


# ============================================
# 代码文件索引配置
# ============================================

CODE_FILES_INDEX_CONFIG: Dict[str, Any] = {
    "settings": {
        "number_of_shards": 3,
        "number_of_replicas": 1,
        "analysis": {
            "analyzer": {
                "code_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop", "snowball"]
                },
                "path_analyzer": {
                    "type": "custom",
                    "tokenizer": "path_hierarchy",
                    "filter": ["lowercase"]
                }
            }
        },
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 100
        }
    },
    "mappings": {
        "properties": {
            # 基本信息
            "file_id": {
                "type": "integer"
            },
            "file_vid": {
                "type": "keyword",
                "index": True
            },
            "repository_id": {
                "type": "integer"
            },
            "knowledge_base_id": {
                "type": "integer"
            },
            "file_path": {
                "type": "text",
                "analyzer": "path_analyzer",
                "fields": {
                    "keyword": {
                        "type": "keyword"
                    }
                }
            },
            "file_name": {
                "type": "text",
                "analyzer": "standard",
                "fields": {
                    "keyword": {
                        "type": "keyword"
                    }
                }
            },
            "language": {
                "type": "keyword"
            },
            
            # 文件内容
            "content": {
                "type": "text",
                "analyzer": "code_analyzer"
            },
            "content_summary": {
                "type": "text",
                "analyzer": "standard"
            },
            
            # 代码统计
            "lines_of_code": {
                "type": "integer"
            },
            "file_size": {
                "type": "long"
            },
            "symbols_count": {
                "type": "integer"
            },
            "imports_count": {
                "type": "integer"
            },
            "complexity_score": {
                "type": "float"
            },
            
            # 向量字段（从配置读取维度，使用 qwen3-embedding:4b）
            # 注意：qwen3-embedding:4b 默认维度是 2560，Ollama 不支持自定义维度参数
            "content_vector": {
                "type": "knn_vector",
                "dimension": settings.TEXT_EMBEDDING_DIMENSION,  # 从配置读取，默认 2560
                "method": {
                    "name": "hnsw",
                    "space_type": "l2",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 128,
                        "m": 24
                    }
                }
            },
            
            # 元数据
            "content_hash": {
                "type": "keyword"
            },
            "processed_content_hash": {
                "type": "keyword"
            },
            "created_at": {
                "type": "date"
            },
            "updated_at": {
                "type": "date"
            },
            "vector_updated_at": {
                "type": "date"
            }
        }
    }
}


# ============================================
# 代码符号索引配置
# ============================================

CODE_SYMBOLS_INDEX_CONFIG: Dict[str, Any] = {
    "settings": {
        "number_of_shards": 3,
        "number_of_replicas": 1,
        # 关键：开启 KNN（用于 content_vector），参考 documents 和 images 索引的设置方式
        "index.knn": True,
        "analysis": {
            "analyzer": {
                "code_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop"]
                },
                "camelCase_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "word_delimiter"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            # 基本信息
            "symbol_id": {
                "type": "integer"
            },
            "symbol_vid": {
                "type": "keyword",
                "index": True
            },
            "file_id": {
                "type": "integer"
            },
            "file_vid": {
                "type": "keyword",
                "index": True
            },
            "repository_id": {
                "type": "integer"
            },
            "knowledge_base_id": {
                "type": "integer"
            },
            
            # 符号信息
            "symbol_name": {
                "type": "text",
                "analyzer": "camelCase_analyzer",
                "fields": {
                    "keyword": {
                        "type": "keyword"
                    }
                }
            },
            "symbol_type": {
                "type": "keyword"
            },
            "qualified_name": {
                "type": "text",
                "analyzer": "camelCase_analyzer",
                "fields": {
                    "keyword": {
                        "type": "keyword"
                    }
                }
            },
            "signature": {
                "type": "text",
                "analyzer": "code_analyzer"
            },
            
            # 文档
            "docstring": {
                "type": "text",
                "analyzer": "standard"
            },
            "parameters": {
                "type": "text",
                "analyzer": "code_analyzer"
            },
            "return_type": {
                "type": "keyword"
            },
            
            # 位置信息
            "file_path": {
                "type": "keyword"
            },
            "start_line": {
                "type": "integer"
            },
            "end_line": {
                "type": "integer"
            },
            
            # 代码内容
            "code_content": {
                "type": "text",
                "analyzer": "code_analyzer"
            },
            
            # 复杂度
            "complexity_score": {
                "type": "float"
            },
            "lines_count": {
                "type": "integer"
            },
            
            # 向量字段（从配置读取维度）
            # 注意：qwen3-embedding:4b 默认维度是 2560，Ollama 不支持自定义维度参数
            "content_vector": {
                "type": "knn_vector",
                "dimension": settings.TEXT_EMBEDDING_DIMENSION,  # 从配置读取，默认 2560
                "method": {
                    "name": "hnsw",
                    "space_type": "l2",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 128,
                        "m": 24
                    }
                }
            },
            
            # 元数据
            "content_hash": {
                "type": "keyword"
            },
            "created_at": {
                "type": "date"
            },
            "updated_at": {
                "type": "date"
            },
            "vector_updated_at": {
                "type": "date"
            }
        }
    }
}


# ============================================
# Wiki 内容索引配置
# ============================================

WIKI_CONTENT_INDEX_CONFIG = {
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 100,
            "number_of_shards": 1,
            "number_of_replicas": 0
        }
    },
    "mappings": {
        "properties": {
            # 基本信息
            "repository_id": {
                "type": "integer"
            },
            "repo_name": {
                "type": "keyword"
            },
            
            # Wiki 内容字段
            "content_type": {
                "type": "keyword"  # 内容类型：project_overview, system_architecture, tech_stack, etc.
            },
            "content_title": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "content_text": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart"
            },
            
            # 向量字段（从配置读取维度）
            "content_vector": {
                "type": "knn_vector",
                "dimension": settings.TEXT_EMBEDDING_DIMENSION,
                "method": {
                    "name": "hnsw",
                    "space_type": "l2",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 128,
                        "m": 24
                    }
                }
            },
            
            # 元数据
            "section": {
                "type": "keyword"  # 章节：base, architecture, tech_stack, etc.
            },
            "created_at": {
                "type": "date"
            },
            "updated_at": {
                "type": "date"
            }
        }
    }
}

# ============================================
# 代码问答记录索引配置
# ============================================

CODE_QA_RECORDS_INDEX_CONFIG: Dict[str, Any] = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 100
        },
        "analysis": {
            "analyzer": {
                "ik_max_word": {
                    "type": "ik_max_word"
                },
                "ik_smart": {
                    "type": "ik_smart"
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "record_id": {
                "type": "keyword"
            },
            "session_id": {
                "type": "keyword"
            },
            "repository_id": {
                "type": "integer"
            },
            "question": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart",
                "fields": {
                    "keyword": {
                        "type": "keyword"
                    }
                }
            },
            "answer": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart"
            },
            "question_vector": {
                "type": "knn_vector",
                "dimension": settings.TEXT_EMBEDDING_DIMENSION,  # 2560
                "method": {
                    "name": "hnsw",
                    "space_type": "l2",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 128,
                        "m": 24
                    }
                }
            },
            "answer_vector": {
                "type": "knn_vector",
                "dimension": settings.TEXT_EMBEDDING_DIMENSION,  # 2560
                "method": {
                    "name": "hnsw",
                    "space_type": "l2",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 128,
                        "m": 24
                    }
                }
            },
            "context_files": {
                "type": "nested",
                "properties": {
                    "file_path": {
                        "type": "keyword"
                    },
                    "file_name": {
                        "type": "keyword"
                    },
                    "language": {
                        "type": "keyword"
                    },
                    "content_summary": {
                        "type": "text"
                    }
                }
            },
            "code_snippets": {
                "type": "nested",
                "properties": {
                    "file_path": {
                        "type": "keyword"
                    },
                    "start_line": {
                        "type": "integer"
                    },
                    "end_line": {
                        "type": "integer"
                    },
                    "language": {
                        "type": "keyword"
                    },
                    "code": {
                        "type": "text"
                    }
                }
            },
            "mermaid_diagrams": {
                "type": "text",
                "index": False
            },
            "question_type": {
                "type": "keyword"
            },
            "classification": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "keyword"
                    },
                    "method": {
                        "type": "keyword"
                    },
                    "confidence": {
                        "type": "float"
                    }
                }
            },
            "call_chain_info": {
                "type": "object",
                "enabled": False
            },
            "processing_info": {
                "type": "object",
                "properties": {
                    "processing_time": {
                        "type": "float"
                    },
                    "token_usage": {
                        "type": "integer"
                    },
                    "model_used": {
                        "type": "keyword"
                    }
                }
            },
            "created_at": {
                "type": "date",
                "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis"
            }
        }
    }
}


# ============================================
# 索引名称常量
# ============================================

CODE_FILES_INDEX = "code_files"
CODE_SYMBOLS_INDEX = "code_symbols"
WIKI_CONTENT_INDEX = "wiki_content"
CODE_QA_RECORDS_INDEX = "code_qa_records"


# ============================================
# 初始化函数
# ============================================

async def init_code_indices(opensearch_client):
    """
    初始化代码索引（参考 documents 和 images 索引的创建方式）
    
    Args:
        opensearch_client: OpenSearch 客户端实例
    """
    from app.core.logging import logger
    from app.config.settings import settings
    
    try:
        # 创建代码问答记录索引
        if not opensearch_client.indices.exists(index=CODE_QA_RECORDS_INDEX):
            opensearch_client.indices.create(
                index=CODE_QA_RECORDS_INDEX,
                body=CODE_QA_RECORDS_INDEX_CONFIG
            )
            logger.info(f"创建代码问答记录索引成功: {CODE_QA_RECORDS_INDEX}，向量维度={settings.TEXT_EMBEDDING_DIMENSION}")
        else:
            logger.info(f"代码问答记录索引已存在: {CODE_QA_RECORDS_INDEX}")
        
        # 创建代码文件索引
        if not opensearch_client.indices.exists(index=CODE_FILES_INDEX):
            opensearch_client.indices.create(
                index=CODE_FILES_INDEX,
                body=CODE_FILES_INDEX_CONFIG
            )
            logger.info(f"创建代码文件索引成功: {CODE_FILES_INDEX}，已设置 index.knn=true，向量字段=content_vector，维度={settings.TEXT_EMBEDDING_DIMENSION}")
            
            # 验证 KNN 设置
            try:
                settings_res = opensearch_client.indices.get_settings(index=CODE_FILES_INDEX)
                knn_flag = settings_res.get(CODE_FILES_INDEX, {}).get('settings', {}).get('index', {}).get('knn')
                logger.info(f"代码文件索引当前 knn 设置: {knn_flag}")
                if str(knn_flag).lower() == 'true':
                    logger.info(f"代码文件索引 knn 已开启: {CODE_FILES_INDEX}")
                else:
                    logger.warning(f"代码文件索引 knn 设置异常: {knn_flag}")
            except Exception as _e:
                logger.warning(f"读取代码文件索引 settings 失败: {_e}")
        else:
            logger.info(f"代码文件索引已存在: {CODE_FILES_INDEX}")
            # 兜底：若 knn 未开启，则在线开启（参考 documents 和 images 索引的处理方式）
            try:
                settings_res = opensearch_client.indices.get_settings(index=CODE_FILES_INDEX)
                knn_flag = settings_res.get(CODE_FILES_INDEX, {}).get('settings', {}).get('index', {}).get('knn')
                if not (str(knn_flag).lower() == 'true'):
                    opensearch_client.indices.put_settings(index=CODE_FILES_INDEX, body={"index.knn": True})
                    logger.info(f"代码文件索引检测到 knn 未开启，已自动开启: {CODE_FILES_INDEX}")
                else:
                    logger.info(f"代码文件索引 knn 已开启: {CODE_FILES_INDEX}")
            except Exception as _e:
                logger.warning(f"代码文件索引 knn 设置检查/开启失败: {_e}")
        
        # 创建代码符号索引
        if not opensearch_client.indices.exists(index=CODE_SYMBOLS_INDEX):
            opensearch_client.indices.create(
                index=CODE_SYMBOLS_INDEX,
                body=CODE_SYMBOLS_INDEX_CONFIG
            )
            logger.info(f"创建代码符号索引成功: {CODE_SYMBOLS_INDEX}，已设置 index.knn=true，向量字段=content_vector，维度={settings.TEXT_EMBEDDING_DIMENSION}")
            
            # 验证 KNN 设置
            try:
                settings_res = opensearch_client.indices.get_settings(index=CODE_SYMBOLS_INDEX)
                knn_flag = settings_res.get(CODE_SYMBOLS_INDEX, {}).get('settings', {}).get('index', {}).get('knn')
                logger.info(f"代码符号索引当前 knn 设置: {knn_flag}")
                if str(knn_flag).lower() == 'true':
                    logger.info(f"代码符号索引 knn 已开启: {CODE_SYMBOLS_INDEX}")
                else:
                    logger.warning(f"代码符号索引 knn 设置异常: {knn_flag}")
            except Exception as _e:
                logger.warning(f"读取代码符号索引 settings 失败: {_e}")
        else:
            logger.info(f"代码符号索引已存在: {CODE_SYMBOLS_INDEX}")
            # 检查 KNN 状态（只检查，不尝试修改，因为 index.knn 不是动态设置）
            try:
                settings_res = opensearch_client.indices.get_settings(index=CODE_SYMBOLS_INDEX)
                knn_flag = settings_res.get(CODE_SYMBOLS_INDEX, {}).get('settings', {}).get('index', {}).get('knn')
                if str(knn_flag).lower() == 'true':
                    logger.info(f"代码符号索引 knn 已开启: {CODE_SYMBOLS_INDEX}")
                else:
                    logger.warning(
                        f"⚠️ 代码符号索引 KNN 未开启: {CODE_SYMBOLS_INDEX}\n"
                        f"   影响：向量搜索功能将无法正常工作\n"
                        f"   原因：index.knn 需要在创建索引时设置，无法动态修改\n"
                        f"   修复：运行以下命令重建索引（会丢失现有数据，需要重新索引）：\n"
                        f"         cd multikb-knowledge-backend && python scripts/init_code_indices.py\n"
                        f"   或者：手动删除索引后重新创建（确保配置中包含 'index.knn': True）"
                    )
            except Exception as _e:
                logger.debug(f"代码符号索引 knn 状态检查失败: {_e}")
        
        return True
        
    except Exception as e:
        logger.error(f"初始化代码索引失败: {e}")
        raise


# ============================================
# 便捷函数
# ============================================

def get_code_files_index_config() -> Dict[str, Any]:
    """获取代码文件索引配置"""
    return CODE_FILES_INDEX_CONFIG


def get_code_symbols_index_config() -> Dict[str, Any]:
    """获取代码符号索引配置"""
    return CODE_SYMBOLS_INDEX_CONFIG
