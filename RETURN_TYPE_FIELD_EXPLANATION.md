# `return_type` 字段说明

## 📋 字段定义

**表名**：`code_symbols`  
**字段名**：`return_type`  
**数据类型**：`VARCHAR(100)`  
**用途**：存储函数/方法的返回值类型信息

---

## 📝 保存的数据内容

### 1. **Python 函数的返回值类型**

从 Python AST 中提取的类型注解：

```python
# 示例 1：简单类型
def get_user(id: int) -> User:
    return User.objects.get(id=id)
# return_type = "User"

# 示例 2：可选类型
def find_user(name: str) -> Optional[User]:
    return User.objects.filter(name=name).first()
# return_type = "Optional[User]"

# 示例 3：联合类型
def process(data: str) -> str | None:
    return data.strip() if data else None
# return_type = "str | None"

# 示例 4：复杂类型
def get_users() -> List[Dict[str, Any]]:
    return [{"id": 1, "name": "test"}]
# return_type = "List[Dict[str, Any]]"
```

### 2. **TypeScript/JavaScript 函数的返回值类型**

从 TypeScript AST 或 JSDoc 注释中提取：

```typescript
// 示例 1：简单类型
function getUser(id: number): User {
    return userService.findById(id);
}
// return_type = "User"

// 示例 2：对象类型（可能很长）
function resolveRepositoryInfoFromPath(path?: string): {
    repositoryKind?: RepositoryKind;
    repositoryName?: string;
    basename?: string;
    repositorySpecifier?: string;
    viewMode?: ViewMode;
    rev?: string;
} {
    // ...
}
// return_type = ": {\r\n  repositoryKind?: RepositoryKind\r\n  repositoryName?: string\r\n  ... }"

// 示例 3：泛型类型
function fetchData<T>(url: string): Promise<T> {
    return fetch(url).then(res => res.json());
}
// return_type = "Promise<T>"

// 示例 4：从 JSDoc 提取
/**
 * @param {string} name - 用户名
 * @returns {Promise<User>} 用户对象
 */
async function getUser(name) {
    // ...
}
// return_type = "Promise<User>"
```

### 3. **实际保存的数据示例**

从错误日志中可以看到的实际数据：

```
原始数据（来自 TypeScript）：
': {\r\n  repositoryKind?: RepositoryKind\r\n  repositoryName?: string\r\n  basename?: string\r\n  repositorySpecifier?: string\r\n  viewMode?: ViewMode\r\n  rev?: string\r\n}'

处理后的数据（保存到 MySQL）：
': { repositoryKind?: RepositoryKind repositoryName?: string basename?: string repositorySpecifier?: string viewMode?: ViewMode rev?: string }'
（因为字段限制为 100 字符，如果超过会被截断）
```

---

## 🔍 数据来源

### 1. **从 AST 节点提取**（主要方式）

#### Python（使用 AST）：
```python
def _extract_type_annotation(self, node):
    """提取 Python 类型注解"""
    if node:
        return ast.unparse(node)  # Python 3.9+
        # 或手动解析节点
    return None
```

#### TypeScript/JavaScript（使用 Tree-sitter）：
```python
def _extract_js_return_type(self, func_node: Node, code: bytes) -> Optional[str]:
    """提取 TypeScript 函数返回值类型"""
    return_type_node = func_node.child_by_field_name('return_type')
    if return_type_node:
        return code[return_type_node.start_byte:return_type_node.end_byte].decode('utf-8')
    return None
```

### 2. **从 JSDoc 注释提取**（备选方式）

如果 AST 中没有类型信息，会尝试从 JSDoc 注释中提取：

```python
def _extract_return_type_from_jsdoc(self, jsdoc: str) -> Optional[str]:
    """从 JSDoc 中提取返回值类型"""
    import re
    # 匹配 @returns {Type} 或 @return {Type}
    match = re.search(r'@returns?\s*\{([^}]+)\}', jsdoc)
    if match:
        return match.group(1).strip()
    return None
```

---

## ⚙️ 数据处理逻辑

### 1. **原始数据提取**

从符号解析结果中获取：
```python
return_type = symbol.get('return_type')  # 原始数据，可能包含换行符
```

### 2. **数据清理和截断**

因为 MySQL 字段是 `VARCHAR(100)`，需要对超长数据进行处理：

