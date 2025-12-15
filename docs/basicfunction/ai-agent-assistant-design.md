# 智能Agent助手功能设计文档

> 版本：v0.1（草案，用于指导实现）  
> 关联文档：`knowledge-graph-design.md`（知识图谱设计文档）  
> 当前阶段：在现有知识库系统基础上，增加**智能Agent助手**，支持多步骤任务自动执行、工具调用、上下文记忆

---

## 1. 目标与约束

### 1.1 业务目标

- **多步骤任务自动执行**
  - 将复杂任务分解为多个步骤
  - 自动执行每个步骤，并根据结果决定下一步
  - 支持工具调用（搜索、创建、更新、删除等）
- **自然语言命令执行**
  - 用户使用自然语言描述任务
  - Agent 理解意图并自动执行
  - 支持多轮对话，持续优化任务执行
- **上下文记忆与状态管理**
  - 保持对话上下文
  - 记录任务执行历史
  - 支持任务中断和恢复
- **智能决策与验证**
  - 在执行关键操作前请求用户确认
  - 自动验证执行结果
  - 错误处理和重试机制

### 1.2 约束与非目标

- 本阶段**不引入外部Agent框架**（如 LangChain Agent），基于现有 LLM 服务实现
- 不实现复杂的规划算法（如 Tree of Thoughts），优先支持线性任务分解
- 不实现多Agent协作，单个Agent处理单个任务

---

## 2. 数据模型设计

### 2.1 Agent任务表（agent_tasks）

```sql
CREATE TABLE `agent_tasks` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL COMMENT '用户ID',
    `knowledge_base_id` INT COMMENT '关联的知识库ID（可选）',
    `task_type` VARCHAR(50) NOT NULL COMMENT '任务类型: create_kb/upload_docs/manage_members/search_and_analyze/custom',
    `description` TEXT NOT NULL COMMENT '任务描述（用户原始输入）',
    `status` VARCHAR(50) DEFAULT 'pending' COMMENT '状态: pending/executing/completed/failed/paused',
    `current_step` INT DEFAULT 0 COMMENT '当前执行步骤',
    `total_steps` INT DEFAULT 0 COMMENT '总步骤数',
    `result` JSON COMMENT '任务执行结果',
    `error_message` TEXT COMMENT '错误信息',
    `context` JSON COMMENT '上下文信息（用于多轮对话）',
    `requires_confirmation` BOOLEAN DEFAULT FALSE COMMENT '是否需要用户确认',
    `confirmation_data` JSON COMMENT '等待确认的数据',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    INDEX `idx_user_status` (`user_id`, `status`),
    INDEX `idx_kb` (`knowledge_base_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_is_deleted` (`is_deleted`),
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Agent任务表';
```

**任务类型定义**：
- `create_kb`: 创建知识库
- `upload_docs`: 上传文档
- `manage_members`: 管理成员
- `search_and_analyze`: 搜索和分析
- `custom`: 自定义任务

### 2.2 Agent任务步骤表（agent_task_steps）

```sql
CREATE TABLE `agent_task_steps` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `task_id` INT NOT NULL COMMENT '任务ID',
    `step_number` INT NOT NULL COMMENT '步骤序号',
    `step_type` VARCHAR(50) NOT NULL COMMENT '步骤类型: tool_call/decision/confirmation/verification/other',
    `tool_name` VARCHAR(100) COMMENT '工具名称（如果是工具调用）',
    `tool_input` JSON COMMENT '工具输入参数',
    `tool_output` JSON COMMENT '工具输出结果',
    `status` VARCHAR(50) DEFAULT 'pending' COMMENT '状态: pending/executing/completed/failed',
    `error_message` TEXT COMMENT '错误信息',
    `execution_time_ms` INT COMMENT '执行耗时（毫秒）',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    INDEX `idx_task_step` (`task_id`, `step_number`),
    INDEX `idx_status` (`status`),
    INDEX `idx_is_deleted` (`is_deleted`),
    FOREIGN KEY (`task_id`) REFERENCES `agent_tasks` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Agent任务步骤表';
```

**步骤类型定义**：
- `tool_call`: 工具调用
- `decision`: 决策判断
- `confirmation`: 等待用户确认
- `verification`: 验证执行结果
- `other`: 其他

### 2.3 Agent对话历史表（agent_conversations）

