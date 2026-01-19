"""
文件级 ReAct Agent
专门用于处理单个大文件的 API 端点或存储系统提取
"""

import os
import json
import hashlib
import time
from typing import Dict, List, Optional, Any
from app.core.logging import logger
from app.services.code_file_react_tools import FileLevelReActTools
from app.services.llm_enhancement_service import LLMEnhancementService
from app.services.llm_tools_definitions import API_ENDPOINTS_TOOL, STORAGE_SYSTEMS_TOOL

# 优化参数（短期优化）
CONFIDENCE_THRESHOLD = 0.85  # 降低阈值（从 0.9 到 0.85）
CONFIDENCE_STOP_THRESHOLD = 0.75  # 置信度未提升的判断阈值（从 0.7 到 0.75）
MAX_CHARS_FOR_FUNCTION_CALLING = 8500  # Function Calling 字符数限制


class FileLevelReActAgent:
    """
    文件级 ReAct Agent
    
    用于处理单个大文件的详细分析，通过多轮迭代提高准确性
    """
    
    def __init__(
        self,
        repo_path: str,
        task_type: str = "api_endpoints",
        max_iterations: int = 3,
        llm_service: Optional[LLMEnhancementService] = None
    ):
        """
        初始化文件级 ReAct Agent
        
        Args:
            repo_path: 代码库根路径
            task_type: 任务类型 ("api_endpoints", "storage_systems")
            max_iterations: 最大迭代次数
            llm_service: LLM 服务实例（可选）
        """
        self.repo_path = repo_path
        self.task_type = task_type
        self.max_iterations = max_iterations
        self.llm_service = llm_service or LLMEnhancementService()
        self.file_tools = FileLevelReActTools(repo_path, self.llm_service)
        
        # Agent 状态
        self.iterations = 0
        self.current_sample = ""
        self.extracted_results = []
        self.confidence = 0.0
        self.observations = []
        self.actions_taken = []
        
        # 性能指标（中期优化）
        self.start_time = None
        self.llm_calls_count = 0
        self.cache_hits = 0
        self.previous_confidence = 0.0
    
    def analyze(self, file_path: str) -> Dict:
        """
        使用 ReAct 模式分析文件
        
        Args:
            file_path: 文件路径（相对于 repo_path）
            
        Returns:
            分析结果字典
        """
        # 记录开始时间（性能指标）
        self.start_time = time.time()
        self.llm_calls_count = 0
        self.cache_hits = 0
        self.previous_confidence = 0.0
        
        logger.info(f"[文件级 ReAct] ========== 开始分析文件 ==========")
        logger.info(f"[文件级 ReAct] 文件路径: {file_path}")
        logger.info(f"[文件级 ReAct] 任务类型: {self.task_type}")
        logger.info(f"[文件级 ReAct] 最大迭代次数: {self.max_iterations}")
        
        # 读取文件
        full_path = os.path.join(self.repo_path, file_path) if not os.path.isabs(file_path) else file_path
        if not os.path.exists(full_path):
            logger.error(f"[文件级 ReAct] ❌ 文件不存在: {full_path}")
            return {
                "success": False,
                "error": f"文件不存在: {full_path}",
                "extracted_results": [],
                "confidence": 0.0
            }
        
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            original_content = f.read()
        
        file_size = len(original_content)
        file_info = {
            "file_path": file_path,
            "file_size": file_size
        }
        
        logger.info(f"[文件级 ReAct] 文件大小: {file_size} 字符")
        
        # 如果文件不大，直接使用 Function Calling
        if file_size <= MAX_CHARS_FOR_FUNCTION_CALLING:
            logger.info(f"[文件级 ReAct] ✅ 文件大小 {file_size} 未超过限制 {MAX_CHARS_FOR_FUNCTION_CALLING}，直接使用 Function Calling")
            result = self._direct_function_calling(file_path, original_content, file_info)
            self._log_final_metrics(result)
            return result
        
        # 大文件：使用 ReAct 模式
        logger.info(f"[文件级 ReAct] ⚠️ 文件大小 {file_size} 超过限制 {MAX_CHARS_FOR_FUNCTION_CALLING}，使用 ReAct 模式分析")
        
        # Round 1: 初始采样
        logger.info(f"[文件级 ReAct] ========== Round 1: 初始采样 ==========")
        observation = self._observe_round1(file_path, file_size)
        self.observations.append(observation)
        logger.debug(f"[文件级 ReAct] Round 1 观察结果: {json.dumps(observation, ensure_ascii=False)}")
        
        action_result = self._act_smart_sample(file_path, observation)
        self.actions_taken.append(action_result)
        
        if not action_result.get("success"):
            logger.error(f"[文件级 ReAct] ❌ Round 1 采样失败: {action_result.get('error', '未知错误')}")
            result = {
                "success": False,
                "error": action_result.get("error", "采样失败"),
                "extracted_results": [],
                "confidence": 0.0
            }
            self._log_final_metrics(result)
            return result
        
        self.current_sample = action_result.get("sampled_content", "")
        sampled_size = action_result.get("sampled_size", 0)
        compression_ratio = action_result.get("compression_ratio", 0)
        logger.info(f"[文件级 ReAct] ✅ Round 1 采样完成: {file_size} -> {sampled_size} 字符 (压缩率: {compression_ratio:.2%})")
        
        # 使用采样后的内容进行第一次提取
        logger.info(f"[文件级 ReAct] Round 1: 开始 Function Calling 提取")
        first_result = self._extract_with_function_calling(file_path, self.current_sample, file_info)
        if first_result.get("success"):
            self.extracted_results = first_result.get("extracted_results", [])
            self.confidence = first_result.get("confidence", 0.7)
            self.previous_confidence = self.confidence
            logger.info(f"[文件级 ReAct] ✅ Round 1 提取完成: {len(self.extracted_results)} 个结果, 置信度: {self.confidence:.2f}")
        else:
            logger.warning(f"[文件级 ReAct] ⚠️ Round 1 提取失败: {first_result.get('error', '未知错误')}")
            self.confidence = 0.5
            self.previous_confidence = 0.5
        
        # Round 2-N: 迭代优化
        while self.iterations < self.max_iterations - 1:
            self.iterations += 1
            current_round = self.iterations + 1
            
            logger.info(f"[文件级 ReAct] ========== Round {current_round}: 迭代优化 ==========")
            
            # 观察当前状态
            observation = self._observe_current_state(file_path, file_size)
            self.observations.append(observation)
            logger.debug(f"[文件级 ReAct] Round {current_round} 观察结果: {json.dumps(observation, ensure_ascii=False)}")
            
            # 判断是否需要继续迭代（短期优化：降低阈值从 0.9 到 0.85）
            if self.confidence >= CONFIDENCE_THRESHOLD:
                logger.info(f"[文件级 ReAct] ✅ 置信度 {self.confidence:.2f} >= {CONFIDENCE_THRESHOLD}，提前终止迭代")
                break
            
            # 验证结果
            logger.info(f"[文件级 ReAct] Round {current_round}: 开始验证结果")
            validation = self._validate_results(file_path, file_info)
            validation_confidence = validation.get("confidence", 0.0)
            validation_completeness = validation.get("completeness", 0.0)
            missing_patterns = validation.get("missing_patterns", [])
            suggestions = validation.get("suggestions", [])
            
            logger.info(f"[文件级 ReAct] Round {current_round} 验证结果: 置信度={validation_confidence:.2f}, 完整度={validation_completeness:.2f}, 遗漏模式={missing_patterns}, 建议={suggestions}")
            
            if validation.get("is_complete", False):
                logger.info(f"[文件级 ReAct] ✅ Round {current_round} 验证通过，停止迭代")
                break
            
            # 根据验证结果决定下一步行动
            # 如果需要补充采样
            if missing_patterns or "补充" in str(suggestions):
                logger.info(f"[文件级 ReAct] Round {current_round}: 需要补充采样，遗漏模式: {missing_patterns}")
                
                # 分析文件结构
                structure = self.file_tools.analyze_file_structure(file_path)
                if structure.get("success"):
                    # 决定补充哪些区域
                    target_areas = self._decide_supplement_areas(structure, missing_patterns)
                    logger.info(f"[文件级 ReAct] Round {current_round}: 决定补充区域: {target_areas}")
                    
                    if target_areas:
                        # 补充采样（短期优化：动态计算补充长度）
                        remaining_length = MAX_CHARS_FOR_FUNCTION_CALLING - len(self.current_sample)
                        max_additional_length = min(remaining_length, 2000)  # 动态计算，不超过剩余空间
                        logger.info(f"[文件级 ReAct] Round {current_round}: 动态计算补充长度: {max_additional_length} 字符 (剩余空间: {remaining_length})")
                        
                        supplement_result = self._act_supplement_sample(
                            file_path, self.current_sample, target_areas, max_additional_length
                        )
                        self.actions_taken.append(supplement_result)
                        
                        if supplement_result.get("success"):
                            self.current_sample = supplement_result.get("supplemented_content", self.current_sample)
                            added_size = supplement_result.get("added_size", 0)
                            logger.info(f"[文件级 ReAct] ✅ Round {current_round} 补充采样完成: +{added_size} 字符, 当前采样大小: {len(self.current_sample)}")
                            
                            # 使用补充后的内容再次提取
                            logger.info(f"[文件级 ReAct] Round {current_round}: 开始 Function Calling 提取（补充后）")
                            new_result = self._extract_with_function_calling(
                                file_path, self.current_sample, file_info
                            )
                            if new_result.get("success"):
                                new_results = new_result.get("extracted_results", [])
                                new_confidence = new_result.get("confidence", 0.7)
                                old_count = len(self.extracted_results)
                                
                                # 合并结果
                                self._merge_results(new_results)
                                new_count = len(self.extracted_results)
                                added_count = new_count - old_count
                                
                                self.confidence = max(self.confidence, new_confidence)
                                logger.info(f"[文件级 ReAct] ✅ Round {current_round} 提取完成: 新增 {added_count} 个结果, 总计 {new_count} 个, 置信度: {self.confidence:.2f} -> {new_confidence:.2f}")
                            else:
                                logger.warning(f"[文件级 ReAct] ⚠️ Round {current_round} 提取失败: {new_result.get('error', '未知错误')}")
                        else:
                            logger.warning(f"[文件级 ReAct] ⚠️ Round {current_round} 补充采样失败: {supplement_result.get('error', '未知错误')}")
                else:
                    logger.warning(f"[文件级 ReAct] ⚠️ Round {current_round} 文件结构分析失败: {structure.get('error', '未知错误')}")
            
            # 如果置信度没有提升，停止迭代（短期优化：更精确的判断，从 0.7 到 0.75）
            confidence_delta = self.confidence - self.previous_confidence
            if self.iterations >= 2 and self.confidence <= CONFIDENCE_STOP_THRESHOLD:
                logger.info(f"[文件级 ReAct] ⚠️ Round {current_round} 置信度 {self.confidence:.2f} <= {CONFIDENCE_STOP_THRESHOLD} 且未提升 (Δ={confidence_delta:.2f})，停止迭代")
                break
            
            # 记录置信度变化
            if confidence_delta <= 0.01:  # 置信度提升很小
                logger.info(f"[文件级 ReAct] Round {current_round} 置信度提升很小 (Δ={confidence_delta:.2f})，可能接近最优")
            
            self.previous_confidence = self.confidence
        
        # 记录最终指标
        total_time = time.time() - self.start_time if self.start_time else 0
        logger.info(f"[文件级 ReAct] ========== 分析完成 ==========")
        logger.info(f"[文件级 ReAct] 总迭代次数: {self.iterations + 1}")
        logger.info(f"[文件级 ReAct] 提取结果数: {len(self.extracted_results)}")
        logger.info(f"[文件级 ReAct] 最终置信度: {self.confidence:.2f}")
        logger.info(f"[文件级 ReAct] LLM 调用次数: {self.llm_calls_count}")
        logger.info(f"[文件级 ReAct] 缓存命中次数: {self.cache_hits}")
        logger.info(f"[文件级 ReAct] 总耗时: {total_time:.2f} 秒")
        
        result = {
            "success": True,
            "extracted_results": self.extracted_results,
            "confidence": self.confidence,
            "iterations": self.iterations + 1,
            "file_path": file_path,
            "observations": self.observations,
            "actions_taken": self.actions_taken,
            # 性能指标（中期优化）
            "metrics": {
                "total_time": time.time() - self.start_time if self.start_time else 0,
                "llm_calls": self.llm_calls_count,
                "cache_hits": self.cache_hits,
                "file_size": file_size
            }
        }
        self._log_final_metrics(result)
        return result
    
    def _log_final_metrics(self, result: Dict):
        """记录最终性能指标"""
        metrics = result.get("metrics", {})
        logger.info(f"[文件级 ReAct] ========== 性能指标 ==========")
        logger.info(f"[文件级 ReAct] 总耗时: {metrics.get('total_time', 0):.2f} 秒")
        logger.info(f"[文件级 ReAct] LLM 调用: {metrics.get('llm_calls', 0)} 次")
        logger.info(f"[文件级 ReAct] 缓存命中: {metrics.get('cache_hits', 0)} 次")
        logger.info(f"[文件级 ReAct] 文件大小: {metrics.get('file_size', 0)} 字符")
        if metrics.get('llm_calls', 0) > 0:
            avg_time_per_call = metrics.get('total_time', 0) / metrics.get('llm_calls', 1)
            logger.info(f"[文件级 ReAct] 平均每次 LLM 调用耗时: {avg_time_per_call:.2f} 秒")
        logger.info(f"[文件级 ReAct] =============================")
    
    def _observe_round1(self, file_path: str, file_size: int) -> Dict:
        """第一轮观察"""
        return {
            "round": 1,
            "file_path": file_path,
            "file_size": file_size,
            "needs_sampling": file_size > MAX_CHARS_FOR_FUNCTION_CALLING,
            "strategy": self.task_type
        }
    
    def _observe_current_state(self, file_path: str, file_size: int) -> Dict:
        """观察当前状态"""
        return {
            "round": self.iterations + 2,
            "file_path": file_path,
            "file_size": file_size,
            "current_sample_size": len(self.current_sample),
            "extracted_count": len(self.extracted_results),
            "confidence": self.confidence
        }
    
    def _act_smart_sample(self, file_path: str, observation: Dict) -> Dict:
        """行动：智能采样"""
        logger.info(f"[文件级 ReAct] Round {observation['round']}: 智能采样")
        return self.file_tools.smart_sample_file(
            file_path,
            strategy=self.task_type,
            max_length=MAX_CHARS_FOR_FUNCTION_CALLING
        )
    
    def _act_supplement_sample(self, file_path: str, current_sample: str, target_areas: List[str], max_additional_length: int = 2000) -> Dict:
        """行动：补充采样"""
        logger.info(f"[文件级 ReAct] Round {self.iterations + 2}: 补充采样, 区域: {target_areas}, 最大补充长度: {max_additional_length}")
        return self.file_tools.supplement_file_sample(
            file_path,
            current_sample,
            target_areas,
            max_additional_length=max_additional_length
        )
    
    def _validate_results(self, file_path: str, file_info: Dict) -> Dict:
        """验证提取结果"""
        logger.info(f"[文件级 ReAct] 验证提取结果: {len(self.extracted_results)} 个结果")
        return self.file_tools.validate_extraction(
            self.extracted_results,
            file_info,
            self.task_type,
            self.current_sample if len(self.current_sample) < 10000 else None
        )
    
    def _extract_with_function_calling(self, file_path: str, content: str, file_info: Dict) -> Dict:
        """使用 Function Calling 提取结果"""
        try:
            self.llm_calls_count += 1
            content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
            content_size = len(content)
            
            logger.debug(f"[文件级 ReAct] Function Calling 调用 #{self.llm_calls_count}: 文件={file_path}, 内容大小={content_size} 字符, 哈希={content_hash[:8]}...")
            
            if self.task_type == "api_endpoints":
                prompt = f"""分析以下代码文件，识别所有 API 端点（HTTP 路由）。

文件路径: {file_path}
代码内容:
```python
{content}
```

请识别所有 HTTP 端点（GET、POST、PUT、DELETE、PATCH 等）。
支持 FastAPI、Flask、Django、Gradio、Streamlit、Tornado、Sanic 等框架。
如果文件不是路由文件，返回空数组。"""
                
                # 中期优化：缓存中间结果（考虑迭代轮次）
                cache_key = f"api_endpoints_react:{file_path}:{content_hash}:iter{self.iterations}"
                logger.debug(f"[文件级 ReAct] 缓存键: {cache_key}")
                
                call_start = time.time()
                # 优化：使用 return_cache_info=True 获取准确的缓存命中信息
                llm_response = self.llm_service.call_llm_with_function_calling(
                    prompt=prompt,
                    tools=[API_ENDPOINTS_TOOL],
                    cache_key=cache_key,
                    task_type="api_endpoints",
                    return_cache_info=True  # 新增：返回缓存命中信息
                )
                call_time = time.time() - call_start
                
                # 优化：从响应中提取缓存命中信息和结果
                if isinstance(llm_response, dict) and "result" in llm_response:
                    cache_hit = llm_response.get("cache_hit", False)
                    cache_type = llm_response.get("cache_type", None)
                    result_dict = llm_response["result"]
                else:
                    # 向后兼容：如果返回的是旧格式，假设未命中缓存
                    cache_hit = False
                    cache_type = None
                    result_dict = llm_response
                
                # 优化：准确记录缓存命中
                if cache_hit:
                    self.cache_hits += 1
                    logger.debug(f"[文件级 ReAct] ✅ 缓存命中 ({cache_type}): 响应时间 {call_time:.3f} 秒")
                else:
                    logger.debug(f"[文件级 ReAct] ❌ 缓存未命中: 响应时间 {call_time:.3f} 秒")
                
                endpoints = result_dict.get("endpoints", [])
                
                logger.debug(f"[文件级 ReAct] Function Calling 完成: 提取 {len(endpoints)} 个端点, 耗时 {call_time:.2f} 秒")
                
                return {
                    "success": True,
                    "extracted_results": endpoints,
                    "confidence": 0.8 if endpoints else 0.5
                }
            
            elif self.task_type == "storage_systems":
                # 存储系统检测的逻辑不同，这里简化处理
                # 实际应该在 detect_storage_systems_with_llm 中处理
                return {
                    "success": False,
                    "error": "存储系统检测不支持文件级 ReAct（应在代码库级别处理）"
                }
            
            else:
                return {
                    "success": False,
                    "error": f"未知任务类型: {self.task_type}"
                }
                
        except Exception as e:
            logger.error(f"[文件级 ReAct] ❌ Function Calling 失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "extracted_results": [],
                "confidence": 0.0
            }
    
    def _direct_function_calling(self, file_path: str, content: str, file_info: Dict) -> Dict:
        """直接使用 Function Calling（文件不大时）"""
        return self._extract_with_function_calling(file_path, content, file_info)
    
    def _decide_supplement_areas(self, structure: Dict, missing_patterns: List[str]) -> List[str]:
        """根据文件结构和遗漏模式，决定补充哪些区域"""
        target_areas = []
        
        # 检查是否有路由区域未覆盖
        routing_sections = structure.get("routing_sections", [])
        if routing_sections and any("路由" in p or "routing" in p.lower() for p in missing_patterns):
            target_areas.append("routing")
        
        # 检查是否需要文件末尾
        if any("末尾" in p or "end" in p.lower() for p in missing_patterns):
            target_areas.append("end")
        
        # 检查是否需要文件中间
        if any("中间" in p or "middle" in p.lower() for p in missing_patterns):
            target_areas.append("middle")
        
        # 如果没有特定建议，默认补充末尾和路由区域
        if not target_areas:
            if routing_sections:
                target_areas.append("routing")
            target_areas.append("end")
        
        return target_areas[:2]  # 最多补充 2 个区域
    
    def _merge_results(self, new_results: List[Dict]):
        """合并新的提取结果"""
        old_count = len(self.extracted_results)
        
        if self.task_type == "api_endpoints":
            # 去重：基于 (method, path)
            existing_keys = {(r.get("method"), r.get("path")) for r in self.extracted_results}
            for result in new_results:
                key = (result.get("method"), result.get("path"))
                if key not in existing_keys:
                    self.extracted_results.append(result)
                    existing_keys.add(key)
        else:
            # 其他任务类型的合并逻辑
            existing_names = {r.get("name") for r in self.extracted_results}
            for result in new_results:
                name = result.get("name")
                if name and name not in existing_names:
                    self.extracted_results.append(result)
                    existing_names.add(name)
        
        new_count = len(self.extracted_results)
        added_count = new_count - old_count
        if added_count > 0:
            logger.debug(f"[文件级 ReAct] 结果合并: 新增 {added_count} 个结果, 总计 {new_count} 个")
