# LLM实体提取优化方案

> 版本：v1.0  
> 创建日期：2025-12-08  
> 目标：优化LLM实体提取的准确率、性能和成本

---

## 📊 当前实现分析

### 现状

1. **提取方式**：
   - ⚠️ 当前：一次LLM调用同时提取实体和关系
   - ✅ **新方案**：两步提取（先实体，后关系）

2. **Prompt结构**：
   - ✅ 已支持动态获取实体类型（从数据库）
   - ⚠️ Prompt模板是硬编码的
   - ⚠️ 示例较少，可能影响准确率

3. **调用方式**：
   - ⚠️ 长文档分块处理，但**串行执行**（慢）
   - ⚠️ 使用同步`requests`库（阻塞）
   - ⚠️ 没有批量处理机制

4. **缓存机制**：
   - ❌ **完全没有缓存**
   - 相同文档会重复调用LLM

5. **实体类型定义**：
   - ✅ 已支持从数据库动态获取
   - ✅ 支持`prompt_hint`（在metadata中）
   - ⚠️ 但类型定义可能不够详细
   - ⚠️ 缺少行业模板支持

---

## 🎯 优化方案

### 1. 两步提取方案（核心优化）

#### 1.1 设计思路

**方案**：将实体提取和关系提取分离为两步

**优势**：
- ✅ 关系提取更准确（LLM知道有哪些实体）
- ✅ 关系中的source和target一定在实体列表中
- ✅ 避免实体名称不匹配的问题
- ✅ 实体提取和关系提取可以独立优化

**成本**：
- ⚠️ 需要两次LLM调用（成本增加约1倍）
- ✅ 但准确率提升，减少错误修正成本

#### 1.2 第一步：实体提取Prompt

```python
# app/services/entity_extraction_service.py

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
   - 确保实体类型必须是上述定义的类型之一

2. **质量控制**：
   - 避免提取过于宽泛的实体（如"东西"、"方法"）
   - 避免提取重复的实体
   - 置信度要合理：高置信度（>0.9）用于明确的实体，低置信度（<0.7）用于推测的实体

请严格按照以下JSON格式返回结果，不要添加任何其他内容：
{{
    "entities": [
        {{
            "name": "实体名称",
            "type": "实体类型（必须是上述类型之一）",
            "description": "实体描述（简要说明，1-2句话）",
            "aliases": ["别名1", "别名2"],
            "confidence": 0.95
        }}
    ]
}}

## 示例1（技术文档）：
文档内容："Python是一种高级编程语言，由Guido van Rossum在1991年创建。Python广泛应用于Web开发、数据科学和人工智能领域。FastAPI是一个基于Python的现代Web框架，它依赖于Starlette和Pydantic。"
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
            "name": "FastAPI",
            "type": "technology",
            "description": "基于Python的现代Web框架",
            "aliases": [],
            "confidence": 0.95
        }},
        {{
            "name": "Starlette",
            "type": "technology",
            "description": "Web框架",
            "aliases": [],
            "confidence": 0.85
        }},
        {{
            "name": "Pydantic",
            "type": "technology",
            "description": "数据验证库",
            "aliases": [],
            "confidence": 0.85
        }},
        {{
            "name": "Web开发",
            "type": "concept",
            "description": "应用开发领域",
            "aliases": [],
            "confidence": 0.80
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
            "source": "FastAPI",
            "target": "Python",
            "relation_type": "depends_on",
            "description": "FastAPI基于Python",
            "evidence": "FastAPI是一个基于Python的现代Web框架",
            "confidence": 0.90
        }},
        {{
            "source": "FastAPI",
            "target": "Starlette",
            "relation_type": "depends_on",
            "description": "FastAPI依赖于Starlette",
            "evidence": "FastAPI是一个基于Python的现代Web框架，它依赖于Starlette和Pydantic",
            "confidence": 0.92
        }},
        {{
            "source": "FastAPI",
            "target": "Pydantic",
            "relation_type": "depends_on",
            "description": "FastAPI依赖于Pydantic",
            "evidence": "FastAPI是一个基于Python的现代Web框架，它依赖于Starlette和Pydantic",
            "confidence": 0.92
        }}
    ]
}}

## 示例：
文档内容："Python是一种高级编程语言，由Guido van Rossum在1991年创建。"
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
        }}
    ]
}}
"""
```