```python
# 处理 return_type：MySQL 字段是 VARCHAR(100)，需要截断
return_type_clean = None
if return_type:
    # 1. 移除换行符，压缩空格
    return_type_single_line = ' '.join(
        return_type.replace('\r\n', ' ')
                   .replace('\n', ' ')
                   .split()
    )
    
    # 2. 截断到 95 字符（留一些余量）
    if len(return_type_single_line) > 95:
        return_type_clean = return_type_single_line[:92] + "..."
    else:
        return_type_clean = return_type_single_line
```

### 3. **完整信息保留**

虽然 `return_type` 字段会被截断，但完整的类型信息会保存在 `signature` 字段中：

```python
# signature 字段是 TEXT 类型，可以存储完整信息
signature = f"({', '.join(signature_parts)})"
if return_type:
    signature += f" -> {return_type}"  # 完整的 return_type，不截断
```

---

## 📊 数据用途

### 1. **函数签名展示**

在代码符号详情页面，显示完整的函数签名：
```
function getUser(id: number): User
                    ^^^^^^^^   ^^^^
                  参数类型    返回类型
```

### 2. **代码搜索**

用于搜索特定返回类型的函数：
```sql
-- 搜索返回 Promise 的函数
SELECT * FROM code_symbols 
WHERE return_type LIKE '%Promise%' 
AND symbol_type = 'function';
```

### 3. **类型统计**

统计代码库中使用的返回类型：
```sql
-- 统计常见的返回类型
SELECT return_type, COUNT(*) as count
FROM code_symbols
WHERE return_type IS NOT NULL
GROUP BY return_type
ORDER BY count DESC
LIMIT 10;
```

### 4. **语义搜索**

在 OpenSearch 中用于向量搜索，帮助理解函数的语义：
```python
# 构建向量化文本时，返回类型信息会被包含
text = f"函数: {symbol_name}\n返回: {return_type}\n签名: {signature}"
vector = vectorize(text)
```

---

## ⚠️ 注意事项

### 1. **字段长度限制**

- **MySQL 字段**：`VARCHAR(100)`，最多 100 字符
- **处理方式**：超长数据会被截断，并添加 `"..."` 后缀
- **完整信息**：可以在 `signature` 字段中找到（`TEXT` 类型）

### 2. **数据格式**

- **可能包含换行符**：原始数据可能包含 `\r\n` 或 `\n`
- **会自动清理**：保存到 MySQL 前会移除换行符，压缩空格
- **保留语义**：清理过程不会改变类型的语义含义

### 3. **数据一致性**

- **与 signature 字段的关系**：`signature` 包含完整的返回类型信息
- **查询建议**：如果需要完整信息，优先查询 `signature` 字段
- **截断信息**：`return_type` 字段只用于快速查询和统计

---

## 💡 使用建议

### ✅ 适合使用 `return_type` 的场景：

1. **快速筛选**：筛选特定返回类型的函数
   ```sql
   WHERE return_type LIKE '%Promise%'
   ```

2. **类型统计**：统计代码库中的返回类型分布
   ```sql
   GROUP BY return_type
   ```

3. **简单展示**：在列表中显示返回类型（不需要完整信息）

### ✅ 适合使用 `signature` 的场景：

1. **完整签名展示**：需要显示完整的函数签名
   ```sql
   SELECT signature FROM code_symbols WHERE id = ?
   ```

2. **类型解析**：需要解析复杂的类型定义

3. **代码生成**：基于签名生成代码文档

---

## 📚 相关字段

| 字段名 | 类型 | 用途 | 说明 |
|--------|------|------|------|
| `return_type` | VARCHAR(100) | 返回值类型（简短） | 可能被截断 |
| `signature` | TEXT | 完整函数签名 | 包含完整返回类型 |
| `parameters` | JSON | 参数列表 | 包含参数类型 |
| `symbol_type` | VARCHAR(50) | 符号类型 | function/class/method |

---

## 🎯 总结

`return_type` 字段保存的是**函数/方法的返回值类型信息**，主要用于：

1. **快速查询和筛选**：找到特定返回类型的函数
2. **类型统计**：分析代码库中的类型使用情况
3. **函数签名展示**：在 UI 中显示函数的返回类型

**注意事项**：
- 字段长度限制为 100 字符，超长会被截断
- 完整信息保存在 `signature` 字段中
- 支持 Python、TypeScript、JavaScript 等多种语言
