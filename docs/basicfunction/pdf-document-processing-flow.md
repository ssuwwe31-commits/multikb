# PDF 文档处理流程梳理

## 整体流程概览

PDF 文档处理流程分为以下几个主要阶段：

1. **文档上传** → 文件验证、重复检测、存储到 MinIO
2. **文档解析** → 使用 pdfplumber 和 PyMuPDF 提取文本、表格、图片
3. **文档分块** → 使用结构分块逻辑（复用 DocxService.chunk_text）
4. **目录提取** → 提取 PDF 书签（目录）
5. **图片处理** → 图片 OCR、向量化、存储
6. **向量化** → 为每个分块生成向量
7. **索引建立** → 将向量和元数据写入 OpenSearch

---

## 详细流程

### 1. 文档上传阶段

**位置**: `spx-knowledge-backend/app/api/v1/routes/documents.py` (第121-184行)
**服务**: `spx-knowledge-backend/app/services/document_service.py` (第72-213行)

**流程**:
1. **接收上传请求**:
   - 前端通过 `multipart/form-data` 上传文件
   - 参数包括: `file`, `knowledge_base_id`, `category_id`, `tags`, `metadata`

2. **文件验证**:
   - 格式验证: 检查文件扩展名和 MIME 类型
   - 大小检查: 默认最大 100MB
   - 安全扫描: 检查文件内容安全性
   - 计算 SHA256 哈希值

3. **重复检测**:
   - 根据文件名、文件大小、SHA256 哈希值检测重复
   - 如果完全重复，可选择拒绝或警告

4. **存储到 MinIO**:
   - 路径格式: `documents/{year}/{month}/{file_hash[:8]}/original/{filename}`
   - 保存原始 PDF 文件

5. **保存元数据到 MySQL**:
   - 创建 `Document` 记录
   - 状态设为 `uploaded`
   - 处理进度设为 0.0

6. **触发异步处理任务**:
   - 调用 `process_document_task.delay(document_id)`
   - 返回 `document_id` 和 `task_id`

**关键代码**:
```python
# 文件验证
validation_result = self.file_validation.validate_file(file)

# 重复检测
duplicate_result = self.duplicate_detection.check_duplicate_comprehensive(
    filename, file_size, file_hash
)

# 存储到 MinIO
storage_result = self.minio_storage.upload_original_file(file, file_hash)

# 触发异步任务
task = process_document_task.delay(document.id)
```

---

### 2. 文档解析阶段

**位置**: `spx-knowledge-backend/app/tasks/document_tasks.py` (第105-144行)
**服务**: `spx-knowledge-backend/app/services/pdf_service.py` (第154-565行)

**流程**:

#### 2.1 下载文件到临时目录
- 从 MinIO 下载 PDF 文件
- 保存到临时目录用于解析

#### 2.2 PDF 解析（使用 pdfplumber）

1. **提取文本和布局**:
   - 逐页处理 PDF
   - 使用 `pdfplumber` 提取单词（words）
   - 提取单词的坐标、字体大小、字体名称等信息

2. **构建文本行和段落**:
   - 按 `top` 坐标将单词分组为行（line_tolerance = 3.0）
   - 按垂直间距将行分组为段落（paragraph_tolerance = 10.0）
   - 计算每个段落的边界框（bbox）

3. **识别标题**:
   - 根据字体大小判断标题
   - 如果 `max_font_size >= avg_font_size * 1.2`，标记为 `Title`
   - 否则标记为 `NarrativeText`

4. **提取表格**:
   - 使用 `pdfplumber.find_tables()` 查找表格
   - 提取表格单元格数据
   - 如果表格无数据（只有表头），转换为文本
   - 合并相邻的表格（如果位置接近）

5. **提取图片**:
   - 使用 `PyMuPDF (fitz)` 提取图片
   - 获取图片的二进制数据和坐标信息
   - 记录图片在页面中的位置

