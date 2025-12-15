# 实体存储策略：多用户、多层级分类场景

## 场景分析

### 问题描述
- **技术实体**有二级分类（如：技术 -> 编程语言 -> Python）
- **多用户**场景，每个用户需求不同
- 需要支持灵活的查询和展示

## 存储策略建议

### 1. 实体类型层级（配置数据）→ **MySQL**

**存储位置**：MySQL `entity_types` 表

**原因**：
- 配置数据，变更频率低
- 需要支持外键关联和事务
- 查询模式：按知识库筛选、按用户权限筛选
- 需要支持层级关系（parent_id）

**建议表结构**：
```sql
CREATE TABLE `entity_types` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `code` VARCHAR(50) NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `parent_id` INT NULL COMMENT '父类型ID（支持层级）',
    `level` INT DEFAULT 1 COMMENT '层级（1=一级，2=二级）',
    `knowledge_base_id` INT NULL COMMENT '所属知识库（NULL=全局类型）',
    `user_id` INT NULL COMMENT '创建用户（NULL=系统类型）',
    -- ... 其他字段
    INDEX `idx_parent` (`parent_id`),
    INDEX `idx_kb_level` (`knowledge_base_id`, `level`)
);
```

**查询场景**：
- ✅ 按知识库获取类型列表（快速）
- ✅ 按层级查询（一级、二级）
- ✅ 按用户权限筛选
- ✅ 统计每个类型的实体数量

---

### 2. 实体实例（数据）→ **MySQL（索引）+ NebulaGraph（完整数据）**

#### MySQL 存储（索引层）

**存储字段**：
- `id`, `knowledge_base_id`, `user_id`（外键关联）
- `name`, `type`, `description`, `aliases`（基础信息）
- `confidence`（排序筛选）
- `parent_entity_id`（层级关系，可选）

**用途**：
- ✅ **快速列表查询**：按知识库、类型、用户筛选
- ✅ **统计聚合**：每个类型的实体数量
- ✅ **层级查询**：查询父实体下的所有子实体
- ✅ **权限控制**：基于 knowledge_base_id 和 user_id

**查询示例**：
```sql
-- 查询某个知识库下"技术"类型的所有实体
SELECT * FROM knowledge_graph_entities 
WHERE knowledge_base_id = 1 
  AND type = 'technology' 
  AND is_deleted = FALSE;

-- 查询某个实体的所有子实体（二级分类）
SELECT * FROM knowledge_graph_entities 
WHERE parent_entity_id = 123 
  AND is_deleted = FALSE;
```

#### NebulaGraph 存储（完整数据层）

**存储字段**：
- 完整实体数据（name, type, description, aliases, metadata）
- 关系网络（实体间的关系）
- 层级关系（通过关系边表示）

**用途**：
- ✅ **图查询**：查询实体的所有关联实体
- ✅ **路径查询**：查找两个实体之间的路径
- ✅ **层级遍历**：查询整个分类树
- ✅ **可视化**：知识图谱可视化

**查询示例**：
```nGQL
-- 查询"Python"实体的所有关联实体
MATCH (n:entity {name: "Python"})-[r:relationship]->(m:entity)
RETURN m.name, r.relation_type;

-- 查询"技术"分类下的所有子分类（通过关系边）
MATCH (parent:entity {type: "technology"})-[r:has_subcategory]->(child:entity)
RETURN child.name, child.type;
```

---

## 多用户场景下的数据隔离

### 方案1：知识库级别隔离（推荐）

**存储策略**：
- MySQL：`knowledge_base_id` 作为分区键
- NebulaGraph：每个知识库一个 Space（`kb_{knowledge_base_id}`）

**优点**：
- ✅ 数据完全隔离
- ✅ 查询性能好（索引优化）
- ✅ 支持多租户

**实现**：
```python
# MySQL 查询
entities = db.query(KnowledgeGraphEntity).filter(
    KnowledgeGraphEntity.knowledge_base_id == kb_id
).all()

# NebulaGraph 查询
space = f"kb_{kb_id}"
entities = await graph_storage.list_entities(space=space)
```

### 方案2：用户级别隔离（可选）

**存储策略**：
- MySQL：`user_id` 作为筛选条件
- NebulaGraph：Space 可以按用户划分（`user_{user_id}`）

**适用场景**：
- 用户需要完全私有的实体数据
- 跨知识库的实体查询需求

---

## 二级分类的实现方案

### 方案A：通过实体类型层级（推荐）

**MySQL 存储**：
```sql
-- 实体类型表（支持层级）
entity_types:
  id=1, code='technology', name='技术', parent_id=NULL, level=1
  id=2, code='programming_language', name='编程语言', parent_id=1, level=2
  id=3, code='framework', name='框架', parent_id=1, level=2

-- 实体实例表
knowledge_graph_entities:
  id=100, name='Python', type='programming_language', knowledge_base_id=1
  id=101, name='Django', type='framework', knowledge_base_id=1
```

**查询**：
```python
# 查询"技术"类型下的所有二级分类实体
sub_types = db.query(EntityType).filter(
    EntityType.parent_id == technology_type_id
).all()

entities = db.query(KnowledgeGraphEntity).filter(
    KnowledgeGraphEntity.type.in_([t.code for t in sub_types])
).all()
```

### 方案B：通过实体关系（图查询）

**NebulaGraph 存储**：
```nGQL
-- 创建层级关系
CREATE EDGE has_subcategory();

-- 插入关系
INSERT EDGE has_subcategory() VALUES 
  "entity_1" -> "entity_2":(),  -- 技术 -> 编程语言
  "entity_2" -> "entity_100":(); -- 编程语言 -> Python
```

**查询**：
```nGQL
-- 查询"技术"下的所有子分类
MATCH (tech:entity {name: "技术"})-[r:has_subcategory*]->(sub:entity)
RETURN sub.name, sub.type;
```

---

## 最终建议

### 存储分配

| 数据类型 | 存储位置 | 原因 |
|---------|---------|------|
| **实体类型配置** | MySQL | 配置数据，需要外键和事务 |
| **实体实例基础信息** | MySQL | 快速查询、统计、权限控制 |
| **实体实例完整数据** | NebulaGraph | 图查询、关系分析 |
| **实体层级关系** | MySQL + NebulaGraph | MySQL用于快速查询，NebulaGraph用于图遍历 |

### 查询策略

1. **列表查询、统计** → MySQL
   - 按知识库、类型、用户筛选
   - 统计每个类型的实体数量
   - 分页查询

2. **图查询、关系分析** → NebulaGraph
   - 查询实体的关联实体
   - 路径查询
   - 层级遍历

3. **混合查询** → MySQL + NebulaGraph
   - MySQL 获取实体列表
   - NebulaGraph 查询关系和详情

### 多用户隔离

- **推荐**：知识库级别隔离（`knowledge_base_id`）
- **可选**：用户级别隔离（`user_id`）
- **NebulaGraph**：每个知识库一个 Space

---

## 总结

**实体应该存储在哪里？**

1. **实体类型（配置）** → MySQL ✅
2. **实体实例（数据）** → MySQL（索引）+ NebulaGraph（完整数据）✅
3. **层级关系** → MySQL（快速查询）+ NebulaGraph（图遍历）✅

**关键原则**：
- MySQL：结构化查询、统计、权限控制
- NebulaGraph：图查询、关系分析、可视化
- 两者结合：兼顾性能和功能

