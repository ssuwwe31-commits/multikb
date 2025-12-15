# 知识库共享与协作设计文档

> 版本：v0.1（草案，用于指导实现）  
> 关联文档：`data-isolation-design.md`（数据隔离与权限管理设计文档）  
> 当前阶段：在 **“完全隔离 v1”** 基础上实现 **“知识库共享 v2（方案A/方案C 第二阶段）”**

---

## 1. 目标与约束

### 1.1 业务目标

- **多用户共享同一知识库**
  - 知识库拥有者可以邀请其他用户加入该知识库。
  - 受邀用户可以在该知识库下 **查看/上传/修改/删除** 文档（取决于角色）。
- **共享后，知识库对应的文档也随之“共享展示”**
  - 共享给某用户的知识库，其下所有文档在前端列表中都可见（权限控制由角色决定，只读或可写）。
- **保持与现有“完全隔离”模型兼容**
  - 继续支持“每个用户私有知识库”的使用方式。
  - 老数据（只有 owner，没有成员表记录）在逻辑上等价于只有一个 `owner` 成员。

### 1.2 约束与非目标

- 本阶段 **不引入组织/团队（Organization/Team）** 概念，只做“个人 + 共享知识库”。
- 不实现“完全公开的知识库（无需登录即可访问）”，仅支持 **登录用户间的共享**。
- 不在本阶段实现复杂的 **行级权限（按文档单独授权）**，权限粒度以“知识库级别”为主。

---

## 2. 数据模型设计

### 2.1 现有相关字段复用

- `knowledge_bases.user_id`
  - 含义：**知识库拥有者（owner）**。
  - 继续保留，用于：
    - 默认 owner 角色的判定；
    - 迁移阶段兼容逻辑（无成员记录时，通过 `user_id` 推断 owner）。
- `documents.knowledge_base_id`
  - 用于关联**文档归属的知识库**。
- `documents.user_id`
  - 当前含义：文档创建人/归属用户（用于 v1 完全隔离）。
  - 本阶段策略：**不删除此字段**，逐步从“权限过滤字段”退化为“创建人信息字段”。

### 2.2 新增表：知识库成员表

