"""
测试 Ollama Function Calling 支持
用于验证 qwen3-coder 是否支持 function calling
"""

import requests
import json
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_function_calling_support():
    """测试 Ollama function calling 支持"""
    # 使用用户提供的地址
    ollama_url = "http://192.168.131.158:11434"
    model = "qwen3-coder:latest"
    url = f"{ollama_url}/api/chat"
    
    # 定义工具
    tools = [
        {
            "type": "function",
            "function": {
                "name": "extract_api_endpoints",
                "description": "从代码文件中提取 HTTP API 端点",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "endpoints": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "method": {
                                        "type": "string",
                                        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]
                                    },
                                    "path": {"type": "string"},
                                    "function_name": {"type": "string"},
                                    "line": {"type": "integer"},
                                    "description": {"type": "string"}
                                },
                                "required": ["method", "path", "function_name"]
                            }
                        }
                    },
                    "required": ["endpoints"]
                }
            }
        }
    ]
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": """分析以下代码，提取 API 端点：

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/api/users")
def get_users():
    return {"users": []}

@app.post("/api/users")
def create_user():
    return {"id": 1}
```

请提取所有 API 端点。"""
            }
        ],
        "tools": tools,
        "tool_choice": "auto",
        "options": {
            "temperature": 0.1
        }
    }
    
    print(f"[测试] Function Calling 支持测试...")
    print(f"模型: {model}")
    print(f"URL: {url}")
    print(f"工具定义: {json.dumps(tools, indent=2, ensure_ascii=False)}")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        # 尝试解析 JSON（可能是流式响应，需要特殊处理）
        try:
            result = response.json()
        except:
            # 如果不是标准 JSON，尝试解析第一行
            text = response.text
            print(f"[调试] 响应文本长度: {len(text)}")
            print(f"[调试] 响应前500字符: {text[:500]}")
            
            # 尝试解析第一行 JSON
            lines = text.strip().split('\n')
            if lines:
                try:
                    result = json.loads(lines[0])
                except:
                    # 如果还是失败，尝试整个文本
                    result = {"raw_response": text}
        
        print(f"[成功] 请求成功")
        print(f"响应结构: {list(result.keys()) if isinstance(result, dict) else type(result)}")
        print()
        
        # 检查是否有 tool_calls
        message = result.get('message', {})
        tool_calls = message.get('tool_calls', [])
        content = message.get('content', '')
        
        if tool_calls:
            print("[成功] Function calling 支持！")
            print(f"工具调用数量: {len(tool_calls)}")
            for i, tool_call in enumerate(tool_calls):
                print(f"\n工具调用 {i+1}:")
                print(f"  ID: {tool_call.get('id', 'N/A')}")
                print(f"  类型: {tool_call.get('type', 'N/A')}")
                function = tool_call.get('function', {})
                print(f"  函数名: {function.get('name', 'N/A')}")
                arguments = function.get('arguments', '')
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except:
                        pass
                print(f"  参数: {json.dumps(arguments, indent=4, ensure_ascii=False)}")
            return True
        else:
            print("[警告] 未返回 tool_calls")
            if content:
                print(f"响应内容: {content[:500]}")
                # 检查是否是 XML 格式
                if '<tool_call>' in content or '<function_calls>' in content:
                    print("[警告] 检测到 XML 格式的工具调用，可能需要特殊解析")
            print(f"\n完整响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"[错误] 请求超时")
        return False
    except Exception as e:
        print(f"[错误] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_function_calling_support()
