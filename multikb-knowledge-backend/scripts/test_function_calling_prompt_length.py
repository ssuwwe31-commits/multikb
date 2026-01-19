"""
测试 Ollama Function Calling 在不同 prompt 长度下的表现
找出支持的临界点
"""

import requests
import json
import time

OLLAMA_URL = "http://192.168.131.158:11434"
MODEL = "qwen3-coder:latest"

# 工具定义（API 端点检测）
API_ENDPOINTS_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_api_endpoints",
        "description": "从代码中提取 API 端点信息",
        "parameters": {
            "type": "object",
            "properties": {
                "endpoints": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "method": {"type": "string"},
                            "path": {"type": "string"},
                            "function_name": {"type": "string"},
                            "line": {"type": "integer"}
                        }
                    }
                }
            },
            "required": ["endpoints"]
        }
    }
}


def generate_test_prompt(length: int) -> str:
    """生成指定长度的测试 prompt"""
    base_prompt = """分析以下代码文件，识别所有 API 端点（HTTP 路由）。

文件路径: test_file.py
代码内容:
```python
"""
    
    # 生成填充内容（模拟代码）
    # 每行大约 80 字符
    lines_needed = (length - len(base_prompt) - 100) // 80  # 预留一些空间给结尾
    
    code_content = ""
    for i in range(lines_needed):
        code_content += f"def test_function_{i}():\n"
        code_content += f"    # This is a test function {i}\n"
        code_content += f"    pass\n\n"
    
    # 如果还不够，添加更多内容
    if len(code_content) < (length - len(base_prompt) - 200):
        remaining = length - len(code_content) - len(base_prompt) - 200
        code_content += "# " + "x" * remaining + "\n"
    
    end_prompt = """
```

请识别所有 HTTP 端点（GET、POST、PUT、DELETE、PATCH 等）。
支持 FastAPI、Flask、Django、Gradio、Streamlit、Tornado、Sanic 等框架。
如果文件不是路由文件，返回空数组。"""
    
    full_prompt = base_prompt + code_content + end_prompt
    
    # 确保长度接近目标
    if len(full_prompt) < length:
        padding = " " * (length - len(full_prompt))
        full_prompt = base_prompt + code_content + padding + end_prompt
    
    return full_prompt[:length]  # 精确截断到目标长度


def test_function_calling(prompt: str, prompt_length: int) -> dict:
    """测试 Function Calling"""
    try:
        url = f"{OLLAMA_URL}/api/chat"
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "tools": [API_ENDPOINTS_TOOL],
            "tool_choice": "auto",
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 4000
            }
        }
        
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=180)
        elapsed_time = time.time() - start_time
        
        response.raise_for_status()
        
        # 解析响应
        text = response.text
        result = None
        
        # 尝试解析完整 JSON
        try:
            result = response.json()
        except json.JSONDecodeError:
            # 流式响应：尝试解析每一行
            lines = text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    line_result = json.loads(line)
                    if line_result.get('message', {}).get('tool_calls'):
                        result = line_result
                        break
                    if 'message' in line_result:
                        result = line_result
                except json.JSONDecodeError:
                    continue
            
            if result is None and lines:
                try:
                    result = json.loads(lines[0])
                except:
                    pass
        
        if result is None:
            return {
                "success": False,
                "error": "无法解析响应",
                "response_text": text[:500],
                "elapsed_time": elapsed_time
            }
        
        message = result.get('message', {})
        tool_calls = message.get('tool_calls', [])
        content = message.get('content', '') or ''
        
        if tool_calls:
            return {
                "success": True,
                "tool_calls_count": len(tool_calls),
                "content_length": len(content),
                "elapsed_time": elapsed_time,
                "response_length": len(text)
            }
        else:
            return {
                "success": False,
                "error": "未返回工具调用",
                "content": content[:200] if content else "(空)",
                "content_length": len(content),
                "elapsed_time": elapsed_time,
                "response_length": len(text)
            }
    
    except requests.Timeout:
        return {
            "success": False,
            "error": "请求超时",
            "elapsed_time": 180
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "elapsed_time": 0
        }


