"""
Entity Extraction Service
实体提取服务
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import json
import re
from app.services.ollama_service import OllamaService
from app.core.logging import logger
from app.config.settings import settings


# 实体提取Prompt模板
ENTITY_EXTRACTION_PROMPT = """
你是一个专业的实体和关系提取专家。请从以下文档内容中提取实体和关系。

## 实体类型定义：
- person: 人物（如：张三、Linus Torvalds）
- location: 地点（如：北京、GitHub）
- concept: 概念（如：异步编程、面向对象）
- product: 产品（如：MySQL、Redis）
- technology: 技术（如：Python、FastAPI）
- event: 事件（如：Python 3.12发布）
- organization: 组织（如：Python Software Foundation）
- other: 其他

## 关系类型定义：
- belongs_to: 属于（如：Python属于编程语言）
- references: 引用（如：文档A引用文档B）
- depends_on: 依赖（如：FastAPI依赖于Starlette）
- compares: 对比（如：异步编程对比同步编程）
- implements: 实现（如：类A实现接口B）
- related_to: 相关（通用相关关系）
- part_of: 部分（如：异步是编程的一部分）
- has_part: 包含（如：Python包含标准库）
- created_by: 创建者（如：Python由Guido van Rossum创建）
- occurs_in: 发生在（如：事件发生在某个地点）
- other: 其他

## 文档内容：
{document_content}

## 要求：
1. 提取所有重要的实体，包括名称、类型、描述和别名
2. 提取实体间的关系，包括关系类型、描述和证据文本
3. 确保实体名称准确，避免重复
4. 关系必须有明确的证据支持

请严格按照以下JSON格式返回结果，不要添加任何其他内容：
{{
    "entities": [
        {{
            "name": "实体名称",
            "type": "实体类型（必须是上述类型之一）",
            "description": "实体描述（简要说明）",
            "aliases": ["别名1", "别名2"],
            "confidence": 0.95
        }}
    ],
    "relationships": [
        {{
            "source": "源实体名称（必须与entities中的name匹配）",
            "target": "目标实体名称（必须与entities中的name匹配）",
            "relation_type": "关系类型（必须是上述类型之一）",
            "description": "关系描述",
            "evidence": "证据文本片段（文档中的原文）",
            "confidence": 0.92
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
            "description": "Python创建者",
            "aliases": [],
            "confidence": 0.95
        }},
        {{
            "name": "Web开发",
            "type": "concept",
            "description": "应用领域",
            "aliases": [],
            "confidence": 0.85
        }}
    ],
    "relationships": [
        {{
            "source": "Python",
            "target": "Guido van Rossum",
            "relation_type": "created_by",
            "description": "Python由Guido van Rossum创建",
            "evidence": "Python是一种高级编程语言，由Guido van Rossum在1991年创建",
            "confidence": 0.95
        }},
        {{
            "source": "Python",
            "target": "Web开发",
            "relation_type": "related_to",
            "description": "Python应用于Web开发",
            "evidence": "Python广泛应用于Web开发、数据科学和人工智能领域",
            "confidence": 0.88
        }}
    ]
}}
"""


class EntityExtractionService:
    """实体提取服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ollama_service = OllamaService(db)
        self.max_chunk_length = 8000  # 根据LLM模型调整
    
    async def extract_with_llm(
        self, 
        document_content: str, 
        document_id: int
    ) -> Dict[str, Any]:
        """使用LLM提取实体和关系
        
        Args:
            document_content: 文档内容
            document_id: 文档ID
            
        Returns:
            包含entities和relationships的字典
        """
        # 长文档处理：如果超过上下文长度，分块处理
        if len(document_content) > self.max_chunk_length:
            return await self._extract_from_chunks(document_content, document_id)
        else:
            return await self._extract_from_single_chunk(document_content)
    
    async def _extract_from_single_chunk(self, content: str) -> Dict[str, Any]:
        """从单个文档块提取实体和关系"""
        prompt = ENTITY_EXTRACTION_PROMPT.format(document_content=content)
        
        try:
            response = await self.ollama_service.generate_text(
                prompt, 
                format="json"
            )
            result = self._parse_and_validate_json(response)
            return result
        except Exception as e:
            logger.error(f"LLM实体提取失败: {e}")
            return {"entities": [], "relationships": []}
    
    async def _extract_from_chunks(
        self, 
        document_content: str, 
        document_id: int
    ) -> Dict[str, Any]:
        """从多个文档块提取实体和关系"""
        chunks = self._split_document_into_chunks(document_content)
        all_entities = []
        all_relationships = []
        
        for chunk in chunks:
            try:
                result = await self._extract_from_single_chunk(chunk)
                all_entities.extend(result.get("entities", []))
                all_relationships.extend(result.get("relationships", []))
            except Exception as e:
                logger.error(f"处理文档块失败: {e}")
                continue
        
        # 合并去重
        return self._merge_extraction_results(all_entities, all_relationships)
    
    def _split_document_into_chunks(
        self, 
        content: str, 
        chunk_size: Optional[int] = None
    ) -> List[str]:
        """将文档分割成块"""
        if chunk_size is None:
            chunk_size = self.max_chunk_length
        
        chunks = []
        current_chunk = ""
        
        # 按段落分割
        paragraphs = content.split("\n\n")
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 2 <= chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _parse_and_validate_json(self, response: str) -> Dict[str, Any]:
        """解析和验证JSON响应"""
        # 尝试提取JSON代码块
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response
        
        try:
            result = json.loads(json_str)
            # 验证格式
            if not isinstance(result, dict):
                raise ValueError("响应不是字典格式")
            if "entities" not in result:
                result["entities"] = []
            if "relationships" not in result:
                result["relationships"] = []
            
            # 验证实体格式
            for entity in result["entities"]:
                if "name" not in entity or "type" not in entity:
                    logger.warning(f"实体格式不完整: {entity}")
                    result["entities"].remove(entity)
            
            # 验证关系格式
            for rel in result["relationships"]:
                if "source" not in rel or "target" not in rel or "relation_type" not in rel:
                    logger.warning(f"关系格式不完整: {rel}")
                    result["relationships"].remove(rel)
            
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 响应内容: {response[:200]}")
            return {"entities": [], "relationships": []}
    
    def _merge_extraction_results(
        self, 
        entities: List[Dict], 
        relationships: List[Dict]
    ) -> Dict[str, Any]:
        """合并提取结果，去重"""
        # 实体去重（基于名称和类型）
        unique_entities = {}
        for entity in entities:
            key = (entity.get("name"), entity.get("type"))
            if key not in unique_entities:
                unique_entities[key] = entity
            else:
                # 合并别名和描述
                existing = unique_entities[key]
                existing_aliases = set(existing.get("aliases", []))
                new_aliases = set(entity.get("aliases", []))
                existing["aliases"] = list(existing_aliases | new_aliases)
                if entity.get("description") and not existing.get("description"):
                    existing["description"] = entity.get("description")
        
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
            "entities": list(unique_entities.values()),
            "relationships": list(unique_relationships.values())
        }
    
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