#### 1.3 第二步：关系提取Prompt

```python
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
   - 置信度要合理：高置信度（>0.9）用于明确的关系，低置信度（<0.7）用于推测的关系

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

# 关系类型定义
RELATIONSHIP_TYPES_SECTION = """
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
```

#### 1.4 两步提取实现

```python
async def extract_entities_and_relationships(
    self,
    document_content: str,
    document_id: int,
    knowledge_base_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    两步提取：先提取实体，再提取关系
    
    流程：
    1. 第一步：提取实体
    2. 第二步：基于实体列表提取关系
    3. 验证关系（确保source和target在实体列表中）
    """
    # 第一步：提取实体
    entity_types_section = await self._get_entity_types_prompt_section(knowledge_base_id)
    entity_prompt = ENTITY_EXTRACTION_PROMPT.format(
        entity_types_section=entity_types_section,
        document_content=document_content
    )
    
    entity_response = await self.ollama_service.generate_text(entity_prompt, format="json")
    entity_result = self._parse_and_validate_json(entity_response)
    entities = entity_result.get("entities", [])
    
    # 如果没有提取到实体，直接返回
    if not entities:
        logger.warning(f"文档 {document_id} 未提取到实体")
        return {"entities": [], "relationships": []}
    
    # 第二步：提取关系
    entities_list = self._format_entities_list(entities)
    relationship_types_section = self._get_relationship_types_section()
    
    relationship_prompt = RELATIONSHIP_EXTRACTION_PROMPT.format(
        entities_list=entities_list,
        relationship_types_section=relationship_types_section,
        document_content=document_content
    )
    
    relationship_response = await self.ollama_service.generate_text(relationship_prompt, format="json")
    relationship_result = self._parse_and_validate_json(relationship_response)
    relationships = relationship_result.get("relationships", [])
    
    # 验证关系：确保source和target都在实体列表中
    entity_names = {e["name"] for e in entities}
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
```

#### 1.5 优化实体类型描述

**优化方案**：在`entity_types`表的`metadata`中添加更详细的描述

```python
# 优化后的metadata结构
{
    "examples": ["张三", "Linus Torvalds"],
    "prompt_hint": "人物（如：张三、Linus Torvalds）",
    "detailed_description": "人物是指具体的个人、角色或用户。包括：真实人物（如科学家、作家）、虚构角色（如小说人物）、用户账号等。",
    "extraction_tips": [
        "识别完整的人名（包括姓和名）",
        "注意区分同名不同人",
        "识别人物的职业、身份等信息"
    ],
    "common_patterns": [
        "人名通常出现在'由...创建'、'...说'等语境中",
        "人物可能以'XX先生'、'XX教授'等形式出现"
    ]
}
```

---

### 2. 批量/异步调用优化

#### 2.1 并发处理文档块

**当前问题**：长文档分块后串行处理，速度慢

**优化方案**：

```python
# app/services/entity_extraction_service.py

import asyncio
from typing import List

async def _extract_from_chunks(
    self, 
    document_content: str, 
    document_id: int,
    knowledge_base_id: Optional[int] = None
) -> Dict[str, Any]:
    """从多个文档块提取实体和关系（并发优化）"""
    chunks = self._split_document_into_chunks(document_content)
    
    # 并发处理所有块
    tasks = [
        self._extract_from_single_chunk(chunk, knowledge_base_id)
        for chunk in chunks
    ]
    
    # 使用asyncio.gather并发执行
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_entities = []
    all_relationships = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"处理文档块 {i+1} 失败: {result}")
            continue
        
        all_entities.extend(result.get("entities", []))
        all_relationships.extend(result.get("relationships", []))
    
    # 合并去重
    return self._merge_extraction_results(all_entities, all_relationships)
```

