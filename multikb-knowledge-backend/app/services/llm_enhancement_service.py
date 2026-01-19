"""
LLM 增强服务（统一封装）
支持缓存、批量处理、JSON 解析、Function Calling 等功能
"""

import hashlib
import requests
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from app.core.logging import logger
from app.config.settings import settings


class LLMEnhancementService:
    """LLM 增强服务（统一封装，支持缓存和批量处理）"""
    
    def __init__(self, db=None, repository_id: Optional[int] = None):
        """
        初始化 LLM 增强服务
        
        Args:
            db: 数据库会话（用于持久化缓存）
            repository_id: 仓库ID（用于缓存关联，可选）
        """
        self.ollama_url = settings.OLLAMA_BASE_URL
        self.llm_model = settings.CODE_LLM_MODEL  # qwen3-coder:latest
        self.db = db  # 数据库会话（用于持久化缓存）
        self.repository_id = repository_id  # 仓库ID（用于缓存关联）
        self.memory_cache = {}  # 内存缓存（临时）
        self.cache_ttl = 86400  # 缓存过期时间（24小时）
    
    def call_llm_with_cache(self, prompt: str, cache_key: str = None, timeout: int = 180) -> str:
        """
        调用 LLM（带缓存）
        
        Args:
            prompt: 提示词
            cache_key: 缓存键（如果提供，会缓存结果）
            timeout: 超时时间（秒），qwen3-coder 可能需要更长时间
            
        Returns:
            LLM 返回的内容
        """
        # 生成缓存键（如果没有提供）
        if not cache_key:
            cache_key = hashlib.md5(prompt.encode()).hexdigest()
        
        # 1. 检查内存缓存
        if cache_key in self.memory_cache:
            logger.debug(f"[LLM缓存] 内存缓存命中: {cache_key[:16]}...")
            return self.memory_cache[cache_key]
        
        # 2. 检查数据库缓存（如果可用）
        if self.db:
            cached_result = self._get_db_cache(cache_key)
            if cached_result:
                logger.debug(f"[LLM缓存] 数据库缓存命中: {cache_key[:16]}...")
                self.memory_cache[cache_key] = cached_result  # 同时更新内存缓存
                return cached_result
        
        # 3. 调用 LLM
        try:
            logger.info(f"[LLM调用] 使用模型 {self.llm_model}, prompt 长度: {len(prompt)} 字符")
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # 降低温度以提高准确性
                        "top_p": 0.9,
                        "num_predict": 4000  # 允许更长的输出
                    }
                },
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("response", "").strip()
            
            if not content:
                raise ValueError("LLM 返回空内容")
            
            # 4. 缓存结果
            self.memory_cache[cache_key] = content
            
            # 持久化到数据库（如果可用）
            if self.db:
                self._save_db_cache(cache_key, content)
            
            logger.info(f"[LLM调用] 成功，响应长度: {len(content)} 字符")
            return content
            
        except requests.Timeout:
            logger.error(f"[LLM调用] 超时: {timeout}秒")
            raise
        except Exception as e:
            logger.error(f"[LLM调用] 失败: {e}")
            raise
    
    def _get_db_cache(self, cache_key: str) -> Optional[str]:
        """从数据库获取缓存"""
        if not self.db:
            return None
        
        try:
            from app.models.code_analysis_cache import CodeAnalysisCache
            
            query = self.db.query(CodeAnalysisCache).filter(
                CodeAnalysisCache.cache_key == cache_key,
                CodeAnalysisCache.cache_type == 'llm_enhancement',
                CodeAnalysisCache.expires_at > datetime.now()
            )
            
            # 如果提供了 repository_id，添加过滤条件（提高查询效率）
            if self.repository_id:
                query = query.filter(CodeAnalysisCache.repository_id == self.repository_id)
            
            cache = query.first()
            
            if cache:
                return cache.cache_data if cache.cache_data else None
        except Exception as e:
            logger.debug(f"[LLM缓存] 数据库查询失败: {e}")
        return None
    
    def _save_db_cache(self, cache_key: str, content: str):
        """保存缓存到数据库"""
        if not self.db:
            return
        
        # 如果没有 repository_id，无法保存到数据库（CodeAnalysisCache 要求 repository_id 非空）
        if not self.repository_id:
            logger.debug(f"[LLM缓存] 缺少 repository_id，跳过数据库缓存（仅使用内存缓存）")
            return
        
        try:
            from app.models.code_analysis_cache import CodeAnalysisCache
            
            # 如果内容太大，保存到 MinIO
            if len(content) > 100000:  # 100KB
                # TODO: 保存到 MinIO 的逻辑
                logger.warning(f"[LLM缓存] 内容过大 ({len(content)} 字符)，跳过数据库缓存")
                return
            
            cache = CodeAnalysisCache(
                repository_id=self.repository_id,  # 必需字段
                cache_key=cache_key,
                cache_type='llm_enhancement',
                cache_data=content,
                expires_at=datetime.now() + timedelta(seconds=self.cache_ttl)
            )
            self.db.add(cache)
            self.db.commit()
        except Exception as e:
            logger.debug(f"[LLM缓存] 数据库保存失败: {e}")
            if self.db:
                self.db.rollback()
    
    def parse_json_response(self, content: str) -> Dict:
        """
        解析 LLM 返回的 JSON（增强版）
        
        Args:
            content: LLM 返回的内容
            
        Returns:
            解析后的 JSON 字典
        """
        # 移除代码块标记
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            # 尝试提取 JSON 部分
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            
            # 如果还是失败，尝试修复常见的 JSON 问题
            # 1. 移除尾随逗号
            content = re.sub(r',\s*}', '}', content)
            content = re.sub(r',\s*]', ']', content)
            
            try:
                return json.loads(content)
            except:
                logger.error(f"[JSON解析] 失败: {e}, 内容前500字符: {content[:500]}")
                raise ValueError(f"无法解析 LLM 返回的 JSON: {e}")
    
    def batch_call_llm(self, prompts: List[str], batch_size: int = 8) -> List[str]:
        """
        批量调用 LLM（充分利用 qwen3-coder 的长上下文）
        
        Args:
            prompts: 提示词列表
            batch_size: 每批处理的提示词数量（默认 8，充分利用 256K tokens）
                       - 256K tokens 需要分配给 prompt 和 response
                       - 实际可用约 200K tokens 用于 prompt
                       - 每个任务平均 20-25K tokens，可以处理 8 个任务
            
        Returns:
            结果列表
        """
        results = []
        
        # qwen3-coder 256K tokens 可以处理更多任务
        # 根据平均 prompt 长度动态调整 batch_size
        for i in range(0, len(prompts), batch_size):
            batch = prompts[i:i+batch_size]
            
            # 合并多个提示词为一个（利用长上下文）
            combined_prompt = "\n\n" + "="*80 + "\n\n".join([
                f"任务 {j+1}/{len(batch)}:\n{prompt}" 
                for j, prompt in enumerate(batch)
            ]) + "\n\n" + "="*80
            
            combined_prompt += f"""

请按顺序回答每个任务，使用 JSON 数组格式返回结果。
数组中的每个元素对应一个任务的结果。

返回格式：
[
  {{"task": 1, "result": ...}},
  {{"task": 2, "result": ...}},
  ...
]
"""
            
            try:
                result = self.call_llm_with_cache(combined_prompt, timeout=300)  # 批量处理需要更长时间
                # 解析批量结果
                parsed = self.parse_json_response(result)
                if isinstance(parsed, list):
                    # 提取每个任务的结果
                    for item in parsed:
                        if isinstance(item, dict) and 'result' in item:
                            results.append(item['result'])
                        else:
                            results.append(item)
                else:
                    results.append(parsed)
                    
                logger.info(f"[批量LLM] 成功处理 {len(batch)} 个任务")
            except Exception as e:
                logger.error(f"[批量LLM] 批量处理失败: {e}，降级为逐个处理")
                # 降级：逐个调用
                for prompt in batch:
                    try:
                        result = self.call_llm_with_cache(prompt)
                        results.append(result)
                    except:
                        results.append(None)
        
        return results
    
    def call_llm_with_function_calling(
        self, 
        prompt: str, 
        tools: List[Dict],
        cache_key: str = None,
        timeout: int = 180,
        tool_choice: str = "auto",
        task_type: str = "general",  # "api_endpoints", "storage_systems", "general"
        return_cache_info: bool = False  # 是否返回缓存命中信息（默认 False，保持向后兼容）
    ) -> Dict:
        """
        使用 Function Calling 调用 LLM（更稳定，推荐用于结构化任务）
        
        策略：
        1. 如果 prompt <= 10K 字符：直接使用 Function Calling
        2. 如果 prompt > 10K 字符：先总结代码，再用 Function Calling 分析总结后的内容
        
        Args:
            prompt: 用户提示词
            tools: 工具定义列表（OpenAI 格式）
            cache_key: 缓存键（如果提供，会缓存结果）
            timeout: 超时时间（秒）
            tool_choice: 工具选择策略（"auto", "required", "none")
            task_type: 任务类型，用于优化总结策略（"api_endpoints", "storage_systems", "general")
            return_cache_info: 是否返回缓存命中信息（默认 False，保持向后兼容）
            
        Returns:
            如果 return_cache_info=True，返回 {"result": ..., "cache_hit": bool, "cache_type": str}
            否则返回原来的结果（保持向后兼容）
            
        Raises:
            ValueError: 如果没有工具调用或解析失败
        """
        # Function Calling 的 prompt 长度限制（已测试验证）
        # 注意：10K 字符是临界点，可能因为 prompt 模板开销导致失败
        # 降低到 9,500 字符，预留更多安全边际
        MAX_FUNCTION_CALLING_PROMPT_LENGTH = 9500  # 9.5K 字符（更保守）
        
        # 生成缓存键（包含工具定义，确保唯一性）
        original_cache_key = cache_key
        if not cache_key:
            tools_hash = hashlib.md5(json.dumps(tools, sort_keys=True).encode()).hexdigest()[:16]
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:16]
            cache_key = f"fc:{tools_hash}:{prompt_hash}"
        else:
            # 如果提供了 cache_key，添加 function_calling 前缀
            cache_key = f"fc:{cache_key}"
        
        # 1. 检查缓存
        if cache_key in self.memory_cache:
            logger.debug(f"[LLM缓存] Function Calling 内存缓存命中: {cache_key[:32]}...")
            result = self.memory_cache[cache_key]
            if return_cache_info:
                return {"result": result, "cache_hit": True, "cache_type": "memory"}
            return result
        
        if self.db:
            cached_result = self._get_db_cache(cache_key)
            if cached_result:
                try:
                    result = json.loads(cached_result)
                    logger.debug(f"[LLM缓存] Function Calling 数据库缓存命中: {cache_key[:32]}...")
                    self.memory_cache[cache_key] = result
                    if return_cache_info:
                        return {"result": result, "cache_hit": True, "cache_type": "database"}
                    return result
                except:
                    pass
        
        # 2. 检查 prompt 长度，如果超过限制，先总结代码
        if len(prompt) > MAX_FUNCTION_CALLING_PROMPT_LENGTH:
            logger.info(f"[LLM调用] Prompt 长度 {len(prompt)} 超过 Function Calling 限制 {MAX_FUNCTION_CALLING_PROMPT_LENGTH}，先总结代码")
            
            # 提取代码内容并总结
            summarized_prompt = self._summarize_code_for_function_calling(prompt, task_type, MAX_FUNCTION_CALLING_PROMPT_LENGTH)
            
            if len(summarized_prompt) > MAX_FUNCTION_CALLING_PROMPT_LENGTH:
                # 如果总结后还是超过，降级到 prompt-based
                logger.warning(f"[LLM调用] 总结后 prompt 长度 {len(summarized_prompt)} 仍超过限制，降级到 prompt-based")
                # 注意：降级到 prompt-based 时，不返回缓存信息（保持向后兼容）
                if original_cache_key:
                    return self.call_llm_with_cache(summarized_prompt, cache_key=original_cache_key)
                else:
                    return self.call_llm_with_cache(summarized_prompt)
            
            logger.info(f"[LLM调用] 代码总结完成: {len(prompt)} -> {len(summarized_prompt)} 字符")
            prompt = summarized_prompt
        
        # 3. 调用 LLM（使用 /api/chat 接口）
        try:
            logger.info(f"[LLM调用] Function Calling 使用模型 {self.llm_model}, prompt 长度: {len(prompt)} 字符, 工具数: {len(tools)}")
            
            url = f"{self.ollama_url}/api/chat"
            payload = {
                "model": self.llm_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "tools": tools,
                "tool_choice": tool_choice,
                "options": {
                    "temperature": 0.1,  # 降低温度以提高准确性
                    "top_p": 0.9,
                    "num_predict": 4000
                }
            }
            
            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            
            # 解析响应（可能是流式响应，多行 JSON）
            text = response.text
            result = None
            
            # 尝试解析完整 JSON
            try:
                result = response.json()
            except json.JSONDecodeError:
                # 流式响应：尝试解析每一行，找到包含 tool_calls 的行
                lines = text.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        line_result = json.loads(line)
                        # 检查是否包含 tool_calls
                        if line_result.get('message', {}).get('tool_calls'):
                            result = line_result
                            break
                        # 或者检查是否包含完整的 message 结构
                        if 'message' in line_result:
                            result = line_result
                    except json.JSONDecodeError:
                        continue
                
                # 如果还是没找到，尝试解析第一行
                if result is None and lines:
                    try:
                        result = json.loads(lines[0])
                    except:
                        pass
            
            if result is None:
                raise ValueError(f"无法解析响应，响应文本: {text[:500]}")
            
            # 3. 提取工具调用结果
            message = result.get('message', {})
            tool_calls = message.get('tool_calls', [])
            content = message.get('content', '') or ''
            
            # 调试：记录响应详情
            if not tool_calls:
                logger.debug(f"[LLM调用] Function Calling 响应中没有 tool_calls，content 长度: {len(content)}, content 前100字符: {content[:100]}")
            
            if not tool_calls:
                # 如果没有工具调用，检查是否是 XML 格式（qwen3-coder 可能使用）
                if content and ('<tool_call>' in content or '<function_calls>' in content):
                    logger.warning(f"[LLM调用] Function Calling 返回 XML 格式，尝试解析...")
                    parsed = self._parse_xml_tool_calls(content, tools)
                    if parsed:
                        # 缓存结果
                        self.memory_cache[cache_key] = parsed
                        if self.db:
                            self._save_db_cache(cache_key, json.dumps(parsed, ensure_ascii=False))
                        logger.info(f"[LLM调用] Function Calling 成功（XML格式），响应长度: {len(content)} 字符")
                        if return_cache_info:
                            return {"result": parsed, "cache_hit": False, "cache_type": None}
                        return parsed
                
                # 降级：尝试从 content 中解析 JSON（向后兼容）
                if content and len(content.strip()) > 10:  # 只有 content 有实际内容时才尝试解析
                    logger.warning(f"[LLM调用] Function Calling 未返回 tool_calls，尝试从 content 解析...")
                    try:
                        parsed = self.parse_json_response(content)
                        if parsed:
                            self.memory_cache[cache_key] = parsed
                            if self.db:
                                self._save_db_cache(cache_key, json.dumps(parsed, ensure_ascii=False))
                            logger.info(f"[LLM调用] Function Calling 降级到 JSON 解析成功")
                            if return_cache_info:
                                return {"result": parsed, "cache_hit": False, "cache_type": None}
                            return parsed
                    except Exception as parse_error:
                        logger.debug(f"[LLM调用] 从 content 解析 JSON 失败: {parse_error}, content: {content[:200]}")
                
                # 如果 content 为空或很短，可能是 LLM 没有理解任务
                raise ValueError(f"Function Calling 未返回工具调用，content: {content[:200] if content else '(空)'}")
            
            # 4. 解析工具调用（结构化，无需 JSON 解析）
            results = []
            for tool_call in tool_calls:
                function = tool_call.get('function', {})
                function_name = function.get('name')
                arguments = function.get('arguments', {})
                
                # arguments 可能是字符串（需要解析）或字典（直接使用）
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError as e:
                        logger.warning(f"[LLM调用] Function Calling 参数解析失败: {e}, 原始: {arguments[:200]}")
                        # 尝试修复常见问题
                        arguments = self._fix_json_string(arguments)
                        try:
                            arguments = json.loads(arguments)
                        except:
                            raise ValueError(f"无法解析工具参数: {arguments[:200]}")
                
                results.append({
                    'function': function_name,
                    'arguments': arguments
                })
            
            # 5. 返回结果（如果只有一个工具调用，直接返回参数；否则返回列表）
            final_result = results[0]['arguments'] if len(results) == 1 else results
            
            # 6. 缓存结果
            self.memory_cache[cache_key] = final_result
            if self.db:
                self._save_db_cache(cache_key, json.dumps(final_result, ensure_ascii=False))
            
            logger.info(f"[LLM调用] Function Calling 成功，工具调用数: {len(results)}, 响应长度: {len(content)} 字符")
            
            # 优化：如果请求缓存信息，返回包含缓存命中信息的字典
            if return_cache_info:
                return {"result": final_result, "cache_hit": False, "cache_type": None}
            return final_result
            
        except requests.Timeout:
            logger.error(f"[LLM调用] Function Calling 超时: {timeout}秒")
            raise
        except Exception as e:
            logger.error(f"[LLM调用] Function Calling 失败: {e}")
            raise
    
    def _parse_xml_tool_calls(self, content: str, tools: List[Dict]) -> Optional[Dict]:
        """
        解析 XML 格式的工具调用（qwen3-coder 可能使用）
        
        示例格式:
        <tool_call>
        <function_name>extract_api_endpoints</function_name>
        <arguments>
        {"endpoints": [...]}
        </arguments>
        </tool_call>
        """
        try:
            import xml.etree.ElementTree as ET
            
            # 尝试解析 XML
            root = ET.fromstring(f"<root>{content}</root>")
            
            # 查找 tool_call 或 function_calls
            tool_calls = root.findall('.//tool_call') or root.findall('.//function_calls')
            
            if not tool_calls:
                return None
            
            # 解析第一个工具调用
            tool_call = tool_calls[0]
            function_name_elem = tool_call.find('function_name') or tool_call.find('name')
            arguments_elem = tool_call.find('arguments') or tool_call.find('parameters')
            
            if function_name_elem is None or arguments_elem is None:
                return None
            
            function_name = function_name_elem.text.strip()
            arguments_text = arguments_elem.text.strip()
            
            # 解析 JSON 参数
            arguments = json.loads(arguments_text)
            
            return {
                'function': function_name,
                'arguments': arguments
            }['arguments']  # 返回参数部分
            
        except Exception as e:
            logger.debug(f"[LLM调用] XML 解析失败: {e}")
            return None
    
    def _summarize_code_for_function_calling(
        self, 
        prompt: str, 
        task_type: str, 
        max_length: int
    ) -> str:
        """
        总结代码内容，使其适合 Function Calling（< 10K 字符）
        
        Args:
            prompt: 原始 prompt（包含代码）
            task_type: 任务类型（"api_endpoints", "storage_systems", "general")
            max_length: 目标最大长度
            
        Returns:
            总结后的 prompt
        """
        # 提取 prompt 的固定部分（指令部分）
        # 假设 prompt 格式：指令 + 代码块
        import re
        
        # 尝试提取代码块
        code_block_pattern = r'```(?:python|javascript|typescript|java|go|rust|cpp|csharp|php|ruby|swift|kotlin|scala|html|css|json|yaml|xml|bash|sql|dockerfile)?\n(.*?)```'
        code_matches = re.findall(code_block_pattern, prompt, re.DOTALL)
        
        if not code_matches:
            # 如果没有代码块，可能是 JSON 数据或其他格式
            # 对于存储系统检测，prompt 包含 JSON 数据，需要特殊处理
            if task_type == "storage_systems":
                # 存储系统检测：限制 JSON 数据的大小
                return self._summarize_storage_prompt(prompt, max_length)
            else:
                # 其他情况：直接截断（保留开头部分）
                return prompt[:max_length]
        
        code_content = code_matches[0] if code_matches else ""
        code_language = re.search(r'```(\w+)', prompt)
        code_language = code_language.group(1) if code_language else "python"
        
        # 提取 prompt 的指令部分（代码块之前和之后）
        parts = re.split(code_block_pattern, prompt, flags=re.DOTALL)
        before_code = parts[0] if parts else ""
        after_code = parts[-1] if len(parts) > 1 else ""
        
        # 根据任务类型总结代码
        if task_type == "api_endpoints":
            # API 端点检测：提取路由相关的代码
            summarized_code = self._extract_api_related_code(code_content, max_length - len(before_code) - len(after_code) - 200)
        elif task_type == "storage_systems":
            # 存储系统检测：提取导入语句和配置
            summarized_code = self._extract_storage_related_code(code_content, max_length - len(before_code) - len(after_code) - 200)
        else:
            # 通用：提取关键部分（函数定义、类定义、导入语句）
            summarized_code = self._extract_key_code_parts(code_content, max_length - len(before_code) - len(after_code) - 200)
        
        # 重新组装 prompt
        summarized_prompt = f"{before_code}```{code_language}\n{summarized_code}\n```{after_code}"
        
        return summarized_prompt
    
    def _extract_api_related_code(self, code: str, max_length: int) -> str:
        """提取 API 路由相关的代码（装饰器、函数定义、路由配置）"""
        lines = code.split('\n')
        key_lines = []
        current_length = 0
        
        for line in lines:
            stripped = line.strip()
            
            # 保留路由装饰器
            if any(keyword in stripped for keyword in [
                '@app.', '@router.', '@route', 'app.get', 'app.post', 'app.put', 
                'app.delete', 'app.patch', 'router.get', 'router.post', 'router.put',
                'router.delete', 'router.patch', 'FastAPI', 'APIRouter', 'Blueprint',
                'app.route', 'flask.', 'django.urls', 'express.', 'koa.', 'hapi.'
            ]):
                if current_length + len(line) + 1 <= max_length:
                    key_lines.append(line)
                    current_length += len(line) + 1
                else:
                    break
            
            # 保留函数定义（可能在装饰器之后）
            elif stripped.startswith(('def ', 'async def ', 'function ', 'const ', 'export ')):
                if current_length + len(line) + 1 <= max_length:
                    key_lines.append(line)
                    current_length += len(line) + 1
                else:
                    break
            
            # 保留类定义（可能包含路由类）
            elif stripped.startswith(('class ', 'export class ')):
                if current_length + len(line) + 1 <= max_length:
                    key_lines.append(line)
                    current_length += len(line) + 1
                else:
                    break
        
        result = '\n'.join(key_lines)
        
        # 如果还是太长，截断
        if len(result) > max_length:
            result = result[:max_length]
            # 尝试在最后一个完整行处截断
            last_newline = result.rfind('\n')
            if last_newline > max_length * 0.8:  # 如果最后一行不太短
                result = result[:last_newline]
        
        return result or code[:max_length]  # 如果提取失败，返回截断的原始代码
    
    def _extract_storage_related_code(self, code: str, max_length: int) -> str:
        """提取存储系统相关的代码（导入语句、配置、初始化）"""
        lines = code.split('\n')
        key_lines = []
        current_length = 0
        
        # 存储相关的关键词
        storage_keywords = [
            'import ', 'from ', 'require(', 'import(',
            'mysql', 'postgres', 'redis', 'mongodb', 'elasticsearch',
            'sqlite', 'oracle', 'mssql', 'cassandra', 'dynamodb',
            's3', 'oss', 'minio', 'hdfs', 'kafka', 'rabbitmq',
            'database', 'db', 'cache', 'storage', 'connection',
            'pool', 'client', 'driver', 'adapter'
        ]
        
        for line in lines:
            stripped = line.strip().lower()
            
            # 保留导入语句
            if any(keyword in stripped for keyword in ['import ', 'from ', 'require(', 'import(']):
                if current_length + len(line) + 1 <= max_length:
                    key_lines.append(line)
                    current_length += len(line) + 1
                else:
                    break
            
            # 保留包含存储关键词的行
            elif any(keyword in stripped for keyword in storage_keywords):
                if current_length + len(line) + 1 <= max_length:
                    key_lines.append(line)
                    current_length += len(line) + 1
                else:
                    break
        
        result = '\n'.join(key_lines)
        
        # 如果还是太长，截断
        if len(result) > max_length:
            result = result[:max_length]
            last_newline = result.rfind('\n')
            if last_newline > max_length * 0.8:
                result = result[:last_newline]
        
        return result or code[:max_length]
    
    def _extract_key_code_parts(self, code: str, max_length: int) -> str:
        """提取代码的关键部分（函数定义、类定义、导入语句）"""
        lines = code.split('\n')
        key_lines = []
        current_length = 0
        
        for line in lines:
            stripped = line.strip()
            
            # 保留导入语句
            if any(stripped.startswith(prefix) for prefix in ['import ', 'from ', 'require(', 'import(']):
                if current_length + len(line) + 1 <= max_length:
                    key_lines.append(line)
                    current_length += len(line) + 1
                else:
                    break
            
            # 保留函数定义
            elif any(stripped.startswith(prefix) for prefix in ['def ', 'async def ', 'function ', 'const ', 'export ']):
                if current_length + len(line) + 1 <= max_length:
                    key_lines.append(line)
                    current_length += len(line) + 1
                else:
                    break
            
            # 保留类定义
            elif any(stripped.startswith(prefix) for prefix in ['class ', 'export class ']):
                if current_length + len(line) + 1 <= max_length:
                    key_lines.append(line)
                    current_length += len(line) + 1
                else:
                    break
        
        result = '\n'.join(key_lines)
        
        # 如果还是太长，截断
        if len(result) > max_length:
            result = result[:max_length]
            last_newline = result.rfind('\n')
            if last_newline > max_length * 0.8:
                result = result[:last_newline]
        
        return result or code[:max_length]
    
    def _summarize_storage_prompt(self, prompt: str, max_length: int) -> str:
        """
        总结存储系统检测的 prompt（包含 JSON 数据，不是代码）
        
        Args:
            prompt: 原始 prompt（包含依赖、配置、导入语句的 JSON）
            max_length: 目标最大长度
            
        Returns:
            总结后的 prompt
        """
        import json
        import re
        
        # 提取 JSON 数据部分
        # 查找 "依赖包:", "配置文件内容:", "关键导入语句:" 等部分
        
        # 尝试提取 JSON 块
        json_pattern = r'```json\s*\n(.*?)\n```'
        json_matches = re.findall(json_pattern, prompt, re.DOTALL)
        
        if json_matches:
            # 如果有 JSON 块，限制 JSON 数据的大小
            # 这里简化处理：直接截断 prompt
            return prompt[:max_length]
        
        # 查找 JSON 对象（不在代码块中）
        # 存储系统检测的 prompt 格式：
        # 依赖包:\n{json}\n配置文件内容:\n{json}\n关键导入语句:\n{json}
        
        # 尝试找到 JSON 对象
        json_obj_pattern = r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'
        json_objs = re.findall(json_obj_pattern, prompt, re.DOTALL)
        
        if json_objs:
            # 限制每个 JSON 对象的大小
            summarized_parts = []
            current_length = len(prompt) - sum(len(obj) for obj in json_objs)
            
            for obj in json_objs:
                try:
                    parsed = json.loads(obj)
                    # 如果是列表，限制数量
                    if isinstance(parsed, list):
                        # 限制列表长度
                        max_items = (max_length - current_length) // (len(json_objs) * 100)  # 估算每个项目 100 字符
                        if max_items > 0:
                            summarized = json.dumps(parsed[:max_items], ensure_ascii=False, indent=2)
                            summarized_parts.append(summarized)
                            current_length += len(summarized)
                        else:
                            summarized_parts.append("[]")
                    else:
                        # 如果是字典，直接使用（通常不会太大）
                        summarized_parts.append(obj)
                        current_length += len(obj)
                except:
                    # 如果解析失败，直接使用
                    summarized_parts.append(obj)
                    current_length += len(obj)
            
            # 重新组装（这里简化处理，实际需要更复杂的逻辑）
            # 暂时直接截断
            return prompt[:max_length]
        
        # 如果都没找到，直接截断
        return prompt[:max_length]
    
    def _fix_json_string(self, json_str: str) -> str:
        """修复常见的 JSON 字符串问题"""
        # 移除尾随逗号
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        # 修复单引号
        json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
        return json_str
