# Word 文档处理流程梳理

## 整体流程概览

Word 文档处理流程分为以下几个主要阶段：

1. **文档下载** → 从 MinIO 下载原始文件
2. **文档解析** → 提取文本、表格、图片等元素
3. **文档分块** → 将解析结果按结构分块
4. **目录提取** → 提取文档目录（TOC）
5. **图片处理** → 图片 OCR、向量化、存储
6. **向量化** → 为每个分块生成向量
7. **索引建立** → 将向量和元数据写入 OpenSearch

---

## 详细流程

### 1. 文档下载阶段

**位置**: `spx-knowledge-backend/app/tasks/document_tasks.py` (第73-98行)

**流程**:
- 从 MinIO 下载文档文件到临时目录
- 创建临时文件用于后续解析
- 记录下载时间和文件大小

**关键代码**:
```python
minio_service = MinioStorageService()
file_content = minio_service.download_file(document.file_path)
```

---

### 2. 文档解析阶段

**位置**: `spx-knowledge-backend/app/tasks/document_tasks.py` (第105-144行)
**服务**: `spx-knowledge-backend/app/services/docx_service.py` (第241-710行)

**流程**:
1. **DOCX 降噪处理**（可选）:
   - 调用 `DocxService.sanitize_docx()` 清理文档
   - 移除目录页、页眉页脚等干扰元素
   - 生成降噪后的 DOCX 副本

2. **解析文档结构**:
   - 使用 `python-docx` 库解析 DOCX 文件
   - 按顺序遍历段落、表格、图片等元素
   - 为每个元素分配 `element_index` 和 `doc_order`

3. **提取内容**:
   - **文本**: 提取段落文本，识别标题样式（Heading 1-6, 标题1-6）
   - **表格**: 提取表格数据，转换为结构化 JSON
   - **图片**: 提取图片二进制数据和元数据

4. **构建元素列表**:
   - `ordered_elements`: 完整的有序元素列表
   - `filtered_elements_light`: 轻量级元素列表（用于分块）
   - `text_element_index_map`: 文本元素的索引映射
   - `images_payload`: 图片二进制数据
   - `tables`: 表格数据

**关键数据结构**:
```python
parse_result = {
    'text_content': str,  # 完整文本内容
    'ordered_elements': List[Dict],  # 有序元素列表
    'filtered_elements_light': List[Dict],  # 轻量级元素列表
    'text_element_index_map': List[Dict],  # 文本索引映射
    'images': List[Dict],  # 图片数据
    'tables': List[Dict],  # 表格数据
    'metadata': {
        'element_count': int,  # 元素总数
    }
}
```

---

### 3. 文档分块阶段

**位置**: `spx-knowledge-backend/app/tasks/document_tasks.py` (第217-415行)
**服务**: `spx-knowledge-backend/app/services/docx_service.py` (第539-709行)

**流程**:

#### 3.1 DOCX 顺序分块（主要逻辑）

1. **文本缓冲分块**:
   - 遍历 `ordered_elements`，按顺序处理文本元素
   - 使用 `text_buffer` 累积文本，当达到 `chunk_max`（默认1024字符）时生成分块
   - 记录每个分块的 `element_index_start` 和 `element_index_end`

2. **表格处理**:
   - 遇到表格元素时，先 `flush_text_buffer()` 清空文本缓冲
   - 表格单独作为一个分块，类型为 `table`
   - 表格数据保存到 `document_tables` 表
   - 如果表格行数 > 400，会进行分片处理

3. **图片处理**:
   - 遇到图片元素时，先 `flush_text_buffer()` 清空文本缓冲
   - 图片单独作为一个分块，类型为 `image`
   - 记录 `element_index` 用于后续回填图片元数据

4. **合并和排序**:
   - 将所有分块（文本、表格、图片）合并到 `merged_items`
   - 按 `pos`（位置值）排序，确保顺序正确
   - 去重：确保每个 `element_index` 仅生成一个分块

5. **保存到数据库**:
   - 将分块保存到 `document_chunks` 表
   - 保存分块元数据（`meta` 字段，JSON 格式）
   - 建立父子关系（`chunk_relations` 表）

6. **归档到 MinIO**:
   - 将分块数据归档到 MinIO（`chunks.jsonl.gz`）
   - 包含 `element_index` 信息，用于后续流式读取

