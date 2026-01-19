"""
代码问答 Function Calling 工具定义
用于日志定位和代码问答
"""

# 搜索文件工具
SEARCH_FILE_BY_PATH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_file_by_path",
        "description": "根据文件路径搜索代码文件。如果日志中提到了文件路径，使用此工具查找对应的文件。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "文件路径（可以是绝对路径或相对路径，系统会自动规范化）"
                }
            },
            "required": ["file_path"]
        }
    }
}

# 搜索函数工具
SEARCH_FUNCTION_BY_NAME_TOOL = {
    "type": "function",
    "function": {
        "name": "search_function_by_name",
        "description": "根据函数名搜索函数定义。如果日志中提到了函数名，使用此工具查找函数所在的文件和位置。",
        "parameters": {
            "type": "object",
            "properties": {
                "function_name": {
                    "type": "string",
                    "description": "函数名（可以是完整函数名或部分匹配）"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数（默认 5）",
                    "default": 5
                }
            },
            "required": ["function_name"]
        }
    }
}

# 搜索类工具
SEARCH_CLASS_BY_NAME_TOOL = {
    "type": "function",
    "function": {
        "name": "search_class_by_name",
        "description": "根据类名搜索类定义。如果日志中提到了类名，使用此工具查找类所在的文件和位置。",
        "parameters": {
            "type": "object",
            "properties": {
                "class_name": {
                    "type": "string",
                    "description": "类名（可以是完整类名或部分匹配）"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数（默认 5）",
                    "default": 5
                }
            },
            "required": ["class_name"]
        }
    }
}

# 读取文件内容工具
READ_FILE_CONTENT_TOOL = {
    "type": "function",
    "function": {
        "name": "read_file_content",
        "description": "读取文件内容。如果找到了相关文件，使用此工具读取文件内容进行分析。可以指定行号范围。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "文件路径（相对路径）"
                },
                "start_line": {
                    "type": "integer",
                    "description": "起始行号（可选，如果日志中提到了行号，使用此参数）",
                    "minimum": 1
                },
                "end_line": {
                    "type": "integer",
                    "description": "结束行号（可选，如果指定了 start_line，可以指定 end_line 来读取特定范围）",
                    "minimum": 1
                },
                "context_lines": {
                    "type": "integer",
                    "description": "上下文行数（如果指定了行号，会读取该行前后各 context_lines 行，默认 10）",
                    "default": 10,
                    "minimum": 0,
                    "maximum": 50
                }
            },
            "required": ["file_path"]
        }
    }
}

# 搜索相关代码工具
SEARCH_RELATED_CODE_TOOL = {
    "type": "function",
    "function": {
        "name": "search_related_code",
        "description": "使用语义搜索查找与问题相关的代码。当无法通过文件路径或函数名直接定位时，使用此工具进行语义搜索。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询（可以是错误消息、问题描述等）"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数（默认 5）",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
}

# 所有代码问答工具列表
CODE_QA_TOOLS = [
    SEARCH_FILE_BY_PATH_TOOL,
    SEARCH_FUNCTION_BY_NAME_TOOL,
    SEARCH_CLASS_BY_NAME_TOOL,
    READ_FILE_CONTENT_TOOL,
    SEARCH_RELATED_CODE_TOOL
]
