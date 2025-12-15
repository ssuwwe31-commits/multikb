# 知识图谱构建与可视化设计文档

> 版本：v0.5（已优化MySQL表设计，明确数据存储策略）  
> 关联文档：`data-isolation-design.md`（数据隔离与权限管理设计文档）  
> 当前阶段：在现有知识库系统基础上，增加**知识图谱构建、存储、查询与可视化**能力

---

## 1. 目标与约束

### 1.1 业务目标

- **自动构建知识图谱**
  - 从文档中自动提取实体（人名、地点、概念、产品、技术等）
  - 自动识别实体间的关系（属于、引用、依赖、对比、实现等）
  - 支持手动创建和编辑实体与关系
- **知识图谱可视化**
  - 交互式知识图谱可视化界面
  - 支持节点搜索、关系路径查询
  - 支持知识图谱的探索和导航
- **增强智能问答**
  - 基于知识图谱的关系查询（如"与Python相关的所有概念"）
  - 通过图谱路径推理回答复杂问题
  - 结合向量检索和图谱查询的混合检索

### 1.2 约束与非目标

**图数据库选型：NebulaGraph**

**选定方案**：使用 **NebulaGraph** 作为知识图谱的存储引擎。

**原因分析**：
1. **性能优势**：路径查询性能优异，支持复杂图算法，原生图查询语言（nGQL）
2. **开源免费**：Apache 2.0 许可证，完全开源，无商业限制，适合 SaaS/多租户场景
3. **分布式架构**：支持水平扩展，适合大规模场景（1万 - 1000万实体）
4. **国产化支持**：中文文档完善，社区活跃
5. **易学易用**：nGQL 查询语言类似 SQL，学习成本低

**数据存储策略**：
- **MySQL**：**主存储**，存储完整的实体和关系数据，用于列表查询、统计查询、关联查询、外键约束和事务保证
- **NebulaGraph**：**图索引**，同步存储图结构数据，用于路径查询、邻居查询、图遍历等图查询
- **OpenSearch**：存储文档内容、向量数据，用于全文检索和向量检索

**数据源角色说明**：
- **MySQL（主存储）**：
  - 实体和关系的完整数据存储
  - ID生成（自增ID，用于生成NebulaGraph VID）
  - 列表查询（分页、排序、筛选）
  - 统计查询（COUNT、GROUP BY）
  - 关联查询（实体-文档关联）
  - 外键约束（保证数据完整性）
  - 事务保证（数据一致性）
- **NebulaGraph（图索引）**：
  - 图结构数据同步存储
  - 路径查询（BFS算法）
  - 邻居查询（1跳、2跳等）
  - 图遍历（复杂图算法）
  - 大规模图查询优化

**数据模型映射**：
- 实体（Entity）→ NebulaGraph 的 Tag（节点类型）
- 关系（Relationship）→ NebulaGraph 的 Edge Type（边类型）
- 知识库隔离 → NebulaGraph 的 Space（图空间）

**其他约束**：
- 不实现复杂的推理引擎，优先支持基础的路径查询和关系查找
- 不实现知识图谱的版本管理，未来可扩展

---

## 2. 数据模型设计

### 2.1 实体表（entities）

