"""
Question Classifier Service
问题分类器服务 - 混合策略（关键词匹配 + LLM 分类）
"""

import hashlib
from typing import Dict, Any, Optional
import requests
from app.core.logging import logger
from app.config.settings import settings


class QuestionClassifier:
    """问题分类器（混合策略）"""
    
    # 高置信度关键词（快速路径）
    HIGH_CONFIDENCE_KEYWORDS = {
        "call_chain": ["调用链", "调用路径", "call chain", "call path", "调用关系", "被哪些地方调用"],
        "diagram": ["绘制", "生成", "逻辑图", "架构图", "流程图", "diagram", "chart", "图表"],
        "architecture": ["系统架构", "架构设计", "architecture", "系统结构", "模块关系"],
        "understanding": ["这个函数", "这个类", "这段代码", "做什么", "是什么", "如何工作"],
        "best_practice": ["有什么问题", "如何优化", "改进建议", "最佳实践", "代码质量"],
    }
    
    # 低置信度关键词（需要 LLM 确认）
    LOW_CONFIDENCE_KEYWORDS = {
        "call_chain": ["调用", "call", "invoke", "被调用", "调用者"],
        "architecture": ["架构", "结构", "模块", "设计", "组织"],
        "understanding": ["什么", "如何", "为什么", "what", "how", "why", "解释"],
        "best_practice": ["问题", "优化", "建议", "issue", "optimize", "改进"],
    }
    
    def __init__(self):
        self.cache = {}
        self.ollama_url = settings.OLLAMA_BASE_URL or "http://localhost:11434"
        self.llm_model = settings.CODE_LLM_MODEL or "qwen2.5-coder:7b"
        logger.info(f"问题分类器初始化完成，LLM模型: {self.llm_model}")
    
    def classify(self, question: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        分类问题（同步方法，内部可能调用异步）
        
        Args:
            question: 用户问题
            use_cache: 是否使用缓存
            
        Returns:
            分类结果：
            {
                'category': 'call_chain',
                'method': 'keyword_high_confidence',
                'confidence': 0.9
            }
        """
        if not question or not question.strip():
            return {
                'category': 'general',
                'method': 'empty',
                'confidence': 0.0
            }
        
        question = question.strip()
        
        # 1. 检查缓存
        if use_cache:
            question_hash = hashlib.md5(question.encode()).hexdigest()
            if question_hash in self.cache:
                result = self.cache[question_hash].copy()
                result['method'] = 'cached'
                logger.debug(f"问题分类（缓存）: {question[:50]} -> {result['category']}")
                return result
        
        # 2. 高置信度关键词匹配（快速路径）
        high_conf_result = self._keyword_match(question, self.HIGH_CONFIDENCE_KEYWORDS)
        if high_conf_result['confidence'] > 0.9:
            result = {
                'category': high_conf_result['category'],
                'method': 'keyword_high_confidence',
                'confidence': high_conf_result['confidence']
            }
            if use_cache:
                self.cache[question_hash] = result
            logger.debug(f"问题分类（高置信度关键词）: {question[:50]} -> {result['category']}")
            return result
        
        # 3. 低置信度关键词匹配（中等路径）
        low_conf_result = self._keyword_match(question, self.LOW_CONFIDENCE_KEYWORDS)
        if low_conf_result['confidence'] > 0.6:
            # 使用 LLM 确认（轻量级）
            try:
                llm_confirmed = self._llm_confirm(question, low_conf_result['category'])
                if llm_confirmed:
                    result = {
                        'category': low_conf_result['category'],
                        'method': 'keyword_llm_confirmed',
                        'confidence': 0.8
                    }
                    if use_cache:
                        self.cache[question_hash] = result
                    logger.debug(f"问题分类（LLM确认）: {question[:50]} -> {result['category']}")
                    return result
            except Exception as e:
                logger.warning(f"LLM 确认失败，降级到关键词匹配: {e}")
                # 降级：使用低置信度结果
                result = {
                    'category': low_conf_result['category'],
                    'method': 'keyword_fallback',
                    'confidence': 0.6
                }
                logger.debug(f"问题分类（降级）: {question[:50]} -> {result['category']}")
                return result
        
        # 4. LLM 完整分类（慢速路径）
        try:
            llm_result = self._llm_classify(question)
            result = {
                'category': llm_result['category'],
                'method': 'llm',
                'confidence': llm_result.get('confidence', 0.7)
            }
            # 只缓存高置信度的 LLM 结果
            if use_cache and result['confidence'] > 0.8:
                question_hash = hashlib.md5(question.encode()).hexdigest()
                self.cache[question_hash] = result
            logger.debug(f"问题分类（LLM）: {question[:50]} -> {result['category']}")
            return result
        except Exception as e:
            logger.error(f"LLM 分类失败: {e}")
            # 降级：返回 general
            result = {
                'category': 'general',
                'method': 'fallback',
                'confidence': 0.5
            }
            logger.debug(f"问题分类（失败降级）: {question[:50]} -> {result['category']}")
            return result
    
    def _keyword_match(self, question: str, keyword_map: Dict) -> Dict:
        """关键词匹配"""
        question_lower = question.lower()
        matches = {}
        
        for category, keywords in keyword_map.items():
            count = sum(1 for keyword in keywords if keyword in question_lower)
            if count > 0:
                matches[category] = count
        
        if not matches:
            return {'category': 'general', 'confidence': 0.0}
        
        # 选择匹配最多的类别
        best_category = max(matches.items(), key=lambda x: x[1])[0]
        # 置信度计算：基础 0.5 + 匹配数 * 0.1，最高 0.9
        confidence = min(0.9, 0.5 + matches[best_category] * 0.1)
        
        return {'category': best_category, 'confidence': confidence}
    
    def _llm_confirm(self, question: str, suggested_category: str) -> bool:
        """LLM 确认分类（轻量级）"""
        prompt = f"""问题：{question}
建议分类：{suggested_category}

这个分类是否合理？只回答 yes 或 no。"""
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # 低温度，更确定
                        "num_predict": 10     # 只需要 yes/no
                    }
                },
                timeout=5  # 5秒超时
            )
            response.raise_for_status()
            result = response.json()
            answer = result.get("response", "").strip().lower()
            return answer.startswith('yes')
        except Exception as e:
            logger.warning(f"LLM 确认失败: {e}")
            return False
    
    def _llm_classify(self, question: str) -> Dict:
        """LLM 完整分类"""
        prompt = f"""你是一个问题分类器。请判断以下问题属于哪个类别：

类别列表：
1. call_chain - 调用逻辑问题（如：调用链、调用路径、谁调用了谁、被哪些地方调用）
2. architecture - 架构问题（如：系统架构、模块关系、设计结构）
3. diagram - 图表生成问题（如：绘制逻辑图、生成架构图、流程图）
4. understanding - 代码理解问题（如：这个函数做什么、如何工作、是什么）
5. best_practice - 最佳实践问题（如：有什么问题、如何优化、改进建议）
6. general - 其他问题

用户问题：{question}

请只返回类别名称（如：call_chain），不要添加其他内容。"""
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # 较低温度，更准确
                        "num_predict": 20     # 只需要类别名
                    }
                },
                timeout=10  # 10秒超时
            )
            response.raise_for_status()
            result = response.json()
            category = result.get("response", "general").strip().lower()
            
            # 清理可能的 markdown 格式
            category = category.replace("```", "").replace("json", "").strip()
            
            # 验证类别是否有效
            valid_categories = ["call_chain", "architecture", "diagram", 
                              "understanding", "best_practice", "general"]
            if category not in valid_categories:
                logger.warning(f"LLM 返回无效类别: {category}，降级到 general")
                category = "general"
            
            return {
                'category': category,
                'confidence': 0.7  # LLM 分类默认置信度
            }
        except Exception as e:
            logger.error(f"LLM 分类失败: {e}")
            raise
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("问题分类器缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            'cache_size': len(self.cache),
            'cache_keys': list(self.cache.keys())[:10]  # 只返回前10个
        }


# 全局单例（可选）
_question_classifier_instance: Optional[QuestionClassifier] = None


def get_question_classifier() -> QuestionClassifier:
    """获取问题分类器实例（单例模式）"""
    global _question_classifier_instance
    if _question_classifier_instance is None:
        _question_classifier_instance = QuestionClassifier()
    return _question_classifier_instance