```sql
CREATE TABLE `knowledge_base_members` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `knowledge_base_id` INT NOT NULL COMMENT '知识库ID',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `role` VARCHAR(20) DEFAULT 'viewer' COMMENT '角色: owner/viewer/editor/admin',
    `invited_by` INT COMMENT '邀请人ID',
    `invited_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '邀请时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_kb_member` (`knowledge_base_id`, `user_id`),
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) COMMENT='知识库成员表';
```

#### 2.2.1 角色定义

- `owner`
  - 唯一，来自 `knowledge_bases.user_id` 或成员表中的 `role=owner` 记录。
- `admin`
  - 管理员：可以管理成员、编辑知识库设置、删除文档等（除了删除知识库本身）。
- `editor`
  - 编辑者：可以查看、上传、修改、删除**自己上传**或**知识库内的文档**（详见权限矩阵）。
- `viewer`
  - 只读者：仅可查看知识库和文档及其内容，不能上传/删除/修改。

### 2.3 知识库可见性字段（预留）

为与长期“公开知识库/组织模式”兼容，本阶段可预留可见性字段，暂不完全启用公开能力：

```sql
ALTER TABLE `knowledge_bases`
ADD COLUMN `visibility` VARCHAR(20) DEFAULT 'private' COMMENT '可见性: private/shared/public' AFTER `user_id`;
```

- `private`：仅 owner 自己 + 通过成员表显式加入的成员可见。
- `shared`：逻辑上与 `private` 一致，但用于前端标识“这是一个已共享的知识库”。
- `public`：本阶段暂不启用（未来扩展）。

> 实现顺序建议：先落地成员表 + 权限逻辑；`visibility` 先按 `private/shared` 做前端展示用标记。

---

## 3. 权限模型与行为矩阵

### 3.1 权限主体

- **主体粒度**：用户（User）在某个知识库（KnowledgeBase）下的角色（Role）。
- **决策入口**：所有与知识库/文档相关的 API，在处理前都需要通过统一的**权限检查函数**。

> 注意：**权限模型只决定“谁可以操作什么”**，并不直接解决“多人同时修改同一文档时的数据一致性问题”。  
> 并发编辑的一致性控制在第 6 章「数据迁移与兼容策略」之后单独设计（见「并发编辑与一致性」小节）。

### 3.2 权限矩阵（知识库级别）

| 操作                         | owner | admin | editor | viewer |
|------------------------------|:-----:|:-----:|:------:|:------:|
| 查看知识库详情               |  ✔    |  ✔    |   ✔    |   ✔    |
| 列表中看到该知识库           |  ✔    |  ✔    |   ✔    |   ✔    |
| 修改知识库名称/描述/分类     |  ✔    |  ✔    |   ✖    |   ✖    |
| 删除知识库                   |  ✔    |  ✖    |   ✖    |   ✖    |
| 管理成员（增/删/改角色）     |  ✔    |  ✔    |   ✖    |   ✖    |

### 3.3 权限矩阵（文档级别，在某知识库下）

> 假设：文档只要在某知识库内，权限由“用户在该知识库的角色”统一决定，不再单独按 `documents.user_id` 做强隔离。

| 操作                                 | owner | admin | editor | viewer |
|--------------------------------------|:-----:|:-----:|:------:|:------:|
| 查看知识库下文档列表                 |  ✔    |  ✔    |   ✔    |   ✔    |
| 查看文档详情与内容                   |  ✔    |  ✔    |   ✔    |   ✔    |
| 上传新文档到该知识库                |  ✔    |  ✔    |   ✔    |   ✖    |
| 修改文档元数据（标题、标签等）      |  ✔    |  ✔    |   ✔    |   ✖    |
| 删除文档                             |  ✔    |  ✔    |   ✔\*  |   ✖    |
| 批量删除/批量移动/批量标签操作       |  ✔    |  ✔    |   ✔    |   ✖    |

- `editor` 删除文档策略：
  - 简化方案（推荐）：**允许删除任意文档**（提升协作效率），但操作会记录在操作日志中；
  - 保守方案：仅允许删除自己上传的文档（需要保留 `documents.user_id` 作为限制条件）。  
  - 本设计默认采用 **简化方案**，如需保守模式可通过配置开关控制。

---

## 4. 权限检查设计

### 4.1 统一权限查询函数

新增一个服务/工具类，例如：`app/services/permission_service.py`：

```python
class KnowledgeBasePermissionService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_role_for_kb(self, kb_id: int, user_id: int) -> Optional[str]:
        """
        返回用户在某知识库下的角色: 'owner' / 'admin' / 'editor' / 'viewer' / None
        """
        # 1. 优先从 knowledge_base_members 查找
        member = (
            self.db.query(KnowledgeBaseMember)
            .filter(
                KnowledgeBaseMember.knowledge_base_id == kb_id,
                KnowledgeBaseMember.user_id == user_id,
            )
            .first()
        )
        if member:
            return member.role or "viewer"

        # 2. 兼容：如果没有成员记录，但当前用户是 knowledge_bases.user_id，则视为 owner
        kb = (
            self.db.query(KnowledgeBase)
            .filter(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.is_deleted == False,
            )
            .first()
        )
        if kb and kb.user_id == user_id:
            return "owner"

        return None

    def ensure_permission(self, kb_id: int, user_id: int, action: str):
        """
        针对某个 action 做权限校验，失败抛出 HTTPException。
        action 可枚举值例如: 'kb:view', 'kb:edit', 'kb:delete', 'kb:manage_members',
                            'doc:view', 'doc:edit', 'doc:delete', 'doc:upload'
        """
        role = self.get_user_role_for_kb(kb_id, user_id)
        if not role:
            raise HTTPException(status_code=403, detail="无权访问该知识库")

        # 角色 -> 可执行 action 列表的映射，可放在配置或常量中
        allowed_actions = ROLE_ACTION_MATRIX[role]
        if action not in allowed_actions:
            raise HTTPException(status_code=403, detail="权限不足")