#### 2.2 异步HTTP调用

**当前问题**：`OllamaService`使用同步`requests`，会阻塞

**优化方案**：

```python
# app/services/ollama_service.py

import httpx  # 使用异步HTTP客户端

async def generate_text(
    self, 
    prompt: str, 
    model: str = settings.OLLAMA_MODEL,
    format: Optional[str] = None,
    timeout: int = 300
) -> str:
    """生成文本（异步优化）"""
    try:
        request_data = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        if format:
            request_data["format"] = format
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=request_data
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
    except Exception as e:
        logger.error(f"Ollama文本生成错误: {e}")
        raise
```

#### 2.3 批量处理多个文档

**优化方案**：添加批量提取接口

```python
async def extract_batch(
    self,
    documents: List[Dict[str, Any]],  # [{"id": 1, "content": "...", "kb_id": 1}, ...]
    max_concurrent: int = 5  # 最大并发数
) -> Dict[int, Dict[str, Any]]:
    """批量提取多个文档的实体
    
    Args:
        documents: 文档列表，每个文档包含id、content、kb_id
        max_concurrent: 最大并发数（避免过载）
    
    Returns:
        {document_id: {"entities": [...], "relationships": [...]}}
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    results = {}
    
    async def extract_one(doc):
        async with semaphore:
            result = await self.extract_with_llm(
                doc["content"],
                doc["id"],
                doc.get("kb_id")
            )
            results[doc["id"]] = result
    
    tasks = [extract_one(doc) for doc in documents]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    return results
```

---

### 3. 添加结果缓存

#### 3.1 基于内容Hash的缓存

**优化方案**：

```python
# app/services/entity_extraction_service.py

import hashlib
import json
from app.core.cache import cache_manager  # 假设有缓存管理器

async def extract_with_llm(
    self, 
    document_content: str, 
    document_id: int,
    knowledge_base_id: Optional[int] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """使用LLM提取实体和关系（带缓存）"""
    
    # 1. 检查缓存
    if use_cache:
        cache_key = self._generate_cache_key(document_content, knowledge_base_id)
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            logger.info(f"使用缓存结果: document_id={document_id}")
            return cached_result
    
    # 2. 执行提取
    if len(document_content) > self.max_chunk_length:
        result = await self._extract_from_chunks(document_content, document_id, knowledge_base_id)
    else:
        result = await self._extract_from_single_chunk(document_content, knowledge_base_id)
    
    # 3. 保存到缓存（TTL: 7天）
    if use_cache:
        await cache_manager.set(cache_key, result, ttl=7*24*3600)
    
    return result

def _generate_cache_key(self, content: str, knowledge_base_id: Optional[int] = None) -> str:
    """生成缓存键"""
    # 使用内容hash + 知识库ID + 实体类型版本
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    # 获取实体类型版本（如果类型定义变化，缓存失效）
    entity_types_version = self._get_entity_types_version(knowledge_base_id)
    
    return f"entity_extraction:{content_hash}:kb_{knowledge_base_id}:v_{entity_types_version}"

def _get_entity_types_version(self, knowledge_base_id: Optional[int] = None) -> str:
    """获取实体类型版本（用于缓存失效）"""
    from app.services.entity_type_service import EntityTypeService
    entity_type_service = EntityTypeService(self.db)
    
    types = entity_type_service.get_all_types(
        is_enabled=True,
        knowledge_base_id=knowledge_base_id
    )
    
    # 使用类型ID和更新时间生成版本号
    version_parts = [f"{t.id}_{t.updated_at}" for t in types]
    version_hash = hashlib.md5("|".join(version_parts).encode()).hexdigest()[:8]
    
    return version_hash
```

#### 3.2 增量提取缓存

**优化方案**：如果文档内容只增加了部分，可以复用之前的提取结果