```sql
CREATE TABLE `agent_conversations` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL COMMENT '用户ID',
    `session_id` VARCHAR(100) NOT NULL COMMENT '会话ID',
    `task_id` INT COMMENT '关联的任务ID（可选）',
    `role` VARCHAR(20) NOT NULL COMMENT '角色: user/assistant/system',
    `content` TEXT NOT NULL COMMENT '消息内容',
    `metadata` JSON COMMENT '扩展元数据（如：工具调用信息）',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    INDEX `idx_session` (`session_id`, `created_at`),
    INDEX `idx_user_session` (`user_id`, `session_id`),
    INDEX `idx_task` (`task_id`),
    INDEX `idx_is_deleted` (`is_deleted`),
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`task_id`) REFERENCES `agent_tasks` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Agent对话历史表';
```

---

## 3. 功能设计

### 3.1 Agent工具系统

#### 3.1.1 工具定义

Agent 可以调用的工具列表：

**知识库管理工具**
- `create_knowledge_base`: 创建知识库
  - 输入：`{name: string, description: string, category_id: int}`
  - 输出：`{knowledge_base_id: int, name: string}`
- `list_knowledge_bases`: 列出知识库
  - 输入：`{keyword: string, page: int, size: int}`
  - 输出：`{list: [], total: int}`
- `get_knowledge_base_detail`: 获取知识库详情
  - 输入：`{knowledge_base_id: int}`
  - 输出：`{knowledge_base: {}}`
- `update_knowledge_base`: 更新知识库
  - 输入：`{knowledge_base_id: int, name: string, description: string}`
  - 输出：`{success: bool}`

**文档管理工具**
- `upload_document`: 上传文档
  - 输入：`{knowledge_base_id: int, file_path: string, title: string}`
  - 输出：`{document_id: int, status: string}`
- `search_documents`: 搜索文档
  - 输入：`{knowledge_base_id: int, query: string, page: int, size: int}`
  - 输出：`{list: [], total: int}`
- `get_document_detail`: 获取文档详情
  - 输入：`{document_id: int}`
  - 输出：`{document: {}}`

**成员管理工具**
- `list_knowledge_base_members`: 列出知识库成员
  - 输入：`{knowledge_base_id: int}`
  - 输出：`{members: []}`
- `invite_member`: 邀请成员
  - 输入：`{knowledge_base_id: int, user_email: string, role: string}`
  - 输出：`{success: bool}`

**搜索工具**
- `search_knowledge_base`: 在知识库中搜索
  - 输入：`{knowledge_base_id: int, query: string, search_type: string}`
  - 输出：`{results: [], total: int}`
- `search_external`: 外部搜索（SearxNG）
  - 输入：`{query: string, limit: int}`
  - 输出：`{results: []}`

**实体和关系工具**
- `search_entities`: 搜索实体（知识图谱）
  - 输入：`{knowledge_base_id: int, query: string}`
  - 输出：`{entities: []}`
- `get_entity_relationships`: 获取实体关系
  - 输入：`{entity_id: int}`
  - 输出：`{relationships: []}`

#### 3.1.2 工具调用格式

```json
{
  "tool_name": "create_knowledge_base",
  "tool_input": {
    "name": "Python教程",
    "description": "关于Python编程的教程文档"
  },
  "tool_output": {
    "knowledge_base_id": 123,
    "name": "Python教程"
  }
}
```

### 3.2 任务分解与执行

#### 3.2.1 任务分解流程

```
用户输入："帮我创建一个关于Python异步编程的知识库，并上传相关文档"

Agent处理流程：
1. 理解意图（Intent Understanding）
   - 识别任务类型：create_kb + upload_docs
   - 提取关键信息：主题="Python异步编程"，需要上传文档

2. 任务分解（Task Decomposition）
   - Step 1: 检查是否已有相似知识库
   - Step 2: 创建新知识库（如果需要）
   - Step 3: 搜索相关文档（可选，从外部或推荐）
   - Step 4: 上传文档到知识库
   - Step 5: 生成知识库摘要

3. 执行步骤（Step Execution）
   - 依次执行每个步骤
   - 根据前一步结果决定下一步
   - 如果某步失败，尝试替代方案或询问用户

4. 结果验证（Result Verification）
   - 验证每个步骤的执行结果
   - 检查最终任务是否完成
   - 生成任务执行报告
```

#### 3.2.2 任务分解Prompt设计