6. **使用 Camelot 补充表格**（可选）:
   - 如果 `pdfplumber` 未检测到表格，使用 `camelot` 尝试提取
   - 支持 `lattice` 和 `stream` 两种模式

7. **过滤噪声**:
   - 过滤页眉页脚（出现在多页相同位置）
   - 过滤目录文本（识别目录特征）
   - 过滤装饰性文本（字符种类少、长度短）

8. **合并短文本**:
   - 合并相邻的短文本段落（长度 <= 60 字符）
   - 避免文本碎片化

**关键数据结构**:
```python
parse_result = {
    'text_content': str,  # 完整文本内容
    'tables': List[Dict],  # 表格数据
    'images': List[Dict],  # 图片数据
    'images_binary': List[Dict],  # 图片二进制数据
    'text_element_index_map': List[Dict],  # 文本索引映射（包含页码和坐标）
    'filtered_elements_light': List[Dict],  # 轻量级元素列表
    'metadata': {
        'element_count': int,  # 元素总数
        'images_count': int,  # 图片数量
        'source': 'pdf',  # 来源标识
    }
}
```

**文本元素索引映射**:
```python
text_element_index_map = [
    {
        'element_index': int,  # 元素索引
        'element_type': str,  # 'Title' | 'NarrativeText'
        'page_number': int,  # 页码（从1开始）
        'coordinates': {  # 归一化坐标（0-1）
            'x': float,
            'y': float,
            'width': float,
            'height': float,
        }
    }
]
```

**表格数据结构**:
```python
table = {
    'element_index': int,
    'table_data': {
        'cells': List[List[str]],  # 单元格数据
        'rows': int,  # 行数
        'columns': int,  # 列数
        'structure': 'pdf_extracted',  # 结构标识
        'html': None,  # PDF 表格无 HTML
    },
    'table_text': str,  # 表格文本（制表符分隔）
    'page_number': int,  # 页码
}
```

**图片数据结构**:
```python
image = {
    'data': bytes,  # 图片二进制数据
    'bytes': bytes,  # 同上
    'element_index': int,  # 元素索引（后续分配）
    'page_number': int,  # 页码
    'coordinates': Dict,  # 归一化坐标
    'bbox': Tuple[float, float, float, float],  # 原始坐标
    'page_width': float,  # 页面宽度
    'page_height': float,  # 页面高度
}
```

---

### 3. 文档分块阶段

**位置**: `spx-knowledge-backend/app/tasks/document_tasks.py` (第387-745行)

**流程**:

#### 3.1 PDF 分块（复用 DocxService.chunk_text）

1. **准备分块元素**:
   - 从 `filtered_elements_light` 创建 `LightElement` 对象
   - 包含 `category`, `text`, `element_index`

2. **调用结构分块**:
   - 使用 `DocxService.chunk_text()` 进行结构分块
   - 传入 `text_content`, `text_element_index_map`, `elements`
   - 分块大小: `min(CHUNK_SIZE, TEXT_EMBED_MAX_CHARS)` (默认 1024 字符)

3. **处理分块结果**:
   - 获取分块内容和元数据
   - 从 `chunks_metadata` 提取 `element_index_start`, `element_index_end`, `page_number`, `coordinates`

4. **构建合并项（merged_items）**:
   - **文本块**: 从分块结果构建，包含页码和坐标信息
   - **表格块**: 从 `tables` 数据构建，包含表格元数据
   - **图片块**: 从 `images` 数据构建，包含图片元数据

5. **排序和去重**:
   - 按 `pos`（位置值）排序
   - 去重：确保每个 `element_index` 仅生成一个分块

6. **保存到数据库**:
   - 保存到 `document_chunks` 表
   - 保存分块元数据（`meta` 字段，JSON 格式）
   - 建立父子关系（`chunk_relations` 表）

7. **归档到 MinIO**:
   - 将分块数据归档到 MinIO（`chunks.jsonl.gz`）
   - 包含 `element_index`, `page_number`, `coordinates` 信息

