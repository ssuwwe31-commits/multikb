"""
代码分析 Agent V2（基于 Function Calling）
使用 LLM 进行真正的推理和迭代，而非简单的规则判断
"""

import os
import json
import re
import ast
import inspect
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from collections import defaultdict

import requests
from app.core.logging import logger
from app.config.settings import settings
from app.services.code_analyzer_service import CodeAnalyzerService
# API 调用链服务已删除
# API 调用链 AI 服务已删除
from app.services.code_parser_service import CodeParserService


class CodeAnalysisAgentV2:
    """
    代码分析 Agent V2（基于 Function Calling）
    
    核心改进：
    1. 使用 LLM 进行真正的推理（而非规则判断）
    2. 支持 Function Calling（工具调用）
    3. 支持 Thinking 模式（如果模型支持）
    4. 智能迭代和优化
    """
    
    # 忽略的目录
    IGNORE_PATTERNS = [
        'node_modules', 'dist', 'build', '__pycache__', '.git',
        'venv', 'env', '.venv', 'target', 'out', '.next',
        'coverage', '.pytest_cache', '.mypy_cache'
    ]
    
    def __init__(self, db: Optional[Any] = None):
        """
        初始化 Agent V2
        
        Args:
            db: 数据库会话（可选，用于向量检索）
        """
        # 使用现有的服务
        self.analyzer_service = CodeAnalyzerService()
        # API 调用链服务已删除
        # API 调用链 AI 服务已删除
        self.parser_service = CodeParserService()
        
        # 向量检索服务（如果可用）
        self.db = db
        self.vector_service = None
        if db:
            try:
                from app.services.vector_service import VectorService
                self.vector_service = VectorService(db)
                logger.info("Agent V2 已启用向量检索支持")
            except Exception as e:
                logger.warning(f"向量检索服务初始化失败: {e}")
        
        # LLM 配置
        self.ollama_url = settings.OLLAMA_BASE_URL or "http://localhost:11434"
        self.llm_model = settings.CODE_LLM_MODEL or "qwen2.5-coder:7b"
        
        # 注册工具
        self.tools = self._register_tools()
        
        # Agent 状态
        self.conversation_history: List[Dict] = []
        self.iteration_count: int = 0
        self.max_iterations: int = 5
        self.current_repo_path: Optional[str] = None  # 当前分析的仓库路径
        
        logger.info(f"代码分析 Agent V2 初始化完成，使用模型: {self.llm_model}")
    
    def _register_tools(self) -> Dict[str, Callable]:
        """注册工具函数"""
        return {
            "analyze_code_structure": self._tool_analyze_code_structure,
            "analyze_code_context": self._tool_analyze_code_context,
            "search_similar_code": self._tool_search_similar_code,
            "evaluate_analysis_quality": self._tool_evaluate_analysis_quality,
        }
    
    def analyze_repository(self, repo_path: str) -> Dict:
        """
        分析代码库（基于 Function Calling）
        
        Args:
            repo_path: 仓库本地路径
            
        Returns:
            分析结果字典
        """
        logger.info(f"Agent V2 开始分析代码库: {repo_path}")
        
        # 重置状态
        self.conversation_history = []
        self.iteration_count = 0
        self.current_repo_path = repo_path  # 保存当前仓库路径
        
        # 1. 初始观察
        observation = self._observe(repo_path)
        logger.info(f"Agent V2 观察完成: {observation['file_count']} 个文件")
        
        # 2. 构建系统提示（包含工具定义）
        system_prompt = self._build_system_prompt()
        
        # 3. 构建初始用户提示
        user_prompt = self._build_initial_prompt(observation, repo_path)
        
        # 4. 迭代分析循环
        all_results = {
            'static_analysis': None,
            'call_chain': None,
            'ai_enhanced': None,
            'agent_metadata': {
                'iterations': [],
                'final_strategy': None,
                'thinking_process': [],
                'total_tool_calls': 0,
                'total_llm_calls': 0
            }
        }
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 初始化思考历史
        self.thinking_history = []
        
        while self.iteration_count < self.max_iterations:
            iteration_result = {
                'iteration': self.iteration_count + 1,
                'messages': [],
                'tool_calls': [],
                'results': {}
            }
            
            # 调用 LLM
            logger.info(f"Agent V2 迭代 {self.iteration_count + 1}/{self.max_iterations}: 调用 LLM")
            all_results['agent_metadata']['total_llm_calls'] += 1
            
            try:
                response = self._call_llm(messages)
            except Exception as e:
                logger.error(f"Agent V2 LLM 调用失败: {e}", exc_info=True)
                # 如果 LLM 调用失败，尝试降级处理
                if self.iteration_count == 0:
                    # 第一次迭代失败，使用基础分析
                    logger.warning("Agent V2 LLM 调用失败，降级到基础分析")
                    all_results['static_analysis'] = self.analyzer_service.analyze_repository(repo_path)
                    # API 调用链分析已移除
                break
            
            # 解析响应（可能包含工具调用）
            parsed_response = self._parse_llm_response(response)
            iteration_result['messages'].append(parsed_response)
            
            # 如果有工具调用，执行工具
            tool_calls = parsed_response.get('tool_calls', [])
            if tool_calls:
                tool_calls_count = len(tool_calls)
                logger.info(f"Agent V2 检测到 {tool_calls_count} 个工具调用: {[tc.get('tool') for tc in tool_calls]}")
                # 更新工具调用计数
                all_results['agent_metadata']['total_tool_calls'] += tool_calls_count
                tool_results = self._execute_tools(tool_calls, repo_path, all_results)
                iteration_result['tool_calls'] = parsed_response['tool_calls']
                iteration_result['results'] = tool_results
                
                # 更新结果
                should_break = False
                for tool_name, tool_result in tool_results.items():
                    # 跳过错误结果
                    if isinstance(tool_result, dict) and 'error' in tool_result:
                        logger.warning(f"工具 {tool_name} 执行失败: {tool_result['error']}")
                        continue
                    
                    if tool_name == 'analyze_code_structure':
                        all_results['static_analysis'] = tool_result
                    elif tool_name == 'evaluate_analysis_quality':
                        # 评估结果，决定是否继续迭代
                        if not tool_result.get('need_iteration', False):
                            logger.info("Agent V2 评估：分析质量满足要求，停止迭代")
                            should_break = True
                            break
                
                if should_break:
                    all_results['agent_metadata']['iterations'].append(iteration_result)
                    break
                
                # 将工具结果添加到对话历史
                messages.append({
                    "role": "assistant",
                    "content": parsed_response.get('content', ''),
                    "tool_calls": parsed_response['tool_calls']
                })
                messages.append({
                    "role": "user",
                    "content": self._format_tool_results(tool_results)
                })
            else:
                # 没有工具调用，可能是最终结论
                logger.info("Agent V2 收到最终结论，停止迭代")
                final_result = self._parse_final_result(parsed_response.get('content', ''))
                all_results.update(final_result)
                break
            
            all_results['agent_metadata']['iterations'].append(iteration_result)
            self.iteration_count += 1
        
        # 保存思考过程到元数据
        if hasattr(self, 'thinking_history') and self.thinking_history:
            all_results['agent_metadata']['thinking_process'] = self.thinking_history
        
        logger.info(f"Agent V2 分析完成: 迭代 {self.iteration_count} 次, "
                   f"LLM 调用 {all_results['agent_metadata']['total_llm_calls']} 次, "
                   f"工具调用 {all_results['agent_metadata']['total_tool_calls']} 次")
        return all_results
    
    def _build_system_prompt(self) -> str:
        """构建系统提示（包含工具定义）"""
        tools_description = """
你可以使用以下工具来分析代码库：

1. analyze_code_structure(repo_path, file_patterns=None, max_files=None)
   - 分析代码库结构，提取文件、函数、类等基本信息
   - 返回：统计信息、文件列表、依赖关系、API 端点统计

2. analyze_code_context(file_path, function_name, context_lines=20)
   - 分析代码上下文，理解函数调用关系
   - 返回：函数代码、调用关系、依赖信息

3. search_similar_code(query, top_k=10, file_type="all")
   - 使用向量搜索查找相似的代码片段
   - 返回：相似代码列表

4. evaluate_analysis_quality(analysis_result, metrics)
   - 评估分析结果质量，判断是否需要迭代
   - 返回：质量评估、是否需要迭代、改进建议

工具调用格式（JSON）：
{
  "tool": "tool_name",
  "arguments": {
    "param1": "value1",
    "param2": "value2"
  }
}

如果需要调用多个工具，可以返回 JSON 数组：
[
  {"tool": "tool1", "arguments": {...}},
  {"tool": "tool2", "arguments": {...}}
]

请根据代码库的特点，智能地选择和使用这些工具，逐步深入分析。
"""
        
        return f"""你是一个专业的代码分析 Agent，擅长分析代码库的结构和依赖关系。

{tools_description}

**分析任务：**

1. **代码结构分析**（必需）
   - 调用 analyze_code_structure 了解代码库整体情况
   - 包括：文件统计、语言分布、函数/类统计、API 端点统计、依赖关系等

2. **深度分析**（可选，根据需要）
   - 使用 analyze_code_context 分析特定函数的上下文
   - 使用 search_similar_code 查找相似代码片段
   - 使用 evaluate_analysis_quality 评估分析质量

**分析流程：**
1. 首先调用 analyze_code_structure 获取代码库的整体信息
2. 根据分析结果，决定是否需要进一步分析特定部分
3. 如果需要，使用其他工具进行深入分析
4. 最后给出清晰的分析结论

请根据代码库的特点，智能地选择和使用工具进行分析。"""
    
    def _build_initial_prompt(self, observation: Dict, repo_path: str) -> str:
        """构建初始用户提示"""
        return f"""请分析以下代码库：

路径: {repo_path}
文件数: {observation['file_count']}
代码行数: {observation['total_lines']}
语言分布: {json.dumps(observation['languages'], indent=2)}
结构: {json.dumps(observation['structure'], indent=2)}

**分析任务：**
1. 首先调用 analyze_code_structure 了解代码库的整体结构
2. 分析代码库的架构、依赖关系、关键组件等
3. 根据需要进行深入分析（如特定函数、相似代码等）

请开始分析，首先调用 analyze_code_structure。"""
    
    def _call_llm(self, messages: List[Dict]) -> str:
        """调用 LLM（支持 thinking 模式）"""
        try:
            # 构建请求
            url = f"{self.ollama_url}/api/chat"
            payload = {
                "model": self.llm_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 4096,  # 增加输出长度，支持更长的工具调用
                }
            }
            
            # 如果模型支持 thinking，添加参数
            if "qwen" in self.llm_model.lower() or "thinking" in self.llm_model.lower():
                payload["options"]["thinking"] = True
                payload["options"]["max_thinking_steps"] = 5
            
            logger.debug(f"Agent V2 调用 LLM: {self.llm_model}, 消息数: {len(messages)}")
            
            response = requests.post(url, json=payload, timeout=600)  # 增加超时到10分钟
            response.raise_for_status()
            
            result = response.json()
            content = result.get('message', {}).get('content', '')
            
            # 提取 thinking 过程（如果有）
            if 'thinking' in result.get('message', {}):
                thinking = result['message']['thinking']
                logger.info(f"Agent V2 Thinking 过程（前200字符）: {thinking[:200]}...")
                # 保存思考过程到元数据
                if not hasattr(self, 'thinking_history'):
                    self.thinking_history = []
                self.thinking_history.append({
                    'iteration': self.iteration_count + 1,
                    'thinking': thinking
                })
            
            logger.debug(f"Agent V2 LLM 响应长度: {len(content)} 字符")
            return content
            
        except requests.exceptions.Timeout:
            logger.error(f"Agent V2 LLM 调用超时: {self.llm_model}")
            raise
        except Exception as e:
            logger.error(f"Agent V2 LLM 调用失败: {e}", exc_info=True)
            raise
    
    def _parse_llm_response(self, response: str) -> Dict:
        """解析 LLM 响应，提取工具调用（支持多种格式）"""
        result = {
            'content': response,
            'tool_calls': []
        }
        
        # 模式1: 纯 JSON 对象（单个工具调用）
        # 匹配: {"tool": "xxx", "arguments": {...}}
        json_obj_pattern = r'\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{[^}]*\}\s*\}'
        json_obj_matches = re.finditer(json_obj_pattern, response, re.DOTALL)
        for match in json_obj_matches:
            try:
                tool_call = json.loads(match.group())
                if 'tool' in tool_call:
                    result['tool_calls'].append(tool_call)
            except:
                pass
        
        # 模式2: JSON 数组（多个工具调用）
        # 匹配: [{"tool": "xxx", "arguments": {...}}, ...]
        array_pattern = r'\[\s*(\{[^}]*"tool"[^}]*\}[,\s]*)+]'
        array_match = re.search(array_pattern, response, re.DOTALL)
        if array_match:
            try:
                tool_calls = json.loads(array_match.group())
                if isinstance(tool_calls, list):
                    result['tool_calls'].extend([tc for tc in tool_calls if isinstance(tc, dict) and 'tool' in tc])
            except:
                pass
        
        # 模式3: 代码块中的 JSON
        # 匹配: ```json\n{...}\n```
        code_block_pattern = r'```(?:json)?\s*(\{[^}]*"tool"[^}]*\})\s*```'
        code_block_matches = re.finditer(code_block_pattern, response, re.DOTALL)
        for match in code_block_matches:
            try:
                tool_call = json.loads(match.group(1))
                if 'tool' in tool_call and tool_call not in result['tool_calls']:
                    result['tool_calls'].append(tool_call)
            except:
                pass
        
        # 模式4: 从文本中提取工具名称和参数（更宽松的匹配）
        if not result['tool_calls']:
            # 查找工具名称
            tool_name_pattern = r'(?:tool|function|调用工具)[:：]\s*"?([a-z_]+)"?'
            tool_names = re.findall(tool_name_pattern, response, re.IGNORECASE)
            
            for tool_name in tool_names:
                if tool_name in self.tools:
                    # 尝试提取参数（查找 arguments 或 parameters）
                    arg_patterns = [
                        rf'"{tool_name}"[^{{]*"arguments"\s*:\s*(\{{[^}}]+\}})',
                        rf'arguments\s*:\s*(\{{[^}}]*\}})',
                        rf'parameters\s*:\s*(\{{[^}}]*\}})',
                    ]
                    
                    arguments = {}
                    for pattern in arg_patterns:
                        arg_match = re.search(pattern, response, re.DOTALL)
                        if arg_match:
                            try:
                                arguments = json.loads(arg_match.group(1))
                                break
                            except:
                                pass
                    
                    result['tool_calls'].append({
                        'tool': tool_name,
                        'arguments': arguments
                    })
        
        # 去重
        seen = set()
        unique_tool_calls = []
        for tc in result['tool_calls']:
            key = (tc.get('tool'), json.dumps(tc.get('arguments', {}), sort_keys=True))
            if key not in seen:
                seen.add(key)
                unique_tool_calls.append(tc)
        result['tool_calls'] = unique_tool_calls
        
        if result['tool_calls']:
            logger.info(f"Agent V2 解析到 {len(result['tool_calls'])} 个工具调用: {[tc.get('tool') for tc in result['tool_calls']]}")
        
        return result
    
    def _execute_tools(self, tool_calls: List[Dict], repo_path: str, all_results: Dict) -> Dict:
        """执行工具调用"""
        results = {}
        
        for tool_call in tool_calls:
            tool_name = tool_call.get('tool')
            arguments = tool_call.get('arguments', {})
            
            if tool_name not in self.tools:
                logger.warning(f"Agent V2 未知工具: {tool_name}")
                results[tool_name] = {"error": f"Unknown tool: {tool_name}"}
                continue
            
            try:
                logger.info(f"Agent V2 执行工具: {tool_name}, 参数: {list(arguments.keys())}")
                tool_func = self.tools[tool_name]
                
                # 准备参数：自动注入 repo_path（如果工具需要）
                import inspect
                sig = inspect.signature(tool_func)
                if 'repo_path' in sig.parameters and 'repo_path' not in arguments:
                    arguments['repo_path'] = repo_path or self.current_repo_path
                
                # 执行工具（只传递工具函数接受的参数）
                valid_args = {}
                for param_name in sig.parameters:
                    if param_name in arguments:
                        valid_args[param_name] = arguments[param_name]
                
                result = tool_func(**valid_args)
                results[tool_name] = result
                
                logger.info(f"Agent V2 工具执行完成: {tool_name}, 结果类型: {type(result).__name__}")
                
            except Exception as e:
                logger.error(f"Agent V2 工具执行失败: {tool_name}, 错误: {e}", exc_info=True)
                results[tool_name] = {"error": str(e)}
        
        return results
    
    def _format_tool_results(self, tool_results: Dict) -> str:
        """格式化工具结果为提示词"""
        formatted = "工具执行结果：\n\n"
        
        has_api_endpoints = False
        api_stats = {}
        
        for tool_name, result in tool_results.items():
            formatted += f"## {tool_name}\n"
            if isinstance(result, dict):
                if 'error' in result:
                    formatted += f"错误: {result['error']}\n\n"
                else:
                    # 检查是否有 API 端点统计
                    if tool_name == 'analyze_code_structure':
                        api_stats = result.get('statistics', {}).get('api_endpoints', {})
                        frontend_count = api_stats.get('frontend', 0)
                        backend_count = api_stats.get('backend', 0)
                        if frontend_count > 0 or backend_count > 0:
                            has_api_endpoints = True
                            formatted += f"**重要发现：检测到前端 API={frontend_count} 个，后端端点={backend_count} 个！**\n\n"
                    
                    formatted += f"{json.dumps(result, indent=2, ensure_ascii=False)}\n\n"
            else:
                formatted += f"{str(result)}\n\n"
        
        formatted += "\n请根据这些结果继续分析，或给出最终结论。"
        
        return formatted
    
    def _parse_final_result(self, content: str) -> Dict:
        """解析最终结果"""
        # 尝试从文本中提取结构化结果
        result = {}
        
        # 查找 JSON 格式的结果
        json_match = re.search(r'\{[^{}]*"static_analysis"[^{}]*\}', content, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
            except:
                pass
        
        return result
    
    # ============================================
    # 工具函数实现
    # ============================================
    
    def _tool_analyze_code_structure(self, repo_path: str, file_patterns: Optional[List[str]] = None, max_files: Optional[int] = None) -> Dict:
        """工具：分析代码结构"""
        logger.info(f"工具执行: analyze_code_structure, repo_path={repo_path}")
        result = self.analyzer_service.analyze_repository(repo_path)
        return result
    
    # API 调用链相关工具函数已删除
    def _tool_analyze_code_context(self, file_path: str, function_name: str, context_lines: int = 20, repo_path: Optional[str] = None) -> Dict:
        """工具：分析代码上下文"""
        logger.info(f"工具执行: analyze_code_context, file={file_path}, function={function_name}")
        
        # 使用当前仓库路径或传入的路径
        repo_path = repo_path or self.current_repo_path
        if not repo_path:
            return {
                'file_path': file_path,
                'function_name': function_name,
                'error': 'repo_path not provided'
            }
        
        # 构建完整文件路径
        full_file_path = os.path.join(repo_path, file_path) if not os.path.isabs(file_path) else file_path
        
        if not os.path.exists(full_file_path):
            return {
                'file_path': file_path,
                'function_name': function_name,
                'error': f'File not found: {full_file_path}'
            }
        
        try:
            with open(full_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            # 检测语言
            language = self.parser_service.detect_language(full_file_path)
            
            # 提取函数代码
            function_code = ""
            function_line_start = 0
            function_line_end = 0
            
            if language == 'python':
                # 使用 AST 提取函数（Python）
                if language == 'python':
                    try:
                        tree = ast.parse(content)
                        for node_ast in ast.walk(tree):
                            if isinstance(node_ast, ast.FunctionDef) and node_ast.name == function_name:
                                function_line_start = node_ast.lineno - 1
                                function_line_end = node_ast.end_lineno if hasattr(node_ast, 'end_lineno') else node_ast.lineno + 20
                                function_code = '\n'.join(lines[function_line_start:function_line_end])
                                break
                    except:
                        # AST 解析失败，使用正则表达式
                        pattern = rf'def\s+{re.escape(function_name)}\s*\([^)]*\):'
                else:
                    # 非 Python 语言，使用正则表达式
                    pattern = rf'(?:function\s+{re.escape(function_name)}|const\s+{re.escape(function_name)}\s*=\s*(?:async\s*)?\(|{re.escape(function_name)}\s*:\s*(?:async\s*)?\()'
                    for i, line in enumerate(lines):
                        if re.match(pattern, line.strip()):
                            function_line_start = i
                            # 查找函数结束（缩进回到函数定义级别）
                            indent_level = len(line) - len(line.lstrip())
                            for j in range(i + 1, min(i + 200, len(lines))):
                                if lines[j].strip() and len(lines[j]) - len(lines[j].lstrip()) <= indent_level:
                                    function_line_end = j
                                    break
                            else:
                                function_line_end = min(i + 50, len(lines))
                            function_code = '\n'.join(lines[function_line_start:function_line_end])
                            break
            
            elif language in ['javascript', 'typescript']:
                # 使用正则表达式提取函数
                pattern = rf'(?:function\s+{re.escape(function_name)}|const\s+{re.escape(function_name)}\s*=\s*(?:async\s*)?\(|{re.escape(function_name)}\s*:\s*(?:async\s*)?\()'
                for i, line in enumerate(lines):
                    if re.search(pattern, line):
                        function_line_start = i
                        # 查找函数结束（简单策略：查找下一个同级别函数或类）
                        brace_count = line.count('{') - line.count('}')
                        for j in range(i + 1, min(i + 200, len(lines))):
                            brace_count += lines[j].count('{') - lines[j].count('}')
                            if brace_count == 0 and lines[j].strip():
                                function_line_end = j + 1
                                break
                        else:
                            function_line_end = min(i + 50, len(lines))
                        function_code = '\n'.join(lines[function_line_start:function_line_end])
                        break
            
            # 提取上下文（函数前后各 context_lines 行）
            context_start = max(0, function_line_start - context_lines)
            context_end = min(len(lines), function_line_end + context_lines)
            context_code = '\n'.join(lines[context_start:context_end])
            
            # 提取导入语句
            imports = []
            for i, line in enumerate(lines[:min(50, len(lines))]):
                if re.match(r'^(import|from)\s+', line.strip()):
                    imports.append(line.strip())
            
            return {
                'file_path': file_path,
                'function_name': function_name,
                'function_code': function_code,
                'function_line_start': function_line_start + 1,
                'function_line_end': function_line_end,
                'context_code': context_code,
                'imports': imports[:10],  # 只返回前10个导入
                'language': language
            }
            
        except Exception as e:
            logger.error(f"分析代码上下文失败: {full_file_path}, {e}", exc_info=True)
            return {
                'file_path': file_path,
                'function_name': function_name,
                'error': str(e)
            }
    
    def _tool_search_similar_code(self, query: str, top_k: int = 10, file_type: str = "all", repo_path: Optional[str] = None) -> List[Dict]:
        """工具：搜索相似代码（使用向量搜索）"""
        logger.info(f"工具执行: search_similar_code, query={query}, top_k={top_k}, file_type={file_type}")
        
        if not self.vector_service or not self.db:
            logger.warning("向量搜索服务不可用，返回空结果")
            return []
        
        repo_path = repo_path or self.current_repo_path
        if not repo_path:
            logger.warning("repo_path 未提供，无法进行向量搜索")
            return []
        
        try:
            # 获取仓库ID（从路径推断或查询数据库）
            repository_id = self._get_repository_id_from_path(repo_path)
            if not repository_id:
                logger.warning(f"无法获取仓库ID: {repo_path}")
                return []
            
            # 生成查询向量
            query_vector = self.vector_service.generate_embedding(query)
            if not query_vector:
                logger.warning("生成查询向量失败")
                return []
            
            # 使用 OpenSearch 进行向量搜索
            from app.services.opensearch_service import OpenSearchService
            from opensearch_schemas.code_indices import CODE_FILES_INDEX, CODE_SYMBOLS_INDEX
            from app.config.settings import settings
            
            opensearch = OpenSearchService()
            results = []
            
            # 搜索代码文件
            if file_type in ['all', 'file']:
                file_results = opensearch.client.search(
                    index=settings.CODE_FILES_INDEX,
                    body={
                        "size": top_k,
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"repository_id": repository_id}},
                                    {
                                        "knn": {
                                            "content_vector": {
                                                "vector": query_vector,
                                                "k": top_k
                                            }
                                        }
                                    }
                                ]
                            }
                        },
                        "_source": ["file_id", "file_path", "file_name", "content_summary", "language"]
                    }
                )
                
                for hit in file_results['hits']['hits']:
                    source = hit['_source']
                    results.append({
                        'type': 'file',
                        'file_path': source.get('file_path'),
                        'file_name': source.get('file_name'),
                        'summary': source.get('content_summary', ''),
                        'language': source.get('language'),
                        'score': hit['_score']
                    })
            
            # 搜索代码符号
            if file_type in ['all', 'symbol']:
                symbol_results = opensearch.client.search(
                    index=settings.CODE_SYMBOLS_INDEX,
                    body={
                        "size": top_k,
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"repository_id": repository_id}},
                                    {
                                        "knn": {
                                            "content_vector": {
                                                "vector": query_vector,
                                                "k": top_k
                                            }
                                        }
                                    }
                                ]
                            }
                        },
                        "_source": ["symbol_id", "symbol_name", "qualified_name", "file_path", "signature", "docstring"]
                    }
                )
                
                for hit in symbol_results['hits']['hits']:
                    source = hit['_source']
                    results.append({
                        'type': 'symbol',
                        'symbol_name': source.get('symbol_name'),
                        'qualified_name': source.get('qualified_name'),
                        'file_path': source.get('file_path'),
                        'signature': source.get('signature', ''),
                        'docstring': source.get('docstring', '')[:200],
                        'score': hit['_score']
                    })
            
            # 使用 Rerank 精排（如果可用）
            if len(results) > 1:
                try:
                    from app.services.rerank_service import RerankService
                    rerank_service = RerankService()
                    
                    if rerank_service.is_available():
                        # 准备 rerank 候选
                        rerank_candidates = []
                        for r in results:
                            # 构建用于 rerank 的内容
                            content_parts = []
                            if r.get('type') == 'file':
                                content_parts.append(f"文件: {r.get('file_path', '')}")
                                content_parts.append(f"摘要: {r.get('summary', '')}")
                            elif r.get('type') == 'symbol':
                                content_parts.append(f"符号: {r.get('qualified_name', r.get('symbol_name', ''))}")
                                content_parts.append(f"签名: {r.get('signature', '')}")
                                content_parts.append(f"说明: {r.get('docstring', '')}")
                            
                            rerank_candidates.append({
                                'content': '\n'.join(content_parts),
                                'score': r.get('score', 0.0),
                                **r
                            })
                        
                        # 使用 rerank 重新排序
                        reranked_results = rerank_service.rerank(
                            query=query,
                            candidates=rerank_candidates,
                            top_k=top_k
                        )
                        
                        logger.info(f"代码搜索 Rerank 完成: 输入={len(rerank_candidates)}, 输出={len(reranked_results)}")
                        return reranked_results[:top_k]
                except Exception as e:
                    logger.warning(f"Rerank 排序失败，使用原始排序: {e}")
            
            # 降级：按原始分数排序
            results.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            logger.info(f"向量搜索完成: 找到 {len(results)} 个相似代码片段")
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"向量搜索失败: {e}", exc_info=True)
            return []
    
    def _get_repository_id_from_path(self, repo_path: str) -> Optional[int]:
        """从路径获取仓库ID"""
        if not self.db:
            return None
        
        try:
            # 从路径中提取仓库ID（路径格式：.../code_repositories/{id}/...）
            import re
            match = re.search(r'code_repositories[\\/](\d+)', repo_path)
            if match:
                return int(match.group(1))
            
            # 或者查询数据库
            from app.models.code_repository import CodeRepository
            repo = self.db.query(CodeRepository).filter(
                CodeRepository.local_path == repo_path
            ).first()
            
            return repo.id if repo else None
            
        except Exception as e:
            logger.warning(f"获取仓库ID失败: {e}")
            return None
    
    def _tool_evaluate_analysis_quality(self, analysis_result: Dict, metrics: Optional[Dict] = None) -> Dict:
        """工具：评估分析质量"""
        logger.info("工具执行: evaluate_analysis_quality")
        
        call_chain = analysis_result.get('call_chain', {})
        static_analysis = analysis_result.get('static_analysis', {})
        
        nodes_count = len(call_chain.get('nodes', []))
        edges_count = len(call_chain.get('edges', []))
        
        # 计算质量指标
        completeness = edges_count / max(nodes_count, 1) if nodes_count > 0 else 0.0
        
        # 覆盖率：已分析的节点数 / 总节点数
        coverage = 1.0
        if static_analysis:
            total_apis = static_analysis.get('statistics', {}).get('api_endpoints', {})
            total_frontend = total_apis.get('frontend', 0)
            total_backend = total_apis.get('backend', 0)
            total_expected = total_frontend + total_backend
            
            if total_expected > 0:
                coverage = nodes_count / total_expected
        
        # 准确度：基于边的置信度
        accuracy = 0.7  # 默认值
        if edges_count > 0:
            confidences = [e.get('confidence', 0.5) for e in call_chain.get('edges', [])]
            if confidences:
                accuracy = sum(confidences) / len(confidences)
        
        # 判断是否需要迭代
        need_iteration = (
            completeness < 0.3 or  # 完整度不足
            edges_count == 0 or  # 没有边
            coverage < 0.5 or  # 覆盖率不足
            accuracy < 0.6  # 准确度不足
        )
        
        suggestions = []
        if completeness < 0.3:
            suggestions.append("完整度不足，建议使用语义匹配增强调用关系")
        if edges_count == 0:
            suggestions.append("没有找到任何调用关系，检查 API 端点提取是否正确")
        if coverage < 0.5:
            suggestions.append("覆盖率不足，可能需要扩大分析范围")
        if accuracy < 0.6:
            suggestions.append("准确度不足，建议使用 AI 增强匹配")
        
        return {
            'completeness': completeness,
            'coverage': coverage,
            'accuracy': accuracy,
            'nodes_count': nodes_count,
            'edges_count': edges_count,
            'need_iteration': need_iteration,
            'suggestions': suggestions if need_iteration else ["分析质量良好"]
        }
    
    # ============================================
    # 辅助方法
    # ============================================
    
    def _observe(self, repo_path: str) -> Dict:
        """观察：获取代码库基本信息"""
        files = []
        languages = defaultdict(int)
        total_lines = 0
        
        for root, dirs, filenames in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not any(p in d for p in self.IGNORE_PATTERNS)]
            
            for filename in filenames:
                file_path = os.path.join(root, filename)
                language = self.parser_service.detect_language(file_path)
                if language:
                    files.append(os.path.relpath(file_path, repo_path))
                    languages[language] += 1
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            total_lines += len(f.readlines())
                    except:
                        pass
        
        structure = self._analyze_structure(repo_path)
        
        return {
            'file_count': len(files),
            'languages': dict(languages),
            'total_lines': total_lines,
            'structure': structure,
            'files': files[:100]
        }
    
    def _analyze_structure(self, repo_path: str) -> Dict:
        """分析代码库结构"""
        structure = {
            'has_frontend': False,
            'has_backend': False,
            'has_tests': False,
            'main_directories': []
        }
        
        common_dirs = ['src', 'app', 'backend', 'frontend', 'client', 'server', 'tests', 'test']
        
        for item in os.listdir(repo_path):
            item_path = os.path.join(repo_path, item)
            if os.path.isdir(item_path):
                item_lower = item.lower()
                
                if any(frontend in item_lower for frontend in ['frontend', 'client', 'web', 'ui']):
                    structure['has_frontend'] = True
                elif any(backend in item_lower for backend in ['backend', 'server', 'api', 'app']):
                    structure['has_backend'] = True
                elif any(test in item_lower for test in ['test', 'spec']):
                    structure['has_tests'] = True
                
                if item in common_dirs:
                    structure['main_directories'].append(item)
        
        return structure