```python
TASK_DECOMPOSITION_PROMPT = """
你是一个智能助手，需要将用户的复杂任务分解为多个可执行的步骤。

用户任务：{user_task}

可用工具列表：
{tools_description}

请将任务分解为步骤，每个步骤应该：
1. 明确调用哪个工具
2. 明确工具的输入参数
3. 明确如何根据上一步结果决定下一步

请以JSON格式返回：
{
  "steps": [
    {
      "step_number": 1,
      "step_type": "tool_call",
      "tool_name": "list_knowledge_bases",
      "tool_input": {
        "keyword": "Python异步编程"
      },
      "description": "检查是否已有相似知识库",
      "next_step_condition": {
        "if_exists": "step_2_update",
        "if_not_exists": "step_2_create"
      }
    },
    {
      "step_number": 2,
      "step_type": "tool_call",
      "tool_name": "create_knowledge_base",
      "tool_input": {
        "name": "Python异步编程",
        "description": "关于Python异步编程的教程文档"
      },
      "description": "创建新知识库"
    }
  ],
  "requires_confirmation": false,
  "estimated_time": 30
}
"""
```

### 3.3 上下文记忆

#### 3.3.1 对话上下文管理

Agent 需要记住的内容：
- **任务上下文**：当前任务的目标、已执行步骤、中间结果
- **用户偏好**：用户常用的知识库、文档类型偏好
- **历史对话**：最近几轮对话的内容（用于多轮对话）

#### 3.3.2 上下文存储结构

```json
{
  "task_context": {
    "goal": "创建Python异步编程知识库",
    "completed_steps": [1, 2],
    "current_step": 3,
    "intermediate_results": {
      "kb_id": 123,
      "kb_name": "Python异步编程"
    }
  },
  "user_preferences": {
    "default_category": "技术文档",
    "preferred_doc_types": ["PDF", "Markdown"]
  },
  "conversation_history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

### 3.4 智能决策与验证

#### 3.4.1 决策点设计

Agent 在执行过程中需要做出决策：

1. **是否需要用户确认**
   - 删除操作（知识库、文档）
   - 批量操作（批量删除、批量移动）
   - 敏感操作（修改权限、邀请成员）

2. **错误处理策略**
   - 工具调用失败：重试 or 跳过 or 询问用户
   - 数据验证失败：修正输入 or 询问用户
   - 权限不足：提示用户 or 跳过该步骤

3. **任务完成判断**
   - 所有步骤完成且结果验证通过
   - 用户明确表示满意
   - 达到最大执行次数

#### 3.4.2 验证机制

```python
async def verify_step_result(
    step: TaskStep, expected_result: Dict
) -> Dict[str, Any]:
    """
    验证步骤执行结果
    
    返回：
    {
        "is_valid": bool,
        "confidence": float,  # 0-1
        "issues": [],  # 发现的问题
        "suggestions": []  # 改进建议
    }
    """