```python
async def extract_incremental(
    self,
    document_content: str,
    document_id: int,
    knowledge_base_id: Optional[int] = None,
    previous_content: Optional[str] = None
) -> Dict[str, Any]:
    """增量提取：如果文档只增加了部分内容，只提取新增部分"""
    
    if not previous_content:
        # 没有之前的内容，完整提取
        return await self.extract_with_llm(
            document_content, document_id, knowledge_base_id
        )
    
    # 计算新增内容
    if document_content.startswith(previous_content):
        new_content = document_content[len(previous_content):]
    else:
        # 内容变化较大，完整提取
        return await self.extract_with_llm(
            document_content, document_id, knowledge_base_id
        )
    
    # 只提取新增部分
    new_result = await self.extract_with_llm(
        new_content, document_id, knowledge_base_id, use_cache=False
    )
    
    # 获取之前的提取结果（从数据库或缓存）
    previous_result = await self._get_previous_extraction_result(document_id)
    
    # 合并结果
    return self._merge_extraction_results(
        previous_result.get("entities", []) + new_result.get("entities", []),
        previous_result.get("relationships", []) + new_result.get("relationships", [])
    )
```

---

### 4. 行业模板支持

#### 4.1 行业模板设计

**设计思路**：
- 预设多个行业的实体类型模板
- 用户创建知识库时可以选择行业模板
- 模板会预填充该行业常用的实体类型
- 用户可以在模板基础上添加、删除、修改类型

**预设行业模板**：
- **技术文档**：technology、framework、standard、product、concept等
- **医疗健康**：person、organization、disease、drug、treatment等
- **法律**：person、organization、location、law、case等
- **金融**：person、organization、financial_product、market等
- **教育**：person、organization、course、subject等
- **通用**：基础8种类型

**实现方案**：

```python
# app/services/entity_type_service.py

def apply_industry_template(
    self,
    knowledge_base_id: int,
    template_code: str
) -> List[KnowledgeBaseEntityType]:
    """应用行业模板到知识库"""
    template = INDUSTRY_TEMPLATES.get(template_code)
    if not template:
        raise CustomException(
            ErrorCode.BAD_REQUEST,
            f"模板 '{template_code}' 不存在"
        )
    
    entity_type_ids = []
    for type_def in template["entity_types"]:
        # 查找或创建实体类型
        code = type_def["code"]
        entity_type = self.get_type_by_code(code)
        
        if not entity_type:
            # 创建新类型（如果不存在）
            entity_type = self.create_type({
                "code": code,
                "name": type_def["name"],
                "description": type_def.get("description", ""),
                "sort_order": type_def.get("sort_order", 0),
                "is_system": False,
                "is_enabled": True,
                "parent_type_id": type_def.get("parent_type_id")
            })
        
        entity_type_ids.append(entity_type.id)
    
    # 配置知识库的实体类型
    return self.configure_knowledge_base_types(
        knowledge_base_id,
        entity_type_ids
    )
```

### 5. 优化实体类型定义

#### 5.1 增强类型描述

**优化方案**：在数据库中添加更详细的类型描述

```sql
-- 更新entity_types表的metadata字段，添加详细描述
UPDATE `entity_types` SET `metadata` = JSON_SET(
    `metadata`,
    '$.detailed_description', '人物是指具体的个人、角色或用户。包括：真实人物（如科学家、作家）、虚构角色（如小说人物）、用户账号等。',
    '$.extraction_tips', JSON_ARRAY(
        '识别完整的人名（包括姓和名）',
        '注意区分同名不同人',
        '识别人物的职业、身份等信息'
    ),
    '$.common_patterns', JSON_ARRAY(
        '人名通常出现在"由...创建"、"...说"等语境中',
        '人物可能以"XX先生"、"XX教授"等形式出现'
    )
) WHERE `code` = 'person';
```

#### 5.2 优化Prompt中的类型描述