```

> 实现时，`ROLE_ACTION_MATRIX` 可配置为字典常量，便于后续调整。

### 4.2 文档权限的接入点

- 对于操作文档的 API（如 `/documents` 列表、详情、删除、批量操作等），在执行查询前：
  1. 先根据 `knowledge_base_id`（入参或通过 `document.knowledge_base_id` 反查）获取 `kb_id`；
  2. 调用 `KnowledgeBasePermissionService.ensure_permission(kb_id, user_id, "doc:XXX")`；
  3. 在**权限通过后**再执行文档查询/操作。

---

## 5. 后端接口设计

### 5.1 成员管理 API

统一挂在 `knowledge_bases` 路由下，例如：`/knowledge-bases/{kb_id}/members`。

#### 5.1.1 邀请成员

- **URL**：`POST /api/knowledge-bases/{kb_id}/members`
- **权限**：`owner` / `admin`
- **请求体**：

```json
{
  "user_id": 2,
  "role": "editor"
}
```

- **逻辑**：
  - 校验当前用户对 `kb_id` 具有 `kb:manage_members` 权限。
  - 校验 `user_id` 是否存在。
  - 若 `knowledge_base_members` 中已存在记录：
    - 若角色相同：直接返回成功（幂等）。
    - 若角色不同：更新角色。
  - 若不存在记录：插入一条新记录，`invited_by = 当前用户ID`。

#### 5.1.2 获取成员列表

- **URL**：`GET /api/knowledge-bases/{kb_id}/members`
- **权限**：所有成员（viewer 及以上）均可查看。
- **返回示例**：

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    { "user_id": 1, "role": "owner", "nickname": "Alice" },
    { "user_id": 2, "role": "editor", "nickname": "Bob" },
    { "user_id": 3, "role": "viewer", "nickname": "Charlie" }
  ]
}
```

#### 5.1.3 更新成员角色

- **URL**：`PUT /api/knowledge-bases/{kb_id}/members/{user_id}`
- **权限**：`owner` / `admin`
- **限制**：
  - 不能修改 `owner` 为其他角色；如需转移 owner，单独提供“转移所有权”的接口（可后续扩展）。

#### 5.1.4 移除成员

- **URL**：`DELETE /api/knowledge-bases/{kb_id}/members/{user_id}`
- **权限**：`owner` / `admin`
- **限制**：
  - 不能删除 `owner` 本人记录（owner 至少要存在一条）。

### 5.2 知识库列表接口调整

#### 5.2.1 现状

- 当前 `GET /knowledge-bases`：只返回 `KnowledgeBase.user_id == 当前用户` 的记录。

#### 5.2.2 调整后逻辑

- 列表中包含：
  - 当前用户是 **owner** 的知识库（`knowledge_bases.user_id == user_id`）；
  - 当前用户在 `knowledge_base_members` 表中存在记录的知识库。

SQL 伪代码：

```sql
SELECT kb.*, kbc.name AS category_name, ...
FROM knowledge_bases kb
LEFT JOIN knowledge_base_categories kbc ON kb.category_id = kbc.id
LEFT JOIN knowledge_base_members km ON kb.id = km.knowledge_base_id
WHERE kb.is_deleted = 0
  AND (
        kb.user_id = :user_id
     OR km.user_id = :user_id
  )
GROUP BY kb.id;
```

> 注意：Service 层统计文档数量的子查询可以保持不变，只需在 base_query 中加入成员 JOIN 与 OR 条件。

### 5.3 文档列表/详情/删除等接口调整

#### 5.3.1 文档列表 `/documents`（按知识库筛选）

- 现状：
  - Service 层：`Document.user_id == 当前用户 or user_id is NULL`；
  - 路由层统计 total 时：`Document.user_id == 当前用户`。
- 目标：
  - 文档可见性统一基于“用户是否是该知识库的成员”。

**新逻辑建议**：

1. 入参中推荐**强制要求 `knowledge_base_id`**（否则难以判断权限）；
2. 获取用户在该 `knowledge_base_id` 下的角色（如无角色则 403）；
3. 如果允许查看文档列表，则：
   - 查询条件：`Document.knowledge_base_id == knowledge_base_id AND Document.is_deleted == False`；
   - 不再按 `Document.user_id` 过滤（除非开启“保守模式”）。

> 对于保守模式（editor 只能看到/删自己上传的文档），可以在 where 条件中增加 `AND (documents.user_id == 当前用户 OR role in ('owner', 'admin'))` 等逻辑。

#### 5.3.2 文档详情 `/documents/{doc_id}`

- 新增步骤：
  1. 先查出 `doc.knowledge_base_id`；
  2. 调用权限服务 `ensure_permission(kb_id, user_id, 'doc:view')`；
  3. 再返回文档详情。

#### 5.3.3 文档删除/批量删除

- 新增步骤：
  1. 对每个文档，先取 `knowledge_base_id`；
  2. 校验 `ensure_permission(kb_id, user_id, 'doc:delete')`；
  3. 再执行删除操作。

> 为降低 SQL 次数，可以：先按 `document_ids` 查一把，拿到 `doc_id -> kb_id` 映射，然后按 `kb_id` 归组做权限判断。

