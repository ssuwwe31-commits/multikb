"""
Entity Extraction Service
实体提取服务
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import json
import re
import asyncio
from app.services.ollama_service import OllamaService
from app.core.logging import logger
from app.config.settings import settings
from app.utils.text_utils import split_text_into_chunks


# 第一步：实体提取Prompt模板
ENTITY_EXTRACTION_PROMPT = """
你是一个专业的实体提取专家。请从以下文档内容中提取实体。

{entity_types_section}

## 文档内容：
{document_content}

## 提取要求：
1. **实体提取**：
   - 提取所有重要的实体，包括名称、类型、描述和别名
   - 实体名称要准确、完整，避免缩写（除非原文就是缩写）
   - 如果实体有多个名称，都放入aliases数组
   {type_constraint}

2. **质量控制**：
   - 避免提取过于宽泛的实体（如"东西"、"方法"）
   - 避免提取重复的实体
   - 置信度要合理：高置信度（>{high_confidence_threshold}）用于明确的实体，低置信度（<{low_confidence_threshold}）用于推测的实体

请严格按照以下JSON格式返回结果，不要添加任何其他内容：
{{
    "entities": [
        {{
            "name": "实体名称",
            "type": "实体类型{type_hint}",
            "description": "实体描述（简要说明，1-2句话）",
            "aliases": ["别名1", "别名2"],
            "confidence": 0.95
        }}
    ]
}}

## 示例：
文档内容："Python是一种高级编程语言，由Guido van Rossum在1991年创建。Python广泛应用于Web开发、数据科学和人工智能领域。"
提取结果：
{{
    "entities": [
        {{
            "name": "Python",
            "type": "technology",
            "description": "高级编程语言",
            "aliases": ["Python语言"],
            "confidence": 0.98
        }},
        {{
            "name": "Guido van Rossum",
            "type": "person",
            "description": "Python编程语言的创建者",
            "aliases": [],
            "confidence": 0.95
        }},
        {{
            "name": "Web开发",
            "type": "concept",
            "description": "应用开发领域",
            "aliases": [],
            "confidence": 0.80
        }}
    ]
}}
"""

# 第二步：关系提取Prompt模板
RELATIONSHIP_EXTRACTION_PROMPT = """
你是一个专业的关系提取专家。请从以下文档内容中提取实体间的关系。

## 已提取的实体列表：
{entities_list}

## 关系类型定义：
{relationship_types_section}

## 文档内容：
{document_content}

## 提取要求：
1. **关系提取**：
   - 只提取上述实体列表中的实体间的关系
   - source和target必须是实体列表中的name（完全匹配）
   - 关系必须有明确的证据支持（文档中的原文）
   - 关系类型必须是上述定义的类型之一

2. **质量控制**：
   - 避免提取过于宽泛的关系
   - 避免提取重复的关系
   - 置信度要合理：高置信度（>{high_confidence_threshold}）用于明确的关系，低置信度（<{low_confidence_threshold}）用于推测的关系

请严格按照以下JSON格式返回结果，不要添加任何其他内容：
{{
    "relationships": [
        {{
            "source": "源实体名称（必须是实体列表中的name）",
            "target": "目标实体名称（必须是实体列表中的name）",
            "relation_type": "关系类型（必须是上述类型之一）",
            "description": "关系描述（简要说明）",
            "evidence": "证据文本片段（文档中的原文，包含该关系的句子）",
            "confidence": 0.92
        }}
    ]
}}

## 示例：
实体列表：
- Python（类型：technology，描述：高级编程语言）
- Guido van Rossum（类型：person，描述：Python编程语言的创建者）