**优化方案**：在`_get_entity_types_prompt_section`中使用更详细的描述

```python
async def _get_entity_types_prompt_section(self, knowledge_base_id: Optional[int] = None) -> str:
    """获取实体类型的Prompt片段（优化版）"""
    from app.services.entity_type_service import EntityTypeService
    entity_type_service = EntityTypeService(self.db)
    
    types = entity_type_service.get_all_types(
        is_enabled=True,
        knowledge_base_id=knowledge_base_id
    )
    
    lines = ["## 实体类型定义："]
    for entity_type in types:
        metadata = entity_type.metadata or {}
        
        # 构建类型描述
        type_desc = f"- {entity_type.code}: {entity_type.name}"
        
        # 添加详细描述
        if metadata.get("detailed_description"):
            type_desc += f"\n  {metadata['detailed_description']}"
        
        # 添加示例
        if metadata.get("examples"):
            examples = ", ".join(metadata["examples"][:3])  # 最多3个示例
            type_desc += f"\n  示例: {examples}"
        
        # 添加提取提示
        if metadata.get("extraction_tips"):
            tips = "\n  ".join([f"  • {tip}" for tip in metadata["extraction_tips"][:2]])  # 最多2个提示
            type_desc += f"\n  提取提示:\n{tips}"
        
        lines.append(type_desc)
    
    return "\n".join(lines)
```

---

## 📋 实施计划

### 阶段一：两步提取实现（1周）

- [ ] 实现第一步：实体提取Prompt
- [ ] 实现第二步：关系提取Prompt
- [ ] 实现两步提取流程
- [ ] 实现关系验证逻辑
- [ ] 测试准确率提升

### 阶段二：性能优化（1周）

- [ ] 实现并发处理文档块
- [ ] 将OllamaService改为异步
- [ ] 实现批量提取接口
- [ ] 测试性能提升

### 阶段三：缓存优化（1周）

- [ ] 实现基于内容Hash的缓存
- [ ] 实现增量提取
- [ ] 测试缓存命中率
- [ ] 优化缓存策略

### 阶段四：类型定义和行业模板优化（1周）

- [ ] 更新数据库中的类型描述
- [ ] 优化Prompt中的类型展示
- [ ] 实现行业模板功能
- [ ] 实现模板应用接口
- [ ] 实现前端模板选择界面
- [ ] 测试准确率提升

---

## 🎯 预期效果

### 准确率提升
- **当前**：约70-80%（一次调用提取实体+关系）
- **优化后**：约85-92%（两步提取，关系提取更准确）
- **提升**：15-22%

### 性能提升
- **当前**：长文档（10块）需要100秒（串行）
- **优化后**：长文档（10块）需要15秒（并发）
- **提升**：约6-7倍

### 成本分析
- **LLM调用次数**：从1次增加到2次（成本增加约1倍）
- **但准确率提升**：减少错误修正成本
- **缓存命中率**：预计30-50%（可以降低部分成本）
- **总体成本**：可能略有增加，但准确率大幅提升

---

## ✅ 检查清单

### 两步提取
- [ ] 第一步实体提取Prompt实现
- [ ] 第二步关系提取Prompt实现
- [ ] 实体列表格式化优化
- [ ] 关系验证逻辑实现
- [ ] 错误处理完善

### 性能优化
- [ ] 并发处理文档块
- [ ] 异步HTTP调用
- [ ] 批量处理接口
- [ ] 性能测试通过

### 缓存优化
- [ ] 基于内容Hash的缓存
- [ ] 增量提取支持
- [ ] 缓存失效策略
- [ ] 缓存命中率监控

### 类型定义和行业模板优化
- [ ] 数据库类型描述更新
- [ ] Prompt中类型展示优化
- [ ] 行业模板功能实现
- [ ] 模板应用流程实现
- [ ] 前端模板选择界面
- [ ] 准确率测试通过

---

**文档版本**：v1.0  
**创建日期**：2025-12-08  
**状态**：优化方案完成