---

## 6. 数据迁移与兼容策略

### 6.1 迁移步骤

1. **创建表 `knowledge_base_members`**，新增字段 `knowledge_bases.visibility`。  
2. **为现有知识库补充 owner 成员记录**：

```sql
INSERT INTO knowledge_base_members (knowledge_base_id, user_id, role, invited_by)
SELECT id AS knowledge_base_id, user_id, 'owner' AS role, user_id AS invited_by
FROM knowledge_bases
WHERE is_deleted = 0
  AND user_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM knowledge_base_members m
      WHERE m.knowledge_base_id = knowledge_bases.id
        AND m.user_id = knowledge_bases.user_id
  );
```

3. **设置默认 visibility**：

```sql
UPDATE knowledge_bases
SET visibility = 'private'
WHERE visibility IS NULL;
```

4. **后端上线后行为**：
   - 即使个别知识库暂时没有成员记录，也可通过 `knowledge_bases.user_id` 推断 owner（权限服务里已兼容）。

### 6.2 渐进式切换文档权限

- 阶段 1（兼容期）：
  - 文档列表/操作仍然保留 `Document.user_id == 当前用户` 的过滤（防止权限突然变宽）。
  - 同时，对“成员”做额外放行：
    - 如果用户在某 `kb_id` 下是成员，且 `Document.knowledge_base_id == kb_id`，则允许访问该文档（即 `OR` 条件）。
- 阶段 2（完全切换）：
  - 当确认成员模型稳定、测试通过后，可以去掉对 `Document.user_id` 的强过滤，只保留按知识库成员的权限判定。
  - 原 `Document.user_id` 字段保留作为“创建人”信息使用。

---

## 7. 前端交互与展示要点（简要）

> 这里只列出后端设计需要前端配合的关键点，不展开全部 UI 细节。

### 7.1 知识库列表页

- 对于每条知识库记录，返回并展示：
  - `role`：当前登录用户在该知识库下的角色（owner/admin/editor/viewer）。
  - `visibility`：private/shared（用于加共享标识）。
- 支持筛选：
  - “我创建的”（role=owner 且 `kb.user_id == 当前用户`）。
  - “共享给我的”（role != owner）。

### 7.2 知识库详情页中的“成员管理”

- 仅在 `role in (owner, admin)` 时展示“成员管理”入口。
- 支持：
  - 列表：展示成员昵称+角色；
  - 邀请：输入用户名/ID -> 后端查用户 -> 调用邀请接口；
  - 修改角色 / 移除成员（owner/admin）。

### 7.3 文档列表页

- 必须带上当前选中的 `knowledge_base_id` 调接口。
- 在无 `kb_id` 情况下调用时，后端可：
  - 直接返回 400，提示必须指定知识库；或
  - 默认列出“当前用户有权限的最近文档”（可后续扩展）。

---

## 8. 并发编辑与数据一致性设计

> 本节补充说明「多人同时编辑同一文档/块」时的一致性策略，默认采用**乐观并发控制**，仅在极少数需要强事务的场景考虑悲观锁。

### 8.1 场景与目标

- 场景：多个用户作为同一知识库成员（editor/admin/owner），可能同时：
  - 修改同一文档的元数据（标题、标签、metadata 等）；
  - 修改同一文档的内容（通过 `DocumentVersion` / `ChunkVersion` 等）。
- 目标：
  - **避免“后保存的人无提示地覆盖前一个人的修改”**；
  - 不做 Google Docs 式的**实时协同编辑**（不需要长连接/字符级合并）；
  - 保持实现简单，对现有接口侵入小。

### 8.2 乐观并发控制（推荐默认策略）

#### 8.2.1 版本/时间戳字段

- 利用现有或补充字段作为并发控制依据，例如：
  - 文档级：`documents.version`（如存在）或 `documents.updated_at`；
  - 块级：`document_chunks.version` / `document_chunks.last_modified_at`。

#### 8.2.2 更新流程（后端视角）

1. 前端获取文档/块详情时，将当前的 `version` 或 `updated_at` 一并返回；
2. 前端在发起更新请求时，**建议携带**该版本字段：  
   - 文档级：通过 `DocumentUpdate.expected_updated_at` 字段提交当前 known 的 `updated_at`；  
   - 块级：可通过请求体中的 `expected_last_modified_at` 字段提交当前 known 的 `last_modified_at`（预留，当前实现主要针对文档级并发）。
