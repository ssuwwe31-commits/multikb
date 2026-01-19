"""
文件级 ReAct 工具集
用于处理大文件的智能采样、结构分析和结果验证
"""

import os
import json
import re
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.core.logging import logger
from app.services.llm_enhancement_service import LLMEnhancementService


class FileLevelReActTools:
    """
    文件级 ReAct 工具集
    
    提供以下工具：
    1. smart_sample_file - 智能采样单个文件
    2. analyze_file_structure - 分析文件结构
    3. supplement_file_sample - 补充文件采样
    4. validate_extraction - 验证提取结果
    """
    
    def __init__(self, repo_path: str, llm_service: Optional[LLMEnhancementService] = None):
        """
        初始化文件级工具
        
        Args:
            repo_path: 代码库根路径
            llm_service: LLM 服务实例（可选）
        """
        self.repo_path = repo_path
        self.llm_service = llm_service or LLMEnhancementService()
    
    def smart_sample_file(
        self, 
        file_path: str, 
        strategy: str = "api_endpoints",
        max_length: int = 8500
    ) -> Dict:
        """
        工具：智能采样单个文件
        
        Args:
            file_path: 文件路径（相对于 repo_path）
            strategy: 采样策略 ("api_endpoints", "storage_systems", "general")
            max_length: 目标最大长度（字符数）
            
        Returns:
            采样结果字典
        """
        logger.info(f"[文件级工具] smart_sample_file: file={file_path}, strategy={strategy}, max_length={max_length}")
        
        try:
            # 构建完整文件路径
            full_path = os.path.join(self.repo_path, file_path) if not os.path.isabs(file_path) else file_path
            
            if not os.path.exists(full_path):
                return {
                    "success": False,
                    "error": f"文件不存在: {full_path}",
                    "file_path": file_path
                }
            
            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            original_size = len(content)
            
            # 根据策略进行智能采样
            if strategy == "api_endpoints":
                sampled_content = self.llm_service._extract_api_related_code(content, max_length)
            elif strategy == "storage_systems":
                sampled_content = self.llm_service._extract_storage_related_code(content, max_length)
            else:
                sampled_content = self.llm_service._extract_key_code_parts(content, max_length)
            
            sampled_size = len(sampled_content)
            compression_ratio = sampled_size / original_size if original_size > 0 else 0
            
            logger.info(f"[文件级工具] smart_sample_file 完成: {original_size} -> {sampled_size} 字符 (压缩率: {compression_ratio:.2%})")
            
            return {
                "success": True,
                "file_path": file_path,
                "original_size": original_size,
                "sampled_size": sampled_size,
                "compression_ratio": compression_ratio,
                "sampled_content": sampled_content,
                "strategy": strategy
            }
            
        except Exception as e:
            logger.error(f"[文件级工具] smart_sample_file 失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    def analyze_file_structure(self, file_path: str) -> Dict:
        """
        工具：分析文件结构，识别关键区域
        
        Args:
            file_path: 文件路径（相对于 repo_path）
            
        Returns:
            文件结构分析结果
        """
        logger.info(f"[文件级工具] analyze_file_structure: file={file_path}")
        
        try:
            # 构建完整文件路径
            full_path = os.path.join(self.repo_path, file_path) if not os.path.isabs(file_path) else file_path
            
            if not os.path.exists(full_path):
                return {
                    "success": False,
                    "error": f"文件不存在: {full_path}",
                    "file_path": file_path
                }
            
            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            
            # 识别路由定义区域
            routing_sections = self._find_routing_sections(lines)
            
            # 识别导入区域
            import_sections = self._find_import_sections(lines)
            
            # 识别配置区域
            config_sections = self._find_config_sections(lines)
            
            # 识别关键代码区域
            key_areas = self._identify_key_areas(lines)
            
            logger.info(f"[文件级工具] analyze_file_structure 完成: 路由区域={len(routing_sections)}, 导入区域={len(import_sections)}")
            
            return {
                "success": True,
                "file_path": file_path,
                "total_lines": total_lines,
                "routing_sections": routing_sections,
                "import_sections": import_sections,
                "config_sections": config_sections,
                "key_areas": key_areas
            }
            
        except Exception as e:
            logger.error(f"[文件级工具] analyze_file_structure 失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    def supplement_file_sample(
        self,
        file_path: str,
        current_sample: str,
        target_areas: List[str],
        max_additional_length: int = 2000
    ) -> Dict:
        """
        工具：补充文件采样
        
        Args:
            file_path: 文件路径
            current_sample: 当前采样内容
            target_areas: 需要补充的区域列表 (["beginning", "middle", "end", "routing", "imports"])
            max_additional_length: 最大额外长度
            
        Returns:
            补充后的采样结果
        """
        logger.info(f"[文件级工具] supplement_file_sample: file={file_path}, areas={target_areas}")
        
        try:
            # 构建完整文件路径
            full_path = os.path.join(self.repo_path, file_path) if not os.path.isabs(file_path) else file_path
            
            if not os.path.exists(full_path):
                return {
                    "success": False,
                    "error": f"文件不存在: {full_path}",
                    "file_path": file_path
                }
            
            # 读取完整文件内容
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                full_content = f.read()
            
            lines = full_content.split('\n')
            total_lines = len(lines)
            
            # 分析文件结构
            structure = self.analyze_file_structure(file_path)
            if not structure.get("success"):
                return structure
            
            # 收集需要补充的内容
            additional_content = []
            current_length = len(current_sample)
            
            for area in target_areas:
                if current_length >= max_additional_length:
                    break
                
                if area == "beginning":
                    # 补充文件开头（前 100 行）
                    start_lines = lines[:100]
                    additional_content.append("// === 文件开头 ===\n" + "\n".join(start_lines))
                    current_length += len("\n".join(start_lines))
                
                elif area == "end":
                    # 补充文件末尾（后 100 行）
                    end_lines = lines[-100:]
                    additional_content.append("// === 文件末尾 ===\n" + "\n".join(end_lines))
                    current_length += len("\n".join(end_lines))
                
                elif area == "middle":
                    # 补充文件中间（中间 100 行）
                    middle_start = total_lines // 2 - 50
                    middle_end = total_lines // 2 + 50
                    middle_lines = lines[middle_start:middle_end]
                    additional_content.append("// === 文件中间 ===\n" + "\n".join(middle_lines))
                    current_length += len("\n".join(middle_lines))
                
                elif area == "routing":
                    # 补充路由定义区域
                    for section in structure.get("routing_sections", []):
                        start = section.get("start_line", 0) - 1
                        end = section.get("end_line", total_lines)
                        section_lines = lines[start:end]
                        additional_content.append(f"// === 路由区域 (行 {start+1}-{end}) ===\n" + "\n".join(section_lines))
                        current_length += len("\n".join(section_lines))
                        if current_length >= max_additional_length:
                            break
                
                elif area == "imports":
                    # 补充导入区域
                    for section in structure.get("import_sections", []):
                        start = section.get("start_line", 0) - 1
                        end = section.get("end_line", total_lines)
                        section_lines = lines[start:end]
                        additional_content.append(f"// === 导入区域 (行 {start+1}-{end}) ===\n" + "\n".join(section_lines))
                        current_length += len("\n".join(section_lines))
                        if current_length >= max_additional_length:
                            break
            
            # 合并内容
            supplemented_content = current_sample + "\n\n" + "\n\n".join(additional_content)
            
            # 如果超过限制，截断
            if len(supplemented_content) > len(current_sample) + max_additional_length:
                supplemented_content = current_sample + "\n\n" + "\n\n".join(additional_content)[:max_additional_length]
            
            added_size = len(supplemented_content) - len(current_sample)
            
            logger.info(f"[文件级工具] supplement_file_sample 完成: +{added_size} 字符")
            
            return {
                "success": True,
                "file_path": file_path,
                "original_sample_size": len(current_sample),
                "supplemented_size": len(supplemented_content),
                "added_size": added_size,
                "supplemented_content": supplemented_content,
                "target_areas": target_areas
            }
            
        except Exception as e:
            logger.error(f"[文件级工具] supplement_file_sample 失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    def validate_extraction(
        self,
        extracted_results: List[Dict],
        file_info: Dict,
        task_type: str,
        file_content: Optional[str] = None
    ) -> Dict:
        """
        工具：验证提取结果的完整性和准确性
        
        Args:
            extracted_results: 已提取的结果列表
            file_info: 文件信息（路径、大小等）
            task_type: 任务类型 ("api_endpoints", "storage_systems")
            file_content: 文件内容（可选，用于验证）
            
        Returns:
            验证结果
        """
        logger.info(f"[文件级工具] validate_extraction: task={task_type}, count={len(extracted_results)}")
        
        try:
            # 基础验证
            result_count = len(extracted_results)
            
            if result_count == 0:
                return {
                    "success": True,
                    "confidence": 0.0,
                    "completeness": 0.0,
                    "missing_patterns": ["未提取到任何结果"],
                    "suggestions": ["检查文件是否包含相关内容", "尝试不同的采样策略"],
                    "is_complete": False
                }
            
            # 使用 LLM 验证（如果提供了文件内容）
            if file_content and len(file_content) < 10000:  # 只对小内容进行 LLM 验证
                validation_prompt = f"""请验证以下提取结果的完整性和准确性：

任务类型: {task_type}
文件路径: {file_info.get('file_path', '')}
文件大小: {file_info.get('file_size', 0)} 字符

已提取结果:
{json.dumps(extracted_results, ensure_ascii=False, indent=2)}

文件内容（部分）:
{file_content[:5000]}

请评估：
1. 提取结果的置信度（0-1）
2. 完整度（0-1，是否遗漏了重要内容）
3. 可能遗漏的模式
4. 改进建议

返回 JSON 格式：
{{
  "confidence": 0.85,
  "completeness": 0.9,
  "missing_patterns": ["动态路由", "中间件路由"],
  "suggestions": ["检查文件末尾的路由定义", "查找动态路由模式"]
}}
"""
                
                try:
                    validation_result = self.llm_service.call_llm_with_cache(
                        prompt=validation_prompt,
                        cache_key=f"validate_{task_type}_{file_info.get('file_path', '')}"
                    )
                    
                    # 解析 LLM 响应
                    json_match = re.search(r'\{[^{}]*"confidence"[^{}]*\}', validation_result, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        return {
                            "success": True,
                            "confidence": parsed.get("confidence", 0.7),
                            "completeness": parsed.get("completeness", 0.7),
                            "missing_patterns": parsed.get("missing_patterns", []),
                            "suggestions": parsed.get("suggestions", []),
                            "is_complete": parsed.get("confidence", 0.7) >= 0.9
                        }
                except Exception as e:
                    logger.warning(f"[文件级工具] LLM 验证失败，使用基础验证: {e}")
            
            # 基础验证（不使用 LLM）
            # 短期优化：改进验证逻辑，增加更多启发式规则
            file_size = file_info.get("file_size", 0)
            
            # 基础置信度计算
            confidence = min(0.7 + (result_count * 0.05), 0.95)  # 结果越多，置信度越高
            completeness = min(0.6 + (result_count * 0.03), 0.9)
            
            missing_patterns = []
            suggestions = []
            
            # 启发式规则 1: 如果结果为空，强制继续迭代
            if result_count == 0:
                logger.warning(f"[文件级工具] 验证: 结果为空，建议继续迭代")
                missing_patterns.append("未提取到任何结果")
                suggestions.append("检查文件是否包含相关内容，尝试不同的采样策略")
                confidence = 0.0
                completeness = 0.0
            
            # 启发式规则 2: 大文件但结果少，可能遗漏
            elif result_count < 3 and file_size > 20000:
                logger.warning(f"[文件级工具] 验证: 大文件 ({file_size} 字符) 但结果少 ({result_count} 个)，可能遗漏")
                missing_patterns.append("大文件但提取结果较少，可能遗漏了内容")
                suggestions.append("尝试补充采样文件的其他区域（末尾、中间、路由区域）")
                confidence = max(0.3, confidence - 0.2)  # 降低置信度
                completeness = max(0.3, completeness - 0.2)
            
            # 启发式规则 3: 结果数量适中但文件很大
            elif result_count >= 3 and result_count < 10 and file_size > 30000:
                logger.info(f"[文件级工具] 验证: 大文件 ({file_size} 字符) 结果适中 ({result_count} 个)，可能还有遗漏")
                missing_patterns.append("文件较大，可能还有未覆盖的区域")
                suggestions.append("考虑补充采样文件末尾或中间区域")
                confidence = max(0.5, confidence - 0.1)
            
            # 启发式规则 4: 结果数量很少
            elif result_count < 3:
                logger.info(f"[文件级工具] 验证: 结果较少 ({result_count} 个)，可能遗漏")
                missing_patterns.append("提取结果较少，可能遗漏了内容")
                suggestions.append("尝试补充采样文件的其他区域")
            
            return {
                "success": True,
                "confidence": confidence,
                "completeness": completeness,
                "missing_patterns": missing_patterns,
                "suggestions": suggestions,
                "is_complete": confidence >= 0.9
            }
            
        except Exception as e:
            logger.error(f"[文件级工具] validate_extraction 失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "confidence": 0.5,
                "completeness": 0.5,
                "is_complete": False
            }
    
    # ============================================
    # 辅助方法
    # ============================================
    
    def _find_routing_sections(self, lines: List[str]) -> List[Dict]:
        """查找路由定义区域"""
        sections = []
        
        # 匹配常见的路由装饰器
        route_patterns = [
            r'@(?:app|router|route)\.(?:get|post|put|delete|patch|head|options)',
            r'@(?:app|router|route)\.route',
            r'@(?:app|router|route)\.(?:api_route|add_url_rule)',
            r'@(?:FastAPI|APIRouter)',
            r'@(?:flask|Flask)\.route',
        ]
        
        for i, line in enumerate(lines):
            for pattern in route_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # 查找函数定义（通常在装饰器后）
                    func_start = i
                    func_end = i + 20  # 假设函数在 20 行内
                    
                    # 查找函数结束（简单策略）
                    for j in range(i + 1, min(i + 50, len(lines))):
                        if lines[j].strip() and not lines[j].startswith(' ') and not lines[j].startswith('\t'):
                            if not lines[j].strip().startswith('@'):  # 不是另一个装饰器
                                func_end = j
                                break
                    
                    sections.append({
                        "start_line": func_start + 1,
                        "end_line": func_end,
                        "type": "routing",
                        "pattern": pattern
                    })
                    break
        
        return sections
    
    def _find_import_sections(self, lines: List[str]) -> List[Dict]:
        """查找导入区域"""
        sections = []
        import_start = None
        
        for i, line in enumerate(lines[:100]):  # 通常导入在前 100 行
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')):
                if import_start is None:
                    import_start = i
            elif import_start is not None and stripped and not stripped.startswith('#'):
                # 导入区域结束
                sections.append({
                    "start_line": import_start + 1,
                    "end_line": i,
                    "type": "imports"
                })
                import_start = None
        
        # 如果文件末尾还有导入
        if import_start is not None:
            sections.append({
                "start_line": import_start + 1,
                "end_line": min(100, len(lines)),
                "type": "imports"
            })
        
        return sections
    
    def _find_config_sections(self, lines: List[str]) -> List[Dict]:
        """查找配置区域"""
        sections = []
        
        # 匹配常见的配置模式
        config_patterns = [
            r'^(?:DATABASE|DB|REDIS|CACHE|CONFIG|SETTINGS)',
            r'^[A-Z_]+ = ',
            r'class.*Config',
            r'@dataclass.*Config',
        ]
        
        for i, line in enumerate(lines):
            for pattern in config_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    sections.append({
                        "start_line": i + 1,
                        "end_line": i + 10,  # 配置通常较短
                        "type": "config",
                        "pattern": pattern
                    })
                    break
        
        return sections
    
    def _identify_key_areas(self, lines: List[str]) -> List[Dict]:
        """识别关键代码区域"""
        key_areas = []
        
        # 识别类定义
        for i, line in enumerate(lines):
            if re.match(r'^class\s+\w+', line.strip()):
                key_areas.append({
                    "type": "class_definition",
                    "line": i + 1,
                    "content": line.strip()[:100]
                })
            
            # 识别函数定义
            elif re.match(r'^(?:def|async def|function|const)\s+\w+', line.strip()):
                key_areas.append({
                    "type": "function_definition",
                    "line": i + 1,
                    "content": line.strip()[:100]
                })
        
        return key_areas[:20]  # 只返回前 20 个关键区域
