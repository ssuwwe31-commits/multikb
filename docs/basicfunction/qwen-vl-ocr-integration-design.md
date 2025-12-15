# Qwen VL 模型 OCR 集成设计方案

> 目标：通过 Ollama 集成 Qwen2-VL 视觉语言模型，提升 OCR 识别准确率，特别是对复杂布局、中文文档、低质量图片的处理能力。支持在 `settings.py` 中灵活配置，保持与现有 OCR 系统的兼容性。

## 1. 背景与目标

### 1.1 当前 OCR 实现问题

**现状**：
- 使用 Tesseract 进行 OCR 识别，实现简单但准确率有限
- 缺少图片预处理步骤
- 未指定语言参数（应使用 `chi_sim+eng`）
- 对复杂场景（模糊、倾斜、复杂布局）识别效果差

**问题表现**：
- OCR 结果碎片化、乱码多
- 中文识别准确率低
- 复杂表格、手写文字识别困难

### 1.2 使用 Qwen VL 的优势

**技术优势**：
- **多模态理解**：不仅能识别文字，还能理解图片上下文、布局、表格结构
- **中英文混合识别**：对中文支持优秀，适合中文文档场景
- **复杂场景处理**：对模糊、倾斜、复杂布局的图片表现更好
- **结构化输出**：能理解文档结构（标题、段落、列表等），不只是文字提取
- **语义理解**：能理解图片内容，提供更准确的识别结果

**性能对比**：

| 方案 | 准确率 | 速度 | 资源需求 | 适用场景 |
|------|--------|------|----------|----------|
| Tesseract | ⭐⭐ | ⭐⭐⭐⭐⭐ | 低 | 清晰文档 |
| EasyOCR | ⭐⭐⭐ | ⭐⭐⭐⭐ | 中 | 一般场景 |
| **Qwen VL** | ⭐⭐⭐⭐⭐ | ⭐⭐ | 高（GPU推荐） | 复杂场景、高质量要求 |

### 1.3 设计目标

1. **可配置性**：通过 `settings.py` 灵活配置 OCR 引擎和模型
2. **兼容性**：保持与现有 OCR 系统的兼容，支持降级策略
3. **性能优化**：支持缓存、批量处理、异步调用
4. **错误处理**：完善的错误处理和降级机制

## 2. 技术方案

### 2.1 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    OCR 服务层                            │
│  ┌──────────────────────────────────────────────────┐  │
│  │  ImageService.extract_ocr_text()                 │  │
│  │  - 统一 OCR 入口                                  │  │
│  │  - 负责状态落库                                    │  │
│  │  - 失败重试与手动重试                              │  │
│  │  - 结果缓存与后处理                               │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                        │
                 ┌──────▼──────┐
                 │  Qwen VL    │
                 │  OCR Engine │
                 │              │
                 │ - 唯一OCR通路│
                 │ - 高准确率   │
                 └──────┬──────┘
                        │
               ┌────────▼────────┐
               │  OllamaService  │
               │  - extract_     │
               │    text_from_   │
               │    image()      │
               └────────┬────────┘
                        │
               ┌────────▼────────┐
               │    Ollama API   │
               │  - qwen2-vl:7b  │
               │  - qwen2-vl:2b  │
               └─────────────────┘
```

### 2.2 OCR 引擎选择策略

> **更新：**根据最新需求，平台将 **只使用 Qwen VL** 进行 OCR，不再调用 EasyOCR 或 Tesseract。以下策略保留作为扩展思路，当前版本仅实现“完全替换”方案。

**策略一：完全替换（当前方案）**
- 所有图片统一使用 Qwen VL 识别
- 失败时只做 Ollama 重试，不再回退其他 OCR 引擎

## 3. 配置设计

### 3.1 Settings 配置项

在 `app/config/settings.py` 中添加以下配置（★ 为新增需求）：

```python
# OCR 配置
OCR_ENGINE: str = "qwen_vl"  # 当前只启用 Qwen VL，其他值保留扩展
OCR_MAX_RETRIES: int = 1  # ★ Ollama 调用失败后自动重试次数（不含首轮）
OCR_RETRY_DELAY_SECONDS: int = 0  # ★ 重试前等待时间