3. 后端更新 SQL 带上版本条件，例如：

```sql
UPDATE documents
SET title = :title,
    updated_at = NOW()
WHERE id = :id
  AND updated_at = :old_updated_at;
```

4. 受影响行数：
   - 若为 1：说明版本匹配，更新成功；
   - 若为 0：说明有其他人已先一步修改，当前更新冲突 → 返回 409/自定义错误码“版本冲突，需要刷新”。

> 对 chunk 级编辑同理，使用 `chunk.version` 或 `last_modified_at` 做条件。

#### 8.2.3 行为与用户体验

- 当发生并发冲突时：
  - 后端返回“版本冲突”错误（HTTP 409 或业务级错误码），附带当前最新版本的时间戳；
  - 前端提示用户“该文档/内容已被其他人更新，请刷新后重新编辑”，或者做简单的“覆盖/放弃”选择。
- 优点：
  - 不需要持有长期锁，不会影响其他人的读取/编辑尝试；
  - 实现成本低，与现有“版本表”设计保持一致。

### 8.3 悲观锁（仅用于少数强事务场景）

- 若未来出现下列场景，可以局部考虑悲观锁/分布式锁：
  - 某些操作需要**强原子性**（例如：大批量重写 chunk 顺序 + 同步外部索引）；
  - 不允许并发写入打断整个过程。
- 可选策略：
  - 数据库层：在关键操作中使用 `SELECT ... FOR UPDATE` 锁住行，事务内完成多步更新；
  - Redis 分布式锁：例如 `lock:doc:{id}`，带过期时间，防止死锁。
- 但这些锁 **不用于普通的“文档内容编辑”场景**，避免把系统变得难以扩展。

### 8.4 与权限模型的关系

- 权限模型（第 3、4 章）决定 **“谁能发起编辑操作”**；
- 乐观并发控制决定 **“多个人都被允许编辑时，如何防止无提示覆盖”**；
- 两者相互独立、叠加使用：
  1. 先通过 `KnowledgeBasePermissionService` 判断用户是否有 `doc:edit` 权限；
  2. 再通过版本检查判断是否存在并发修改冲突。

---

## 9. 实施拆解建议

> 便于后续按任务拆分开发与评审。

1. **数据层（DB & Model）**
   - 创建 `knowledge_base_members` 表。
   - 新增 `knowledge_bases.visibility` 字段。
   - 增加对应 SQLAlchemy Model：`KnowledgeBaseMember`。
2. **服务层**
   - 新建 `KnowledgeBasePermissionService`，实现 `get_user_role_for_kb` 和 `ensure_permission`。
   - 新建 `KnowledgeBaseMemberService`（或在 `KnowledgeBaseService` 中增加成员相关方法）。
3. **API 层（后端路由）**
   - 在 `knowledge_bases` 路由中增加成员管理接口（增删改查）。
   - 调整 `GET /knowledge-bases` 查询逻辑为“owner + member”联合。
   - 在 `documents` 路由中接入权限检查逻辑（列表/详情/删除/批量操作）。
4. **迁移 & 回填**
   - 编写 SQL/脚本为现有知识库补齐 owner 成员记录。
   - 上线前在测试环境跑全量回填，确认无异常。
5. **前端适配**
   - 列表中展示角色与共享标识。
   - 知识库详情中增加成员管理 UI。
   - 文档列表强制带 `knowledge_base_id` 调用。
6. **测试与验证**
   - 单用户场景：行为与 v1 完全隔离模式保持一致。
   - 多用户共享场景：验证 viewer/editor/admin/owner 不同权限矩阵。
   - 并发编辑场景：模拟两个用户几乎同时保存同一文档/块，验证乐观锁的冲突提示是否生效。

---

## 10. 总结

- 本设计在 `data-isolation-design.md` 的基础上，**具体化了“方案A / 方案C 第二阶段”的落地实现**：
  - 定义了知识库成员表与角色模型；
  - 给出了知识库与文档在共享场景下的权限矩阵；
  - 设计了统一的权限服务与关键 API；
  - 提供了迁移策略，确保与 v1 完全隔离模型兼容。
- 实现后，将支持：
  - **多个用户共享同一知识库，并在前端自然地看到同一批文档**；
  - 通过角色控制不同程度的读写/管理权限；
  - 在不破坏现有个人使用体验的前提下，引入团队协作能力。