**关键代码**:
```python
# 文本缓冲分块
def flush_text_buffer():
    # 当文本累积达到 chunk_max 时，生成分块
    if current_len >= chunk_max:
        emit_chunk()

# 表格/图片处理
if elem_type == 'table':
    flush_text_buffer()  # 先清空文本缓冲
    # 创建表格分块
elif elem_type == 'image':
    flush_text_buffer()  # 先清空文本缓冲
    # 创建图片分块
```

**分块元数据结构**:
```python
chunk_meta = {
    'element_index_start': int,  # 文本块的起始元素索引
    'element_index_end': int,  # 文本块的结束元素索引
    'element_index': int,  # 表格/图片的元素索引
    'doc_order_start': int,  # 文档顺序起始
    'doc_order_end': int,  # 文档顺序结束
    'chunk_index': int,  # 分块索引
    'table_id': str,  # 表格ID（仅表格块）
    'image_id': int,  # 图片ID（仅图片块，后续回填）
    'image_path': str,  # 图片路径（仅图片块，后续回填）
}
```

---

### 4. 目录提取阶段

**位置**: `spx-knowledge-backend/app/tasks/document_tasks.py` (第1220-1230行)
**服务**: `spx-knowledge-backend/app/services/document_toc_service.py`

**流程**:
1. **PDF 目录提取**:
   - 使用 `PyPDF2` 解析 PDF 书签
   - 提取标题、页码、层级关系
   - 构建树形结构

2. **Word 目录提取**:
   - 遍历文档段落，识别标题样式（Heading 1-6, 标题1-6）
   - 根据标题级别构建层级结构
   - 记录 `paragraph_index` 用于定位

3. **保存到数据库**:
   - 保存到 `document_toc` 表
   - 建立父子关系（`parent_id`）

**注意**: 目录提取是简化版本，仅保留提取功能，不进行与分块的关联。

---

### 5. 图片处理阶段

**位置**: `spx-knowledge-backend/app/tasks/document_tasks.py` (第973-1198行)

**流程**:
1. **图片持久化**:
   - 从解析结果中获取图片二进制数据
   - 计算 SHA256 哈希值，检查是否已存在
   - 保存图片到 MinIO
   - 保存图片元数据到 `document_images` 表

2. **图片 OCR**:
   - 对图片进行 OCR 识别，提取文本
   - 保存 OCR 文本到 `document_images.ocr_text`

3. **图片向量化**:
   - 生成图片向量（512维）
   - 如果图片已存在，复用已有向量

4. **图片索引**:
   - 将图片向量和元数据写入 OpenSearch
   - 索引名称: `images`

5. **回填图片元数据到分块**:
   - 根据 `element_index` 找到对应的图片分块
   - 更新分块的 `meta` 字段，添加 `image_id` 和 `image_path`

**关键代码**:
```python
# 回填图片元数据
if element_index is not None:
    chunk_row = image_chunk_rows.get(element_index)
    if chunk_row:
        # 更新分块 meta，添加 image_id 和 image_path
        existing_meta.update({
            'image_id': image_row.id,
            'image_path': image_row.image_path,
        })
```

---

### 6. 向量化阶段

**位置**: `spx-knowledge-backend/app/tasks/document_tasks.py` (第1205-1459行)

**流程**:
1. **读取分块内容**:
   - 如果 `STORE_CHUNK_TEXT_IN_DB=True`，从数据库读取
   - 否则从 MinIO 的 `chunks.jsonl.gz` 流式读取

2. **处理表格块**:
   - 从 `meta.table_data` 中提取完整的表格数据
   - 将表格单元格数据转换为文本（制表符分隔）
   - 如果表格数据不存在，尝试从 HTML 解析

3. **生成向量**:
   - 调用 `VectorService.generate_embedding()` 生成文本向量
   - 向量维度: 768（默认配置）
   - 如果 Ollama 不可用，返回空列表（允许继续索引文本）

4. **构建索引文档**:
   - 包含分块内容、向量、元数据等
   - 准备批量写入 OpenSearch

**关键代码**:
```python
# 生成向量
vector = vector_service.generate_embedding(chunk_text)

# 构建索引文档
chunk_doc = {
    "document_id": document_id,
    "chunk_id": chunk.id,
    "knowledge_base_id": document.knowledge_base_id,
    "content": chunk_text,
    "chunk_type": chunk.chunk_type,
    "metadata": chunk_metadata,  # JSON 字符串
    "content_vector": vector,  # 768维向量
    "created_at": chunk.created_at.isoformat(),
}
```

---

### 7. 索引建立阶段

**位置**: `spx-knowledge-backend/app/tasks/document_tasks.py` (第1460-1500行)