**关键代码**:
```python
# PDF 分块（复用 DocxService.chunk_text）
elements_for_chunking = [
    LightElement(elem.get('category'), elem.get('text', ''), elem.get('element_index', i))
    for i, elem in enumerate(filtered_elements_light)
]

chunks_with_index = DocxService(db).chunk_text(
    text_content,
    text_element_index_map=text_element_index_map,
    elements=elements_for_chunking
)
```

**分块元数据结构**:
```python
chunk_meta = {
    'element_index_start': int,  # 文本块的起始元素索引
    'element_index_end': int,  # 文本块的结束元素索引
    'element_index': int,  # 表格/图片的元素索引
    'page_number': int,  # 页码（PDF特有）
    'coordinates': Dict,  # 归一化坐标（PDF特有）
    'chunk_index': int,  # 分块索引
    'table_id': str,  # 表格ID（仅表格块）
    'image_id': int,  # 图片ID（仅图片块，后续回填）
    'image_path': str,  # 图片路径（仅图片块，后续回填）
}
```

---

### 4. 目录提取阶段

**位置**: `spx-knowledge-backend/app/tasks/document_tasks.py` (第1220-1230行)
**服务**: `spx-knowledge-backend/app/services/document_toc_service.py` (第21-67行)

**流程**:
1. **从 MinIO 下载 PDF**:
   - 使用 `MinioStorageService` 下载 PDF 文件

2. **使用 PyPDF2 解析书签**:
   - 打开 PDF 文件
   - 读取 `pdf_reader.outline`（书签/目录）
   - 递归解析嵌套的书签结构

3. **提取目录信息**:
   - 提取标题（title）
   - 提取页码（page_number）
   - 确定层级（level）
   - 建立父子关系（parent_id）

4. **保存到数据库**:
   - 保存到 `document_toc` 表
   - 建立树形结构

**关键代码**:
```python
pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
if pdf_reader.outline:
    for item in pdf_reader.outline:
        result = self._parse_outline_item(item, document_id, position, pdf_reader)
```

**目录数据结构**:
```python
toc_item = {
    'document_id': int,
    'level': int,  # 目录级别（1-6）
    'title': str,  # 标题
    'page_number': int,  # 页码
    'position': int,  # 位置（用于排序）
    'parent_id': int,  # 父级目录ID
}
```

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
# 图片处理
for img in images_meta:
    # 保存图片
    image_row = img_service.create_image_from_bytes(
        document_id,
        data,
        image_ext=img.get('ext', '.png'),
    )
    
    # 生成向量
    image_vector = vector_service.generate_image_embedding_prefer_memory(data)
    
    # 索引到 OpenSearch
    os_service.index_image_sync({
        "image_id": image_row.id,
        "image_vector": image_vector,
        "page_number": page_number,
        "coordinates": coordinates,
        ...
    })
    
    # 回填到分块
    chunk_row = image_chunk_rows.get(element_index)
    if chunk_row:
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
PDF 文档上传
    ↓
[1. 文件验证] → 格式、大小、安全性检查
    ↓
[2. 重复检测] → 文件名、大小、SHA256
    ↓
[3. 存储到 MinIO] → documents/{year}/{month}/{hash}/original/{filename}
    ↓
[4. 保存元数据] → MySQL (Document 表)
    ↓
[5. 触发异步任务] → Celery (process_document_task)
    ↓
[6. 下载文件] → 从 MinIO 下载到临时目录
    ↓
[7. PDF 解析] → PdfService.parse_document()
    ├─→ pdfplumber: 提取文本、表格
    ├─→ PyMuPDF: 提取图片
    └─→ Camelot: 补充表格（可选）
    ↓
[8. 分块] → DocxService.chunk_text() (复用)
    ├─→ 文本分块 (text)
    ├─→ 表格分块 (table) → document_tables 表
    └─→ 图片分块 (image)
    ↓