# Qwen VL 模型配置
OLLAMA_OCR_MODEL: str = "qwen2-vl:7b"
OLLAMA_OCR_BASE_URL: Optional[str] = None
OLLAMA_OCR_TIMEOUT: int = 120
OLLAMA_OCR_MAX_RETRIES: int = 2  # Ollama HTTP 层面的重试

# OCR 图片预处理配置
OCR_PREPROCESS_ENABLED: bool = True
OCR_PREPROCESS_MAX_SIZE: int = 2048
OCR_PREPROCESS_DENOISE: bool = False  # 默认关闭，保留原图

# OCR 结果后处理配置
OCR_POSTPROCESS_ENABLED: bool = True
OCR_POSTPROCESS_MIN_CONFIDENCE: float = 0.3
OCR_POSTPROCESS_CLEAN_TEXT: bool = True

# OCR 缓存配置
OCR_CACHE_ENABLED: bool = True
OCR_CACHE_TTL: int = 86400

# OCR 批量处理配置
OCR_BATCH_SIZE: int = 1
OCR_BATCH_TIMEOUT: int = 300
```

### 3.2 配置说明

**OCR_ENGINE**：
- `"qwen_vl"`：当前默认值，也是唯一启用的路径
- 其他取值（`"tesseract"`, `"easyocr"`, `"auto"`, `"hybrid"`）暂不生效，仅在配置层保留占位，避免未来扩展时破坏兼容

**OLLAMA_OCR_MODEL**：
- `"qwen2-vl:2b"`: 2B 参数版本，速度快，适合 CPU
- `"qwen2-vl:7b"`: 7B 参数版本，准确率高，推荐 GPU
- `"qwen2-vl:72b"`: 72B 参数版本，最高准确率，需要大显存

**OCR_FALLBACK_ENABLED**：
- 当 Qwen VL 识别失败或超时时，自动降级到传统 OCR
- 确保系统稳定性

## 4. API 设计

### 4.1 OllamaService 扩展

在 `app/services/ollama_service.py` 中添加以下方法：

```python
async def extract_text_from_image(
    self,
    image: Union[Image.Image, str, bytes],
    model: Optional[str] = None,
    prompt: Optional[str] = None,
    timeout: Optional[int] = None
) -> str:
    """
    使用 Qwen VL 模型从图片中提取文字
    
    Args:
        image: PIL Image 对象、图片路径或图片字节数据
        model: 模型名称（默认使用 settings.OLLAMA_OCR_MODEL）
        prompt: OCR 提示词（默认使用内置提示词）
        timeout: 超时时间（默认使用 settings.OLLAMA_OCR_TIMEOUT）
    
    Returns:
        OCR 识别的文本内容
    """
    pass