文档内容："Python是一种高级编程语言，由Guido van Rossum在1991年创建。"
提取结果：
{{
    "relationships": [
        {{
            "source": "Python",
            "target": "Guido van Rossum",
            "relation_type": "created_by",
            "description": "Python由Guido van Rossum创建",
            "evidence": "Python是一种高级编程语言，由Guido van Rossum在1991年创建",
            "confidence": 0.95
        }}
    ]
}}
"""


class EntityExtractionService:
    """实体提取服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ollama_service = OllamaService(db)
        # 从配置读取，如果没有则使用默认值
        self.max_chunk_length = getattr(settings, 'ENTITY_EXTRACTION_CHUNK_SIZE', 8000)
        self.chunk_overlap_ratio = getattr(settings, 'ENTITY_EXTRACTION_CHUNK_OVERLAP_RATIO', 0.2)
        self.max_concurrent = getattr(settings, 'ENTITY_EXTRACTION_MAX_CONCURRENT', 5)
        self.cross_chunk_enabled = getattr(settings, 'ENTITY_EXTRACTION_CROSS_CHUNK_ENABLED', True)
    
    async def extract_with_llm(
        self, 
        document_content: str, 
        document_id: int,
        knowledge_base_id: Optional[int] = None,
        entity_type_mode: str = "system",
        entity_type_codes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """使用LLM两步提取实体和关系
        
        流程：
        1. 第一步：提取实体
        2. 第二步：基于实体列表提取关系
        
        Args:
            document_content: 文档内容
            document_id: 文档ID
            knowledge_base_id: 知识库ID（用于获取知识库特定的实体类型）
            entity_type_mode: 实体类型模式 (system/user/model)
            entity_type_codes: 要提取的实体类型代码列表（可选）
            
        Returns:
            包含entities和relationships的字典
        """
        # 长文档处理：如果超过上下文长度，分块处理
        if len(document_content) > self.max_chunk_length:
            return await self._extract_from_chunks(document_content, document_id, knowledge_base_id, entity_type_mode, entity_type_codes)
        else:
            return await self._extract_entities_and_relationships(document_content, knowledge_base_id, entity_type_mode, entity_type_codes)
    
    async def _get_entity_types_prompt_section(
        self, 
        knowledge_base_id: Optional[int] = None,
        entity_type_mode: str = "system",
        entity_type_codes: Optional[List[str]] = None
    ) -> str:
        """获取实体类型的Prompt片段
        
        Args:
            knowledge_base_id: 知识库ID
            entity_type_mode: 实体类型模式
                - system: 仅使用系统默认类型（is_system=True）
                - user: 仅使用用户创建类型（is_system=False）
                - model: 不限制类型，让模型自由提取
            entity_type_codes: 要提取的实体类型代码列表（可选，如果提供则只使用这些类型）
        """
        # 如果是模型自由模式，返回空提示（不限制类型）
        if entity_type_mode == "model":
            return """## 实体类型定义：
你可以自由定义实体类型，根据文档内容提取最合适的类型。常见的实体类型包括但不限于：
- 人物、组织、地点、时间、事件
- 概念、方法、技术、产品、工具
- 文档、配置、协议、标准
- 其他你认为合适的类型

请根据文档内容，为每个实体选择最合适的类型名称。"""
        
        from app.services.entity_type_service import EntityTypeService
        entity_type_service = EntityTypeService(self.db)
        
        # 根据模式过滤类型
        if entity_type_mode == "system":
            # 仅系统类型
            types = entity_type_service.get_all_types(
                is_enabled=True,
                is_system=True,
                knowledge_base_id=knowledge_base_id
            )
        elif entity_type_mode == "user":
            # 仅用户创建类型
            types = entity_type_service.get_all_types(
                is_enabled=True,
                is_system=False,
                knowledge_base_id=knowledge_base_id
            )
        else:
            # 默认：所有启用的类型
            types = entity_type_service.get_all_types(
                is_enabled=True,
                knowledge_base_id=knowledge_base_id
            )
        
        # 如果指定了实体类型代码列表，进一步过滤
        if entity_type_codes and len(entity_type_codes) > 0:
            types = [t for t in types if t.code in entity_type_codes]
        
        if not types:
            # 如果没有找到类型，根据模式给出提示
            if entity_type_mode == "system":
                return "## 实体类型定义：\n未找到系统默认的实体类型，请先创建系统类型。"
            elif entity_type_mode == "user":
                return "## 实体类型定义：\n未找到用户创建的实体类型，请先创建自定义类型。"
            else:
                return "## 实体类型定义：\n未找到启用的实体类型。"
        
        lines = ["## 实体类型定义："]
        lines.append("**重要：实体类型必须是以下定义的类型之一，不能使用其他类型。**")
        lines.append("")
        
        for entity_type in types:
            prompt_hint = ""
            if entity_type.meta_data and isinstance(entity_type.meta_data, dict):
                prompt_hint = entity_type.meta_data.get("prompt_hint", "")
            
            if prompt_hint:
                lines.append(f"- {entity_type.code}: {entity_type.name}（{prompt_hint}）")
            else:
                lines.append(f"- {entity_type.code}: {entity_type.name}")
        
        return "\n".join(lines)
    
    async def _extract_entities_and_relationships(
        self,
        document_content: str,
        knowledge_base_id: Optional[int] = None,
        entity_type_mode: str = "system",
        entity_type_codes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        两步提取：先提取实体，再提取关系
        
        流程：
        1. 第一步：提取实体
        2. 第二步：基于实体列表提取关系
        3. 验证关系（确保source和target在实体列表中）
        
        Args:
            document_content: 文档内容
            knowledge_base_id: 知识库ID
            entity_type_mode: 实体类型模式 (system/user/model)
            entity_type_codes: 要提取的实体类型代码列表（可选）
        """
        # 第一步：提取实体
        logger.info(f"开始第一步：提取实体，模式={entity_type_mode}，文档内容长度={len(document_content)} 字符")
        if entity_type_codes:
            logger.info(f"指定了实体类型代码列表: {entity_type_codes}")
        entity_types_section = await self._get_entity_types_prompt_section(knowledge_base_id, entity_type_mode, entity_type_codes)
        
        # 根据模式调整Prompt中的类型约束说明
        type_constraint_text = ""
        type_hint_text = ""
        if entity_type_mode == "model":
            type_constraint_text = "   - 实体类型可以根据文档内容自由定义，选择最合适的类型名称"
            type_hint_text = "（根据文档内容自由定义）"
        else:
            type_constraint_text = "   - 确保实体类型必须是上述定义的类型之一"
            type_hint_text = "（必须是上述类型之一）"
        
        # 构建实体提取Prompt
        entity_prompt = ENTITY_EXTRACTION_PROMPT.format(
            entity_types_section=entity_types_section,
            document_content=document_content,
            high_confidence_threshold=settings.KG_HIGH_CONFIDENCE_THRESHOLD,
            low_confidence_threshold=settings.KG_LOW_CONFIDENCE_THRESHOLD,
            type_constraint=type_constraint_text,
            type_hint=type_hint_text
        )
        
        try:
            logger.info(f"调用LLM提取实体，提示词长度={len(entity_prompt)} 字符")
            entity_response = await self.ollama_service.generate_text(entity_prompt, format="json")
            logger.info(f"LLM实体提取响应完成，响应长度={len(entity_response)} 字符")
            entity_result = self._parse_and_validate_json(entity_response)
            entities = entity_result.get("entities", [])
            logger.info(f"第一步实体提取完成，提取到 {len(entities)} 个实体")
            
            # 记录提取出的原始实体数据格式（仅在DEBUG级别且启用详细日志时输出）
            # 注释掉详细的数据类型日志，减少日志量
            # if entities and logger.isEnabledFor(logging.DEBUG):
            #     logger.debug(f"提取到 {len(entities)} 个实体")
        except Exception as e:
            logger.error(f"第一步实体提取失败: {e}", exc_info=True)
            return {"entities": [], "relationships": []}
        
        # 如果没有提取到实体，直接返回
        if not entities:
            logger.warning("未提取到实体，跳过关系提取")
            return {"entities": [], "relationships": []}
        
        # 第二步：提取关系
        logger.info(f"开始第二步：提取关系，实体数量={len(entities)}")
        entities_list = self._format_entities_list(entities)
        relationship_types_section = self._get_relationship_types_section()
        
        relationship_prompt = RELATIONSHIP_EXTRACTION_PROMPT.format(
            entities_list=entities_list,
            relationship_types_section=relationship_types_section,
            document_content=document_content,
            high_confidence_threshold=settings.KG_HIGH_CONFIDENCE_THRESHOLD,
            low_confidence_threshold=settings.KG_LOW_CONFIDENCE_THRESHOLD
        )
        
        try:
            logger.info(f"调用LLM提取关系，提示词长度={len(relationship_prompt)} 字符")
            relationship_response = await self.ollama_service.generate_text(relationship_prompt, format="json")
            logger.info(f"LLM关系提取响应完成，响应长度={len(relationship_response)} 字符")
            relationship_result = self._parse_and_validate_json(relationship_response)
            relationships = relationship_result.get("relationships", [])
            logger.info(f"第二步关系提取完成，提取到 {len(relationships)} 个关系")
            
            # 记录提取出的原始关系数据格式（仅在DEBUG级别且启用详细日志时输出）
            # 注释掉详细的数据类型日志，减少日志量
            # if relationships and logger.isEnabledFor(logging.DEBUG):
            #     logger.debug(f"提取到 {len(relationships)} 个关系")
        except Exception as e:
            logger.error(f"第二步关系提取失败: {e}", exc_info=True)
            # 即使关系提取失败，也返回已提取的实体
            return {"entities": entities, "relationships": []}
        
        # 验证关系：确保source和target都在实体列表中
        entity_names = {e.get("name") for e in entities}
        validated_relationships = [
            rel for rel in relationships
            if rel.get("source") in entity_names and rel.get("target") in entity_names
        ]
        
        return {
            "entities": entities,
            "relationships": validated_relationships
        }
    
    def _format_entities_list(self, entities: List[Dict]) -> str:
        """格式化实体列表为字符串（用于关系提取Prompt）"""
        lines = []
        for entity in entities:
            name = entity.get("name", "")
            entity_type = entity.get("type", "")
            description = entity.get("description", "")
            lines.append(f"- {name}（类型：{entity_type}，描述：{description}）")
        return "\n".join(lines)
    
    def _get_relationship_types_section(self) -> str:
        """获取关系类型的Prompt片段"""
        return """
## 关系类型定义：
- belongs_to: 属于（如：Python属于编程语言，部门属于公司）
- references: 引用（如：文档A引用文档B，论文引用其他论文）
- depends_on: 依赖（如：FastAPI依赖于Starlette，系统依赖于数据库）
- compares: 对比（如：异步编程对比同步编程，方案A对比方案B）
- implements: 实现（如：类A实现接口B，系统实现某个标准）
- related_to: 相关（通用相关关系，如：人员与组织相关，概念与应用相关）
- part_of: 部分（如：异步是编程的一部分，模块是系统的一部分）
- has_part: 包含（如：Python包含标准库，系统包含多个模块）
- created_by: 创建者（如：Python由Guido van Rossum创建，公司由某人创建）
- occurs_in: 发生在（如：事件发生在某个地点，会议发生在某个时间）
- works_at: 工作于（如：张三在北京大学工作）
- studies: 学习（如：学生研究某个领域）
- other: 其他未分类的关系
"""
    
    async def _extract_from_chunks(
        self,
        document_content: str,
        document_id: int,
        knowledge_base_id: Optional[int] = None,
        entity_type_mode: str = "system",
        entity_type_codes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        从多个文档块提取实体和关系（并发优化）
        
        使用重叠窗口分块 + 并发处理
        """
        # 使用重叠窗口分块
        chunk_data_list = self._split_document_into_chunks(document_content)
        
        if not chunk_data_list:
            return {"entities": [], "relationships": []}
        
        # 使用信号量控制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def extract_chunk_with_semaphore(chunk_data: Dict[str, Any]):
            """带信号量的块提取"""
            async with semaphore:
                try:
                    result = await self._extract_entities_and_relationships(
                        chunk_data["text"], 
                        knowledge_base_id,
                        entity_type_mode,
                        entity_type_codes
                    )
                    # 添加块位置信息（用于跨块关系检测）
                    result["chunk_info"] = {
                        "chunk_index": chunk_data["chunk_index"],
                        "start_pos": chunk_data["start_pos"],
                        "end_pos": chunk_data["end_pos"]
                    }
                    return result
                except Exception as e:
                    logger.error(f"处理文档块 {chunk_data.get('chunk_index', 'unknown')} 失败: {e}")
                    return {"entities": [], "relationships": [], "chunk_info": chunk_data}
        
        # 并发处理所有块
        tasks = [
            extract_chunk_with_semaphore(chunk_data) 
            for chunk_data in chunk_data_list
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集所有实体和关系
        all_entities = []
        all_relationships = []
        chunk_results = []
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"块处理异常: {result}")
                continue
            
            all_entities.extend(result.get("entities", []))
            all_relationships.extend(result.get("relationships", []))
            chunk_results.append(result)
        
        # 合并去重 + 跨块关系检测
        if self.cross_chunk_enabled:
            return self._merge_and_detect_cross_chunk_relationships(
                all_entities, 
                all_relationships,
                chunk_results,
                document_content
            )
        else:
            return self._merge_extraction_results(all_entities, all_relationships)
    
    def _split_document_into_chunks(
        self, 
        content: str, 
        chunk_size: Optional[int] = None,
        overlap_ratio: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        将文档分割成块（带重叠窗口）
        
        复用现有的 split_text_into_chunks，但适配实体提取需求
        
        Args:
            content: 文档内容
            chunk_size: 块大小（字符数）
            overlap_ratio: 重叠比例（0.2 = 20%）
        
        Returns:
            块列表，每个块包含：
            - text: 块文本
            - start_pos: 在原文中的起始位置
            - end_pos: 在原文中的结束位置
            - chunk_index: 块索引
        """
        if chunk_size is None:
            chunk_size = self.max_chunk_length
        if overlap_ratio is None:
            overlap_ratio = self.chunk_overlap_ratio
        
        overlap_size = int(chunk_size * overlap_ratio)
        
        # 复用现有的分块函数
        chunk_texts = split_text_into_chunks(
            content, 
            chunk_size=chunk_size, 
            overlap=overlap_size
        )
        
        # 转换为带位置信息的格式
        chunks = []
        current_pos = 0
        
        for i, chunk_text in enumerate(chunk_texts):
            chunks.append({
                "text": chunk_text,
                "start_pos": current_pos,
                "end_pos": current_pos + len(chunk_text),
                "chunk_index": i
            })
            # 计算下一个块的起始位置（考虑重叠）
            current_pos += len(chunk_text) - overlap_size
        
        return chunks
    
    def _parse_and_validate_json(self, response: str) -> Dict[str, Any]:
        """解析和验证JSON响应（改进版：支持修复截断的JSON）"""
        json_str = None
        
        # 方法1：尝试提取JSON代码块（如果有markdown格式）
        # 注意：对于大JSON，需要使用平衡括号算法而不是简单的非贪婪匹配
        json_match = re.search(r'```(?:json)?\s*(\{.*)\s*```', response, re.DOTALL)
        if json_match:
            # 从代码块中提取的JSON，使用平衡括号算法找到完整的JSON
            code_block_content = json_match.group(1)
            json_str = self._extract_json_with_balance(code_block_content)
            # 减少JSON解析的详细日志（已注释）
            # if json_str:
            #     logger.debug(f"从markdown代码块提取JSON，长度={len(json_str)}")
        
        # 方法2：如果方法1失败，直接从响应中查找第一个{到最后一个}（平衡括号算法）
        if not json_str:
            json_str = self._extract_json_with_balance(response)
            # 减少JSON解析的详细日志（已注释）
            # if json_str:
            #     logger.debug(f"使用平衡括号算法提取JSON，长度={len(json_str)}")
        
        # 方法3：如果方法2失败，尝试从响应末尾向前查找（处理响应末尾有额外内容的情况）
        if not json_str:
            # 查找最后一个}，然后向前查找匹配的{
            last_brace_idx = response.rfind('}')
            if last_brace_idx > 0:
                # 从最后一个}向前查找匹配的{
                reverse_text = response[:last_brace_idx+1]
                json_str = self._extract_json_with_balance(reverse_text)
                # 减少JSON解析的详细日志（已注释）
                # if json_str:
                #     logger.debug(f"从末尾向前查找提取JSON，长度={len(json_str)}")
        
        if not json_str:
            # 记录更多调试信息
            first_brace_idx = response.find('{')
            last_brace_idx = response.rfind('}')
            brace_count = response.count('{')
            close_brace_count = response.count('}')
            
            logger.warning(f"无法从响应中提取JSON，响应长度={len(response)}, "
                         f"第一个{{位置={first_brace_idx}, 最后一个}}位置={last_brace_idx}, "
                         f"{{数量={brace_count}, }}数量={close_brace_count}, "
                         f"前500字符: {response[:500]}, "
                         f"后500字符: {response[-500:] if len(response) > 500 else response}")
            
            # 如果括号数量不匹配，尝试修复
            if brace_count != close_brace_count:
                logger.warning(f"括号数量不匹配（{{={brace_count}, }}={close_brace_count}），可能JSON被截断")
                # 如果缺少闭合括号，尝试修复
                if brace_count > close_brace_count:
                    missing_closes = brace_count - close_brace_count
                    logger.info(f"尝试修复JSON：缺少{missing_closes}个闭合括号")
                    
                    # 方法1：简单修复 - 直接添加缺失的}
                    potential_json = response[first_brace_idx:] + '}' * missing_closes
                    try:
                        result = json.loads(potential_json)
                        logger.info(f"通过添加缺失的}}成功解析JSON（添加了{missing_closes}个}}）")
                        return result if isinstance(result, dict) else {"entities": [], "relationships": []}
                    except json.JSONDecodeError as e:
                        logger.debug(f"简单修复失败: {e}, 错误位置={e.pos if hasattr(e, 'pos') else 'unknown'}")
                    
                    # 方法2：智能修复 - 找到最后一个完整的实体对象，然后添加缺失的括号和数组/对象闭合
                    # 从最后一个}向前查找，找到最后一个完整的实体对象
                    last_brace_pos = response.rfind('}')
                    if last_brace_pos > 0:
                        # 检查最后一个}之后是否有未闭合的字符串（需要考虑转义）
                        remaining_text = response[last_brace_pos+1:]
                        quote_count = 0
                        escape_next = False
                        for char in remaining_text:
                            if escape_next:
                                escape_next = False
                                continue
                            if char == '\\':
                                escape_next = True
                                continue
                            if char == '"':
                                quote_count += 1
                        
                        # 查找entities数组的开始位置
                        entities_start = response.find('"entities": [', first_brace_idx)
                        if entities_start < 0:
                            entities_start = first_brace_idx
                        
                        # 构造修复后的JSON
                        if quote_count % 2 == 1:
                            # 有未闭合的引号，先闭合字符串，然后添加缺失的括号
                            # 需要：闭合引号 + 缺失的实体对象闭合} + 数组闭合] + 对象闭合}
                            potential_json = response[entities_start:last_brace_pos+1] + '"' + '}' * missing_closes + ']' + '}'
                            logger.debug(f"智能修复：检测到未闭合的字符串，添加闭合引号和{missing_closes}个}}")
                        else:
                            # 没有未闭合的引号，直接添加缺失的括号
                            # 需要添加：缺失的实体对象闭合} + 数组闭合] + 对象闭合}
                            potential_json = response[entities_start:last_brace_pos+1] + '}' * missing_closes + ']' + '}'
                            logger.debug(f"智能修复：没有未闭合的字符串，添加{missing_closes}个}}")
                        
                        try:
                            result = json.loads(potential_json)
                            logger.info(f"通过智能修复成功解析JSON（添加了{missing_closes}个}}和数组/对象闭合）")
                            return result if isinstance(result, dict) else {"entities": [], "relationships": []}
                        except json.JSONDecodeError as e:
                            error_pos = e.pos if hasattr(e, 'pos') else 0
                            context_start = max(0, error_pos - 100)
                            context_end = min(len(potential_json), error_pos + 100)
                            error_context = potential_json[context_start:context_end]
                            logger.debug(f"智能修复失败: {e}, 错误位置={error_pos}, "
                                       f"修复后的JSON长度={len(potential_json)}, "
                                       f"错误位置附近: ...{error_context}...")
                    
                    # 方法3：截断修复 - 找到最后一个完整的实体对象，截断到那里
                    # 从最后一个}向前查找，找到最后一个完整的实体对象
                    if last_brace_pos > 0:
                        # 向前查找，找到entities数组的最后一个完整项
                        # 查找最后一个完整的实体对象（以}结尾，前面有完整的字段）
                        truncated_json = self._truncate_to_last_complete_entity(response[first_brace_idx:])
                        if truncated_json:
                            try:
                                result = json.loads(truncated_json)
                                logger.info(f"通过截断到最后一个完整实体成功解析JSON")
                                return result if isinstance(result, dict) else {"entities": [], "relationships": []}
                            except json.JSONDecodeError as e:
                                logger.debug(f"截断修复失败: {e}")
            
            return {"entities": [], "relationships": []}
        
        # 尝试解析JSON
        result = None
        parse_error = None
        
        try:
            result = json.loads(json_str)
        except json.JSONDecodeError as e:
            parse_error = e
            logger.warning(f"JSON解析失败（第一次尝试）: {e}, JSON长度={len(json_str)}, 错误位置={e.pos if hasattr(e, 'pos') else 'unknown'}")
            
            # 尝试修复常见的JSON错误
            json_str_fixed = self._try_fix_json(json_str, e)
            if json_str_fixed and json_str_fixed != json_str:
                try:
                    result = json.loads(json_str_fixed)
                    logger.info(f"JSON修复成功，使用修复后的JSON")
                except json.JSONDecodeError as e2:
                    logger.warning(f"JSON修复后仍然失败: {e2}")
            
            # 如果还是失败，尝试截取到错误位置之前的部分
            if not result and hasattr(parse_error, 'pos') and parse_error.pos > 0:
                try:
                    # 尝试在错误位置之前查找最后一个完整的对象或数组
                    truncated_json = self._truncate_json_to_valid(json_str, parse_error.pos)
                    if truncated_json:
                        result = json.loads(truncated_json)
                        logger.info(f"使用截断的JSON成功解析（截断到位置{parse_error.pos}）")
                except Exception as e3:
                    logger.debug(f"截断JSON尝试失败: {e3}")
        
        if not result:
            # 记录更多调试信息
            error_pos = parse_error.pos if parse_error and hasattr(parse_error, 'pos') else 0
            context_start = max(0, error_pos - 200)
            context_end = min(len(json_str), error_pos + 200)
            error_context = json_str[context_start:context_end]
            logger.error(f"JSON解析最终失败: {parse_error}, 响应长度={len(response)}, JSON长度={len(json_str)}, "
                        f"错误位置附近内容: ...{error_context}...")
            return {"entities": [], "relationships": []}
        
        # 验证格式
        if not isinstance(result, dict):
            logger.error(f"解析结果不是字典格式: {type(result)}")
            return {"entities": [], "relationships": []}
        
        if "entities" not in result:
            result["entities"] = []
        if "relationships" not in result:
            result["relationships"] = []
        
        # 验证实体格式（在迭代时创建新列表，避免修改正在迭代的列表）
        valid_entities = []
        for entity in result["entities"]:
            if isinstance(entity, dict) and "name" in entity and "type" in entity:
                valid_entities.append(entity)
            else:
                logger.warning(f"实体格式不完整，跳过: {entity}")
        result["entities"] = valid_entities
        
        # 验证关系格式
        valid_relationships = []
        for rel in result["relationships"]:
            if isinstance(rel, dict) and "source" in rel and "target" in rel and "relation_type" in rel:
                valid_relationships.append(rel)
            else:
                logger.warning(f"关系格式不完整，跳过: {rel}")
        result["relationships"] = valid_relationships
        
        return result
    
    def _extract_json_with_balance(self, text: str) -> Optional[str]:
        """使用平衡括号算法提取完整的JSON对象"""
        # 查找第一个 {
        start_idx = text.find('{')
        if start_idx == -1:
            # 减少JSON解析的详细日志
            # logger.debug(f"平衡括号算法：未找到开始符号{{，文本长度={len(text)}")
            return None
        
        # 减少JSON解析的详细日志
        # logger.debug(f"平衡括号算法：找到开始位置={start_idx}，文本总长度={len(text)}")
        
        # 从第一个 { 开始，使用平衡括号算法找到匹配的 }
        depth = 0
        in_string = False
        escape_next = False
        max_depth = 0
        
        for i in range(start_idx, len(text)):
            char = text[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if char == '{':
                depth += 1
                max_depth = max(max_depth, depth)
            elif char == '}':
                depth -= 1
                if depth == 0:
                    # 找到匹配的 }
                    json_str = text[start_idx:i+1]
                    # 减少JSON解析的详细日志
                    # logger.debug(f"平衡括号算法：成功提取JSON，长度={len(json_str)}，最大深度={max_depth}")
                    return json_str
        
        # 如果没有找到匹配的 }，记录调试信息
        logger.warning(f"平衡括号算法：未找到匹配的}}，文本长度={len(text)}，开始位置={start_idx}，"
                      f"最终深度={depth}，最大深度={max_depth}，"
                      f"最后100字符: {text[-100:] if len(text) > 100 else text}")
        return None
    
    def _try_fix_json(self, json_str: str, error: json.JSONDecodeError) -> Optional[str]:
        """尝试修复常见的JSON错误"""
        if not hasattr(error, 'pos'):
            return None
        
        pos = error.pos
        fixed = json_str
        
        # 错误信息包含的信息
        error_msg = str(error)
        
        # 尝试修复缺少逗号的情况
        if "Expecting ',' delimiter" in error_msg or "Expecting delimiter" in error_msg:
            # 在错误位置之前查找最后一个}或]，然后添加逗号
            # 但这可能很复杂，先尝试简单的方法
            pass
        
        # 尝试修复未闭合的字符串
        if "Unterminated string" in error_msg:
            # 在错误位置添加闭合引号
            # 但这可能不正确，先不处理
            pass
        
        # 尝试修复截断的JSON（在最后一个完整的对象或数组处截断）
        if "Unterminated string" in error_msg or "Expecting" in error_msg:
            # 尝试移除末尾不完整的内容
            # 找到最后一个完整的 } 或 ]
            last_complete_brace = fixed.rfind('}')
            last_complete_bracket = fixed.rfind(']')
            last_complete = max(last_complete_brace, last_complete_bracket)
            
            if last_complete > 0:
                # 检查是否在字符串内部
                before_pos = fixed[:last_complete+1]
                string_count = before_pos.count('"') - before_pos.count('\\"')
                if string_count % 2 == 0:  # 字符串是闭合的
                    return fixed[:last_complete+1] + '}'
        
        return fixed
    
    def _truncate_to_last_complete_entity(self, json_str: str) -> Optional[str]:
        """截断到最后一个完整的实体对象"""
        try:
            # 查找entities数组的开始位置
            entities_start = json_str.find('"entities": [')
            if entities_start < 0:
                # 如果没有找到entities数组，尝试直接构造
                entities_start = json_str.find('{')
            
            if entities_start < 0:
                return None
            
            # 从entities数组开始，使用平衡括号算法找到最后一个完整的实体对象
            # 查找最后一个完整的实体对象（以}结尾，且不在字符串内）
            entities_content = json_str[entities_start:]
            
            # 使用平衡括号算法，找到最后一个完整的实体对象
            # 从后向前查找，找到最后一个完整的实体对象
            last_brace_pos = entities_content.rfind('}')
            if last_brace_pos <= 0:
                return None
            
            # 检查最后一个}是否在字符串内（通过检查引号数量）
            before_brace = entities_content[:last_brace_pos]
            quote_count = 0
            escape_next = False
            for char in before_brace:
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char == '"':
                    quote_count += 1
            
            # 如果引号数量是奇数，最后一个}可能在字符串内，向前查找下一个}
            if quote_count % 2 == 1:
                # 可能在字符串内，向前查找下一个完整的}
                # 从倒数第二个}开始查找
                second_last_brace = before_brace.rfind('}')
                if second_last_brace > 0:
                    last_brace_pos = second_last_brace
            
            # 截断到最后一个完整的实体对象
            truncated = entities_content[:last_brace_pos+1]
            
            # 构造完整的JSON：添加数组闭合]和对象闭合}
            # 检查entities数组是否已经闭合
            if truncated.rstrip().endswith(']'):
                # 数组已闭合，只需要添加对象闭合}
                complete_json = json_str[:entities_start] + truncated + '}'
            else:
                # 数组未闭合，需要添加]和}
                complete_json = json_str[:entities_start] + truncated + ']}'
            
            logger.debug(f"截断到最后一个完整实体：原始长度={len(json_str)}, 截断后长度={len(complete_json)}")
            
            # 验证JSON是否有效
            try:
                test_result = json.loads(complete_json)
                if isinstance(test_result, dict) and "entities" in test_result:
                    logger.info(f"截断修复成功：保留了{len(test_result.get('entities', []))}个实体")
                    return complete_json
            except json.JSONDecodeError as e:
                logger.debug(f"截断后的JSON验证失败: {e}, 错误位置={e.pos if hasattr(e, 'pos') else 'unknown'}")
            
            return None
        except Exception as e:
            logger.debug(f"截断到最后一个完整实体失败: {e}", exc_info=True)
            return None
    
    def _truncate_json_to_valid(self, json_str: str, error_pos: int) -> Optional[str]:
        """尝试截取到错误位置之前的有效JSON"""
        if error_pos <= 0:
            return None
        
        # 在错误位置之前查找最后一个完整的对象
        truncated = json_str[:error_pos]
        
        # 尝试找到最后一个完整的数组项（如果是relationships数组）
        # 或者找到最后一个完整的对象（如果是entities数组）
        
        # 简化：尝试在错误位置之前找到最后一个完整的 }]
        last_valid_close = truncated.rfind('}]')
        if last_valid_close > 0:
            # 检查是否有对应的开始
            potential_json = truncated[:last_valid_close+1] + ']}'
            try:
                json.loads(potential_json)
                return potential_json
            except:
                pass
        
        # 尝试找到最后一个完整的对象
        last_valid_obj_end = truncated.rfind('}')
        if last_valid_obj_end > 0:
            # 向前查找匹配的 {
            depth = 1
            for i in range(last_valid_obj_end - 1, -1, -1):
                if truncated[i] == '}':
                    depth += 1
                elif truncated[i] == '{':
                    depth -= 1
                    if depth == 0:
                        # 找到完整的对象
                        obj_start = i
                        # 尝试构造有效的JSON
                        obj_json = truncated[obj_start:last_valid_obj_end+1]
                        # 尝试包装成有效的结构
                        if '"relationships"' in truncated[:obj_start]:
                            potential = truncated[:obj_start] + '"relationships": [' + obj_json + ']}'
                        elif '"entities"' in truncated[:obj_start]:
                            potential = truncated[:obj_start] + '"entities": [' + obj_json + ']}'
                        else:
                            potential = '{' + obj_json + '}'
                        
                        try:
                            json.loads(potential)
                            return potential
                        except:
                            break
                elif truncated[i] == '"':
                    # 可能在字符串中，跳过
                    continue
        
        return None
    
    def _merge_extraction_results(
        self, 
        entities: List[Dict], 
        relationships: List[Dict]
    ) -> Dict[str, Any]:
        """合并提取结果，去重（改进版：支持别名匹配）"""
        # 使用改进的实体合并方法
        merged_entities = self._merge_entities_with_aliases(entities)
        
        # 关系去重（基于源、目标和关系类型）
        unique_relationships = {}
        for rel in relationships:
            key = (
                rel.get("source"), 
                rel.get("target"), 
                rel.get("relation_type")
            )
            if key not in unique_relationships:
                unique_relationships[key] = rel
        
        return {
            "entities": merged_entities,
            "relationships": list(unique_relationships.values())
        }
    
    def _merge_entities_with_aliases(self, entities: List[Dict]) -> List[Dict]:
        """
        合并实体（支持别名匹配）
        
        改进点：
        1. 基于名称和类型去重
        2. 别名匹配（如果实体A的别名与实体B的名称匹配，合并）
        3. 名称标准化（大小写、空格等）
        """
        # 实体映射：key -> entity
        entity_map = {}
        # 别名映射：alias -> key
        alias_map = {}
        
        for entity in entities:
            name = self.normalize_entity_name(entity.get("name", ""))
            entity_type = entity.get("type", "")
            key = (name, entity_type)
            
            # 检查是否已存在
            if key in entity_map:
                # 合并别名和描述
                existing = entity_map[key]
                existing_aliases = set(existing.get("aliases", []))
                new_aliases = set(entity.get("aliases", []))
                existing["aliases"] = list(existing_aliases | new_aliases)
                
                # 更新别名映射
                for alias in existing["aliases"]:
                    alias_map[alias.lower()] = key
                
                # 合并描述（取更详细的）
                if entity.get("description") and (
                    not existing.get("description") or 
                    len(entity.get("description", "")) > len(existing.get("description", ""))
                ):
                    existing["description"] = entity.get("description")
                
                # 合并置信度（取更高的）
                default_confidence = settings.KG_ENTITY_DEFAULT_CONFIDENCE
                existing["confidence"] = max(
                    existing.get("confidence", default_confidence),
                    entity.get("confidence", default_confidence)
                )
            else:
                # 检查别名是否匹配已有实体
                matched_key = None
                for alias in entity.get("aliases", []):
                    alias_lower = alias.lower()
                    if alias_lower in alias_map:
                        matched_key = alias_map[alias_lower]
                        break
                
                # 也检查名称本身是否匹配别名
                if not matched_key and name.lower() in alias_map:
                    matched_key = alias_map[name.lower()]
                
                if matched_key and matched_key in entity_map:
                    # 合并到已有实体
                    existing = entity_map[matched_key]
                    existing_aliases = set(existing.get("aliases", []))
                    new_aliases = {name} | set(entity.get("aliases", []))
                    existing["aliases"] = list(existing_aliases | new_aliases)
                    
                    # 更新别名映射
                    for alias in existing["aliases"]:
                        alias_map[alias.lower()] = matched_key
                    
                    # 合并描述和置信度
                    if entity.get("description") and (
                        not existing.get("description") or 
                        len(entity.get("description", "")) > len(existing.get("description", ""))
                    ):
                        existing["description"] = entity.get("description")
                    default_confidence = settings.KG_ENTITY_DEFAULT_CONFIDENCE
                    existing["confidence"] = max(
                        existing.get("confidence", default_confidence),
                        entity.get("confidence", default_confidence)
                    )
                else:
                    # 新实体
                    entity_map[key] = entity.copy()
                    # 添加别名映射
                    alias_map[name.lower()] = key
                    for alias in entity.get("aliases", []):
                        alias_map[alias.lower()] = key
        
        return list(entity_map.values())
    
    def _merge_and_detect_cross_chunk_relationships(
        self,
        entities: List[Dict],
        relationships: List[Dict],
        chunk_results: List[Dict],
        full_document: str
    ) -> Dict[str, Any]:
        """
        合并结果并检测跨块关系
        
        Args:
            entities: 所有实体
            relationships: 所有关系
            chunk_results: 每个块的提取结果（包含chunk_info）
            full_document: 完整文档内容
        """
        # 1. 实体去重和合并（改进版）
        merged_entities = self._merge_entities_with_aliases(entities)
        
        # 2. 关系去重
        unique_relationships = {}
        for rel in relationships:
            key = (
                rel.get("source"), 
                rel.get("target"), 
                rel.get("relation_type")
            )
            if key not in unique_relationships:
                unique_relationships[key] = rel
        unique_relationships = list(unique_relationships.values())
        
        # 3. 检测跨块关系（如果启用）
        cross_chunk_relationships = []
        if self.cross_chunk_enabled:
            cross_chunk_relationships = self._detect_cross_chunk_relationships(
                merged_entities,
                unique_relationships,
                chunk_results,
                full_document
            )
        
        # 4. 合并关系
        all_relationships = unique_relationships + cross_chunk_relationships
        
        return {
            "entities": merged_entities,
            "relationships": all_relationships
        }
    
    def _detect_cross_chunk_relationships(
        self,
        entities: List[Dict],
        existing_relationships: List[Dict],
        chunk_results: List[Dict],
        full_document: str
    ) -> List[Dict]:
        """
        检测跨块关系
        
        策略：
        1. 找出出现在多个块中的实体对
        2. 检查这些实体对在完整文档中是否有关联
        3. 如果有关联，提取关系
        """
        cross_chunk_relationships = []
        
        # 构建实体名称到实体的映射
        entity_name_map = {e.get("name"): e for e in entities}
        
        # 找出出现在多个块中的实体
        entity_chunks = {}  # entity_name -> [chunk_indices]
        for chunk_result in chunk_results:
            chunk_info = chunk_result.get("chunk_info", {})
            chunk_index = chunk_info.get("chunk_index", -1)
            for entity in chunk_result.get("entities", []):
                entity_name = entity.get("name")
                if entity_name:
                    if entity_name not in entity_chunks:
                        entity_chunks[entity_name] = []
                    entity_chunks[entity_name].append(chunk_index)
        
        # 找出出现在不同块中的实体对
        multi_chunk_entities = {
            name: chunks 
            for name, chunks in entity_chunks.items() 
            if len(set(chunks)) > 1
        }
        
        # 检查这些实体对是否已有关系
        existing_rel_keys = {
            (rel.get("source"), rel.get("target"))
            for rel in existing_relationships
        }
        
        # 对于出现在不同块中的实体对，检查是否可能有关系
        entity_names = list(multi_chunk_entities.keys())
        for i, entity1_name in enumerate(entity_names):
            for entity2_name in entity_names[i+1:]:
                # 跳过已有关系
                if (entity1_name, entity2_name) in existing_rel_keys or \
                   (entity2_name, entity1_name) in existing_rel_keys:
                    continue
                
                entity1 = entity_name_map.get(entity1_name)
                entity2 = entity_name_map.get(entity2_name)
                
                if not entity1 or not entity2:
                    continue
                
                # 简化版：如果两个实体都出现在多个块中，且块有重叠，可能有关联
                chunks1 = set(multi_chunk_entities[entity1_name])
                chunks2 = set(multi_chunk_entities[entity2_name])
                
                # 如果实体出现在相邻块中，可能有关联
                if chunks1 & chunks2:  # 有重叠块
                    # 添加一个低置信度的关系，标记为待验证
                    cross_chunk_relationships.append({
                        "source": entity1_name,
                        "target": entity2_name,
                        "relation_type": "related_to",  # 默认关系类型
                        "description": f"{entity1_name}与{entity2_name}相关（跨块检测）",
                        "evidence": "",  # 需要从文档中提取
                        "confidence": settings.KG_PENDING_VERIFICATION_CONFIDENCE,  # 较低置信度，需要人工验证
                        "is_cross_chunk": True  # 标记为跨块关系
                    })
        
        return cross_chunk_relationships
    
    def normalize_entity_name(self, name: str) -> str:
        """实体名称标准化"""
        # 去除前后空格
        name = name.strip()
        # 去除特殊字符（保留中英文、数字、常见符号）
        name = re.sub(r'[^\w\s\u4e00-\u9fff\-_\.]', '', name)
        return name
    
    async def merge_similar_entities(
        self, 
        entities: List[Dict], 
        kb_id: int
    ) -> List[Dict]:
        """合并相似实体
        
        Args:
            entities: 实体列表
            kb_id: 知识库ID
            
        Returns:
            合并后的实体列表
        """
        # TODO: 实现实体合并逻辑
        # 1. 计算名称相似度
        # 2. 计算语义相似度
        # 3. 合并相似实体
        return entities