**流程**:
1. **批量写入 OpenSearch**:
   - 使用 `OpenSearchService.index_document_chunk_sync()` 批量索引
   - 索引名称: `document_chunks`
   - 每批处理多个分块，提高效率

2. **更新文档状态**:
   - 文档状态更新为 `DOC_STATUS_COMPLETED`
   - 处理进度更新为 100%

**关键代码**:
```python
# 批量索引
opensearch_service.bulk_index_document_chunks(docs_to_index)

# 更新文档状态
document.status = DOC_STATUS_COMPLETED
document.processing_progress = 100.0
```

---

## 数据流图

```
Word 文档 (MinIO)
    ↓
[1. 下载] → 临时文件
    ↓
[2. 解析] → DocxService.parse_document()
    ├─→ ordered_elements (有序元素列表)
    ├─→ filtered_elements_light (轻量级元素)
    ├─→ images (图片数据)
    └─→ tables (表格数据)
    ↓
[3. 分块] → 顺序分块逻辑
    ├─→ 文本分块 (text)
    ├─→ 表格分块 (table) → document_tables 表
    └─→ 图片分块 (image)
    ↓
[4. 保存] → document_chunks 表
    ├─→ 分块内容（可选）
    ├─→ 分块元数据 (meta, JSON)
    └─→ 归档到 MinIO (chunks.jsonl.gz)
    ↓
[5. 图片处理] → ImageService
    ├─→ 保存到 MinIO
    ├─→ 保存到 document_images 表
    ├─→ OCR 识别
    ├─→ 向量化 (512维)
    ├─→ 索引到 OpenSearch (images)
    └─→ 回填到图片分块 (image_id, image_path)
    ↓
[6. 向量化] → VectorService
    ├─→ 读取分块内容
    ├─→ 生成向量 (768维)
    └─→ 构建索引文档
    ↓
[7. 索引] → OpenSearchService
    ├─→ 批量写入 OpenSearch (document_chunks)
    └─→ 更新文档状态
    ↓
完成
```

---

## 关键数据结构

### 1. 分块类型 (chunk_type)
- `text`: 文本分块
- `table`: 表格分块
- `image`: 图片分块

### 2. 元素索引 (element_index)
- 每个解析出的元素都有唯一的 `element_index`
- 用于关联分块和原始元素
- 用于图片回填和位置验证

### 3. 文档顺序 (doc_order)
- 每个元素在文档中的顺序
- 用于分块排序和位置计算

### 4. 分块元数据 (meta)
```json
{
  "element_index_start": 1,
  "element_index_end": 5,
  "element_index": 10,  // 仅表格/图片
  "doc_order_start": 0,
  "doc_order_end": 4,
  "chunk_index": 0,
  "table_id": "uuid",  // 仅表格
  "image_id": 123,  // 仅图片（后续回填）
  "image_path": "path/to/image.png"  // 仅图片（后续回填）
}
```

---

## 配置参数

### 分块大小
- `CHUNK_SIZE`: 默认 1000 字符
- `TEXT_EMBED_MAX_CHARS`: 默认 1024 字符
- 实际使用: `min(CHUNK_SIZE, TEXT_EMBED_MAX_CHARS)`

### 存储配置
- `STORE_CHUNK_TEXT_IN_DB`: 是否在数据库存储分块正文
  - `True`: 从数据库读取分块内容
  - `False`: 从 MinIO 流式读取分块内容

### 表格分片
- `MAX_ROWS_PER_PART`: 400 行
- 超过 400 行的表格会分片存储

---

## 错误处理

1. **解析失败**: 记录错误日志，文档状态设为 `DOC_STATUS_FAILED`
2. **分块失败**: 记录警告，继续处理其他分块
3. **图片处理失败**: 记录警告，不影响主流程
4. **向量化失败**: 记录错误，跳过该分块，继续处理其他分块
5. **索引失败**: 记录错误，但允许部分成功

---

## 性能优化

1. **流式读取**: 当不在数据库存储正文时，从 MinIO 流式读取分块内容
2. **批量索引**: 批量写入 OpenSearch，提高索引效率
3. **向量复用**: 相同图片复用已有向量，避免重复计算
4. **分片存储**: 大表格分片存储，避免单条记录过大

---

## 总结

Word 文档处理流程是一个完整的管道，从原始文档到可搜索的向量索引：

1. **解析** → 提取结构化内容
2. **分块** → 按结构智能分块
3. **向量化** → 生成语义向量
4. **索引** → 建立可搜索索引

整个过程保证了：
- 内容的完整性和顺序性
- 元数据的准确关联
- 高效的存储和检索