[9. 保存] → document_chunks 表
    ├─→ 分块内容（可选）
    ├─→ 分块元数据 (meta, JSON)
    └─→ 归档到 MinIO (chunks.jsonl.gz)
    ↓
[10. 目录提取] → DocumentTOCService.extract_toc_from_pdf()
    └─→ document_toc 表
    ↓
[11. 图片处理] → ImageService
    ├─→ 保存到 MinIO
    ├─→ 保存到 document_images 表
    ├─→ OCR 识别
    ├─→ 向量化 (512维)
    ├─→ 索引到 OpenSearch (images)
    └─→ 回填到图片分块 (image_id, image_path)
    ↓
[12. 向量化] → VectorService
    ├─→ 读取分块内容
    ├─→ 生成向量 (768维)
    └─→ 构建索引文档
    ↓
[13. 索引] → OpenSearchService
    ├─→ 批量写入 OpenSearch (document_chunks)
    └─→ 更新文档状态
    ↓
完成
```

---

## PDF 与 Word 处理的差异

### 1. 解析方式
- **PDF**: 使用 `pdfplumber` + `PyMuPDF` + `Camelot`
- **Word**: 使用 `python-docx`

### 2. 文本提取
- **PDF**: 基于坐标和字体信息提取，需要处理布局
- **Word**: 直接读取段落文本，保留样式信息

### 3. 表格提取
- **PDF**: 使用 `pdfplumber.find_tables()` 或 `Camelot`，需要识别表格边界
- **Word**: 直接读取表格对象，保留完整结构

### 4. 坐标信息
- **PDF**: 包含页面坐标（bbox）和归一化坐标（coordinates）
- **Word**: 使用 `element_index` 和 `doc_order`，无坐标信息

### 5. 页码信息
- **PDF**: 每个元素都有 `page_number`
- **Word**: 无页码概念（单文档）

### 6. 目录提取
- **PDF**: 从 PDF 书签（outline）提取
- **Word**: 从标题样式（Heading 1-6）提取

### 7. 分块逻辑
- **PDF**: 复用 `DocxService.chunk_text()`，但使用不同的元数据（页码、坐标）
- **Word**: 使用顺序分块逻辑，基于 `ordered_elements`

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

### 3. 页码和坐标（PDF 特有）
- `page_number`: 页码（从1开始）
- `coordinates`: 归一化坐标（0-1范围）
  ```python
  {
      "x": float,  # 左边界（0-1）
      "y": float,  # 上边界（0-1）
      "width": float,  # 宽度（0-1）
      "height": float,  # 高度（0-1）
  }
  ```

### 4. 分块元数据 (meta)
```json
{
  "element_index_start": 1,
  "element_index_end": 5,
  "element_index": 10,  // 仅表格/图片
  "page_number": 3,  // PDF特有
  "coordinates": {  // PDF特有
    "x": 0.1,
    "y": 0.2,
    "width": 0.8,
    "height": 0.1
  },
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

### PDF 解析参数
- `line_tolerance`: 3.0（行合并容差）
- `paragraph_tolerance`: 10.0（段落合并容差）
- `merge_tolerance`: 8.0（表格合并容差）

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
5. **表格合并**: 合并相邻的表格，减少碎片化

---

## 总结

PDF 文档处理流程是一个完整的管道，从原始文档到可搜索的向量索引：

1. **上传** → 文件验证、存储、元数据保存
2. **解析** → 使用多种工具提取结构化内容
3. **分块** → 按结构智能分块（复用 Word 分块逻辑）
4. **向量化** → 生成语义向量
5. **索引** → 建立可搜索索引

整个过程保证了：
- 内容的完整性和顺序性
- 元数据的准确关联（页码、坐标）
- 高效的存储和检索

PDF 处理相比 Word 处理更复杂，因为需要处理布局和坐标信息，但通过复用分块逻辑，保持了代码的一致性。