```

### 3.5 自然语言命令解析

#### 3.5.1 意图识别

用户输入分类：
- **创建类**：创建知识库、创建文档
- **查询类**：搜索文档、查询知识库
- **管理类**：更新、删除、移动
- **分析类**：统计分析、生成报告
- **组合类**：多个操作的组合

#### 3.5.2 实体提取

从用户输入中提取：
- **知识库名称/ID**：如"Python教程"
- **文档名称/ID**：如"异步编程指南.pdf"
- **操作参数**：如"批量上传5个文件"
- **条件约束**：如"最近7天上传的文档"

---

## 4. 后端实现设计

### 4.1 服务层设计

#### 4.1.1 AgentService

```python
class AgentService:
    """智能Agent服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ollama_service = OllamaService(db)
        self.tool_registry = ToolRegistry()
    
    async def process_user_request(
        self, user_id: int, request: str, session_id: str,
        context: Optional[Dict] = None
    ) -> AgentTask:
        """
        处理用户请求，创建并执行Agent任务
        
        流程：
        1. 理解用户意图
        2. 分解任务为步骤
        3. 创建Agent任务
        4. 开始执行任务
        """
    
    async def execute_task(self, task_id: int) -> AgentTask:
        """执行Agent任务（异步）"""
    
    async def execute_step(
        self, task_id: int, step: TaskStep
    ) -> TaskStep:
        """执行单个步骤"""
    
    async def call_tool(
        self, tool_name: str, tool_input: Dict, user_id: int
    ) -> Dict:
        """调用工具"""
    
    async def confirm_task_step(
        self, task_id: int, step_id: int, confirmed: bool,
        modified_input: Optional[Dict] = None
    ) -> AgentTask:
        """用户确认任务步骤"""
    
    async def get_task_status(self, task_id: int) -> Dict:
        """获取任务状态"""
    
    async def pause_task(self, task_id: int) -> AgentTask:
        """暂停任务"""
    
    async def resume_task(self, task_id: int) -> AgentTask:
        """恢复任务"""
    
    async def cancel_task(self, task_id: int) -> AgentTask:
        """取消任务"""
```

#### 4.1.2 TaskDecompositionService

```python
class TaskDecompositionService:
    """任务分解服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ollama_service = OllamaService(db)
    
    async def decompose_task(
        self, user_request: str, available_tools: List[str],
        context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        将用户任务分解为步骤
        
        返回步骤列表：
        [
            {
                "step_number": 1,
                "step_type": "tool_call",
                "tool_name": "...",
                "tool_input": {...},
                "description": "..."
            }
        ]
        """
```

#### 4.1.3 ToolRegistry

```python
class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools = {}
        self._register_default_tools()
    
    def register_tool(self, tool_name: str, tool_func: Callable):
        """注册工具"""
    
    def get_tool(self, tool_name: str) -> Optional[Callable]:
        """获取工具"""
    
    def list_tools(self) -> List[Dict]:
        """列出所有可用工具"""
    
    def get_tool_description(self, tool_name: str) -> str:
        """获取工具描述（用于LLM理解）"""
    
    def _register_default_tools(self):
        """注册默认工具"""
        # 注册所有可用的工具
```

### 4.2 任务层设计

#### 4.2.1 Celery任务

```python
@celery_app.task(bind=True)
def execute_agent_task_task(self, task_id: int):
    """执行Agent任务的异步任务"""
    # 1. 获取任务信息
    # 2. 依次执行每个步骤
    # 3. 根据步骤结果决定下一步
    # 4. 如果需要用户确认，暂停任务
    # 5. 更新任务状态
```

### 4.3 API层设计

#### 4.3.1 Agent任务接口

```
POST /api/v1/agent/chat
  - 用户发送消息，Agent处理并执行任务
Request Body:
{
  "message": "帮我创建一个Python知识库",
  "session_id": "session_123"  // 可选，用于多轮对话
}

Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": 123,
    "response": "我已经开始为您创建知识库...",
    "status": "executing",
    "requires_confirmation": false
  }
}

GET /api/v1/agent/tasks/{task_id}
  - 获取任务状态

POST /api/v1/agent/tasks/{task_id}/confirm
  - 确认需要确认的步骤
Request Body:
{
  "step_id": 1,
  "confirmed": true,
  "modified_input": {}  // 可选，修改输入参数
}

POST /api/v1/agent/tasks/{task_id}/pause
  - 暂停任务

POST /api/v1/agent/tasks/{task_id}/resume
  - 恢复任务

POST /api/v1/agent/tasks/{task_id}/cancel
  - 取消任务

GET /api/v1/agent/tasks
  - 获取用户的任务列表
Query Parameters:
  - status: string (可选)
  - page: int = 1
  - size: int = 20
```

#### 4.3.2 对话历史接口

```
GET /api/v1/agent/conversations/{session_id}
  - 获取会话历史

DELETE /api/v1/agent/conversations/{session_id}
  - 清空会话历史
```

---

## 5. 前端实现设计

### 5.1 Agent聊天界面

**组件位置**：`src/views/Agent/Chat.vue`

**功能**：
1. **聊天消息区**
   - 显示用户消息和Agent回复
   - 显示任务执行进度
   - 显示工具调用信息

2. **输入区域**
   - 文本输入框
   - 语音输入（可选）
   - 快捷命令按钮

3. **任务状态面板**
   - 显示当前任务进度
   - 显示任务步骤列表
   - 显示执行结果

4. **确认对话框**
   - 当需要用户确认时弹出
   - 显示操作详情
   - 支持修改参数

### 5.2 任务管理页面

**组件位置**：`src/views/Agent/Tasks.vue`

**功能**：
- 任务列表：显示所有Agent任务
- 任务筛选：按状态、类型筛选
- 任务详情：查看任务执行详情
- 任务操作：暂停、恢复、取消

### 5.3 对话历史页面

**组件位置**：`src/views/Agent/Conversations.vue`

**功能**：
- 会话列表：显示所有对话会话
- 会话详情：查看对话历史
- 会话操作：删除会话、导出对话

---

## 6. 使用场景示例

### 场景1：创建知识库并上传文档

```
用户："帮我创建一个关于Python异步编程的知识库，并上传文档 async_programming.pdf"

Agent处理：
1. 检查是否已有"Python异步编程"知识库
2. 创建新知识库（如果没有）
3. 上传文档 async_programming.pdf
4. 生成知识库摘要
5. 返回结果："已创建知识库'Python异步编程'，并上传了文档 async_programming.pdf"
```

### 场景2：搜索并分析

```
用户："在Python知识库中搜索'异步编程'相关内容，并总结一下"

Agent处理：
1. 搜索知识库中的相关内容
2. 获取搜索结果
3. 使用LLM总结搜索结果
4. 返回总结报告
```

### 场景3：批量操作

```
用户："把我最近上传的10个PDF文档都移动到'技术文档'知识库"

Agent处理：
1. 查询用户最近上传的10个PDF文档
2. 检查目标知识库是否存在
3. 逐个移动文档（需要用户确认批量操作）
4. 返回操作结果
```

### 场景4：多轮对话

```
用户："创建一个Python知识库"
Agent："已创建知识库'Python'，ID为123"

用户："再上传文档 tutorial.pdf"
Agent："已在知识库'Python'中上传文档 tutorial.pdf"

用户："现在搜索一下关于异步的内容"
Agent："在知识库'Python'中搜索到3个相关文档..."
```

---

## 7. 实施步骤

### 阶段一（2-3周）：基础框架

1. **数据库设计与迁移**
   - 创建 Agent 任务表、步骤表、对话表
   - 编写数据库迁移脚本

2. **工具系统**
   - 实现 ToolRegistry
   - 实现基础工具（知识库、文档管理）
   - 实现工具调用接口

3. **基础服务**
   - 实现 AgentService 基础方法
   - 实现任务创建和查询接口
   - 实现基础的任务执行逻辑

4. **前端基础页面**
   - 实现聊天界面
   - 实现任务列表页面
   - 实现基础的消息显示

### 阶段二（2-3周）：任务分解与执行

1. **任务分解**
   - 实现 TaskDecompositionService
   - 实现基于LLM的任务分解
   - 实现步骤执行逻辑

2. **上下文管理**
   - 实现对话历史管理
   - 实现任务上下文存储
   - 实现多轮对话支持

3. **错误处理与验证**
   - 实现错误处理机制
   - 实现结果验证逻辑
   - 实现重试机制

4. **前端优化**
   - 实现任务进度展示
   - 实现确认对话框
   - 优化用户体验

### 阶段三（1-2周）：高级功能

1. **自然语言理解增强**
   - 优化意图识别
   - 增强实体提取
   - 支持复杂查询

2. **智能决策**
   - 实现智能决策逻辑
   - 实现自动验证
   - 实现任务优化

3. **性能优化**
   - 优化任务执行性能
   - 实现任务缓存
   - 优化LLM调用

---

## 8. 技术依赖

### 后端依赖

- **LLM服务**：Ollama（用于任务分解、意图理解）
- **数据库**：MySQL（存储任务和对话）
- **任务队列**：Celery（异步执行任务）

### 前端依赖

- **UI组件**：Element Plus（聊天界面组件）
- **可选：Markdown渲染**：用于显示Agent回复中的Markdown内容

---

## 9. 性能考虑

### 9.1 任务执行性能

- **异步执行**：所有任务异步执行，不阻塞用户
- **批量操作**：合并多个小步骤为批量操作
- **缓存策略**：缓存常用查询结果

### 9.2 LLM调用优化

- **批量处理**：合并多个LLM调用
- **缓存结果**：缓存任务分解结果
- **超时控制**：设置LLM调用超时

---

## 10. 安全与权限

### 10.1 权限控制

- Agent 只能执行用户有权限的操作
- 所有工具调用都需验证用户权限
- 记录所有Agent操作的审计日志

### 10.2 数据隔离

- Agent 任务按用户隔离
- 只能访问用户有权限的知识库和文档

---

## 11. 未来扩展

### 11.1 高级规划算法

- 支持 Tree of Thoughts 等高级规划算法
- 支持任务并行执行
- 支持任务依赖关系

### 11.2 多Agent协作

- 支持多个Agent协作完成任务
- 支持Agent间的通信和协调

### 11.3 工具扩展

- 支持用户自定义工具
- 支持外部API调用工具
- 支持数据库查询工具

---

**文档版本**：v0.1  
**创建日期**：2025-01-28  
**最后更新**：2025-01-28  
**状态**：草案

