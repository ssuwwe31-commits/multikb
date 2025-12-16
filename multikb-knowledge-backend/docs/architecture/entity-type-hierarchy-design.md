# 实体类型层级设计文档

## 设计原则

### 1. 最多支持3级分类
- **层级限制**：最多支持3级分类（一级、二级、三级）
- **自动计算level**：`level` 字段根据 `parent_id` 自动计算，无需手动设置
- **代码强制限制**：在创建和更新类型时，如果超过3级会直接报错
- **递归查询**：支持查询所有后代类型和所有祖先类型（最多3级）

### 2. 二级分类的合理性分析

#### 当前二级分类设计

**技术（technology）的二级分类**：
- 编程语言（programming_language）
- 框架（framework）
- 库（library）
- 工具（tool）
- 平台（platform）
- 协议（protocol）
- 标准（standard）
- 方法（method）

**合理性评估**：
- ✅ **优点**：
  - 分类清晰，覆盖技术领域的主要维度
  - 每个二级分类都有明确的定义和示例
  - 便于用户快速定位和选择
  
- ⚠️ **潜在问题**：
  - 某些分类可能有重叠（如"框架"和"库"）
  - 某些技术可能同时属于多个分类（如"React"既是框架也是库）
  - 对于特定领域，可能需要更细粒度的分类

#### 是否需要三级、四级分类？

**场景分析**：

1. **编程语言 → 具体语言 → 版本**
   ```
   技术 (level=1)
   └── 编程语言 (level=2)
       └── Python (level=3)
           └── Python 3.12 (level=4)
   ```
   **建议**：❌ 不需要
   - 版本信息应该存储在实体的 `metadata` 中，而不是作为类型
   - 实体实例（如"Python 3.12"）本身就是具体的技术，不需要再细分

2. **框架 → 前端框架 → React生态**
   ```
   技术 (level=1)
   └── 框架 (level=2)
       └── 前端框架 (level=3)
           └── React (level=4)
               └── React Router (level=5)
   ```
   **建议**：✅ 可以考虑
   - 对于大型技术栈，三级分类有助于组织
   - 但要注意不要过度细分，避免分类过深导致使用困难

3. **平台 → 云平台 → AWS → AWS服务**
   ```
   技术 (level=1)
   └── 平台 (level=2)
       └── 云平台 (level=3)
           └── AWS (level=4)
               └── AWS S3 (level=5)
   ```
   **建议**：⚠️ 谨慎使用
   - 三级分类（云平台）可能有用
   - 四级及以上建议用实体实例+关系来表示，而不是类型层级

### 3. 层级限制说明

#### 最多支持3级分类（代码强制限制）

**一级分类（8个）**：
- 人物、地点、概念、产品、技术、事件、组织、其他

**二级分类（按需）**：
- 技术 → 编程语言、框架、库、工具、平台、协议、标准、方法
- 产品 → 软件、服务
- 概念 → 设计模式、原则

**三级分类（可选）**：
- 仅在确实需要细分时使用
- 例如：框架 → 前端框架 → React生态
- 例如：平台 → 云平台 → AWS

**四级及以上（不支持）**：
- ❌ **代码限制**：创建或更新类型时，如果超过3级会直接报错
- ✅ **替代方案**：使用实体实例+关系来表示更细粒度的分类
- 例如：不要创建"技术 → 编程语言 → Python → Python 3.12"
- 而是：创建实体"Python 3.12"，类型为"编程语言"，通过关系关联到"Python"

#### 分类原则

1. **按维度分类，不按实例分类**
   - ✅ 正确：技术 → 编程语言（维度）
   - ❌ 错误：技术 → Python（实例）

2. **遵守3级限制**
   - 最多只能创建3级分类，超过会报错
   - 如果某个分类下只有1-2个子分类，考虑合并
   - 如果确实需要更细粒度，使用实体实例+关系

3. **保持分类的互斥性**
   - 尽量确保一个实体只属于一个类型
   - 如果确实需要多分类，使用标签或关系

4. **考虑用户使用场景**
   - 分类应该便于用户快速找到和选择
   - 3级分类已经足够满足大多数场景

## 实现细节

### 自动计算level并验证限制

```python
# 最大层级限制
MAX_LEVEL = 3

def _calculate_level(self, parent_id: Optional[int]) -> int:
    """计算层级深度（最多支持3级分类）"""
    if not parent_id:
        return 1
    
    parent_type = self.get_type_by_id(parent_id)
    if not parent_type:
        return 1
    
    return parent_type.level + 1

def _validate_level(self, level: int):
    """验证层级深度是否超过限制"""
    if level > self.MAX_LEVEL:
        raise CustomException(
            ErrorCode.BAD_REQUEST,
            f"实体类型最多支持{self.MAX_LEVEL}级分类，当前层级为{level}，超过限制"
        )
```

### 递归查询方法

```python
# 获取所有后代类型
def get_all_descendants(self, parent_id: int) -> List[EntityType]:
    """递归获取所有子类型、孙类型等"""
    ...

# 获取所有祖先类型
def get_all_ancestors(self, type_id: int) -> List[EntityType]:
    """获取从根到父类型的路径"""
    ...
```

### 数据修复

```python
# 重新计算所有类型的level
def recalculate_all_levels(self) -> int:
    """用于数据修复，重新计算所有类型的level"""
    ...
```

## API使用示例

### 创建三级分类

```python
# 1. 创建一级分类（如果不存在）
technology = create_type({
    "code": "technology",
    "name": "技术",
    "level": 1  # 自动计算，可省略
})

# 2. 创建二级分类
framework = create_type({
    "code": "framework",
    "name": "框架",
    "parent_id": technology.id  # level会自动计算为2
})

# 3. 创建三级分类
frontend_framework = create_type({
    "code": "frontend_framework",
    "name": "前端框架",
    "parent_id": framework.id  # level会自动计算为3
})
```

### 查询类型树

```python
# 获取完整的类型树（包含所有层级）
GET /api/v1/entity-types/tree

# 获取指定类型的所有后代
GET /api/v1/entity-types/{type_id}/children?recursive=true

# 限制查询深度
GET /api/v1/entity-types/tree?max_depth=3
```

## 总结

1. **最多支持3级分类**：代码强制限制，超过3级会报错
2. **二级分类合理**：当前的技术二级分类设计合理，覆盖主要维度
3. **三级分类可选**：根据实际需求使用，但最多只能到3级
4. **四级及以上不支持**：代码会直接拒绝，使用实体实例+关系来表示更细粒度的分类

