# 数据库迁移执行指南

## 迁移文件

- **MVP 版本**：`migrations/2026011201_code_repository_mvp.sql` ✅ 已执行
- **深度集成版本**：`migrations/2026011202_code_integration.sql` ✅ 已执行（2026-01-12）

---

## 执行前检查

### 1. 确保 MySQL 服务运行

```bash
# Windows - 检查 MySQL 服务状态
net start MySQL80

# 或者通过服务管理器启动
services.msc
# 找到 MySQL 服务并启动
```

### 2. 确认数据库连接信息

从 `.env` 文件或配置中获取：
- 数据库主机：`MYSQL_HOST`
- 数据库端口：`MYSQL_PORT`  
- 数据库名称：`MYSQL_DATABASE`
- 用户名：`MYSQL_USER`
- 密码：`MYSQL_PASSWORD`

---

## 方法1：使用 MySQL 命令行（推荐）

### Windows PowerShell

```powershell
# 找到 MySQL 安装路径
# 通常在: C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe

# 执行迁移
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" `
  -u root `
  -p `
  multikb_knowledge `
  < migrations/2026011202_code_integration.sql

# 或者先登录 MySQL，再执行
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p

# 在 MySQL 提示符下：
USE multikb_knowledge;
SOURCE F:/spxknowlage/multikb-knowledge-backend/migrations/2026011202_code_integration.sql;
```

---

## 方法2：使用 Python 脚本

### 步骤 1：修改配置

编辑 `run_migration.py` 文件，修改数据库配置：

```python
DB_CONFIG = {
    'host': 'localhost',     # 你的数据库主机
    'port': 3306,           # 你的数据库端口
    'user': 'root',         # 你的数据库用户名
    'password': '你的密码',  # 修改这里
    'database': 'multikb_knowledge',  # 你的数据库名
    'charset': 'utf8mb4'
}
```

### 步骤 2：执行迁移

```bash
cd multikb-knowledge-backend
python run_migration.py migrations/2026011202_code_integration.sql
```

---

## 方法3：使用数据库管理工具

### A. MySQL Workbench

1. 打开 MySQL Workbench
2. 连接到数据库
3. 打开 SQL 文件：`File` → `Open SQL Script`
4. 选择：`migrations/2026011202_code_integration.sql`
5. 点击 `Execute` 按钮执行

### B. Navicat

1. 打开 Navicat
2. 连接到数据库
3. 右键数据库 → `Execute SQL File`
4. 选择迁移文件并执行

### C. phpMyAdmin

1. 打开 phpMyAdmin
2. 选择数据库
3. 点击 `Import` 标签
4. 上传 SQL 文件
5. 点击 `Go` 执行

---

## 方法4：手动逐步执行（最安全）

打开 `migrations/2026011202_code_integration.sql` 文件，手动复制粘贴 SQL 语句到数据库工具中执行。

### 执行顺序：

1. **扩展 code_repositories 表**（添加 knowledge_base_id 等字段）
2. **创建 code_files 表**
3. **创建 code_symbols 表**
4. **创建 code_dependencies 表**
5. **创建 code_kb_mappings 表**
6. **验证查询**（可选）

---

## 验证迁移成功

执行以下 SQL 验证：

```sql
-- 1. 验证新表是否创建
SHOW TABLES LIKE 'code%';

-- 应该看到：
-- code_repositories
-- code_analysis_cache
-- code_files
-- code_symbols
-- code_dependencies
-- code_kb_mappings

-- 2. 验证 code_repositories 表的新字段
DESC code_repositories;

-- 应该看到新增字段：
-- knowledge_base_id
-- kb_document_id
-- description
-- readme_content
-- tags
-- visibility

-- 3. 查看表结构
DESC code_files;
DESC code_symbols;
DESC code_dependencies;
DESC code_kb_mappings;

-- 4. 验证外键约束
SELECT 
    CONSTRAINT_NAME,
    TABLE_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'multikb_knowledge'
  AND TABLE_NAME IN ('code_files', 'code_symbols', 'code_dependencies', 'code_kb_mappings', 'code_repositories')
  AND REFERENCED_TABLE_NAME IS NOT NULL;
```

---

## 迁移内容说明

### 扩展的表

**code_repositories**：
- 新增 `knowledge_base_id`：关联知识库ID
- 新增 `kb_document_id`：对应的文档ID
- 新增 `description`：仓库描述
- 新增 `readme_content`：README内容
- 新增 `tags`：标签（JSON）
- 新增 `visibility`：可见性

### 新增的表

1. **code_files**（代码文件表）
   - 文件路径、语言、大小
   - 代码行数、符号数量、复杂度
   - OpenSearch 向量索引ID

2. **code_symbols**（代码符号表）
   - 函数、类、方法、变量
   - 签名、文档字符串、参数
   - 复杂度、行数
   - 向量索引

3. **code_dependencies**（依赖关系表）
   - 导入、调用、继承、实现关系
   - 源文件/符号 → 目标文件/符号
   - 依赖语句、行号

4. **code_kb_mappings**（代码-文档映射表）
   - 文档 ↔ 代码文件/符号
   - 映射类型、上下文、置信度

---

## 常见问题

### Q: 提示 "Duplicate column name 'knowledge_base_id'"

**A**: 字段已存在，可以忽略这个错误，或者先删除该字段再执行：

```sql
ALTER TABLE code_repositories DROP COLUMN knowledge_base_id;
```

### Q: 提示 "Table 'code_files' already exists"

**A**: 表已存在。如果需要重新创建，先删除：

```sql
DROP TABLE IF EXISTS code_kb_mappings;
DROP TABLE IF EXISTS code_dependencies;
DROP TABLE IF EXISTS code_symbols;
DROP TABLE IF EXISTS code_files;
```

**⚠️ 警告**：删除表会丢失所有数据！

### Q: 外键约束失败

**A**: 确保：
1. `knowledge_bases` 表存在
2. `documents` 表存在
3. 先执行 MVP 迁移脚本（`2026011201_code_repository_mvp.sql`）

---

## 回滚（如果需要）

```sql
-- 删除新增的表
DROP TABLE IF EXISTS code_kb_mappings;
DROP TABLE IF EXISTS code_dependencies;
DROP TABLE IF EXISTS code_symbols;
DROP TABLE IF EXISTS code_files;

-- 删除 code_repositories 的新字段
ALTER TABLE code_repositories 
DROP FOREIGN KEY fk_code_repo_kb,
DROP COLUMN knowledge_base_id,
DROP COLUMN kb_document_id,
DROP COLUMN description,
DROP COLUMN readme_content,
DROP COLUMN tags,
DROP COLUMN visibility;
```

---

## 下一步

迁移完成后：

1. ✅ 重启后端服务
2. ✅ 验证 API 是否正常工作
3. ✅ 开始使用深度集成功能

---

**迁移文件位置**：`migrations/2026011202_code_integration.sql`

**需要帮助？** 查看设计文档：`docs/architecture/code-repository-integration-design.md`