```sql
CREATE TABLE `knowledge_graph_entities` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `knowledge_base_id` INT NOT NULL COMMENT '所属知识库ID',
    `user_id` INT NOT NULL COMMENT '创建用户ID',
    `name` VARCHAR(255) NOT NULL COMMENT '实体名称',
    `type` VARCHAR(50) NOT NULL COMMENT '实体类型: person/location/concept/product/technology/event/organization/other',
    `description` TEXT COMMENT '实体描述',
    `aliases` JSON COMMENT '实体别名列表，如: ["Python", "Python语言"]',
    `confidence` FLOAT DEFAULT 0.7 COMMENT '置信度分数（0-1），用于表示实体提取的可信度',
    `metadata` JSON COMMENT '扩展元数据，如: {"source": "doc_123", "extraction_method": "llm"}',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    `nebula_synced` BOOLEAN DEFAULT FALSE COMMENT '是否已同步到NebulaGraph',
    `nebula_synced_at` DATETIME COMMENT '同步到NebulaGraph的时间',
    `nebula_sync_error` TEXT COMMENT '同步错误信息（如果同步失败）',
    INDEX `idx_kb_name` (`knowledge_base_id`, `name`),
    INDEX `idx_type` (`type`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_is_deleted` (`is_deleted`),
    -- 组合索引优化：提高查询性能
    INDEX `idx_kb_deleted` (`knowledge_base_id`, `is_deleted`),
    INDEX `idx_type_deleted` (`type`, `is_deleted`),
    INDEX `idx_nebula_synced` (`nebula_synced`, `updated_at`) COMMENT '用于同步任务查询',
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    -- 唯一键约束：移除 is_deleted，避免逻辑删除后无法创建同名实体
    -- 注意：需要在应用层确保同一知识库下未删除的实体名称+类型唯一
    UNIQUE KEY `uk_kb_name_type` (`knowledge_base_id`, `name`, `type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识图谱实体表（主存储，用于列表查询、统计查询、关联查询）';
```

**MySQL实体表的作用**：
- ✅ **主存储**：存储完整的实体数据（name、type、description等）
- ✅ **ID生成**：自增ID，用于生成NebulaGraph VID（`entity_{id}`）
- ✅ **列表查询**：支持分页、排序、筛选（type、keyword等），性能优异
- ✅ **统计查询**：支持COUNT、GROUP BY等聚合查询
- ✅ **关联查询**：实体-文档关联表依赖实体ID（外键约束）
- ✅ **事务保证**：MySQL事务保证数据一致性
- ✅ **同步跟踪**：`nebula_synced`字段跟踪同步状态，便于同步任务

**实体类型定义**：
- `person`: 人物（如：张三、Linus Torvalds）
- `location`: 地点（如：北京、GitHub）
- `concept`: 概念（如：异步编程、面向对象）
- `product`: 产品（如：MySQL、Redis）
- `technology`: 技术（如：Python、FastAPI）
- `event`: 事件（如：Python 3.12发布）
- `organization`: 组织（如：Python Software Foundation）
- `other`: 其他

### 2.2 关系表（relationships）

```sql
CREATE TABLE `knowledge_graph_relationships` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `knowledge_base_id` INT NOT NULL COMMENT '所属知识库ID',
    `user_id` INT NOT NULL COMMENT '创建用户ID',
    `source_entity_id` INT NOT NULL COMMENT '源实体ID',
    `target_entity_id` INT NOT NULL COMMENT '目标实体ID',
    `relation_type` VARCHAR(50) NOT NULL COMMENT '关系类型: belongs_to/references/depends_on/compares/implements/related_to/part_of/has_part/created_by/occurs_in/other',
    `description` TEXT COMMENT '关系描述',
    `weight` FLOAT DEFAULT 0.5 COMMENT '关系权重（0-1），用于表示关系强度（基于共现频率、语义相似度等计算）',
    `confidence` FLOAT DEFAULT 0.7 COMMENT '置信度分数（0-1），用于表示关系提取的可信度',
    `metadata` JSON COMMENT '扩展元数据，如: {"source": "doc_123", "evidence": "文档片段", "extraction_method": "llm"}',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    `nebula_synced` BOOLEAN DEFAULT FALSE COMMENT '是否已同步到NebulaGraph',
    `nebula_synced_at` DATETIME COMMENT '同步到NebulaGraph的时间',
    `nebula_sync_error` TEXT COMMENT '同步错误信息（如果同步失败）',
    INDEX `idx_kb` (`knowledge_base_id`),
    INDEX `idx_source` (`source_entity_id`),
    INDEX `idx_target` (`target_entity_id`),
    INDEX `idx_relation_type` (`relation_type`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_is_deleted` (`is_deleted`),
    -- 组合索引优化：提高查询性能
    INDEX `idx_kb_deleted` (`knowledge_base_id`, `is_deleted`),
    INDEX `idx_source_deleted` (`source_entity_id`, `is_deleted`),
    INDEX `idx_target_deleted` (`target_entity_id`, `is_deleted`),
    INDEX `idx_nebula_synced` (`nebula_synced`, `updated_at`) COMMENT '用于同步任务查询',
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`source_entity_id`) REFERENCES `knowledge_graph_entities` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`target_entity_id`) REFERENCES `knowledge_graph_entities` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    -- 唯一键约束：移除 is_deleted，避免逻辑删除后无法创建同名关系
    -- 注意：需要在应用层确保未删除的关系唯一
    UNIQUE KEY `uk_source_target_relation` (`source_entity_id`, `target_entity_id`, `relation_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识图谱关系表（主存储，用于列表查询、统计查询）';
```

**MySQL关系表的作用**：
- ✅ **主存储**：存储完整的关系数据（relation_type、description、weight等）
- ✅ **ID生成**：自增ID，用于记录关系
- ✅ **列表查询**：支持分页、排序、筛选（relation_type、source、target等）
- ✅ **统计查询**：支持关系类型分布、关系数量统计等
- ✅ **外键约束**：依赖实体表，保证数据完整性
- ✅ **事务保证**：MySQL事务保证数据一致性
- ✅ **同步跟踪**：`nebula_synced`字段跟踪同步状态，便于同步任务

**关系类型定义**：
- `belongs_to`: 属于（如：Python属于编程语言）
- `references`: 引用（如：文档A引用文档B）
- `depends_on`: 依赖（如：FastAPI依赖于Starlette）
- `compares`: 对比（如：异步编程对比同步编程）
- `implements`: 实现（如：类A实现接口B）
- `related_to`: 相关（通用相关关系）
- `part_of`: 部分（如：异步是编程的一部分）
- `has_part`: 包含（如：Python包含标准库）
- `created_by`: 创建者（如：Python由Guido van Rossum创建）
- `occurs_in`: 发生在（如：事件发生在某个地点）
- `other`: 其他

### 2.3 实体-文档关联表（entity_document_mappings）

```sql
CREATE TABLE `knowledge_graph_entity_documents` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `entity_id` INT NOT NULL COMMENT '实体ID',
    `document_id` INT NOT NULL COMMENT '文档ID',
    `chunk_id` INT COMMENT '文档块ID（可选）',
    `mentions_count` INT DEFAULT 1 COMMENT '提及次数',
    `first_mention_position` INT COMMENT '首次提及位置（字符偏移）',
    `metadata` JSON COMMENT '扩展元数据',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    INDEX `idx_entity` (`entity_id`),
    INDEX `idx_document` (`document_id`),
    INDEX `idx_chunk` (`chunk_id`),
    INDEX `idx_is_deleted` (`is_deleted`),
    FOREIGN KEY (`entity_id`) REFERENCES `knowledge_graph_entities` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`chunk_id`) REFERENCES `document_chunks` (`id`) ON DELETE SET NULL,
    UNIQUE KEY `uk_entity_document_chunk` (`entity_id`, `document_id`, `chunk_id`, `is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实体-文档关联表（记录实体在文档中的提及情况）';
```

**MySQL关联表的作用**：
- ✅ **关联查询**：记录实体在哪些文档中被提及
- ✅ **统计查询**：统计实体提及频率（mentions_count）
- ✅ **反向查询**：从实体查找相关文档，从文档查找相关实体
- ✅ **外键约束**：依赖实体表和文档表，保证数据完整性
- ✅ **事务保证**：MySQL事务保证关联关系的一致性

**作用**：
- 记录实体在哪些文档中被提及
- 支持从实体反向查找相关文档
- 统计实体提及频率，用于排序和推荐

**更新策略**：
- **文档更新时**：重新提取实体，更新关联表（删除旧关联，创建新关联）
- **文档删除时**：使用外键 `ON DELETE CASCADE` 自动删除关联记录
- **实体删除时**：使用外键 `ON DELETE CASCADE` 自动删除关联记录
- **一致性保证**：使用数据库事务确保关联表与实体表的一致性

### 2.4 实体提取任务表（entity_extraction_tasks）

```sql
CREATE TABLE `knowledge_graph_extraction_tasks` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `knowledge_base_id` INT NOT NULL COMMENT '知识库ID',
    `document_id` INT COMMENT '文档ID（可选，为空表示批量提取）',
    `status` VARCHAR(50) DEFAULT 'pending' COMMENT '状态: pending/processing/completed/failed',
    `total_entities` INT DEFAULT 0 COMMENT '提取的实体数量',
    `total_relationships` INT DEFAULT 0 COMMENT '提取的关系数量',
    `error_message` TEXT COMMENT '错误信息',
    `metadata` JSON COMMENT '扩展元数据',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    INDEX `idx_kb` (`knowledge_base_id`),
    INDEX `idx_document` (`document_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_is_deleted` (`is_deleted`),
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实体提取任务表';
```

### 2.5 数据同步策略

**MySQL和NebulaGraph双写策略**：

由于我们使用MySQL存储元数据和关联关系，使用NebulaGraph存储图数据，需要确保数据同步。

**同步策略**：

1. **双写模式**：
   - 实体和关系创建时，同时写入MySQL和NebulaGraph
   - MySQL写入为主，NebulaGraph写入失败不影响MySQL
   - NebulaGraph写入失败时，记录错误日志，后续可重试同步

2. **ID映射规则**：
   - **实体VID生成**：`vid = f"entity_{mysql_id}"`（如：`entity_123`）
   - **关系VID**：关系不需要VID，使用源实体VID和目标实体VID
   - **映射存储**：在NebulaGraph的Tag和Edge中存储`mysql_id`字段，用于反向映射

3. **同步流程**：
   ```python
   # 实体创建流程
   async def create_entity_with_sync(kb_id: int, entity_data: Dict, user_id: int):
       # 1. 写入MySQL（主）
       entity = create_entity_in_mysql(kb_id, entity_data, user_id)
       
       # 2. 同步到NebulaGraph（从）
       try:
           space = f"kb_{kb_id}"
           vid = f"entity_{entity.id}"
           await nebula_storage.create_entity(space, {
               **entity_data,
               "mysql_id": entity.id,  # 保存MySQL ID用于映射
               "id": vid
           })
       except Exception as e:
           logger.error(f"同步实体到NebulaGraph失败: {e}, entity_id={entity.id}")
           # 记录同步失败，但不影响MySQL写入
           # 可以后续通过同步任务重试
   ```

4. **数据一致性保证**：
   - **写入顺序**：先写MySQL，再写NebulaGraph
   - **事务处理**：MySQL使用事务保证一致性，NebulaGraph写入失败不影响MySQL事务
   - **同步检查**：定期检查MySQL和NebulaGraph数据一致性（可选）
   - **同步重试**：NebulaGraph写入失败时，记录到同步队列，定期重试

5. **查询策略**：
   - **列表查询**：从MySQL查询（实体列表、关系列表，支持分页、排序、筛选）
   - **统计查询**：从MySQL查询（实体数量、类型分布、关系分布等）
   - **详情查询**：从MySQL查询（实体详情、关系详情、关联文档等）
   - **图结构查询**：从NebulaGraph查询（路径查询、邻居查询、图遍历等）
   - **混合查询**：先查NebulaGraph获取VID列表，再查MySQL获取详细信息

6. **同步状态跟踪**：
   - **同步字段**：`nebula_synced`（是否已同步）、`nebula_synced_at`（同步时间）、`nebula_sync_error`（同步错误）
   - **同步任务**：定期查询未同步的记录，重试同步到NebulaGraph
   - **同步监控**：监控同步失败率，及时发现同步问题

---

## 3. 功能设计

### 3.1 实体自动提取

#### 3.1.1 触发时机

1. **文档处理完成后自动提取**
   - **集成点**：在 `process_document_task` 完成向量化和索引后，使用 Celery 的 `chain` 或 `link` 功能触发
   - **异步任务**：`extract_entities_from_document_task`
   - **配置开关**：知识库级别配置 `enable_auto_entity_extraction`（默认开启）
   - **错误处理**：实体提取失败不应影响文档处理流程（独立异步任务）
   - **代码示例**：
     ```python
     # 在 process_document_task 的最后阶段
     if kb.enable_auto_entity_extraction:
         extract_entities_from_document_task.apply_async(
             args=[document_id, user_id],
             link_error=handle_extraction_error.s(document_id)
         )
     ```
2. **批量提取**
   - 支持对整个知识库的文档进行批量实体提取
   - 手动触发：`POST /api/v1/knowledge-graph/extract`
3. **增量提取**
   - 文档更新后，重新提取实体和关系
   - 支持增量更新，避免重复提取
   - **更新策略**：删除旧实体关联，创建新实体关联（基于文档ID匹配）

#### 3.1.2 提取方法

**方法：基于LLM的两步提取（推荐）**

**设计思路**：
- **第一步**：使用LLM提取实体（简单、准确）
- **第二步**：基于实体列表，使用LLM提取关系（更准确，因为LLM知道有哪些实体）

**优势**：
- ✅ 关系提取更准确（LLM知道有哪些实体）
- ✅ 关系中的source和target一定在实体列表中
- ✅ 避免实体名称不匹配的问题
- ✅ 实体类型完全可控（用户自定义）

**第一步：实体提取Prompt**

```python
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
```

**第二步：关系提取Prompt**

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
实体列表：["Python", "Guido van Rossum", "Web开发"]
文档内容："Python是一种高级编程语言，由Guido van Rossum在1991年创建。Python广泛应用于Web开发、数据科学和人工智能领域。"
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
```

**提取流程**：

```python
async def extract_entities_and_relationships(
    document_content: str,
    knowledge_base_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    使用LLM两步提取实体和关系
    
    处理流程：
    1. 第一步：提取实体
       - 获取知识库的实体类型定义
       - 调用LLM提取实体
       - 验证和标准化实体
    2. 第二步：提取关系
       - 基于第一步的实体列表
       - 调用LLM提取关系
       - 验证关系（确保source和target在实体列表中）
    3. 返回结果
    """
    # 第一步：提取实体
    entity_types_section = await _get_entity_types_prompt_section(knowledge_base_id)
    entity_prompt = ENTITY_EXTRACTION_PROMPT.format(
        entity_types_section=entity_types_section,
        document_content=document_content
    )
    
    entity_response = await ollama_service.generate_text(entity_prompt, format="json")
    entity_result = parse_and_validate_json(entity_response)
    entities = entity_result.get("entities", [])
    
    # 如果没有提取到实体，直接返回
    if not entities:
        return {"entities": [], "relationships": []}
    
    # 第二步：提取关系
    entities_list = _format_entities_list(entities)
    relationship_types_section = _get_relationship_types_section()
    
    relationship_prompt = RELATIONSHIP_EXTRACTION_PROMPT.format(
        entities_list=entities_list,
        relationship_types_section=relationship_types_section,
        document_content=document_content
    )
    
    relationship_response = await ollama_service.generate_text(relationship_prompt, format="json")
    relationship_result = parse_and_validate_json(relationship_response)
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

def _format_entities_list(entities: List[Dict]) -> str:
    """格式化实体列表为字符串"""
    lines = []
    for entity in entities:
        name = entity.get("name", "")
        entity_type = entity.get("type", "")
        description = entity.get("description", "")
        lines.append(f"- {name}（类型：{entity_type}，描述：{description}）")
    return "\n".join(lines)
```

**置信度评分机制**：

1. **实体置信度**：
   - **LLM返回置信度**：LLM在提取时返回置信度分数（0-1）
   - **证据质量**：基于证据文本长度和来源文档质量
   - **综合置信度**：`confidence = 0.7 * llm_confidence + 0.3 * evidence_quality`

2. **关系置信度**：
   - **LLM返回置信度**：LLM在提取时返回置信度分数（0-1）
   - **证据质量**：基于证据文本的完整性和来源
   - **实体置信度**：基于源实体和目标实体的置信度
   - **综合置信度**：`confidence = 0.5 * llm_confidence + 0.3 * evidence_quality + 0.2 * min(source_conf, target_conf)`

3. **置信度阈值**：
   - **高置信度**：>= 0.8，直接保存
   - **中置信度**：0.6-0.8，保存但标记为待审核
   - **低置信度**：< 0.6，不保存或标记为待人工审核

**格式验证与错误处理**：
- 使用 JSON Schema 验证返回格式
- 如果格式不正确，尝试修复（如：提取JSON代码块）
- 如果修复失败，记录错误并返回空结果（不抛出异常，避免影响文档处理）
- 支持重试机制（最多3次）
- **置信度验证**：如果LLM未返回置信度，使用默认值0.7（中等置信度）

**长文档处理**：
- 如果文档超过LLM上下文限制，进行分块处理
- ✅ **重叠窗口策略**：每个块与前一个块有20%重叠，避免跨块关系丢失
- ✅ **并发处理**：使用 `asyncio.gather` 并发处理多个块，性能提升5倍
- ✅ **跨块关系检测**：检测出现在不同块中的实体对，提取跨块关系
- 最后合并去重

> **详细优化方案**：参见 [long-document-extraction-optimization.md](./long-document-extraction-optimization.md)

**错误处理**：
- 实体提取失败：返回空实体列表，跳过关系提取
- 关系提取失败：返回已提取的实体，关系为空
- 支持重试机制（最多3次）

#### 3.1.3 实体类型管理与行业模板

**实体类型管理**：
- ✅ 支持用户自定义实体类型（增删改查）
- ✅ 支持知识库级别的类型配置
- ✅ 系统类型（`is_system=True`）不可删除，但可编辑名称、描述等
- ✅ 用户自定义类型可完全控制（增删改查）

**行业模板设计**：

**设计思路**：
- 预设多个行业的实体类型模板
- 用户创建知识库时可以选择行业模板
- 模板会预填充该行业常用的实体类型
- 用户可以在模板基础上添加、删除、修改类型

**行业模板示例**：

```python
# 行业模板定义
INDUSTRY_TEMPLATES = {
    "technology": {
        "name": "技术文档",
        "description": "适用于技术文档、开发文档、API文档等",
        "entity_types": [
            {"code": "person", "name": "人物", "sort_order": 1},
            {"code": "technology", "name": "技术", "sort_order": 2},
            {"code": "framework", "name": "框架", "sort_order": 3},
            {"code": "standard", "name": "标准", "sort_order": 4},
            {"code": "product", "name": "产品", "sort_order": 5},
            {"code": "concept", "name": "概念", "sort_order": 6},
            {"code": "method", "name": "方法", "sort_order": 7},
            {"code": "document", "name": "文档", "sort_order": 8},
        ]
    },
    "medical": {
        "name": "医疗健康",
        "description": "适用于医疗文档、健康知识等",
        "entity_types": [
            {"code": "person", "name": "人物", "sort_order": 1},
            {"code": "organization", "name": "组织", "sort_order": 2},
            {"code": "concept", "name": "概念", "sort_order": 3},
            {"code": "method", "name": "方法", "sort_order": 4},
            # 可以添加行业特定类型
            {"code": "disease", "name": "疾病", "parent_type": "concept", "sort_order": 5},
            {"code": "drug", "name": "药物", "parent_type": "product", "sort_order": 6},
            {"code": "treatment", "name": "治疗方法", "parent_type": "method", "sort_order": 7},
        ]
    },
    "legal": {
        "name": "法律",
        "description": "适用于法律文档、法规等",
        "entity_types": [
            {"code": "person", "name": "人物", "sort_order": 1},
            {"code": "organization", "name": "组织", "sort_order": 2},
            {"code": "location", "name": "地点", "sort_order": 3},
            {"code": "event", "name": "事件", "sort_order": 4},
            {"code": "document", "name": "文档", "sort_order": 5},
            # 行业特定类型
            {"code": "law", "name": "法律", "parent_type": "document", "sort_order": 6},
            {"code": "case", "name": "案例", "parent_type": "event", "sort_order": 7},
        ]
    },
    "finance": {
        "name": "金融",
        "description": "适用于金融文档、财务报告等",
        "entity_types": [
            {"code": "person", "name": "人物", "sort_order": 1},
            {"code": "organization", "name": "组织", "sort_order": 2},
            {"code": "product", "name": "产品", "sort_order": 3},
            {"code": "concept", "name": "概念", "sort_order": 4},
            {"code": "event", "name": "事件", "sort_order": 5},
            # 行业特定类型
            {"code": "financial_product", "name": "金融产品", "parent_type": "product", "sort_order": 6},
            {"code": "market", "name": "市场", "parent_type": "concept", "sort_order": 7},
        ]
    },
    "education": {
        "name": "教育",
        "description": "适用于教育文档、课程资料等",
        "entity_types": [
            {"code": "person", "name": "人物", "sort_order": 1},
            {"code": "organization", "name": "组织", "sort_order": 2},
            {"code": "location", "name": "地点", "sort_order": 3},
            {"code": "concept", "name": "概念", "sort_order": 4},
            {"code": "document", "name": "文档", "sort_order": 5},
            # 行业特定类型
            {"code": "course", "name": "课程", "parent_type": "concept", "sort_order": 6},
            {"code": "subject", "name": "学科", "parent_type": "concept", "sort_order": 7},
        ]
    },
    "general": {
        "name": "通用",
        "description": "通用模板，包含基础实体类型",
        "entity_types": [
            {"code": "person", "name": "人物", "sort_order": 1},
            {"code": "location", "name": "地点", "sort_order": 2},
            {"code": "organization", "name": "组织", "sort_order": 3},
            {"code": "concept", "name": "概念", "sort_order": 4},
            {"code": "product", "name": "产品", "sort_order": 5},
            {"code": "technology", "name": "技术", "sort_order": 6},
            {"code": "event", "name": "事件", "sort_order": 7},
            {"code": "other", "name": "其他", "sort_order": 8},
        ]
    }
}
```

**模板应用流程**：

```python
def apply_industry_template(
    knowledge_base_id: int,
    template_code: str
) -> List[KnowledgeBaseEntityType]:
    """
    应用行业模板到知识库
    
    流程：
    1. 获取模板定义
    2. 查找或创建模板中的实体类型
    3. 配置知识库的实体类型（启用模板中的类型）
    4. 返回配置结果
    """
    template = INDUSTRY_TEMPLATES.get(template_code)
    if not template:
        raise ValueError(f"模板 '{template_code}' 不存在")
    
    entity_type_ids = []
    for type_def in template["entity_types"]:
        # 查找或创建实体类型
        entity_type = get_or_create_entity_type(type_def)
        entity_type_ids.append(entity_type.id)
    
    # 配置知识库的实体类型
    return configure_knowledge_base_types(knowledge_base_id, entity_type_ids)
```

**数据库设计**（可选，用于存储模板）：

```sql
-- 行业模板表（可选）
CREATE TABLE IF NOT EXISTS `entity_type_templates` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `code` VARCHAR(50) NOT NULL COMMENT '模板代码（如：technology、medical）',
    `name` VARCHAR(100) NOT NULL COMMENT '模板名称',
    `description` TEXT COMMENT '模板描述',
    `entity_type_configs` JSON COMMENT '实体类型配置列表',
    `is_system` BOOLEAN DEFAULT TRUE COMMENT '是否系统模板',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实体类型模板表';
```

#### 3.1.4 LLM实体提取优化

> **详细优化方案**：参见 [llm-entity-extraction-optimization.md](./llm-entity-extraction-optimization.md)

**优化目标**：
- 提高提取准确率（目标：70-80% → 85-90%）
- 提升处理性能（目标：长文档处理时间减少6-7倍）
- 降低LLM调用成本（目标：通过缓存降低30-50%）

**优化方向**：

1. **两步提取优化**
   - ✅ 第一步：提取实体（简单、专注）
   - ✅ 第二步：基于实体列表提取关系（更准确）
   - ⚠️ 优化两步提取的Prompt
   - ⚠️ 优化实体列表格式化（让LLM更容易理解）

2. **批量/异步调用优化**
   - ⚠️ 并发处理文档块（从串行改为并发）
   - ⚠️ 将OllamaService改为异步（使用httpx替代requests）
   - ⚠️ 两步提取可以并发执行（实体提取和关系提取可以并行，但关系提取依赖实体结果）

3. **结果缓存**
   - ⚠️ 基于内容Hash的缓存（相同内容不重复调用LLM）
   - ⚠️ 实体提取结果缓存（可以单独缓存）
   - ⚠️ 关系提取结果缓存（依赖实体列表）
   - ⚠️ 预期缓存命中率：30-50%

4. **实体类型定义优化**
   - ⚠️ 在数据库中添加详细描述、提取提示、常见模式
   - ⚠️ 在Prompt中展示更详细的类型信息
   - ⚠️ 支持行业模板（预设行业常用类型）

**实施计划**：
- **阶段一**：Prompt优化（1周）- 最快见效
- **阶段二**：缓存机制（1周）- 成本降低明显
- **阶段三**：并发处理（1周）- 性能提升明显
- **阶段四**：类型定义优化（1周）- 准确率提升

**预期效果**：
- **准确率**：70-80% → 85-90%（提升10-15%）
- **性能**：长文档处理时间从100秒 → 15秒（提升6-7倍）
- **成本**：通过缓存降低30-50%

#### 3.1.4 实体合并与去重

**实体名称标准化**：
- 处理别名（如："Python"和"Python语言"合并为一个实体）
- 处理大小写（如："MySQL"和"mysql"合并）
- 处理全称和简称（如："FastAPI"和"Fast API"）
- 去除前后空格和特殊字符

**实体合并策略**：

1. **名称相似度计算**：
   - **编辑距离（Levenshtein距离）**：
     ```python
     def levenshtein_similarity(name1: str, name2: str) -> float:
         max_len = max(len(name1), len(name2))
         if max_len == 0:
             return 1.0
         distance = levenshtein_distance(name1, name2)
         return 1 - (distance / max_len)
     ```
   - **Jaccard相似度**（基于字符集合）：
     ```python
     def jaccard_similarity(name1: str, name2: str) -> float:
         set1 = set(name1.lower())
         set2 = set(name2.lower())
         intersection = len(set1 & set2)
         union = len(set1 | set2)
         return intersection / union if union > 0 else 0.0
     ```
   - **阈值**：名称相似度 > 0.8 时考虑合并

2. **语义相似度计算**：
   - 使用向量相似度（基于OpenSearch的向量检索）
   - 计算实体描述的向量相似度
   - **阈值**：语义相似度 > 0.9 时考虑合并

3. **上下文相似度**：
   - 计算实体出现的文档集合的Jaccard相似度
   - 如果两个实体经常出现在相同文档中，更可能是同一实体

4. **合并流程**：
   - **自动合并**：相似度超过阈值且用户已启用自动合并（`enable_auto_merge`）
   - **手动确认**：相似度在阈值范围内（0.7-0.9），需要用户确认
   - **合并记录**：记录合并历史（保留被合并实体的ID），支持撤销
   - **关系迁移**：合并实体时，将被合并实体的关系迁移到目标实体

5. **合并算法**：
   ```python
   async def merge_similar_entities(entities: List[Dict], kb_id: int) -> List[Dict]:
       merged = []
       processed = set()
       
       for i, entity1 in enumerate(entities):
           if i in processed:
               continue
           
           similar_entities = [entity1]
           for j, entity2 in enumerate(entities[i+1:], start=i+1):
               if j in processed:
                   continue
               
               # 计算相似度
               name_sim = levenshtein_similarity(entity1["name"], entity2["name"])
               semantic_sim = await calculate_semantic_similarity(entity1, entity2)
               
               # 判断是否合并
               if name_sim > 0.8 or semantic_sim > 0.9:
                   similar_entities.append(entity2)
                   processed.add(j)
           
           # 合并相似实体
           if len(similar_entities) > 1:
               merged_entity = merge_entity_list(similar_entities)
               merged.append(merged_entity)
           else:
               merged.append(entity1)
           
           processed.add(i)
       
       return merged
   ```

### 3.2 关系自动提取

#### 3.2.1 关系提取方法

**方法1：基于LLM的关系抽取（推荐）**

- 使用 LLM 分析句子语义，识别实体间关系
- 支持复杂关系（如：多跳关系、隐含关系）

**方法2：基于依存句法分析的关系抽取**

- 使用依存句法分析器（如：spaCy、Stanford NLP）
- 分析句子结构，识别主语-谓语-宾语关系

**方法3：基于模式匹配的关系抽取**

- 定义关系模式（如："X依赖Y"、"X属于Y"）
- 使用正则表达式或模式匹配识别关系

#### 3.2.2 关系权重计算

**权重计算方法**（参考WikiLink的综合权重策略）：

关系权重综合考虑统计权重和语义权重：

```python
def calculate_relationship_weight(
    cooccurrence_freq: int,      # 共现频率：两个实体在同一文档/块中出现的次数
    semantic_sim: float,         # 语义相似度：基于向量相似度（0-1）
    evidence_quality: float,    # 证据质量：基于证据文本长度和来源（0-1）
    user_feedback_score: float = 1.0  # 用户反馈评分（0-1，默认1.0）
) -> float:
    """
    综合计算关系权重
    
    权重计算公式：
    weight = 0.4 * normalize_freq(cooccurrence_freq) +
             0.3 * semantic_sim +
             0.2 * evidence_quality +
             0.1 * user_feedback_score
    
    返回：0-1之间的权重值
    """
    # 归一化共现频率（使用对数缩放，避免高频关系权重过大）
    normalized_freq = min(1.0, math.log10(cooccurrence_freq + 1) / math.log10(100))
    
    # 综合权重计算
    weight = (
        0.4 * normalized_freq +
        0.3 * semantic_sim +
        0.2 * evidence_quality +
        0.1 * user_feedback_score
    )
    
    return min(1.0, max(0.0, weight))
```

**权重更新策略**：
- **初始权重**：基于提取时的共现频率和语义相似度计算
- **动态更新**：基于用户反馈（确认/拒绝）调整权重
- **定期重算**：定期重新计算所有关系的权重（如：每周一次）

**证据质量评估**：
```python
def calculate_evidence_quality(
    evidence_text: str,          # 证据文本
    source_document_quality: float = 1.0  # 来源文档质量（0-1）
) -> float:
    """
    计算证据质量
    
    评估因素：
    1. 证据文本长度（适中最好，太短或太长都降低质量）
    2. 来源文档质量（文档的权威性和完整性）
    3. 证据文本的完整性（是否包含完整的句子）
    """
    text_length = len(evidence_text)
    
    # 文本长度评分（50-200字符最佳）
    if 50 <= text_length <= 200:
        length_score = 1.0
    elif text_length < 50:
        length_score = text_length / 50.0
    else:
        length_score = max(0.5, 1.0 - (text_length - 200) / 200.0)
    
    # 综合质量
    quality = 0.6 * length_score + 0.4 * source_document_quality
    return quality
```

### 3.3 知识图谱查询

#### 3.3.1 基础查询接口

**获取实体列表**
```
GET /api/v1/knowledge-graph/entities
Query Parameters:
  - knowledge_base_id: int (必需)
  - type: string (可选，实体类型)
  - keyword: string (可选，实体名称关键词)
  - page: int = 1
  - size: int = 20

Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      {
        "id": 1,
        "name": "Python",
        "type": "technology",
        "description": "...",
        "aliases": ["Python语言"],
        "related_documents_count": 10,
        "related_entities_count": 5
      }
    ],
    "total": 100
  }
}
```

**获取实体详情**
```
GET /api/v1/knowledge-graph/entities/{entity_id}

Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "entity": {
      "id": 1,
      "name": "Python",
      "type": "technology",
      "description": "...",
      "aliases": ["Python语言"],
      "metadata": {}
    },
    "relationships": [
      {
        "id": 1,
        "target_entity": {
          "id": 2,
          "name": "FastAPI",
          "type": "technology"
        },
        "relation_type": "related_to",
        "description": "...",
        "weight": 0.8
      }
    ],
    "related_documents": [
      {
        "document_id": 1,
        "title": "...",
        "mentions_count": 5
      }
    ]
  }
}
```

**获取关系列表**
```
GET /api/v1/knowledge-graph/relationships
Query Parameters:
  - knowledge_base_id: int (必需)
  - source_entity_id: int (可选)
  - target_entity_id: int (可选)
  - relation_type: string (可选)
  - page: int = 1
  - size: int = 20
```

#### 3.3.2 高级查询接口

**关系路径查询**

**算法说明**：
- **算法选择**：使用 BFS（广度优先搜索）算法查找路径
- **性能优化**：限制最大跳数（默认3跳），避免深度搜索
- **循环检测**：记录已访问的节点，避免重复访问
- **路径排序**：按路径长度和总权重排序，返回最短路径

**实现示例**：
```python
async def find_paths(
    source_entity_id: int,
    target_entity_id: int,
    max_hops: int = 3,
    relation_types: Optional[List[str]] = None
) -> List[Dict]:
    """
    查找两个实体间的路径
    
    算法：BFS（广度优先搜索）
    1. 从源实体开始，逐层扩展
    2. 记录访问路径和已访问节点
    3. 找到目标实体时，记录路径
    4. 限制最大跳数，避免深度搜索
    """
    from collections import deque
    
    queue = deque([(source_entity_id, [source_entity_id], [])])
    visited = {(source_entity_id,): True}  # 使用路径元组避免循环
    paths = []
    
    while queue:
        current_id, path, relationships = queue.popleft()
        
        if len(path) > max_hops:
            continue
        
        if current_id == target_entity_id and len(path) > 1:
            paths.append({
                "entities": path,
                "relationships": relationships,
                "path_length": len(path) - 1,
                "total_weight": sum(r.get("weight", 1.0) for r in relationships)
            })
            continue
        
        # 获取当前实体的邻居
        neighbors = await get_entity_neighbors(
            current_id,
            relation_type=None if not relation_types else relation_types[0],
            max_depth=1
        )
        
        for neighbor in neighbors:
            neighbor_id = neighbor["entity_id"]
            relation = neighbor["relationship"]
            
            # 避免循环：检查是否已访问过该节点（在当前路径中）
            if neighbor_id in path:
                continue
            
            new_path = path + [neighbor_id]
            new_path_key = tuple(new_path)
            
            if new_path_key not in visited:
                visited[new_path_key] = True
                new_relationships = relationships + [relation]
                queue.append((neighbor_id, new_path, new_relationships))
    
    # 按路径长度和权重排序
    paths.sort(key=lambda x: (x["path_length"], -x["total_weight"]))
    return paths[:10]  # 返回前10条路径
```

**API接口**：
```
POST /api/v1/knowledge-graph/paths
Request Body:
{
  "source_entity_id": 1,
  "target_entity_id": 5,
  "max_hops": 3,  // 最大跳数（默认3）
  "relation_types": ["related_to", "depends_on"]  // 可选，限制关系类型
}

Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "paths": [
      {
        "entities": [1, 2, 3, 5],
        "relationships": [
          {"source": 1, "target": 2, "type": "related_to"},
          {"source": 2, "target": 3, "type": "depends_on"},
          {"source": 3, "target": 5, "type": "related_to"}
        ],
        "total_weight": 2.1,
        "path_length": 3
      }
    ]
  }
}
```

**实体邻居查询**
```
GET /api/v1/knowledge-graph/entities/{entity_id}/neighbors
Query Parameters:
  - relation_type: string (可选)
  - max_depth: int = 1 (最大深度)
  - limit: int = 50 (返回数量限制)
```

**实体搜索（模糊匹配）**
```
GET /api/v1/knowledge-graph/search
Query Parameters:
  - q: string (搜索关键词)
  - knowledge_base_id: int (可选)
  - type: string (可选，实体类型)

Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "entities": [
      {
        "id": 1,
        "name": "Python",
        "type": "technology",
        "score": 0.95,  // 匹配得分
        "matched_field": "name"  // 匹配的字段
      }
    ]
  }
}
```

### 3.4 知识图谱可视化

#### 3.4.1 前端可视化组件

**技术选型**：
- **D3.js**：强大的数据可视化库，灵活性高
- **vis.js / vis-network**：专门的网络图可视化库，性能好
- **Cytoscape.js**：专业的图可视化库，功能丰富
- **ECharts Graph**：基于 ECharts 的图可视化（如果前端已使用 ECharts）

**推荐**：使用 **vis-network** 或 **Cytoscape.js**，专门用于网络图可视化，性能好，交互丰富。

#### 3.4.2 可视化功能

1. **节点展示**
   - 节点大小：根据实体关联度或文档数量
   - 节点颜色：根据实体类型
   - 节点标签：实体名称
   - 节点详情：悬停显示实体描述

2. **边（关系）展示**
   - 边的颜色：根据关系类型
   - 边的粗细：根据关系权重
   - 边的标签：显示关系类型
   - 有向边：显示关系方向

3. **交互功能**
   - 节点拖拽：调整节点位置
   - 节点点击：显示实体详情面板
   - 边点击：显示关系详情
   - 缩放和平移：查看大图谱
   - 搜索定位：搜索实体并高亮
   - 路径高亮：高亮两个实体间的路径

4. **布局算法**
   - **力导向布局**（Force-Directed）：节点自然分布，关系清晰
   - **层次布局**（Hierarchical）：按实体类型或关系层级布局
   - **圆形布局**（Circular）：节点均匀分布在圆周上

#### 3.4.3 可视化API设计

**获取知识图谱数据（用于可视化）**
```
GET /api/v1/knowledge-graph/visualization
Query Parameters:
  - knowledge_base_id: int (必需)
  - entity_ids: int[] (可选，指定要展示的实体ID列表)
  - relation_types: string[] (可选，限制关系类型)
  - max_nodes: int = 100 (最大节点数，避免渲染过慢)
  - layout: string = "force" (布局类型: force/hierarchical/circular)

Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "nodes": [
      {
        "id": 1,
        "label": "Python",
        "type": "technology",
        "group": "technology",  // 用于分组着色
        "value": 10,  // 节点大小
        "title": "实体描述..."  // 悬停提示
      }
    ],
    "edges": [
      {
        "from": 1,
        "to": 2,
        "label": "related_to",
        "value": 0.8,  // 边的粗细
        "title": "关系描述..."  // 悬停提示
      }
    ],
    "layout": "force"
  }
}
```

### 3.5 知识图谱增强智能问答

#### 3.5.1 混合检索策略

**策略1：向量检索 + 图谱查询**

**详细流程**：

1. **用户提问 → 意图识别**
   ```python
   async def identify_query_intent(question: str) -> str:
       """识别查询意图：relation_query（关系查询）或 content_query（内容查询）"""
       prompt = f"""
       判断以下问题属于哪种类型：
       1. relation_query: 询问实体间的关系（如："与Python相关的技术有哪些？"）
       2. content_query: 询问具体内容（如："Python异步编程的使用方法"）
       
       问题：{question}
       
       只返回类型名称（relation_query 或 content_query）。
       """
       result = await ollama_service.generate_text(prompt)
       return result.strip().lower()
   ```

2. **关系查询处理流程**（如："与Python相关的技术"）：
   - **步骤1**：从问题中提取实体名称（使用NER或LLM）
   - **步骤2**：在知识图谱中查找实体
   - **步骤3**：查询实体的邻居节点（相关实体）
   - **步骤4**：从相关实体关联的文档中检索（使用向量检索）
   - **步骤5**：合并图谱查询结果和向量检索结果
   - **步骤6**：生成答案，包含实体关系和文档片段

3. **内容查询处理流程**（如："Python异步编程的使用方法"）：
   - **步骤1**：使用向量检索找到相关文档
   - **步骤2**：从检索结果中提取实体（使用知识图谱）
   - **步骤3**：基于实体扩展检索范围（查询实体的邻居节点）
   - **步骤4**：合并原始检索结果和扩展结果
   - **步骤5**：生成答案，包含文档片段和实体信息

**结果合并策略**：
- **图谱查询结果**：实体列表、关系列表、路径信息
- **向量检索结果**：文档片段列表、相似度分数
- **合并方式**：
  1. 优先展示图谱结果（实体和关系）
  2. 然后展示相关文档片段（按相似度排序）
  3. 在答案中明确标注数据来源（图谱 vs 文档）

**策略2：图谱路径推理**

```
用户问题："FastAPI和Django的关系是什么？"

处理流程：
1. 识别实体：FastAPI、Django
2. 查询知识图谱：查找两个实体间的关系路径
3. 如果存在直接关系：返回关系描述
4. 如果存在间接关系：返回路径并解释
5. 如果不存在关系：基于文档内容生成答案
```

#### 3.5.2 问答API扩展

**基于图谱的问答接口**
```
POST /api/v1/qa/graph-enhanced
Request Body:
{
  "question": "与Python相关的技术有哪些？",
  "knowledge_base_id": 1,
  "use_graph": true  // 是否使用知识图谱
}

Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "answer": "...",
    "entities": [
      {"id": 1, "name": "Python", "type": "technology"},
      {"id": 2, "name": "FastAPI", "type": "technology"}
    ],
    "relationships": [
      {"source": "Python", "target": "FastAPI", "type": "related_to"}
    ],
    "source_documents": [...],
    "reasoning_path": "通过知识图谱查询Python实体的邻居节点，找到相关技术..."
  }
}
```

---

## 4. 后端实现设计

### 4.1 服务层设计

#### 4.1.1 KnowledgeGraphService

```python
class KnowledgeGraphService:
    """知识图谱服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ollama_service = OllamaService(db)
    
    # 实体相关
    async def extract_entities_from_document(
        self, document_id: int, user_id: int
    ) -> ExtractionTask:
        """从文档中提取实体和关系"""
    
    async def create_entity(
        self, kb_id: int, entity_data: Dict, user_id: int
    ) -> Entity:
        """创建实体"""
    
    async def update_entity(
        self, entity_id: int, entity_data: Dict, user_id: int
    ) -> Entity:
        """更新实体"""
    
    async def delete_entity(self, entity_id: int, user_id: int) -> bool:
        """删除实体"""
    
    async def get_entities(
        self, kb_id: int, filters: Dict, page: int, size: int
    ) -> Dict:
        """获取实体列表"""
    
    async def get_entity_detail(self, entity_id: int) -> Dict:
        """获取实体详情（包含关系和文档）"""
    
    # 关系相关
    async def create_relationship(
        self, kb_id: int, relationship_data: Dict, user_id: int
    ) -> Relationship:
        """创建关系"""
    
    async def update_relationship(
        self, relationship_id: int, relationship_data: Dict, user_id: int
    ) -> Relationship:
        """更新关系"""
    
    async def delete_relationship(
        self, relationship_id: int, user_id: int
    ) -> bool:
        """删除关系"""
    
    async def get_relationships(
        self, kb_id: int, filters: Dict, page: int, size: int
    ) -> Dict:
        """获取关系列表"""
    
    # 查询相关
    async def find_paths(
        self, kb_id: int, source_entity_id: int, target_entity_id: int, 
        max_hops: int = 3
    ) -> List[Dict]:
        """查找两个实体间的路径
        
        实现逻辑：
        1. 将MySQL entity_id转换为NebulaGraph VID
        2. 调用NebulaGraph的路径查询
        3. 将结果中的VID转换回MySQL entity_id
        4. 从MySQL查询实体详细信息
        """
    
    async def get_entity_neighbors(
        self, kb_id: int, entity_id: int, relation_type: Optional[str] = None,
        max_depth: int = 1
    ) -> Dict:
        """获取实体邻居
        
        实现逻辑：
        1. 将MySQL entity_id转换为NebulaGraph VID
        2. 调用NebulaGraph的邻居查询
        3. 将结果中的VID转换回MySQL entity_id
        4. 从MySQL查询实体详细信息
        """
    
    # ID转换辅助方法
    def entity_id_to_vid(self, entity_id: int) -> str:
        """将MySQL实体ID转换为NebulaGraph VID"""
        return f"entity_{entity_id}"
    
    def vid_to_entity_id(self, vid: str) -> int:
        """将NebulaGraph VID转换为MySQL实体ID"""
        if vid.startswith("entity_"):
            return int(vid.replace("entity_", ""))
        raise ValueError(f"无效的VID格式: {vid}")
    
    async def search_entities(
        self, query: str, kb_id: Optional[int] = None
    ) -> List[Dict]:
        """搜索实体"""
    
    # 可视化相关
    async def get_visualization_data(
        self, kb_id: int, filters: Dict, layout: str = "force"
    ) -> Dict:
        """获取可视化数据"""
    
    # 合并与去重
    async def merge_entities(
        self, entity_ids: List[int], target_entity_id: int, user_id: int
    ) -> Entity:
        """合并实体"""
```

#### 4.1.2 EntityExtractionService

```python
class EntityExtractionService:
    """实体提取服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ollama_service = OllamaService(db)
    
    async def extract_with_llm(
        self, document_content: str, document_id: int
    ) -> Dict[str, Any]:
        """使用LLM提取实体和关系"""
    
    async def extract_with_ner(
        self, document_content: str, document_id: int
    ) -> Dict[str, Any]:
        """使用NER模型提取实体"""
    
    async def normalize_entity_name(self, name: str) -> str:
        """实体名称标准化"""
    
    async def merge_similar_entities(
        self, entities: List[Dict], kb_id: int
    ) -> List[Dict]:
        """合并相似实体"""
```

### 4.2 任务层设计

#### 4.2.1 Celery任务

```python
@celery_app.task(
    bind=True,
    max_retries=3,  # 最大重试次数
    default_retry_delay=60,  # 默认重试延迟（秒）
    retry_backoff=True,  # 指数退避
    retry_backoff_max=600,  # 最大退避时间（10分钟）
    retry_jitter=True  # 添加随机抖动
)
def extract_entities_from_document_task(
    self, document_id: int, user_id: int
):
    """从文档中提取实体的异步任务
    
    错误处理策略：
    1. LLM调用失败：重试（最多3次）
    2. JSON解析失败：记录错误，不重试（数据质量问题）
    3. 数据库写入失败：重试（最多3次）
    4. 部分成功：保存已提取的实体，标记任务为"部分成功"
    """
    db = SessionLocal()
    extraction_task = None
    try:
        # 1. 创建提取任务记录
        extraction_task = create_extraction_task(db, document_id, user_id)
        
        # 2. 获取文档内容
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"文档 {document_id} 不存在")
        
        # 3. 获取文档内容（从MinIO或OpenSearch）
        document_content = await get_document_content(document)
        
        # 4. 调用 EntityExtractionService 提取实体
        extraction_service = EntityExtractionService(db)
        result = await extraction_service.extract_with_llm(document_content, document_id)
        
        # 5. 保存实体和关系到MySQL和NebulaGraph（双写）
        nebula_storage = NebulaGraphStorage(connection_pool)
        space = f"kb_{document.knowledge_base_id}"
        
        with db.begin():
            entities = result.get("entities", [])
            relationships = result.get("relationships", [])
            
            saved_entities = []
            entity_vid_map = {}  # MySQL ID -> NebulaGraph VID映射
            
            # 5.1 保存实体到MySQL
            for entity_data in entities:
                entity = create_or_update_entity(db, entity_data, document.knowledge_base_id, user_id)
                saved_entities.append(entity)
            
            # 5.2 同步实体到NebulaGraph
            for entity in saved_entities:
                try:
                    vid = f"entity_{entity.id}"
                    entity_vid_map[entity.id] = vid
                    await nebula_storage.create_entity(space, {
                        "name": entity.name,
                        "type": entity.type,
                        "description": entity.description or "",
                        "aliases": json.dumps(entity.aliases or []),
                        "confidence": entity.confidence,
                        "metadata": json.dumps(entity.metadata or {}),
                        "mysql_id": entity.id,
                        "user_id": entity.user_id,
                        "id": vid
                    })
                    # 更新同步状态
                    entity.nebula_synced = True
                    entity.nebula_synced_at = datetime.now()
                    entity.nebula_sync_error = None
                except Exception as e:
                    logger.error(f"同步实体到NebulaGraph失败: {e}, entity_id={entity.id}")
                    # 记录同步失败状态
                    entity.nebula_synced = False
                    entity.nebula_sync_error = str(e)
                    # 记录错误但不影响MySQL写入，后续可重试同步
            
            # 5.3 保存关系到MySQL
            saved_relationships = []
            for rel_data in relationships:
                relationship = create_or_update_relationship(
                    db, rel_data, saved_entities, document.knowledge_base_id, user_id
                )
                saved_relationships.append(relationship)
            
            # 5.4 同步关系到NebulaGraph
            for relationship in saved_relationships:
                try:
                    source_vid = entity_vid_map.get(relationship.source_entity_id)
                    target_vid = entity_vid_map.get(relationship.target_entity_id)
                    if source_vid and target_vid:
                        await nebula_storage.create_relationship(space, source_vid, target_vid, {
                            "relation_type": relationship.relation_type,
                            "description": relationship.description or "",
                            "weight": relationship.weight,
                            "confidence": relationship.confidence,
                            "metadata": json.dumps(relationship.metadata or {}),
                            "mysql_id": relationship.id,
                            "user_id": relationship.user_id
                        })
                        # 更新同步状态
                        relationship.nebula_synced = True
                        relationship.nebula_synced_at = datetime.now()
                        relationship.nebula_sync_error = None
                except Exception as e:
                    logger.error(f"同步关系到NebulaGraph失败: {e}, relationship_id={relationship.id}")
                    # 记录同步失败状态
                    relationship.nebula_synced = False
                    relationship.nebula_sync_error = str(e)
                    # 记录错误但不影响MySQL写入，后续可重试同步
            
            # 6. 更新实体-文档关联表
            update_entity_document_mappings(db, saved_entities, document_id)
            
            # 7. 更新提取任务状态
            extraction_task.status = "completed"
            extraction_task.total_entities = len(saved_entities)
            extraction_task.total_relationships = len(saved_relationships)
            extraction_task.completed_at = datetime.now()
            db.commit()
        
        return {
            "status": "success",
            "entities_count": len(saved_entities),
            "relationships_count": len(saved_relationships)
        }
        
    except Exception as exc:
        # 错误处理
        db.rollback()
        
        # 更新任务状态
        if extraction_task:
            extraction_task.status = "failed"
            extraction_task.error_message = str(exc)
            extraction_task.completed_at = datetime.now()
            db.commit()
        
        # 判断是否需要重试
        if isinstance(exc, (ConnectionError, TimeoutError)):
            # 网络错误，重试
            raise self.retry(exc=exc)
        elif isinstance(exc, ValueError):
            # 数据错误，不重试
            logger.error(f"实体提取失败（数据错误）: {exc}")
            return {"status": "failed", "error": str(exc)}
        else:
            # 其他错误，重试
            logger.error(f"实体提取失败: {exc}", exc_info=True)
            raise self.retry(exc=exc)
    finally:
        db.close()
```

### 4.3 API层设计

#### 4.3.1 实体相关接口

**单个实体操作**：
```
POST /api/v1/knowledge-graph/entities
  - 权限要求：kg:edit
  - 权限检查：确保用户对 knowledge_base_id 有编辑权限
  - Request Body: {knowledge_base_id, name, type, description, aliases, metadata}

GET /api/v1/knowledge-graph/entities
  - 权限要求：kg:view
  - 权限检查：确保用户对 knowledge_base_id 有查看权限
  - Query Parameters: knowledge_base_id, type, keyword, page, size

GET /api/v1/knowledge-graph/entities/{entity_id}
  - 权限要求：kg:view
  - 权限检查：确保用户对实体所属知识库有查看权限

PUT /api/v1/knowledge-graph/entities/{entity_id}
  - 权限要求：kg:edit
  - 权限检查：确保用户对实体所属知识库有编辑权限

DELETE /api/v1/knowledge-graph/entities/{entity_id}
  - 权限要求：kg:delete
  - 权限检查：确保用户对实体所属知识库有删除权限

POST /api/v1/knowledge-graph/entities/merge
  - 权限要求：kg:edit
  - 权限检查：确保用户对所有实体所属知识库有编辑权限
```

**批量实体操作**：
```
POST /api/v1/knowledge-graph/entities/batch
  - 权限要求：kg:edit
  - 批量创建实体
  - Request Body: {"entities": [{...}, {...}]}

PUT /api/v1/knowledge-graph/entities/batch
  - 权限要求：kg:edit
  - 批量更新实体
  - Request Body: {"entities": [{"id": 1, ...}, {"id": 2, ...}]}

DELETE /api/v1/knowledge-graph/entities/batch
  - 权限要求：kg:delete
  - 批量删除实体
  - Request Body: {"entity_ids": [1, 2, 3]}
```

#### 4.3.2 关系相关接口

```
POST /api/v1/knowledge-graph/relationships
GET /api/v1/knowledge-graph/relationships
GET /api/v1/knowledge-graph/relationships/{relationship_id}
PUT /api/v1/knowledge-graph/relationships/{relationship_id}
DELETE /api/v1/knowledge-graph/relationships/{relationship_id}
```

#### 4.3.3 查询相关接口

```
POST /api/v1/knowledge-graph/paths
GET /api/v1/knowledge-graph/entities/{entity_id}/neighbors
GET /api/v1/knowledge-graph/search
GET /api/v1/knowledge-graph/visualization
```

#### 4.3.4 提取相关接口

```
POST /api/v1/knowledge-graph/extract
  - 权限要求：kg:extract
  - 批量提取整个知识库的实体
  - Request Body: {knowledge_base_id, document_ids: Optional[List[int]]}

POST /api/v1/knowledge-graph/extract/document/{document_id}
  - 权限要求：kg:extract
  - 提取单个文档的实体
  - 权限检查：确保用户对文档所属知识库有提取权限

GET /api/v1/knowledge-graph/extract/tasks/{task_id}
  - 权限要求：kg:view
  - 查询提取任务状态
```

#### 4.3.5 统计信息接口

```
GET /api/v1/knowledge-graph/stats
  - 权限要求：kg:view
  - 获取知识图谱统计信息
  - Query Parameters: knowledge_base_id (必需)
  
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "total_entities": 150,
    "total_relationships": 320,
    "entity_type_distribution": {
      "technology": 50,
      "concept": 40,
      "product": 30,
      "person": 20,
      "organization": 10
    },
    "relation_type_distribution": {
      "related_to": 150,
      "depends_on": 80,
      "belongs_to": 50,
      "references": 40
    },
    "graph_density": 0.014,  // 图谱密度（实际边数 / 最大可能边数）
    "average_degree": 4.27,  // 平均度数
    "largest_component_size": 120  // 最大连通分量大小
  }
}
```

---

## 5. 前端实现设计

### 5.1 知识图谱可视化页面

**组件位置**：`src/views/KnowledgeGraph/index.vue`

**功能**：
1. **图谱可视化区域**
   - 使用 vis-network 或 Cytoscape.js 渲染知识图谱
   - 支持缩放、平移、拖拽
   - 支持节点和边的交互

2. **工具栏**
   - 搜索框：搜索实体并定位
   - 筛选器：按实体类型、关系类型筛选
   - 布局切换：切换不同的布局算法
   - 导出图片：导出图谱为PNG/SVG

3. **详情面板**
   - 节点详情：显示实体信息、相关文档
   - 关系详情：显示关系信息、证据文本
   - 路径分析：显示两个实体间的路径

4. **操作按钮**
   - 添加实体：手动创建实体
   - 添加关系：手动创建关系
   - 合并实体：合并重复实体
   - 重新提取：触发实体提取任务

### 5.2 实体管理页面

**组件位置**：`src/views/KnowledgeGraph/Entities.vue`

**功能**：
- 实体列表：表格展示实体列表
- 实体筛选：按类型、关键词筛选
- 实体详情：点击查看详情
- 实体编辑：编辑实体信息
- 实体删除：删除实体（级联删除关系）

### 5.3 关系管理页面

**组件位置**：`src/views/KnowledgeGraph/Relationships.vue`

**功能**：
- 关系列表：表格展示关系列表
- 关系筛选：按类型、实体筛选
- 关系编辑：编辑关系信息
- 关系删除：删除关系

---

## 6. 实施步骤

### 阶段一（2-3周）：基础实体与关系管理

1. **数据库设计与迁移**
   - 创建实体表、关系表、关联表
   - 编写数据库迁移脚本

2. **后端基础服务**
   - 实现 `KnowledgeGraphService` 基础方法
   - 实现实体和关系的CRUD接口
   - 实现基础查询接口

3. **前端基础页面**
   - 实现实体管理页面
   - 实现关系管理页面
   - 实现基础的可视化组件

### 阶段二（2-3周）：自动提取与可视化

1. **实体自动提取**
   - 实现 `EntityExtractionService`
   - 实现基于LLM的实体提取
   - 实现实体合并与去重逻辑
   - 实现异步提取任务

2. **知识图谱可视化**
   - 集成 vis-network 或 Cytoscape.js
   - 实现交互式可视化界面
   - 实现路径查询和展示

3. **前端优化**
   - 优化可视化性能
   - 实现高级筛选和搜索
   - 实现实体和关系的批量操作

### 阶段三（1-2周）：高级查询与问答增强

1. **高级查询功能**
   - 实现路径查询算法
   - 实现邻居查询
   - 实现实体搜索

2. **问答增强**
   - 集成知识图谱到问答流程
   - 实现混合检索策略
   - 实现基于图谱的问答接口

3. **优化与测试**
   - 性能优化（大规模图谱查询）
   - 单元测试和集成测试
   - 用户体验优化

---

## 7. 技术依赖

### 后端依赖

- **LLM服务**：Ollama（用于实体和关系提取）
- **可选：NER模型**：spaCy / NLPIR（用于实体识别）
- **图数据库**：NebulaGraph
  - **版本**：3.x 或更高
  - **Python客户端**：nebula3-python
  - **部署**：Docker / Docker Compose / Kubernetes
- **关系数据库**：MySQL（存储元数据、任务状态、提取任务等非图数据）

### 前端依赖

- **图谱可视化库**：
  - `vis-network` 或 `cytoscape.js`
  - `d3.js`（如果需要自定义可视化）
- **图表库**：`echarts`（如果需要统计图表）

---

## 8. 性能考虑

### 8.1 大规模图谱优化

**分页加载策略**：
- **初始加载**：只加载中心节点（如用户搜索的实体）及其1跳邻居
- **按需扩展**：用户点击节点时，加载该节点的邻居（懒加载）
- **限制初始节点数**：默认最多100个节点，避免渲染过慢
- **分页参数**：`max_nodes` 参数控制最大节点数

**性能优化技术**：
- **Web Worker**：使用Web Worker进行图谱布局计算（避免阻塞主线程）
- **虚拟化**：使用虚拟化技术，只渲染可见区域的节点（对于超大规模图谱）
- **Canvas渲染**：对于大规模图谱（> 5000节点），使用Canvas而非SVG（性能更好）
- **数据预处理**：在后端预处理图谱数据（计算布局、筛选节点）
- **CDN缓存**：使用CDN缓存静态图谱数据

**索引优化**：
- 为常用查询字段添加组合索引（已在数据模型设计中添加）
- 使用覆盖索引减少回表查询

**缓存策略**：
- **Redis缓存**：缓存可视化数据和常见查询结果（TTL: 1小时）
- **浏览器缓存**：使用HTTP缓存头，缓存静态图谱数据
- **增量更新**：只更新变化的节点和边，避免全量刷新

### 8.2 提取性能优化

- **批量提取**：批量处理多个文档
- **增量提取**：只处理新增或修改的文档
- **异步任务**：提取任务异步执行，不阻塞主流程

---

## 9. 安全与权限

### 9.1 数据隔离

**数据隔离规则**：
- 实体和关系按知识库隔离（`knowledge_base_id` 字段）
- 只有知识库成员才能查看和编辑知识图谱
- 编辑权限遵循知识库权限矩阵

**权限动作定义**：

在 `ROLE_ACTION_MATRIX` 中添加知识图谱相关权限：

```python
ROLE_ACTION_MATRIX = {
    "owner": [
        # ... 现有权限 ...
        "kg:view",      # 查看知识图谱
        "kg:edit",      # 编辑实体和关系
        "kg:extract",   # 触发实体提取
        "kg:delete",    # 删除实体和关系
    ],
    "admin": [
        # ... 现有权限 ...
        "kg:view",
        "kg:edit",
        "kg:extract",
        "kg:delete",
    ],
    "editor": [
        # ... 现有权限 ...
        "kg:view",
        "kg:edit",      # 允许编辑
        "kg:extract",   # 允许触发提取
    ],
    "viewer": [
        # ... 现有权限 ...
        "kg:view",      # 只能查看
    ],
}
```

**API权限检查**：
- **查看接口**（GET）：需要 `kg:view` 权限
- **创建/更新接口**（POST/PUT）：需要 `kg:edit` 权限
- **删除接口**（DELETE）：需要 `kg:delete` 权限
- **提取接口**（POST /extract）：需要 `kg:extract` 权限

**权限检查实现**：
```python
# 在每个API接口中检查权限
from app.services.permission_service import KnowledgeBasePermissionService

perm = KnowledgeBasePermissionService(db)
perm.ensure_permission(knowledge_base_id, user_id, "kg:view")  # 或其他权限动作
```

### 9.2 操作审计

- 记录实体和关系的创建、修改、删除操作
- 记录实体提取任务的执行情况

---

## 10. NebulaGraph 图数据库集成

### 10.1 NebulaGraph 简介

**选定方案：NebulaGraph**

**基本信息**：
- **许可证**：Apache 2.0 ✅（完全开源，商业友好）
- **类型**：原生分布式图数据库
- **查询语言**：nGQL（NebulaGraph Query Language）
- **GitHub**：https://github.com/vesoft-inc/nebula
- **官方文档**：https://docs.nebula-graph.io/

**核心优势**：
1. ✅ **完全开源**：Apache 2.0 许可证，无任何商业限制，适合 SaaS/多租户场景
2. ✅ **高性能**：原生图数据库，路径查询性能优异
3. ✅ **分布式架构**：支持水平扩展，适合大规模场景
4. ✅ **国产化支持**：中文文档完善，社区活跃
5. ✅ **易学易用**：nGQL 查询语言类似 SQL，学习成本低
6. ✅ **功能完整**：支持复杂图算法、事务、索引等

**适用场景**：
- 中小到大规模图谱（1万 - 1000万实体）
- 复杂路径查询（3+跳）
- 需要图算法支持
- 需要分布式扩展
- SaaS/多租户场景（许可证友好）

### 10.2 NebulaGraph 数据模型设计

**数据模型映射**：

我们的知识图谱数据模型到 NebulaGraph 的映射：

| 我们的模型 | NebulaGraph 模型 | 说明 |
|-----------|-----------------|------|
| **实体（Entity）** | **Tag（节点类型）** | 每个实体类型对应一个 Tag |
| **关系（Relationship）** | **Edge Type（边类型）** | 每个关系类型对应一个 Edge Type |
| **实体属性** | **Tag 属性** | name, type, description, aliases, confidence, metadata, mysql_id 等 |
| **关系属性** | **Edge 属性** | relation_type, description, weight, confidence, metadata, mysql_id 等 |
| **知识库隔离** | **Space（图空间）** | 每个知识库对应一个 Space |
| **实体ID** | **VID（Vertex ID）** | 使用字符串格式：`entity_{mysql_id}`（如：`entity_123`） |
| **ID映射** | **mysql_id字段** | NebulaGraph中存储MySQL ID，用于双向映射 |

**Schema 设计示例**：

```nGQL
-- 创建图空间（对应知识库）
CREATE SPACE knowledge_base_1(partition_num=10, replica_factor=1);

-- 使用图空间
USE knowledge_base_1;

-- 创建实体 Tag（节点类型）
CREATE TAG entity(
    name string,
    type string,
    description string,
    aliases string,  -- JSON字符串
    confidence double,  -- 置信度分数（0-1）
    metadata string,  -- JSON字符串
    mysql_id int,  -- MySQL中的实体ID，用于映射
    user_id int,
    created_at timestamp,
    updated_at timestamp
);

-- 创建关系 Edge Type（边类型）
CREATE EDGE relationship(
    relation_type string,
    description string,
    weight double,
    confidence double,  -- 置信度分数（0-1）
    metadata string,  -- JSON字符串
    mysql_id int,  -- MySQL中的关系ID，用于映射
    user_id int,
    created_at timestamp,
    updated_at timestamp
);

-- 创建索引（提高查询性能）
CREATE TAG INDEX entity_name_index ON entity(name(20));
CREATE TAG INDEX entity_type_index ON entity(type);
CREATE EDGE INDEX relationship_type_index ON relationship(relation_type);
```

**数据隔离策略**：
- **Space 隔离**：每个知识库使用独立的 Space
- **权限控制**：在应用层实现，NebulaGraph 提供用户和角色管理
- **数据查询**：查询时指定 Space，确保数据隔离

### 10.2 NebulaGraph 集成设计

**接口抽象层设计**：

```python
class GraphStorageInterface:
    """图存储接口抽象层"""
    async def create_entity(self, space: str, entity_data: Dict) -> str:
        """创建实体（节点），返回VID"""
        pass
    
    async def create_relationship(
        self, space: str, source_vid: str, target_vid: str, rel_data: Dict
    ) -> bool:
        """创建关系（边）"""
        nGQL = f"""
        USE {space};
        INSERT EDGE relationship(relation_type, description, weight, confidence, metadata, mysql_id, user_id, created_at, updated_at)
        VALUES "{source_vid}" -> "{target_vid}":(
            "{rel_data.get('relation_type', 'related_to')}",
            "{rel_data.get('description', '')}",
            {rel_data.get('weight', 0.5)},
            {rel_data.get('confidence', 0.7)},
            "{json.dumps(rel_data.get('metadata', {}))}",
            {rel_data.get('mysql_id', 0)},
            {rel_data.get('user_id', 0)},
            timestamp(),
            timestamp()
        );
        """
        await self.execute(nGQL)
        return True
    
    async def find_paths(
        self, space: str, source_vid: str, target_vid: str, max_hops: int = 3
    ) -> List[Dict]:
        """查找路径"""
        pass
    
    async def get_entity_neighbors(
        self, space: str, entity_vid: str, relation_type: Optional[str] = None
    ) -> List[Dict]:
        """获取邻居节点"""
        pass
    
    async def search_entities(
        self, space: str, keyword: str, entity_type: Optional[str] = None
    ) -> List[Dict]:
        """搜索实体"""
        pass

class NebulaGraphStorage(GraphStorageInterface):
    """NebulaGraph实现"""
    def __init__(self, connection_pool):
        self.pool = connection_pool
    
    async def create_entity(self, space: str, entity_data: Dict) -> str:
        """使用 nGQL 插入节点"""
        vid = entity_data.get("id") or f"entity_{entity_data.get('mysql_id')}"
        if not vid:
            raise ValueError("必须提供id或mysql_id")
        
        nGQL = f"""
        USE {space};
        INSERT VERTEX entity(name, type, description, aliases, confidence, metadata, mysql_id, user_id, created_at, updated_at)
        VALUES "{vid}":(
            "{entity_data['name']}",
            "{entity_data['type']}",
            "{entity_data.get('description', '')}",
            "{json.dumps(entity_data.get('aliases', []))}",
            {entity_data.get('confidence', 0.7)},
            "{json.dumps(entity_data.get('metadata', {}))}",
            {entity_data.get('mysql_id', 0)},
            {entity_data['user_id']},
            timestamp(),
            timestamp()
        );
        """
        await self.execute(nGQL)
        return vid
    
    async def find_paths(
        self, space: str, source_vid: str, target_vid: str, max_hops: int = 3
    ) -> List[Dict]:
        """使用 nGQL 查找路径"""
        nGQL = f"""
        USE {space};
        FIND SHORTEST PATH FROM "{source_vid}" TO "{target_vid}" 
        OVER relationship 
        UPTO {max_hops} STEPS;
        """
        return await self.execute(nGQL)
```

**Python 客户端**：

使用 `nebula3-python` 客户端库：

```python
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config

# 连接配置
config = Config()
config.max_connection_pool_size = 10

# 创建连接池
connection_pool = ConnectionPool()
connection_pool.init([('127.0.0.1', 9669)], config)

# 获取会话
session = connection_pool.get_session('root', 'password')

# 执行查询
result = session.execute('USE knowledge_base_1; MATCH (v:entity) RETURN v LIMIT 10;')
```

### 10.3 部署与运维

**部署方式**：

1. **Docker 部署**（推荐）：
   ```bash
   docker run -d --name nebula-graph \
     -p 9669:9669 -p 9779:9779 -p 9780:9780 \
     vesoft/nebula-graphd:latest
   ```

2. **Docker Compose 部署**（生产环境）：
   - GraphD（图数据库服务）
   - MetaD（元数据服务）
   - StorageD（存储服务）
   - 支持集群部署

3. **Kubernetes 部署**：
   - 支持 Helm Chart
   - 支持 StatefulSet 部署

**运维要点**：
- **监控**：使用 Prometheus + Grafana 监控
- **备份**：支持数据备份和恢复
- **扩容**：支持水平扩展，添加新节点
- **性能调优**：索引优化、查询优化、分区策略

### 10.4 学习资源

- **官方文档**：https://docs.nebula-graph.io/
- **nGQL 教程**：https://docs.nebula-graph.io/manual-CN/3.ngql-guide/
- **Python 客户端**：https://github.com/vesoft-inc/nebula-python
- **示例代码**：https://github.com/vesoft-inc/nebula-python/tree/master/example

### 10.5 未来扩展

**已实现（v0.3）**：
- ✅ **关系权重计算**：综合统计权重和语义权重的计算方法
- ✅ **置信度评分**：实体和关系的置信度评分机制
- ✅ **Prompt优化**：Few-shot示例和格式验证

**中优先级扩展（建议实现）**：

1. **细粒度实体类型**
   - **目标**：细分概念类型，提高实体分类精度
   - **实现**：将 `concept` 细分为 `concept:programming_paradigm`、`concept:design_pattern`、`concept:algorithm` 等
   - **参考**：AliCG的细粒度概念提取方法
   - **数据库变更**：扩展 `type` 字段支持层级结构（如：`concept:programming_paradigm`）

2. **动态更新机制**
   - **目标**：基于用户反馈动态调整知识图谱
   - **实现**：
     - 用户反馈表：记录用户对实体和关系的确认/拒绝
     - 动态权重调整：基于用户反馈调整实体置信度和关系权重
     - 定期重评估：定期重新评估低置信度实体和关系
   - **参考**：AliCG的动态更新策略
   - **数据库变更**：添加 `user_feedback` 表

3. **本体层设计（模式层）**
   - **目标**：定义知识图谱的模式和约束
   - **实现**：
     - 本体表：定义实体类型、关系类型、属性约束
     - 本体验证：实体和关系创建时验证是否符合本体定义
     - 层次结构：支持实体类型的层次结构（如：`technology` → `programming_language` → `python`）
   - **参考**：其他项目的模式层设计
   - **数据库变更**：添加 `knowledge_graph_ontology` 表

**低优先级扩展（可选实现）**：

1. **长尾概念挖掘**
   - **目标**：识别低频但重要的概念
   - **实现**：使用短语挖掘技术和TF-IDF识别长尾概念
   - **参考**：AliCG的长尾概念挖掘方法

2. **实体表示学习**
   - **目标**：基于图结构学习实体表示
   - **实现**：使用Node2Vec或GraphSAGE学习实体向量，融合文本向量和图向量
   - **参考**：StarGraph的二跳邻居子图方法

3. **社区检测**
   - **目标**：识别知识图谱中的社区结构
   - **实现**：使用社区检测算法（如：Louvain算法）识别实体社区
   - **参考**：GraphRAG的社区检测功能

4. **知识图谱版本管理**
   - **目标**：记录知识图谱的变化历史，支持版本回滚
   - **实现**：版本快照、变更记录、版本对比

5. **知识图谱合并**
   - **目标**：支持跨知识库的知识图谱合并，支持知识图谱的导入导出
   - **实现**：实体对齐、关系合并、冲突解决

---

**文档版本**：v0.5  
**创建日期**：2025-01-28  
**最后更新**：2025-01-28  
**状态**：已优化MySQL表设计，明确数据存储策略，可用于实施

**更新日志**：
- v0.5 (2025-01-28): 
  - 分析MySQL表设计（使用NebulaGraph后）
  - 明确数据存储策略（MySQL主存储 + NebulaGraph图索引）
  - 添加同步状态字段（nebula_synced、nebula_synced_at、nebula_sync_error）
  - 添加同步状态索引（用于同步任务查询）
  - 更新代码示例（补充同步状态更新逻辑）
  - 明确MySQL表的作用（列表查询、统计查询、关联查询、外键约束）
  - 创建MySQL表分析文档（knowledge-graph-mysql-table-analysis.md）
- v0.4 (2025-01-28): 
  - 完整检查设计文档，发现并修复关键问题
  - 补充数据同步策略章节（MySQL和NebulaGraph双写策略）
  - 明确ID映射规则（MySQL INT ID ↔ NebulaGraph VID）
  - 更新NebulaGraph Schema（添加confidence和mysql_id字段）
  - 更新代码示例（补充完整的双写逻辑）
  - 添加ID转换方法（entity_id_to_vid、vid_to_entity_id）
  - 更新查询方法签名（添加kb_id参数，明确ID转换逻辑）
  - 创建完整检查报告（knowledge-graph-design-check-report.md）
- v0.3 (2025-01-28): 
  - 对比分析其他项目实现方案（GraphRAG、AliCG、WikiLink、StarGraph等）
  - 补充关系权重计算方法（综合统计权重和语义权重，参考WikiLink）
  - 添加置信度评分机制（实体和关系的置信度评分）
  - 优化Prompt模板（添加Few-shot示例，参考GraphRAG）
  - 添加证据质量评估方法
  - 更新数据库Schema（添加confidence字段）
  - 创建对比分析文档（knowledge-graph-design-comparison.md）
- v0.2 (2025-01-28): 修复唯一键约束问题、添加组合索引、补充权限设计、完善错误处理、补充Prompt设计、补充实体合并算法、补充路径查询算法、补充可视化性能优化、补充集成点说明、补充问答集成流程、添加批量操作接口