async def extract_text_from_image_with_confidence(
    self,
    image: Union[Image.Image, str, bytes],
    model: Optional[str] = None,
    prompt: Optional[str] = None,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    使用 Qwen VL 模型从图片中提取文字（带置信度信息）
    
    Returns:
        {
            "text": str,  # OCR 文本
            "confidence": float,  # 置信度（0-1）
            "model": str,  # 使用的模型
            "processing_time": float  # 处理时间（秒）
        }
    """
    pass
```

### 4.2 ImageService 扩展

在 `app/services/image_service.py` 中修改 `extract_ocr_text` 方法：

```python
def extract_ocr_text(
    self,
    image_path: str,
    engine: Optional[str] = None,
    use_cache: bool = True
) -> str:
    """
    提取 OCR 文字（支持多种引擎）
    
    Args:
        image_path: 图片路径
        engine: OCR 引擎（可选，默认使用 settings.OCR_ENGINE）
        use_cache: 是否使用缓存
    
    Returns:
        OCR 识别的文本内容
    """
    pass

def extract_ocr_text_with_engine(
    self,
    image_path: str,
    engine: str
) -> Dict[str, Any]:
    """
    使用指定引擎提取 OCR 文字
    
    Args:
        image_path: 图片路径
        engine: OCR 引擎名称（"tesseract", "easyocr", "qwen_vl"）
    
    Returns:
        {
            "text": str,  # OCR 文本
            "engine": str,  # 使用的引擎
            "confidence": float,  # 置信度（如果支持）
            "processing_time": float  # 处理时间（秒）
        }
    """
    pass
```

## 5. 实现细节

### 5.1 Qwen VL OCR 实现流程

```
1. 图片预处理（可选）
   ├─ 尺寸调整（如果超过最大尺寸）
   ├─ 格式转换（确保 RGB 格式）
   └─ 去噪处理（如果启用）

2. 图片编码
   ├─ 读取图片文件
   ├─ 转换为 base64 编码
   └─ 准备 Ollama API 请求

3. 调用 Ollama API
   ├─ 构建请求（包含图片和 prompt）
   ├─ 发送 POST 请求到 /api/chat
   ├─ 处理响应
   └─ 提取 OCR 文本

4. 结果后处理（可选）
   ├─ 文本清理（去除乱码）
   ├─ 格式规范化
   └─ 置信度评估

5. 缓存结果（如果启用）
   └─ 保存到 Redis 缓存
```

### 5.2 Ollama API 调用格式

**请求格式**：
```json
{
  "model": "qwen2-vl:7b",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "请识别这张图片中的所有文字，保持原有格式和结构。如果图片中包含表格，请以表格形式输出。"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,iVBORw0KGgoAAAANS..."
          }
        }
      ]
    }
  ],
  "stream": false,
  "options": {
    "temperature": 0.1,  # 低温度，提高准确性
    "top_p": 0.9
  }
}
```

**响应格式**：
```json
{
  "model": "qwen2-vl:7b",
  "created_at": "2025-11-27T10:44:29.123456Z",
  "message": {
    "role": "assistant",
    "content": "识别出的文字内容..."
  },
  "done": true
}
```

### 5.3 图片预处理（可选）

**预处理步骤**（如果 `OCR_PREPROCESS_ENABLED=True`）：
1. **尺寸调整**：如果图片尺寸超过 `OCR_PREPROCESS_MAX_SIZE`，按比例缩放
2. **格式转换**：确保图片为 RGB 格式
3. **去噪处理**（如果 `OCR_PREPROCESS_DENOISE=True`）：
   - 使用中值滤波或高斯模糊去除噪点
   - 注意：Qwen VL 对原始图片处理效果更好，建议关闭去噪

**注意**：Qwen VL 模型对图片预处理的需求较低，通常直接使用原始图片效果更好。

### 5.4 结果后处理

**后处理步骤**（如果 `OCR_POSTPROCESS_ENABLED=True`）：
1. **文本清理**：
   - 去除明显的乱码字符
   - 合并被分割的单词
   - 修复常见 OCR 错误（如 `0` vs `O`，`1` vs `l`）

2. **置信度评估**：
   - 如果置信度低于 `OCR_POSTPROCESS_MIN_CONFIDENCE`，标记为低质量结果
   - 触发降级策略（如果启用）

3. **格式规范化**：
   - 统一换行符
   - 去除多余空格
   - 保持原有段落结构

### 5.5 缓存机制

**缓存策略**（如果 `OCR_CACHE_ENABLED=True`）：
1. **缓存键**：使用图片的 SHA256 哈希值作为缓存键
2. **缓存值**：存储 OCR 文本和元数据（置信度、处理时间等）
3. **缓存过期**：根据 `OCR_CACHE_TTL` 设置过期时间
4. **缓存更新**：如果图片被重新处理，更新缓存

**缓存格式**：
```json
{
  "text": "OCR 识别的文本内容",
  "engine": "qwen_vl",
  "model": "qwen2-vl:7b",
  "confidence": 0.95,
  "processing_time": 2.34,
  "timestamp": "2025-11-27T10:44:29Z"
}
```

### 5.6 MySQL 状态字段与重试记录（★ 新增）

为便于前后端展示与重试，需在 `document_images`（或对应图片表）新增/确认以下字段：

| 字段名 | 类型 | 说明 |
| --- | --- | --- |
| `status` | `VARCHAR(20)` | `pending` / `processing` / `completed` / `failed` |
| `retry_count` | `INT` | 已执行的重试次数（不含第一次调用） |
| `error_message` | `TEXT` | 最近一次失败原因（截断到 1KB） |
| `last_processed_at` | `DATETIME` | 最近一次完成（成功或失败）的时间戳 |

**状态流转：**
1. **初始化**：上传或解析阶段插入记录，`status=pending`，`retry_count=0`。
2. **开始处理**：任务启动时更新为 `processing`，写入 `last_processed_at=NOW()`。
3. **成功**：写入 OCR 文本与元数据，`status=completed`。
4. **失败**：
   - 若 `retry_count < OCR_MAX_RETRIES` → 增加 `retry_count`，延迟重试
   - 否则 `status=failed`，写入 `error_message`，等待人工触发重试

**手动重试 API（后续实现）：**
- `POST /api/images/{image_id}/retry-ocr`
- 权限校验后将记录重置为 `pending` 并重新投递任务；重试成功后需：
  1. 更新 `document_images.ocr_text`、`status=completed`、`last_processed_at`
  2. 重新生成图片向量（CLIP/ResNet 等）并写回 OpenSearch `images` 索引（覆盖旧向量）
  3. 将最新的 `image_id/image_path`、OCR 文本引用回填到关联的分块 `meta`

## 6. 错误处理与降级策略

### 6.1 错误处理

**错误类型**：
1. **Ollama 服务不可用**：连接失败、超时
2. **模型不存在**：指定的 Qwen VL 模型未安装
3. **图片格式错误**：无法读取或处理图片
4. **API 调用失败**：Ollama API 返回错误

**处理策略**：
1. **重试机制**：根据 `OCR_MAX_RETRIES` + `OCR_RETRY_DELAY_SECONDS` 进行业务层重试；每次失败都会记录 `retry_count` 和 `error_message`。
2. **HTTP 重试**：`OLLAMA_OCR_MAX_RETRIES` 作用于 Ollama HTTP 请求层，确保网络抖动时及时补偿。
3. **状态落库**：所有失败都会记录为 `failed` 状态，由前端/运维手动触发重试。
4. **日志追踪**：携带 `image_id`、`document_id`、`retry_count`、`status`，便于排查。

### 6.2 手动重试与告警

- 自动重试耗尽后，记录置为 `failed`，前端提示“重新识别”按钮。
- 触发 `POST /api/images/{image_id}/retry-ocr`：
  1. 将 `status` 重置为 `pending`、`retry_count` 清零或按策略累加。
  2. 推送 Celery 任务重新执行 OCR。
  3. 操作全程写审计日志，确保可追踪。
- 可在告警系统中订阅 `status=failed` 的图片，及时反馈给运维/标注人员。

## 7. 性能优化

### 7.1 异步处理

- OCR 识别是耗时操作，应使用异步方法
- 在 Celery 任务中异步调用 OCR
- 支持并发处理多张图片

### 7.2 批量处理

- 虽然 Qwen VL 暂不支持批量 API，但可以通过并发处理多张图片
- 使用 `asyncio.gather()` 并发调用多个 OCR 请求

### 7.3 资源管理

- **GPU 资源**：如果有 GPU，优先使用 GPU 加速
- **内存管理**：及时释放图片内存，避免内存泄漏
- **连接池**：复用 Ollama API 连接，减少连接开销

### 7.4 缓存优化

- 使用 Redis 缓存 OCR 结果
- 根据图片哈希值判断是否已识别
- 减少重复识别，提升处理速度

## 8. 兼容性考虑

### 8.1 向后兼容

- 保持现有 `ImageService.extract_ocr_text()` 方法签名不变
- 默认行为可通过配置控制
- 现有调用代码无需修改

### 8.2 渐进式迁移

- 支持逐步从传统 OCR 迁移到 Qwen VL
- 可以通过配置控制使用比例
- 支持 A/B 测试，对比不同引擎效果

### 8.3 多引擎支持

- 同时支持 Tesseract、EasyOCR、Qwen VL
- 可以根据场景选择最合适的引擎
- 支持结果融合，提高准确率

> **说明**：当前版本只启用 Qwen VL，其余能力暂未开放，但代码架构保留可扩展性。

### 8.4 前端展示与手动重试（★ 新增）

- 图片详情面板新增以下信息：
  - 处理状态（Tag/Badge）
  - 最近处理时间
  - 重试次数
  - 失败原因（可折叠展示）
- 当状态为 `failed` 时，显示“重新识别”按钮，调用 `POST /api/images/{image_id}/retry-ocr`
  - 点击后提示“任务已触发”，前端可轮询或等待 WebSocket/轮询刷新
  - 按钮在 `processing` 状态时置灰，避免重复触发
- **图片管理列表**（上图示例）中卡片展示增强：
  - 显示 OCR 文本的前几行摘要（或“查看全文”链接）
  - 显示图片向量化状态（如“已向量化/待向量化/失败”）
  - 显示最近处理时间、文件大小等元信息
  - 成功状态 (`status=completed`) 图片的重试按钮隐藏或禁用

## 9. 实施步骤

### 9.1 第一阶段：基础集成

1. **配置添加**：
   - 在 `settings.py` 中添加 OCR 相关配置项
   - 设置默认值为 Qwen VL

2. **OllamaService 扩展**：
   - 实现 `extract_text_from_image()` 方法
   - 实现 `extract_text_from_image_with_confidence()` 方法
   - 添加错误处理和重试机制

3. **ImageService 修改**：
   - 修改 `extract_ocr_text()` 方法，支持引擎选择
   - 添加 `extract_ocr_text_with_engine()` 方法
   - 实现降级策略

4. **测试验证**：
   - 单元测试：测试各个方法
   - 集成测试：测试完整 OCR 流程
   - 性能测试：测试处理速度和资源消耗

### 9.2 第二阶段：优化增强

1. **缓存机制**：
   - 实现 Redis 缓存
   - 添加缓存命中率统计

2. **预处理优化**：
   - 实现图片预处理流程
   - 优化预处理参数

3. **后处理优化**：
   - 实现文本清理和格式化
   - 添加置信度评估

4. **监控告警**：
   - 添加 OCR 处理时间监控
   - 添加错误率监控
   - 添加缓存命中率监控

### 9.3 第三阶段：高级功能

1. **智能选择**：
   - 实现基于图片特征的引擎选择
   - 添加图片质量评估

2. **结果融合**：
   - 实现多引擎结果融合
   - 添加置信度加权算法

3. **批量优化**：
   - 优化批量处理流程
   - 添加并发控制

## 10. 测试方案

### 10.1 单元测试

- 测试 `OllamaService.extract_text_from_image()` 方法
- 测试 `ImageService.extract_ocr_text()` 方法
- 测试错误处理和降级策略
- 测试缓存机制

### 10.2 集成测试

- 测试完整 OCR 流程（从图片到文本）
- 测试不同图片格式（PNG、JPG、PDF 等）
- 测试不同场景（清晰、模糊、复杂布局等）

### 10.3 性能测试

- 测试处理速度（单张图片、批量图片）
- 测试资源消耗（CPU、内存、GPU）
- 测试并发处理能力

### 10.4 准确率测试

- 对比不同 OCR 引擎的准确率
- 测试不同场景下的识别效果
- 收集用户反馈，持续优化

## 11. 监控与运维

### 11.1 监控指标

- **处理时间**：OCR 处理平均时间、P95、P99
- **成功率**：OCR 识别成功率
- **错误率**：各种错误类型的统计
- **缓存命中率**：OCR 缓存命中率
- **资源使用**：CPU、内存、GPU 使用率

### 11.2 日志记录

- 记录 OCR 处理开始和结束时间
- 记录使用的引擎和模型
- 记录错误信息和堆栈跟踪
- 记录性能指标

### 11.3 告警规则

- OCR 处理时间超过阈值
- OCR 错误率超过阈值
- Ollama 服务不可用
- 缓存命中率过低

## 12. 注意事项

### 12.1 资源需求

- **Qwen2-VL-2B**：约 2GB 内存，适合 CPU
- **Qwen2-VL-7B**：约 7GB 内存，推荐 GPU（至少 8GB 显存）
- **Qwen2-VL-72B**：约 72GB 内存，需要大显存（至少 80GB）

### 12.2 性能考虑

- Qwen VL 处理速度比传统 OCR 慢（通常 2-5 秒/张）
- 建议使用异步处理和任务队列
- 对于大批量处理，考虑使用 GPU 加速

### 12.3 成本优化

- 使用缓存减少重复识别
- 根据图片重要性选择引擎
- 考虑使用较小的模型（2B）平衡速度和准确率

### 12.4 模型管理

- 确保 Ollama 中已安装 Qwen VL 模型
- 定期更新模型版本
- 监控模型性能，及时调整配置

## 13. 后续优化方向

### 13.1 模型优化

- 针对特定文档类型进行 fine-tuning
- 使用量化模型减少资源消耗
- 探索更小的模型（如 Qwen2-VL-1.5B）

### 13.2 功能扩展

- 支持表格结构化识别
- 支持手写文字识别
- 支持多语言识别
- 支持图片内容理解（不只是文字）

### 13.3 架构优化

- 支持分布式 OCR 处理
- 支持 OCR 结果实时流式输出
- 支持 OCR 结果的可视化展示

### 13.4 风险与注意事项（★ 新增）

1. **重试控制**
   - 业务层（`OCR_MAX_RETRIES`）与 HTTP 层（`OLLAMA_OCR_MAX_RETRIES`）要区分，避免嵌套导致处理时间过长。
   - 建议在日志中记录每次重试的来源（业务/HTTP）与耗时，便于定位。
2. **手动重试限流**
   - `POST /api/images/{image_id}/retry-ocr` 建议做防抖与权限校验，必要时添加操作频率限制，避免频繁触发。
3. **错误信息处理**
   - `error_message` 字段需截断（如 1KB）并做脱敏，避免将模型返回的敏感信息直接暴露给前端或日志。
4. **前端状态刷新**
   - 前端可基于轮询或 WebSocket 更新状态，需与后端约定刷新间隔，防止轮询过于频繁。
5. **资源消耗监控**
   - Qwen VL 较耗 GPU/CPU，部署时需监控模型实例的资源使用率，避免 OCR 任务拖慢其它 LLM 功能。

## 14. 参考资源

- [Qwen2-VL 官方文档](https://github.com/QwenLM/Qwen2-VL)
- [Ollama 官方文档](https://ollama.ai/docs)
- [Ollama Python API](https://github.com/ollama/ollama-python)
- [Qwen2-VL 模型下载](https://ollama.ai/library/qwen2-vl)

---

**文档版本**：v1.0  
**创建日期**：2025-11-27  
**最后更新**：2025-11-27