def main():
    """主测试函数"""
    print("=" * 80)
    print("测试 Ollama Function Calling 在不同 prompt 长度下的表现")
    print(f"Ollama URL: {OLLAMA_URL}")
    print(f"模型: {MODEL}")
    print("=" * 80)
    print()
    
    # 测试不同的 prompt 长度
    test_lengths = [
        1000,      # 1K
        5000,      # 5K
        10000,     # 10K
        15000,     # 15K
        20000,     # 20K
        30000,     # 30K
        40000,     # 40K
        50000,     # 50K
        54355,     # 日志中的失败长度
        60000,     # 60K
        70000,     # 70K
        80000,     # 80K
        100000,    # 100K
    ]
    
    results = []
    
    for length in test_lengths:
        print(f"[测试] Prompt 长度: {length:,} 字符 ({length/1024:.1f} KB)")
        
        # 生成测试 prompt
        prompt = generate_test_prompt(length)
        actual_length = len(prompt)
        
        print(f"  - 实际 prompt 长度: {actual_length:,} 字符")
        
        # 测试
        result = test_function_calling(prompt, actual_length)
        result["prompt_length"] = actual_length
        
        if result["success"]:
            print(f"  [成功] 工具调用数: {result['tool_calls_count']}, "
                  f"响应长度: {result['response_length']} 字符, "
                  f"耗时: {result['elapsed_time']:.2f} 秒")
        else:
            print(f"  [失败] 错误: {result['error']}")
            if 'content' in result:
                print(f"  - Content: {result['content']}")
            if 'elapsed_time' in result and result['elapsed_time'] > 0:
                print(f"  - 耗时: {result['elapsed_time']:.2f} 秒")
        
        results.append(result)
        print()
        
        # 如果连续失败，可以提前停止
        if not result["success"] and length >= 20000:
            # 检查是否连续失败
            recent_failures = sum(1 for r in results[-3:] if not r.get("success"))
            if recent_failures >= 2:
                print(f"[警告] 连续失败 {recent_failures} 次，可能已达到临界点")
                # 继续测试，但记录警告
    
    # 汇总结果
    print("=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    print()
    
    print(f"{'Prompt 长度':<15} {'状态':<10} {'工具调用':<10} {'耗时(秒)':<12} {'错误信息'}")
    print("-" * 80)
    
    success_count = 0
    failure_count = 0
    max_success_length = 0
    
    for result in results:
        length = result["prompt_length"]
        if result["success"]:
            status = "成功"
            tool_calls = str(result.get("tool_calls_count", 0))
            elapsed = f"{result.get('elapsed_time', 0):.2f}"
            error = "-"
            success_count += 1
            if length > max_success_length:
                max_success_length = length
        else:
            status = "失败"
            tool_calls = "-"
            elapsed = f"{result.get('elapsed_time', 0):.2f}" if result.get('elapsed_time') else "-"
            error = result.get("error", "未知错误")[:30]
            failure_count += 1
        
        print(f"{length:>12,}  {status:<10} {tool_calls:<10} {elapsed:<12} {error}")
    
    print("-" * 80)
    print(f"总计: {len(results)} 次测试")
    print(f"成功: {success_count} 次")
    print(f"失败: {failure_count} 次")
    print(f"最大成功长度: {max_success_length:,} 字符 ({max_success_length/1024:.1f} KB)")
    
    # 找出临界点
    if max_success_length > 0:
        # 找到第一个失败的长度
        first_failure_length = None
        for result in results:
            if not result["success"] and result["prompt_length"] > max_success_length:
                first_failure_length = result["prompt_length"]
                break
        
        if first_failure_length:
            print(f"临界点估计: {max_success_length:,} - {first_failure_length:,} 字符之间")
        else:
            print(f"所有测试长度都成功，或未找到明确的临界点")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
