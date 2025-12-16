"""
Fallback Strategy Service
根据知识问答系统设计文档实现降级处理策略
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import numpy as np
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.config.settings import settings
from app.services.ollama_service import OllamaService
from app.core.exceptions import CustomException, ErrorCode

class FallbackStrategyService:
    """降级处理策略服务 - 根据设计文档实现"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ollama_service = OllamaService(db)
        
        # 相关性阈值 - 根据设计文档
        self.RELEVANCE_THRESHOLDS = {
            "high": settings.FALLBACK_HIGH_RELEVANCE_THRESHOLD,      # 高相关性
            "medium": settings.FALLBACK_MEDIUM_RELEVANCE_THRESHOLD,    # 中等相关性
            "low": settings.FALLBACK_LOW_RELEVANCE_THRESHOLD,       # 低相关性
            "none": 0.0       # 无相关性
        }
        
        # 降级策略定义 - 根据设计文档
        self.FALLBACK_STRATEGIES = {
            "knowledge_base_answer": {
                "name": "知识库回答",
                "condition": "high_relevance",
                "threshold": settings.FALLBACK_HIGH_RELEVANCE_THRESHOLD,
                "description": "基于知识库内容生成答案，提供详细引用和来源信息"
            },
            "llm_answer": {
                "name": "大模型回答",
                "condition": "medium_relevance", 
                "threshold": settings.FALLBACK_MEDIUM_RELEVANCE_THRESHOLD,
                "description": "结合知识库内容和LLM知识，补充知识库不足的信息"
            },
            "hybrid_answer": {
                "name": "混合回答",
                "condition": "low_relevance",
                "threshold": settings.FALLBACK_LOW_RELEVANCE_THRESHOLD,
                "description": "主要依赖LLM，少量参考知识库，提供一般性回答和建议"
            },
            "no_info_reply": {
                "name": "无信息回复",
                "condition": "no_relevance",
                "threshold": 0.0,
                "description": "直接回复'知识库中无相关信息'，明确告知用户无相关信息"
            }
        }
    
    async def evaluate_relevance_and_decide_strategy(
        self,
        search_results: List[Dict[str, Any]],
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        评估相关性并决定降级策略 - 根据设计文档实现
        
        Args:
            search_results: 检索结果列表
            question: 用户问题
            context: 上下文信息
            
        Returns:
            降级策略决策结果
        """
        try:
            logger.info(f"开始评估相关性并决定降级策略，检索结果数量: {len(search_results)}")
            
            # 1. 结果评估 - 根据设计文档
            evaluation_result = await self._evaluate_search_results(search_results, question)
            
            # 2. 相关性判断 - 根据设计文档
            relevance_assessment = self._assess_relevance(evaluation_result)
            
            # 3. 降级决策 - 根据设计文档
            strategy_decision = self._decide_fallback_strategy(relevance_assessment)
            
            # 4. 处理策略 - 根据设计文档
            processing_result = await self._execute_fallback_strategy(
                strategy_decision, search_results, question, context
            )
            
            result = {
                "strategy": strategy_decision["strategy_name"],
                "strategy_type": strategy_decision["strategy_type"],
                "relevance_score": relevance_assessment["overall_score"],
                "relevance_level": relevance_assessment["relevance_level"],
                "evaluation_details": evaluation_result,
                "processing_result": processing_result,
                "decision_time": datetime.now().isoformat()
            }
            
            logger.info(f"降级策略决策完成，策略: {strategy_decision['strategy_name']}, 相关性: {relevance_assessment['relevance_level']}")
            return result
            
        except Exception as e:
            logger.error(f"降级策略决策失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.FALLBACK_STRATEGY_FAILED,
                message=f"降级策略决策失败: {str(e)}"
            )
    
    async def _evaluate_search_results(
        self,
        search_results: List[Dict[str, Any]],
        question: str
    ) -> Dict[str, Any]:
        """结果评估 - 根据设计文档实现"""
        try:
            logger.info("开始评估检索结果")
            
            if not search_results:
                return {
                    "similarity_scores": [],
                    "match_scores": [],
                    "completeness_scores": [],
                    "accuracy_scores": [],
                    "overall_evaluation": {
                        "avg_similarity": 0.0,
                        "avg_match": 0.0,
                        "avg_completeness": 0.0,
                        "avg_accuracy": 0.0,
                        "total_results": 0,
                        "high_quality_results": 0
                    }
                }
            
            similarity_scores = []
            match_scores = []
            completeness_scores = []
            accuracy_scores = []
            
            # 评估每个检索结果
            for result in search_results:
                # 相似度分数
                similarity_score = result.get("similarity_score", 0.0)
                similarity_scores.append(similarity_score)
                
                # 匹配度
                match_score = await self._calculate_match_score(result, question)
                match_scores.append(match_score)
                
                # 完整性
                completeness_score = self._calculate_completeness_score(result)
                completeness_scores.append(completeness_score)
                
                # 准确性
                accuracy_score = await self._calculate_accuracy_score(result, question)
                accuracy_scores.append(accuracy_score)
            
            # 计算整体评估
            overall_evaluation = {
                "avg_similarity": np.mean(similarity_scores) if similarity_scores else 0.0,
                "avg_match": np.mean(match_scores) if match_scores else 0.0,
                "avg_completeness": np.mean(completeness_scores) if completeness_scores else 0.0,
                "avg_accuracy": np.mean(accuracy_scores) if accuracy_scores else 0.0,
                "total_results": len(search_results),
                "high_quality_results": len([s for s in similarity_scores if s > 0.7])
            }
            
            return {
                "similarity_scores": similarity_scores,
                "match_scores": match_scores,
                "completeness_scores": completeness_scores,
                "accuracy_scores": accuracy_scores,
                "overall_evaluation": overall_evaluation
            }
            
        except Exception as e:
            logger.error(f"检索结果评估失败: {e}", exc_info=True)
            return {
                "similarity_scores": [],
                "match_scores": [],
                "completeness_scores": [],
                "accuracy_scores": [],
                "overall_evaluation": {
                    "avg_similarity": 0.0,
                    "avg_match": 0.0,
                    "avg_completeness": 0.0,
                    "avg_accuracy": 0.0,
                    "total_results": 0,
                    "high_quality_results": 0
                }
            }
    
    def _assess_relevance(self, evaluation_result: Dict[str, Any]) -> Dict[str, Any]:
        """相关性判断 - 根据设计文档实现"""
        try:
            overall_eval = evaluation_result["overall_evaluation"]
            
            # 计算综合相关性分数
            similarity_weight = settings.FALLBACK_SIMILARITY_WEIGHT
            match_weight = settings.FALLBACK_MATCH_WEIGHT
            completeness_weight = settings.FALLBACK_COMPLETENESS_WEIGHT
            accuracy_weight = settings.FALLBACK_ACCURACY_WEIGHT
            
            overall_score = (
                overall_eval["avg_similarity"] * similarity_weight +
                overall_eval["avg_match"] * match_weight +
                overall_eval["avg_completeness"] * completeness_weight +
                overall_eval["avg_accuracy"] * accuracy_weight
            )
            
            # 确定相关性等级
            if overall_score > self.RELEVANCE_THRESHOLDS["high"]:
                relevance_level = "high"
            elif overall_score > self.RELEVANCE_THRESHOLDS["medium"]:
                relevance_level = "medium"
            elif overall_score > self.RELEVANCE_THRESHOLDS["low"]:
                relevance_level = "low"
            else:
                relevance_level = "none"
            
            return {
                "overall_score": overall_score,
                "relevance_level": relevance_level,
                "similarity_score": overall_eval["avg_similarity"],
                "match_score": overall_eval["avg_match"],
                "completeness_score": overall_eval["avg_completeness"],
                "accuracy_score": overall_eval["avg_accuracy"],
                "high_quality_count": overall_eval["high_quality_results"],
                "total_count": overall_eval["total_results"]
            }
            
        except Exception as e:
            logger.error(f"相关性判断失败: {e}", exc_info=True)
            return {
                "overall_score": 0.0,
                "relevance_level": "none",
                "similarity_score": 0.0,
                "match_score": 0.0,
                "completeness_score": 0.0,
                "accuracy_score": 0.0,
                "high_quality_count": 0,
                "total_count": 0
            }
    
    def _decide_fallback_strategy(self, relevance_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """降级决策 - 根据设计文档实现"""
        try:
            relevance_level = relevance_assessment["relevance_level"]
            overall_score = relevance_assessment["overall_score"]
            
            # 根据相关性等级决定策略
            if relevance_level == "high":
                strategy_type = "knowledge_base_answer"
                strategy_name = "知识库回答"
                description = "基于知识库内容生成答案，提供详细引用和来源信息"
                
            elif relevance_level == "medium":
                strategy_type = "llm_answer"
                strategy_name = "大模型回答"
                description = "结合知识库内容和LLM知识，补充知识库不足的信息"
                
            elif relevance_level == "low":
                strategy_type = "hybrid_answer"
                strategy_name = "混合回答"
                description = "主要依赖LLM，少量参考知识库，提供一般性回答和建议"
                
            else:  # none
                strategy_type = "no_info_reply"
                strategy_name = "无信息回复"
                description = "直接回复'知识库中无相关信息'，明确告知用户无相关信息"
            
            return {
                "strategy_type": strategy_type,
                "strategy_name": strategy_name,
                "description": description,
                "relevance_level": relevance_level,
                "confidence": min(overall_score + settings.FALLBACK_CONFIDENCE_BOOST, 1.0),
                "decision_reason": f"基于相关性评估结果({relevance_level})选择{strategy_name}策略"
            }
            
        except Exception as e:
            logger.error(f"降级决策失败: {e}", exc_info=True)
            return {
                "strategy_type": "no_info_reply",
                "strategy_name": "无信息回复",
                "description": "系统错误，使用默认策略",
                "relevance_level": "none",
                "confidence": 0.0,
                "decision_reason": "系统错误"
            }
    
    async def _execute_fallback_strategy(
        self,
        strategy_decision: Dict[str, Any],
        search_results: List[Dict[str, Any]],
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行降级策略 - 根据设计文档实现"""
        try:
            strategy_type = strategy_decision["strategy_type"]
            logger.info(f"执行降级策略: {strategy_type}")
            
            if strategy_type == "knowledge_base_answer":
                return await self._execute_knowledge_base_strategy(search_results, question, context)
            
            elif strategy_type == "llm_answer":
                return await self._execute_llm_strategy(search_results, question, context)
            
            elif strategy_type == "hybrid_answer":
                return await self._execute_hybrid_strategy(search_results, question, context)
            
            elif strategy_type == "no_info_reply":
                return await self._execute_no_info_strategy(question, context)
            
            else:
                raise CustomException(
                    code=ErrorCode.UNKNOWN_STRATEGY,
                    message=f"未知的降级策略: {strategy_type}"
                )
                
        except Exception as e:
            logger.error(f"执行降级策略失败: {e}", exc_info=True)
            # 降级到无信息回复
            return await self._execute_no_info_strategy(question, context)
    
    async def _execute_knowledge_base_strategy(
        self,
        search_results: List[Dict[str, Any]],
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """策略1 - 知识库回答 (高相关性)"""
        try:
            logger.info("执行知识库回答策略")
            
            # 构建知识库上下文
            kb_context = self._build_knowledge_base_context(search_results)
            
            # 生成基于知识库的答案
            answer = await self._generate_knowledge_base_answer(question, kb_context)
            
            # 构建引用信息
            citations = self._build_citations(search_results)
            
            return {
                "answer": answer,
                "answer_type": "knowledge_base",
                "confidence": 0.9,
                "citations": citations,
                "source_count": len(search_results),
                "strategy_details": {
                    "context_length": len(kb_context),
                    "high_quality_sources": len([r for r in search_results if r.get("similarity_score", 0) > 0.8]),
                    "answer_length": len(answer)
                }
            }
            
        except Exception as e:
            logger.error(f"知识库回答策略执行失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.KNOWLEDGE_BASE_STRATEGY_FAILED,
                message=f"知识库回答策略执行失败: {str(e)}"
            )
    
    async def _execute_llm_strategy(
        self,
        search_results: List[Dict[str, Any]],
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """策略2 - 大模型回答 (中等相关性)"""
        try:
            logger.info("执行大模型回答策略")
            
            # 构建混合上下文（知识库 + LLM知识）
            mixed_context = self._build_mixed_context(search_results, question)
            
            # 生成混合答案
            answer = await self._generate_llm_answer(question, mixed_context)
            
            # 构建引用信息
            citations = self._build_citations(search_results)
            
            return {
                "answer": answer,
                "answer_type": "llm_enhanced",
                "confidence": 0.7,
                "citations": citations,
                "source_count": len(search_results),
                "strategy_details": {
                    "kb_context_length": len(mixed_context.get("kb_context", "")),
                    "llm_enhancement": True,
                    "answer_length": len(answer)
                }
            }
            
        except Exception as e:
            logger.error(f"大模型回答策略执行失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.LLM_STRATEGY_FAILED,
                message=f"大模型回答策略执行失败: {str(e)}"
            )
    
    async def _execute_hybrid_strategy(
        self,
        search_results: List[Dict[str, Any]],
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """策略3 - 混合回答 (低相关性)"""
        try:
            logger.info("执行混合回答策略")
            
            # 主要依赖LLM，少量参考知识库
            limited_context = self._build_limited_context(search_results)
            
            # 生成一般性回答
            answer = await self._generate_general_answer(question, limited_context)
            
            # 构建简化引用信息
            citations = self._build_simplified_citations(search_results)
            
            return {
                "answer": answer,
                "answer_type": "general",
                "confidence": settings.FALLBACK_DEFAULT_CONFIDENCE,
                "citations": citations,
                "source_count": min(len(search_results), 3),  # 最多3个来源
                "strategy_details": {
                    "llm_dominant": True,
                    "kb_reference_minimal": True,
                    "answer_length": len(answer)
                }
            }
            
        except Exception as e:
            logger.error(f"混合回答策略执行失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.HYBRID_STRATEGY_FAILED,
                message=f"混合回答策略执行失败: {str(e)}"
            )
    
    async def _execute_no_info_strategy(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """策略4 - 无信息回复 (无相关性)"""
        try:
            logger.info("执行无信息回复策略")
            
            # 生成无信息回复
            answer = "很抱歉，知识库中暂无与您问题相关的信息。建议您：\n1. 尝试使用不同的关键词重新提问\n2. 检查问题是否表述清楚\n3. 联系管理员添加相关文档到知识库"
            
            return {
                "answer": answer,
                "answer_type": "no_info",
                "confidence": 1.0,
                "citations": [],
                "source_count": 0,
                "strategy_details": {
                    "no_relevant_sources": True,
                    "suggestions_provided": True,
                    "answer_length": len(answer)
                }
            }
            
        except Exception as e:
            logger.error(f"无信息回复策略执行失败: {e}", exc_info=True)
            return {
                "answer": "系统暂时无法处理您的问题，请稍后重试。",
                "answer_type": "error",
                "confidence": 0.0,
                "citations": [],
                "source_count": 0,
                "strategy_details": {
                    "error_occurred": True,
                    "fallback_message": True
                }
            }
    
    # 辅助方法实现
    
    async def _calculate_match_score(self, result: Dict[str, Any], question: str) -> float:
        """计算匹配度"""
        try:
            content = result.get("content", "")
            question_words = set(question.lower().split())
            content_words = set(content.lower().split())
            
            if not question_words:
                return 0.0
            
            # 计算词汇重叠度
            overlap = len(question_words.intersection(content_words))
            match_score = overlap / len(question_words)
            
            return min(match_score, 1.0)
            
        except Exception:
            return 0.0
    
    def _calculate_completeness_score(self, result: Dict[str, Any]) -> float:
        """计算完整性分数"""
        try:
            content = result.get("content", "")
            
            # 基于内容长度和结构计算完整性
            length_score = min(len(content) / 500, 1.0)  # 500字符为满分
            
            # 检查是否包含完整句子
            sentence_count = content.count('.') + content.count('。')
            structure_score = min(sentence_count / 3, 1.0)  # 3个句子为满分
            
            completeness_score = (length_score + structure_score) / 2
            return completeness_score
            
        except Exception:
            return 0.0
    
    async def _calculate_accuracy_score(self, result: Dict[str, Any], question: str) -> float:
        """计算准确性分数"""
        try:
            # 简单的准确性评估
            content = result.get("content", "")
            
            # 检查内容是否包含事实性信息
            factual_indicators = ["是", "不是", "有", "没有", "可以", "不能", "应该", "不应该"]
            factual_count = sum(1 for indicator in factual_indicators if indicator in content)
            
            # 检查内容是否包含具体信息
            specific_indicators = ["具体", "详细", "例如", "比如", "包括", "包含"]
            specific_count = sum(1 for indicator in specific_indicators if indicator in content)
            
            accuracy_score = min((factual_count + specific_count) / 10, 1.0)
            return accuracy_score
            
        except Exception:
            return 0.0
    
    def _build_knowledge_base_context(self, search_results: List[Dict[str, Any]]) -> str:
        """构建知识库上下文"""
        try:
            context_parts = []
            
            for i, result in enumerate(search_results[:5]):  # 最多5个结果
                content = result.get("content", "")
                source = result.get("source", f"来源{i+1}")
                similarity = result.get("similarity_score", 0.0)
                
                context_parts.append(f"[来源{i+1}: {source} (相似度: {similarity:.2f})]\n{content}\n")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"构建知识库上下文失败: {e}")
            return ""
    
    async def _generate_knowledge_base_answer(self, question: str, context: str) -> str:
        """生成基于知识库的答案"""
        try:
            prompt = f"""基于以下知识库内容回答用户问题：

知识库内容：
{context}

用户问题：{question}

请基于知识库内容提供准确、详细的回答，并在回答中明确引用来源信息。如果知识库内容不足以回答问题，请说明。"""

            # 使用 generate_text 方法
            answer = await self.ollama_service.generate_text(prompt)
            return answer
            
        except Exception as e:
            logger.error(f"生成知识库答案失败: {e}")
            return "基于知识库内容生成答案时出现错误。"
    
    def _build_citations(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """构建引用信息"""
        try:
            citations = []
            
            for i, result in enumerate(search_results[:10]):  # 最多10个引用
                citation = {
                    "id": f"ref_{i+1}",
                    "document_id": result.get("document_id", ""),
                    "document_title": result.get("document_title", f"文档{i+1}"),
                    "knowledge_base_name": result.get("knowledge_base_name", "未知知识库"),
                    "content_snippet": result.get("content", "")[:200] + "...",
                    "similarity_score": result.get("similarity_score", 0.0),
                    "position_info": {
                        "chunk_index": result.get("chunk_index", 0),
                        "page_number": result.get("page_number", 0),
                        "url_link": result.get("url_link", "")
                    }
                }
                citations.append(citation)
            
            return citations
            
        except Exception as e:
            logger.error(f"构建引用信息失败: {e}")
            return []
    
    def _build_mixed_context(self, search_results: List[Dict[str, Any]], question: str) -> Dict[str, Any]:
        """构建混合上下文"""
        try:
            kb_context = self._build_knowledge_base_context(search_results)
            
            return {
                "kb_context": kb_context,
                "question_context": question,
                "context_type": "mixed"
            }
            
        except Exception as e:
            logger.error(f"构建混合上下文失败: {e}")
            return {"kb_context": "", "question_context": question, "context_type": "mixed"}
    
    async def _generate_llm_answer(self, question: str, context: Dict[str, Any]) -> str:
        """生成LLM增强答案"""
        try:
            kb_context = context.get("kb_context", "")
            
            prompt = f"""基于知识库内容和你的知识回答用户问题：

知识库内容：
{kb_context}

用户问题：{question}

请结合知识库内容和你的知识提供全面的回答。如果知识库内容不足，请用你的知识补充。请明确标注哪些信息来自知识库，哪些是你的补充。"""

            # 使用 generate_text 方法
            answer = await self.ollama_service.generate_text(prompt)
            return answer
            
        except Exception as e:
            logger.error(f"生成LLM答案失败: {e}")
            return "生成答案时出现错误。"
    
    def _build_limited_context(self, search_results: List[Dict[str, Any]]) -> str:
        """构建有限上下文"""
        try:
            # 只使用前2个结果
            limited_results = search_results[:2]
            context_parts = []
            
            for i, result in enumerate(limited_results):
                content = result.get("content", "")[:200]  # 限制长度
                context_parts.append(f"参考信息{i+1}: {content}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"构建有限上下文失败: {e}")
            return ""
    
    async def _generate_general_answer(self, question: str, context: str) -> str:
        """生成一般性回答"""
        try:
            prompt = f"""用户问题：{question}

参考信息：
{context}

请基于你的知识提供一般性的回答和建议。如果参考信息有用，可以简单提及。请明确说明这是基于一般知识的回答。"""

            # 使用 generate_text 方法
            answer = await self.ollama_service.generate_text(prompt)
            return answer
            
        except Exception as e:
            logger.error(f"生成一般性答案失败: {e}")
            return "基于一般知识提供回答时出现错误。"
    
    def _build_simplified_citations(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """构建简化引用信息"""
        try:
            citations = []
            
            for i, result in enumerate(search_results[:3]):  # 最多3个引用
                citation = {
                    "id": f"ref_{i+1}",
                    "document_title": result.get("document_title", f"文档{i+1}"),
                    "similarity_score": result.get("similarity_score", 0.0),
                    "content_snippet": result.get("content", "")[:100] + "..."
                }
                citations.append(citation)
            
            return citations
            
        except Exception as e:
            logger.error(f"构建简化引用信息失败: {e}")
            return []
