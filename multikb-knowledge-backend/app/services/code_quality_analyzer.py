"""
代码质量分析模块
负责检测代码异味、生成重构建议、测试建议等
"""

import os
import re
import json
from typing import Dict, List
from pathlib import Path

from app.core.logging import logger


class CodeQualityAnalyzer:
    """代码质量分析器"""
    
    def __init__(self, is_minified_file_func=None):
        """
        初始化代码质量分析器
        
        Args:
            is_minified_file_func: 判断是否为压缩文件的函数（可选）
        """
        self._is_minified_file = is_minified_file_func or (lambda x: False)
    
    def generate_code_quality_recommendations(
        self,
        analyzed_files: List[Dict],
        statistics: Dict
    ) -> Dict:
        """
        生成代码质量建议
        
        Args:
            analyzed_files: 已分析的文件列表
            statistics: 统计信息
            
        Returns:
            {
                "code_smells": [...],
                "refactoring_suggestions": [...],
                "test_suggestions": [...]
            }
        """
        logger.info("开始生成代码质量建议")
        
        # 1. 检测代码异味
        code_smells = self.detect_code_smells(analyzed_files)
        
        # 2. 使用 LLM 生成重构建议
        refactoring_suggestions = self.generate_refactoring_suggestions_llm(
            code_smells, analyzed_files
        )
        
        # 3. 生成测试建议
        test_suggestions = self.generate_test_suggestions(analyzed_files)
        
        return {
            "code_smells": code_smells,
            "refactoring_suggestions": refactoring_suggestions,
            "test_suggestions": test_suggestions
        }
    
    def detect_code_smells(self, analyzed_files: List[Dict]) -> List[Dict]:
        """检测代码异味"""
        smells = []
        
        for file_data in analyzed_files:
            file_path = file_data.get('file_path', '')
            symbols = file_data.get('symbols', [])
            complexity = file_data.get('complexity', {})
            
            # 检测长函数
            for symbol in symbols:
                if symbol.get('type') == 'function':
                    func_lines = symbol.get('end_line', 0) - symbol.get('line', 0)
                    if func_lines > 100:
                        smells.append({
                            "type": "长函数",
                            "severity": "中",
                            "file": file_path,
                            "symbol": symbol.get('name'),
                            "line": symbol.get('line'),
                            "description": f"函数 {symbol.get('name')} 超过 100 行，建议拆分"
                        })
            
            # 检测复杂类
            for symbol in symbols:
                if symbol.get('type') == 'class':
                    methods = symbol.get('methods', [])
                    if len(methods) > 20:
                        smells.append({
                            "type": "复杂类",
                            "severity": "中",
                            "file": file_path,
                            "symbol": symbol.get('name'),
                            "line": symbol.get('line'),
                            "description": f"类 {symbol.get('name')} 有 {len(methods)} 个方法，建议拆分"
                        })
            
            # 检测高复杂度
            cyclomatic = complexity.get('cyclomatic', 0)
            if cyclomatic > 20:
                most_complex_symbol = None
                most_complex_line = None
                max_symbol_complexity = 0
                max_symbol_lines = 0
                
                for symbol in symbols:
                    if symbol.get('type') in ['function', 'method']:
                        symbol_complexity = symbol.get('complexity_score', 0)
                        if symbol_complexity > 15 and symbol_complexity > max_symbol_complexity:
                            most_complex_symbol = symbol.get('name')
                            most_complex_line = symbol.get('line')
                            max_symbol_complexity = symbol_complexity
                
                if not most_complex_symbol:
                    for symbol in symbols:
                        if symbol.get('type') in ['function', 'method']:
                            start_line = symbol.get('line', 0)
                            end_line = symbol.get('end_line', start_line)
                            symbol_lines = max(1, end_line - start_line + 1)
                            if symbol_lines > max_symbol_lines:
                                most_complex_symbol = symbol.get('name')
                                most_complex_line = symbol.get('line')
                                max_symbol_lines = symbol_lines
                
                if not most_complex_symbol:
                    for symbol in symbols:
                        if symbol.get('type') in ['function', 'method']:
                            most_complex_symbol = symbol.get('name')
                            most_complex_line = symbol.get('line')
                            break
                
                is_minified = self._is_minified_file(file_path)
                symbol_display = most_complex_symbol
                description_suffix = ""
                
                if is_minified:
                    description_suffix = "（注意：此文件为压缩代码，符号名称可能无意义，建议查看源代码文件）"
                    if most_complex_symbol and len(most_complex_symbol) == 1:
                        symbol_display = None
                elif most_complex_symbol:
                    description_suffix = f"（最复杂符号: {most_complex_symbol}）"
                
                smells.append({
                    "type": "高复杂度",
                    "severity": "高" if cyclomatic > 30 else "中",
                    "file": file_path,
                    "symbol": symbol_display,
                    "line": most_complex_line,
                    "description": f"文件复杂度 {cyclomatic}，建议重构{description_suffix}"
                })
        
        return sorted(smells, key=lambda x: {'高': 3, '中': 2, '低': 1}.get(x.get('severity', '低'), 1), reverse=True)
    
    def generate_refactoring_suggestions_llm(
        self,
        code_smells: List[Dict],
        analyzed_files: List[Dict]
    ) -> List[Dict]:
        """使用 LLM 生成重构建议"""
        try:
            import requests
            from app.config.settings import settings
            
            context = f"""
## 检测到的代码异味
{json.dumps(code_smells[:10], ensure_ascii=False, indent=2)}

## 代码统计
总文件数: {len(analyzed_files)}
"""
            
            prompt = f"""基于以下代码质量分析结果，生成具体的重构建议：

{context}

请生成 3-5 条重构建议，每条建议包含：
1. suggestion: 重构建议内容
2. priority: 优先级（高/中/低）
3. affected_files: 受影响的文件列表（文件名）
4. steps: 重构步骤（简要说明）

返回 JSON 格式：
{{
  "suggestions": [
    {{
      "suggestion": "重构建议",
      "priority": "高",
      "affected_files": ["file1.py", "file2.py"],
      "steps": "步骤说明"
    }}
  ]
}}
"""
            
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.CODE_LLM_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("response", "").strip()
            
            try:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    suggestions_data = json.loads(json_match.group())
                    suggestions = suggestions_data.get('suggestions', [])
                    logger.info(f"LLM 生成重构建议成功，数量: {len(suggestions)}")
                    return suggestions
            except json.JSONDecodeError:
                logger.warning("LLM 返回的 JSON 格式不正确，使用默认建议")
            
            return [
                {
                    "suggestion": "拆分长函数，提高代码可读性",
                    "priority": "中",
                    "affected_files": [],
                    "steps": "识别长函数，提取子函数，保持单一职责"
                }
            ]
            
        except Exception as e:
            logger.error(f"LLM 生成重构建议失败: {e}")
            return []
    
    def generate_test_suggestions(self, analyzed_files: List[Dict]) -> List[Dict]:
        """生成测试建议"""
        suggestions = []
        
        # 检查测试文件覆盖率
        test_files = [f for f in analyzed_files if 'test' in f.get('file_path', '').lower()]
        test_ratio = len(test_files) / max(len(analyzed_files), 1)
        
        if test_ratio < 0.2:
            suggestions.append({
                "type": "测试覆盖率不足",
                "severity": "高",
                "description": f"测试文件占比 {test_ratio*100:.1f}%，建议提高测试覆盖率",
                "files": []
            })
        
        # 检查关键文件是否有测试
        key_files = [f for f in analyzed_files if any(kw in f.get('file_path', '').lower() for kw in ['service', 'api', 'controller'])]
        untested_key_files = []
        for key_file in key_files[:10]:
            file_name = Path(key_file.get('file_path', '')).stem
            has_test = any(file_name in tf.get('file_path', '') for tf in test_files)
            if not has_test:
                untested_key_files.append(key_file.get('file_path', ''))
        
        if untested_key_files:
            suggestions.append({
                "type": "关键文件缺少测试",
                "severity": "中",
                "description": f"发现 {len(untested_key_files)} 个关键文件缺少测试",
                "files": untested_key_files[:5]
            })
        
        return suggestions
