# PowerPoint (PPTX) 文档上传解析与分块方案

> 目标：为 `.pptx` 文件提供稳定的上传、解析、分块与索引闭环，实现与 PDF / Word / TXT / Excel 一致的文档入库体验，充分利用 PowerPoint 的幻灯片结构（标题、内容、表格、图片）提升分块质量和检索准确性。

## 1. 适用场景与输入约束

| 项目 | 建议 |
| --- | --- |
| 支持的后缀 | `.pptx`（Office 2007+ Open XML 格式） |
| 文件大小 | 默认 50 MB，可在配置中调整（PPTX 通常包含较多图片） |
| 幻灯片数量 | 默认上限 500 张，可配置；超过后提示用户 |
| 每张幻灯片内容 | 支持文本、表格、形状、图片、SmartArt 等 |
| 备注页 | 提取每张幻灯片的备注内容，与幻灯片内容关联 |
| 母版/布局 | 识别并记录母版信息，但不作为主要内容提取 |
| 动画效果 | 不解析动画效果，仅提取静态内容 |
| 编码 | PPTX 内部使用 UTF-8，无需额外编码探测 |

## 2. 解析流程

### 2.1 整体流程

1. **上传**：沿用现有 `POST /api/documents/upload` 接口，记录文件类型 `pptx`。
2. **文件验证**：检查是否为有效的 PPTX 格式（ZIP 结构，包含 `ppt/` 目录）。
3. **幻灯片扫描**：
   - 使用 `python-pptx` 库打开 PPTX 文件
   - 统计幻灯片总数、布局类型
   - 识别每张幻灯片的结构（标题、内容、表格、图片、形状等）
4. **内容提取**：
   - 按幻灯片顺序提取内容
   - 提取每张幻灯片的标题、正文文本
   - 提取表格（转换为结构化数据）
   - 提取图片和嵌入对象
   - 提取备注页内容
5. **结构化组织**：
   - 按幻灯片组织内容
   - 保留幻灯片之间的顺序关系
   - 建立标题层级（基于幻灯片布局和标题样式）

### 2.2 详细解析步骤

#### 步骤 1：加载 PPTX 文件
```python
from pptx import Presentation

prs = Presentation(file_path)
slide_count = len(prs.slides)
```

#### 步骤 2：遍历幻灯片
对每张幻灯片（Slide）：
- 提取幻灯片布局信息（layout name）
- 识别标题占位符（title placeholder）
- 识别内容占位符（content placeholder）
- 遍历所有形状（shapes）

#### 步骤 3：提取文本内容
- **标题文本**：从标题占位符或标题形状中提取
- **正文文本**：从内容占位符、文本框、形状文本中提取
- **表格文本**：从表格形状（Table）中提取，保留行列结构
- **备注文本**：从备注页（notes_slide）中提取

#### 步骤 4：提取表格
- 识别表格形状（`shape.has_table`）
- 提取表头和数据行
- 构建标准 `table_data` 结构：
  ```python
  {
      "cells": [[...], [...]],  # 单元格数据（第一行通常是表头）
      "rows": int,              # 行数
      "columns": int,           # 列数
      "structure": "pptx_extracted",  # 结构标识
      "html": None              # HTML 格式（PPTX 通常为 None）
  }
  ```
- 生成 `table_text`：制表符分隔的文本格式（用于检索）
- 记录表格在幻灯片中的位置（`slide_number`）

#### 步骤 5：提取图片
- 识别图片形状（`shape.shape_type == MSO_SHAPE_TYPE.PICTURE`）
- 提取图片二进制数据
- 记录图片尺寸、位置信息
- 保存到对象存储，生成访问链接

#### 步骤 6：处理 SmartArt 和其他形状
- SmartArt：提取文本内容，忽略图形结构
- 其他形状：提取包含的文本，忽略样式信息

## 3. 分块策略

PPTX 文档的分块策略应充分利用幻灯片结构，同时考虑内容连续性和检索需求。

### 3.1 分块原则

| 分块类型 | 场景 | 构造方式 |
| --- | --- | --- |
| **幻灯片级分块** | 标准幻灯片（有明确标题和内容） | 每张幻灯片作为一个独立分块，数据库 `chunks.chunk_type` 为 `text`，metadata 中记录 `chunk_type: "slide"`，包含：幻灯片标题 + 内容文本（不包括表格和长备注） |
| **多幻灯片合并** | 连续的主题相关幻灯片 | 如果相邻幻灯片没有明确标题分隔，且总内容 < `chunk_max`，则合并为一块，metadata 中记录多个 `slide_number` |
| **表格分块** | 所有表格 | 表格单独成块，数据库 `chunks.chunk_type` 为 `table`，metadata 记录 `element_index`、`table_id`、`table_group_uid`、`n_rows`、`n_cols`。表格数据存储在 `document_tables` 表中，通过 `table_id` 懒加载 |
| **备注分块** | 备注内容较长（> 200 字） | 备注单独成块，数据库 `chunks.chunk_type` 为 `text`，metadata 中记录 `chunk_type: "notes"` 和 `slide_number`，关联到对应幻灯片 |
| **滑动窗口** | 超大幻灯片（> `chunk_max` 字符） | 使用滑动窗口（默认 1000 字，overlap 200 字）切分 |

### 3.2 分块优先级（由高到低）

1. **表格边界**：每个表格单独成块（保留完整性）
2. **幻灯片边界**：有明确标题的幻灯片作为分块候选
3. **备注边界**：较长的备注内容单独成块
4. **段落边界**：幻灯片内多个段落合并
5. **滑动窗口**：超大内容使用窗口切分

### 3.3 分块元数据

每个分块应包含以下元数据（与现有 DOCX/PDF 分块格式保持一致）：

```json
{
  "element_index_start": 1,      // 分块起始元素索引（文本块必需）
  "element_index_end": 5,         // 分块结束元素索引（文本块必需）
  "doc_order_start": 0,          // 分块起始文档顺序（文本块必需）
  "doc_order_end": 4,            // 分块结束文档顺序（文本块必需）
  "chunk_index": 0,              // 分块索引（必需）
  "page_number": null,           // PPTX 无页码概念，始终为 null
  "coordinates": null,           // PPTX 无坐标概念，始终为 null
  "line_start": null,            // 行号起始（PPTX 通常为 null）
  "line_end": null,              // 行号结束（PPTX 通常为 null）
  "section_hint": null,          // 段落提示（可选）
  
  // PPTX 特有字段（可选，存储在 meta 中）
  "slide_number": 1,             // 所属幻灯片编号（从 1 开始）
  "slide_title": "幻灯片标题",   // 幻灯片标题
  "slide_layout": "Title and Content",  // 幻灯片布局名称
  "chunk_type": "slide",         // PPTX 特有分块类型：slide（幻灯片）、notes（备注）、mixed（混合）
  "has_table": true,            // 是否包含表格
  "has_images": false,           // 是否包含图片
  "has_notes": true,            // 是否包含备注
  "table_index": null,           // 如果是表格块，记录表格索引（已废弃，使用 table_id）
  "image_refs": [],             // 图片引用列表（图片 ID 或路径，后续回填）
  "image_id": null,             // 图片 ID（后续回填，仅图片块）
  "image_path": null,           // 图片路径（后续回填，仅图片块）
  
  // 表格块特有字段（仅表格块，存储在 meta 中）
  "element_index": 5,            // 表格元素索引（表格块必需，替代 element_index_start/end）
  "table_id": "abc123...",       // 表格 UID（必需，用于从 document_tables 表懒加载表格数据）
  "table_group_uid": "abc123...", // 表格组 UID（必需，用于分片表格，不分片时与 table_id 相同）
  "n_rows": 10,                 // 表格行数
  "n_cols": 5,                  // 表格列数
  "table_data": {...}           // 可选：完整的表格数据（旧数据可能包含，新设计使用懒加载）
}
```

**注意**：
- `chunk_type` 字段在数据库的 `chunks.chunk_type` 列中存储，值为 `text`、`table` 或 `image`
- PPTX 特有的元数据（如 `slide_number`、`slide_title` 等）存储在 `chunks.meta` JSON 字段中
- **文本块**：必须包含 `element_index_start/end` 和 `doc_order_start/end`，用于关联原始元素
- **表格块**：使用 `element_index`（单个值）替代 `element_index_start/end`，必须包含 `table_id` 和 `table_group_uid`
- **图片块**：使用 `element_index`（单个值），`image_id` 和 `image_path` 在图片处理完成后回填
- **表格存储**：表格数据存储在 `document_tables` 表中，分块 metadata 中只存储 `table_id` 用于懒加载

### 3.4 分块示例

**场景 1：标准幻灯片分块**
```
幻灯片 1: "项目介绍"
  标题: "项目介绍"
  内容: "这是一个关于..." (300 字)
  → 生成 1 个分块

幻灯片 2: "技术架构"
  标题: "技术架构"
  内容: "系统采用微服务..." (800 字)
  备注: "需要强调可扩展性" (50 字)
  → 生成 1 个分块（备注合并到主内容）
```

**场景 2：包含表格的幻灯片**
```
幻灯片 3: "性能对比"
  标题: "性能对比"
  内容: "以下是性能数据对比："
  表格: [大型表格，15 行 × 8 列]
  → 生成 2 个分块：
     - 文本块：标题 + 内容介绍
     - 表格块：完整表格
```

**场景 3：超长备注**
```
幻灯片 4: "总结"
  标题: "总结"
  内容: "主要结论如下..." (200 字)
  备注: [详细说明，800 字]
  → 生成 2 个分块：
     - 幻灯片内容块
     - 备注块（关联到幻灯片 4）
```

## 4. 元信息与存储

### 4.1 文档级元数据

| 字段 | 说明 | 示例 |
| --- | --- | --- |
| `slide_count` | 幻灯片总数 | `25` |
| `layout_types` | 使用的布局类型列表 | `["Title Slide", "Title and Content", "Blank"]` |
| `has_notes` | 是否包含备注页 | `true` |
| `table_count` | 表格总数 | `3` |
| `image_count` | 图片总数 | `15` |
| `has_smartart` | 是否包含 SmartArt | `false` |
| `presentation_size` | 演示文稿尺寸（宽×高，单位：英寸） | `{"width": 10, "height": 7.5}` |
| `slides` | 幻灯片列表（摘要信息） | `[{"number": 1, "title": "封面", "layout": "Title Slide", "has_table": false, "has_images": true}]` |

### 4.2 分块级元数据

| 字段 | 说明 |
| --- | --- |
| `chunk_type` | 分块类型：存储在数据库 `chunks.chunk_type` 列，值为 `text`、`table` 或 `image`；PPTX 特有的类型（如 `slide`、`notes`）存储在 `meta` JSON 中 |
| `slide_number` | 所属幻灯片编号（从 1 开始） |
| `slide_title` | 幻灯片标题 |
| `slide_layout` | 幻灯片布局名称 |
| `table_index` | 如果是表格块，记录表格在幻灯片中的索引（已废弃，使用 `table_id`） |
| `table_id` | 表格 UID（必需，用于从 `document_tables` 表懒加载表格数据） |
| `table_group_uid` | 表格组 UID（必需，用于分片表格，不分片时与 `table_id` 相同） |
| `n_rows` | 表格行数（表格块必需） |
| `n_cols` | 表格列数（表格块必需） |
| `table_data` | 完整的表格数据（可选，新设计使用懒加载，旧数据可能包含） |
| `has_notes` | 是否包含备注内容 |
| `has_images` | 是否包含图片引用 |
| `image_refs` | 图片引用列表（图片 ID 或 URL，可选） |
| `image_id` | 图片 ID（后续回填，由 ImageService 处理） |
| `image_path` | 图片路径（后续回填，由 ImageService 处理） |

### 4.3 存储结构

**文档级元数据**：写入 `documents.meta`（JSON 格式）

```json
{
  "text_length": 5000,
  "element_count": 50,
  "slide_count": 25,
  "layout_types": ["Title Slide", "Title and Content"],
  "has_notes": true,
  "table_count": 3,
  "image_count": 15,
  "presentation_size": {"width": 10, "height": 7.5},
  "slides": [
    {
      "number": 1,
      "title": "项目介绍",
      "layout": "Title Slide",
      "has_table": false,
      "has_images": true
    }
  ]
}
```

**分块级元数据**：写入 `chunks.meta`（JSON 格式）

```json
{
  "element_index_start": 1,
  "element_index_end": 5,
  "doc_order_start": 0,
  "doc_order_end": 4,
  "chunk_index": 0,
  "page_number": null,
  "coordinates": null,
  "line_start": null,
  "line_end": null,
  "section_hint": null,
  
  // PPTX 特有字段
  "slide_number": 1,
  "slide_title": "项目介绍",
  "slide_layout": "Title Slide",
  "chunk_type": "slide",  // PPTX 特有类型，存储在 meta 中
  "has_notes": false,
  "has_images": true,
  "image_refs": [],
  "image_id": 123,        // 后续回填（仅图片块）
  "image_path": "documents/1/images/abc123.png"  // 后续回填（仅图片块）
}

// 表格块示例（chunks.meta）
{
  "element_index": 5,            // 表格元素索引
  "chunk_index": 2,
  "page_number": null,
  "table_id": "abc123def456...",  // 表格 UID（必需）
  "table_group_uid": "abc123def456...",  // 表格组 UID（必需）
  "n_rows": 10,
  "n_cols": 5,
  "slide_number": 3,
  "slide_title": "性能对比"
}
```

**注意**：
- `chunks.chunk_type` 列存储的是 `text`、`table` 或 `image`（与现有格式一致）
- PPTX 特有的 `chunk_type` 值（如 `slide`、`notes`）存储在 `chunks.meta` JSON 中
- `image_id` 和 `image_path` 在图片处理完成后回填到分块元数据中

## 5. 错误处理与用户提示

| 场景 | 行为 |
| --- | --- |
| 不支持的文件格式 | 在验证阶段抛出 `DocumentParseError`，提示"请使用 .pptx 格式" |
| 受损的 PPTX 文件 | 尝试恢复可读取的幻灯片，记录错误日志，提示用户部分内容可能丢失 |
| 幻灯片数量超限 | 警告用户，可选择"仅处理前 N 张幻灯片"或"全部处理" |
| 图片提取失败 | 记录警告日志，继续处理其他内容，在 metadata 中标记缺失的图片 |
| 表格解析失败 | 回退到文本提取模式，尝试提取表格中的文本内容 |
| 编码问题 | PPTX 内部使用 UTF-8，理论上不会出现编码问题，但需处理特殊字符 |
| 内存不足 | 对于超大文件，采用流式处理，逐张幻灯片处理，避免一次性加载 |

## 6. API / 任务设计

### 6.1 上传入口

沿用现有 `POST /api/documents/upload` 接口：
- 文件类型自动识别为 `pptx`（通过文件扩展名或 MIME 类型）
- 文件验证：通过 `FileValidationService` 验证文件格式
- 可选参数（通过 `Document.meta` 传递）：
  - `slide_whitelist`：指定要处理的幻灯片编号列表（如 `[1, 3, 5]`），默认处理所有幻灯片
  - `include_notes`：是否提取备注，默认 `true`
  - `max_slides`：最大处理幻灯片数量，默认 500

**上传流程**：
1. 文件上传到 MinIO 对象存储
2. 文件信息保存到 `documents` 表
3. 触发异步任务 `process_document_task` 处理文档

### 6.2 解析任务集成

在 `document_tasks.process_document_task` 中新增 PPTX 处理分支：

**步骤 1**：在文件类型判断部分添加 `is_pptx` 判断：
```python
file_suffix = (document.original_filename or '').split('.')[-1].lower()
file_type = (document.file_type or '').lower()
is_docx = file_suffix == 'docx' or file_type == 'docx'
is_pdf = file_suffix == 'pdf' or file_type == 'pdf'
is_txt = file_suffix in ('txt', 'log') or file_type == 'txt'
is_md = file_suffix in ('md', 'markdown', 'mkd') or file_type in ('md', 'markdown')
is_excel = file_suffix in ('xlsx', 'xls', 'xlsb', 'csv') or file_type in ('excel', 'xlsx', 'xls', 'csv')
is_pptx = file_suffix == 'pptx' or file_type == 'pptx'  # 新增
if not (is_docx or is_pdf or is_txt or is_md or is_excel or is_pptx):  # 更新条件
    raise Exception("当前处理流程仅支持 DOCX / PDF / TXT / MD / Excel / PPTX 文档")
```

**步骤 2**：在文件顶部导入 PptxService：
```python
from app.services.pptx_service import PptxService  # 新增导入
```

**步骤 3**：在解析分支中添加 PPTX 处理：
```python
elif is_pptx:
    logger.info(f"[任务ID: {task_id}] 步骤4/7: 使用 PptxService 解析 PowerPoint 文档")
    parser = PptxService(db)
    # PPTX 解析不需要额外选项（与 DOCX/PDF 一致）
    parse_result = parser.parse_document(parsed_file_path)
elif is_md:
    logger.info(f"[任务ID: {task_id}] 步骤4/7: 使用 MarkdownService 解析 Markdown 文档")
    parser = MarkdownService(db)
    parse_result = parser.parse_document(parsed_file_path)
else:
    logger.info(f"[任务ID: {task_id}] 步骤4/7: 使用 TxtService 解析纯文本文档")
    parser = TxtService(db)
    parse_result = parser.parse_document(parsed_file_path)
```

**步骤 4**：在预览生成判断中，PPTX 已包含在 `is_office` 中：
```python
# 在 document_tasks.py 中（已实现，无需修改）
is_office = file_suffix in {'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'} or file_type in {'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}
# PPTX 会自动包含在 is_office 中，预览生成逻辑已支持
```

**步骤 5**：在目录提取部分添加 PPTX 支持（可选）：
```python
# 在 document_tasks.py 的目录提取部分（索引阶段）
try:
    from app.services.document_toc_service import DocumentTOCService
    import asyncio
    toc_service = DocumentTOCService(db)
    
    if is_pptx and document.file_path:
        # 从 metadata 中的 slides 列表提取目录
        doc_meta = document.meta or {}
        if isinstance(doc_meta, str):
            import json as _json
            try:
                doc_meta = _json.loads(doc_meta)
            except Exception:
                doc_meta = {}
        slides = doc_meta.get('slides', [])
        if slides:
            # 调用 PPTX 目录提取方法（需要在 DocumentTOCService 中实现）
            toc_items = asyncio.run(toc_service.extract_toc_from_pptx(document_id, slides))
            if toc_items:
                logger.info(f"[任务ID: {task_id}] PPTX目录提取成功，共 {len(toc_items)} 个目录项")
        else:
            logger.debug(f"[任务ID: {task_id}] PPTX文件无幻灯片信息，跳过目录提取")
    # ... 其他格式的目录提取
except Exception as e:
    logger.warning(f"[任务ID: {task_id}] 提取文档目录失败（不影响主流程）: {e}")
```

**完整处理流程**：
1. ✅ 文件类型判断（添加 `is_pptx`）
2. ✅ 文件下载到临时目录
3. ✅ 文档解析（调用 `PptxService.parse_document`）
4. ✅ 元数据更新（幻灯片信息写入 `document.meta`）
5. ✅ 预览生成（如果启用，自动生成 PDF 预览）
6. ✅ 分块处理（复用现有分块逻辑）
7. ✅ 表格处理（写入 `document_tables` 表）
8. ✅ 图片处理（保存、OCR、向量化、索引）
9. ✅ 向量化（生成文本向量）
10. ✅ 索引（写入 OpenSearch）
11. ✅ 目录提取（可选，从幻灯片标题构建）

### 6.3 预览生成（可选，需要 LibreOffice）

**重要说明**：PPTX 文件的在线预览功能需要 LibreOffice 支持，但这是**可选功能**，不影响文档内容解析和搜索。

#### 6.3.1 预览生成流程

在文档处理任务中，如果启用了预览生成（`ENABLE_PREVIEW_GENERATION=True`），系统会自动：

1. **PDF 预览生成**：
   - 使用 LibreOffice 的 `impress_pdf_Export` 过滤器将 PPTX 转换为 PDF
   - 生成的 PDF 保存到 MinIO 对象存储
   - 路径记录在 `document.converted_pdf_url` 字段中
   - PDF 文件超过 10MB 会自动压缩（使用 Ghostscript）

2. **HTML 预览生成**：
   - **注意**：当前实现中，HTML 预览仅对 Excel 文件生成，PPTX 主要使用 PDF 预览
   - 如需 HTML 预览，可以使用 LibreOffice 的 `impress_html_Export` 过滤器

#### 6.3.2 LibreOffice 配置

LibreOffice 是**可选依赖**：
- **如果已安装**：系统会自动检测并使用，PPTX 文档可以生成 PDF 预览
- **如果未安装**：文档解析和内容提取不受影响，但无法生成预览，前端会提示下载原始文件

**配置方式**：

```bash
# 方式1：自动检测（推荐）
# 系统会自动在 PATH 中查找 soffice 或 libreoffice 命令

# 方式2：手动配置路径
# 在 .env 文件中设置：
SOFFICE_PATH=/path/to/libreoffice/soffice

# 安装 LibreOffice（Ubuntu/Debian）
sudo apt-get install libreoffice

# 安装 LibreOffice（CentOS/RHEL）
sudo yum install libreoffice

# 安装 LibreOffice（macOS）
brew install --cask libreoffice

# 安装 LibreOffice（Windows）
# 从官网下载安装包：https://www.libreoffice.org/download/
```

**系统自动检测逻辑**：
- 优先使用配置的 `SOFFICE_PATH`
- 否则查找系统 PATH 中的 `soffice` 或 `libreoffice` 命令
- 如果都找不到，预览功能将被禁用，但不会报错

#### 6.3.3 预览生成时机

预览在文档处理任务中异步生成，流程如下：

```python
# 在 document_tasks.py 中（已实现）
if settings.ENABLE_PREVIEW_GENERATION and is_office:
    # 生成 PDF 预览（适用于 DOCX、PPTX、XLSX）
    pdf_path = convert_office_to_pdf(temp_file_path)
    if pdf_path:
        # 上传到 MinIO
        # 更新 document.converted_pdf_url
    
    # 对于 Excel，还会生成 HTML 预览
    # PPTX 主要使用 PDF 预览
```

**预览生成的时机**：
- 在文档解析完成后，上传到 MinIO 之前生成
- 如果生成失败，记录警告日志，**不影响文档解析流程**
- 前端会检测预览状态，如果文档已完成但预览未生成，会显示下载提示

#### 6.3.4 前端预览显示

前端会根据预览生成情况显示：
1. **优先显示 PDF 预览**：如果有 `converted_pdf_url`，使用 iframe 嵌入 PDF
2. **降级到下载**：如果没有 PDF 预览，显示下载按钮供用户下载原始文件

**预览状态检测**：
- 前端会轮询检查预览是否已生成（最多重试 30 次，每次间隔 3 秒）
- 如果文档处理完成但预览仍未生成，显示下载提示
- 用户可以正常使用文档内容提取、搜索等功能，只是无法在线预览

#### 6.3.5 预览生成失败处理

- **LibreOffice 未安装或转换失败**：
  - 记录警告日志（`logger.warning`）
  - **不影响文档解析流程**
  - 前端会显示下载提示

- **预览文件上传失败**：
  - 记录错误日志
  - 不影响文档解析流程
  - 用户可以下载原始文件

- **文档解析与预览独立**：
  - ✅ 即使没有 LibreOffice，PPTX 文档的解析、分块、向量化、搜索等功能完全正常
  - ✅ 预览失败不会导致文档处理任务失败
  - ✅ 用户可以通过下载原始文件来查看完整内容

### 6.4 PptxService 接口设计

**文件位置**：`spx-knowledge-backend/app/services/pptx_service.py`

```python
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from pptx import Presentation
from pptx.shapes.base import BaseShape
from pptx.shapes.table import Table
from pptx.shapes.picture import Picture
from pptx.shapes.autoshape import Shape
from pptx.enum.shapes import MSO_SHAPE_TYPE
from app.core.logging import logger

class PptxService:
    """PowerPoint 文档解析服务，输出结构与 DOCX/PDF 解析保持一致。"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def parse_document(self, file_path: str) -> Dict[str, Any]:
        """
        解析 PPTX 文档
        
        Args:
            file_path: PPTX 文件路径
            
        Returns:
            返回结构（与 DocxService 保持一致）:
            {
                "text_content": str,  # 合并后的完整文本
                "ordered_elements": List[Dict],  # 有序元素列表
                "filtered_elements_light": List[Dict],  # 过滤后的轻量元素
                "text_element_index_map": List[Dict],  # 文本元素索引映射
                "tables": List[Dict],  # 表格列表
                "images": List[Dict],  # 图片列表（必须包含 data 和 bytes 字段）
                "images_binary": List[Dict],  # 图片二进制列表（可选，用于兼容）
                "metadata": Dict  # 元数据
            }
        """
        # 实现细节见 7.2 核心方法设计
        pass
    
    def _load_presentation(self, file_path: str) -> Presentation:
        """加载 PPTX 文件"""
        try:
            return Presentation(file_path)
        except Exception as e:
            logger.error(f"[PPTX] 加载文件失败: {e}")
            raise
    
    def _extract_slide_content(self, slide, slide_number: int) -> Dict[str, Any]:
        """提取单张幻灯片的内容"""
        # 返回：标题、正文文本、表格列表、图片列表、备注
        pass
    
    def _extract_text_from_shape(self, shape: BaseShape) -> str:
        """从形状中提取文本"""
        pass
    
    def _extract_table_data(self, shape: Table) -> Optional[Dict[str, Any]]:
        """提取表格数据"""
        # 返回标准 table_data 结构
        pass
    
    def _extract_images(self, slide) -> List[Dict[str, Any]]:
        """提取幻灯片中的图片"""
        # 返回包含 data 和 bytes 字段的图片列表
        pass
    
    def _extract_notes(self, notes_slide) -> str:
        """提取备注页内容"""
        pass
    
    def _build_slide_title(self, slide) -> str:
        """构建幻灯片标题"""
        pass
    
    def _identify_slide_layout(self, slide) -> str:
        """识别幻灯片布局"""
        pass
```

**关键实现要点**：
1. 所有方法必须处理异常，避免单个幻灯片错误导致整个文档解析失败
2. `element_index` 从 1 开始递增，确保唯一性
3. `doc_order` 按元素出现顺序递增
4. 图片必须同时包含 `data` 和 `bytes` 字段
5. 表格必须包含完整的 `table_data` 结构
6. 元数据必须包含 `element_count` 字段

### 6.5 元数据处理

解析完成后，PPTX 特有的元数据需要写入 `document.meta`：

```python
# 在 document_tasks.py 中（解析完成后）
parse_metadata = parse_result.get('metadata', {}) or {}
doc_meta = document.meta or {}
doc_meta = doc_meta.copy() if isinstance(doc_meta, dict) else {}

# 更新通用元数据
doc_meta.update({
    "text_length": len(text_content),
    "element_count": elements_count,
})

# 更新 PPTX 特有元数据
for key in ("slide_count", "layout_types", "has_notes", "table_count", 
            "image_count", "has_smartart", "presentation_size", "slides"):
    if parse_metadata.get(key) is not None:
        doc_meta[key] = parse_metadata[key]

document.meta = doc_meta
db.commit()
```

### 6.6 输出格式示例

```python
# ordered_elements 示例（文本元素）
{
    "type": "text",
    "text": "幻灯片标题：项目介绍\n\n这是一个关于...",
    "element_index": 1,  # 从 1 开始
    "doc_order": 0,
    "category": "NarrativeText",  # 或 "Title"
    "style": "",  # 样式名称（可选）
    "length": 100,  # 文本长度
    # PPTX 特有字段（可选）
    "slide_number": 1,
    "slide_title": "项目介绍",
    "slide_layout": "Title Slide"
}

# ordered_elements 示例（表格元素）
{
    "type": "table",
    "element_index": 5,
    "doc_order": 4,
    "slide_number": 3
}

# ordered_elements 示例（图片元素）
{
    "type": "image",
    "element_index": 2,
    "doc_order": 1,
    "slide_number": 1,
    "image_ext": ".png"
}

# tables 示例（tables 列表中的项）
{
    "element_index": 5,
    "doc_order": 4,
    "table_data": {
        "cells": [["列1", "列2"], ["值1", "值2"]],  # 必需：单元格数据
        "rows": 2,      # 必需：行数
        "columns": 2,   # 必需：列数
        "structure": "pptx_extracted",  # 可选：结构标识
        "html": None    # 可选：HTML 格式（PPTX 通常为 None）
    },
    "table_text": "列1\t列2\n值1\t值2",  # 必需：制表符分隔的文本（用于检索）
    "slide_number": 3,  # PPTX 特有：所属幻灯片编号
    "page_number": None  # PPTX 没有页码概念，始终为 None
}

# images 示例（必须同时包含 data 和 bytes 字段）
{
    "data": bytes,      # 图片二进制数据
    "bytes": bytes,     # 图片二进制数据（与 data 相同，用于兼容）
    "element_index": 2, # 元素索引（必需，用于关联图片分块）
    "doc_order": 5,     # 文档顺序
    "page_number": None,  # PPTX 无页码概念
    "slide_number": 1,    # 所属幻灯片编号
    "image_ext": ".png",  # 图片扩展名
    "width": 800,        # 图片宽度（可选）
    "height": 600         # 图片高度（可选）
}
```

## 7. 实现细节

### 7.1 依赖库

#### 必需依赖

主要依赖 `python-pptx`（用于内容解析）：
```bash
pip install python-pptx
```

**依赖包清单**：
- ✅ `python-pptx>=1.0.0` - PPTX 文档解析（**已添加到 `requirements/base.txt`**）
- ✅ `python-docx>=1.1.0` - DOCX 文档解析（**已添加到 `requirements/base.txt`**，DocxService 需要）

**注意**：所有文档解析相关的依赖包都已添加到 `requirements/base.txt` 中：
```
# Document Processing
unstructured>=0.10.0
openpyxl>=3.1.0
pandas>=2.0.0
xlrd>=2.0.0
python-docx>=1.1.0      # DOCX 解析
python-pptx>=1.0.0      # PPTX 解析
```

**其他文档格式的依赖**（已在 `requirements.txt` 中）：
- PDF: `pdfplumber>=0.11.0`, `PyMuPDF>=1.23.0`, `camelot-py==0.10.1`
- Markdown: `mistune>=3.0.0`（已在 `requirements/base.txt` 中）
- Excel: `openpyxl>=3.1.0`, `pandas>=2.0.0`, `xlrd>=2.0.0`（已在 `requirements/base.txt` 中）

#### 可选依赖（预览功能）

**LibreOffice**（用于生成 PDF/HTML 预览，可选）：
- 如果不需要在线预览功能，可以不安装 LibreOffice
- 安装方式见 [6.3.2 LibreOffice 配置](#632-libreoffice-配置)

**总结**：
- ✅ **内容解析**：只需 `python-pptx`，无需 LibreOffice
- ✅ **在线预览**：需要 LibreOffice（可选功能）
- ✅ **两者独立**：即使没有 LibreOffice，PPTX 文档的解析、分块、向量化、搜索等功能完全正常

### 7.2 核心方法设计

```python
class PptxService:
    def parse_document(self, file_path: str) -> Dict[str, Any]:
        """主解析方法"""
        
    def _load_presentation(self, file_path: str) -> Presentation:
        """加载 PPTX 文件"""
        
    def _extract_slide_content(self, slide: Slide, slide_number: int) -> Dict[str, Any]:
        """提取单张幻灯片的内容"""
        
    def _extract_text_from_shape(self, shape: Shape) -> str:
        """从形状中提取文本"""
        
    def _extract_table_data(self, shape: Shape) -> Optional[Dict[str, Any]]:
        """提取表格数据"""
        
    def _extract_images(self, slide: Slide) -> List[Dict[str, Any]]:
        """提取幻灯片中的图片"""
        
    def _extract_notes(self, notes_slide: NotesSlide) -> str:
        """提取备注页内容"""
        
    def _build_slide_title(self, slide: Slide) -> str:
        """构建幻灯片标题"""
        
    def _identify_slide_layout(self, slide: Slide) -> str:
        """识别幻灯片布局"""
```

### 7.3 文本提取逻辑

1. **标题提取**：
   - 优先从标题占位符（`slide.shapes.title`）提取
   - 如果不存在，查找包含标题样式的形状
   - 如果仍不存在，使用布局默认标题位置

2. **正文提取**：
   - 遍历所有形状（`slide.shapes`）
   - 跳过标题形状和表格形状
   - 提取文本框和形状中的文本
   - 保留文本之间的换行关系

3. **表格提取**：
   - 识别表格形状（`shape.has_table`）
   - 遍历所有单元格，提取文本
   - 构建标准 `table_data` 结构（包含 `cells`、`rows`、`columns`）
   - 生成 `table_text`：制表符分隔的文本格式（用于检索和向量化）
   - 记录表头行（通常为第一行，存储在 `cells[0]`）
   - **注意**：表格数据在 `document_tasks.py` 中会写入 `document_tables` 表，并生成 `table_uid` 和 `table_group_uid`

### 7.4 图片处理

1. **图片识别**：
   - 检查形状类型是否为图片（`MSO_SHAPE_TYPE.PICTURE`）
   - 或从图片集合中提取（`slide.part.image_parts`）

2. **图片提取**：
   - 获取图片二进制数据（`image.part.blob`）
   - 识别图片格式（JPEG、PNG 等）
   - 记录图片尺寸和位置

3. **图片存储**：
   - 图片二进制数据在解析阶段提取，存储在 `images` 列表中
   - 在 `document_tasks.py` 的图片处理阶段，通过 `ImageService` 保存到 MinIO
   - 图片元数据保存到 `document_images` 表
   - 图片向量化后索引到 OpenSearch
   - 最后回填 `image_id` 和 `image_path` 到对应的图片分块 metadata 中

### 7.5 备注处理

1. **备注提取**：
   - 获取备注页（`slide.notes_slide`）
   - 提取备注页中的文本内容
   - 与对应幻灯片关联

2. **备注分块策略**：
   - 如果备注较短（< 200 字），合并到幻灯片内容中
   - 如果备注较长（> 200 字），单独成块（`chunk_type` 为 `text`，但在 `meta` 中标记 `chunk_type: "notes"`）
   - 在 metadata 中标记 `has_notes: true`
   - 备注块需要包含 `element_index_start/end` 和 `doc_order_start/end`，关联到对应的备注元素

## 8. 目录提取（可选增强）

### 8.1 幻灯片大纲提取

PPTX 文件可能包含大纲视图信息，可以提取为目录结构：

```python
def _extract_outline(self, prs: Presentation) -> List[Dict[str, Any]]:
    """
    提取演示文稿大纲（目录结构）
    基于幻灯片标题构建层级关系
    """
    outline = []
    for slide in prs.slides:
        title = self._build_slide_title(slide)
        if title:
            outline.append({
                "level": 1,  # 默认所有幻灯片为同一层级
                "title": title,
                "slide_number": slide.slide_id,
                "position": len(outline) + 1
            })
    return outline
```

### 8.2 与 DocumentTOCService 集成

需要在 `DocumentTOCService` 中实现 `extract_toc_from_pptx` 方法：

**在 `app/services/document_toc_service.py` 中添加**：
```python
async def extract_toc_from_pptx(self, document_id: int, slides: List[Dict[str, Any]]) -> List[DocumentTOC]:
    """
    从 PPTX 幻灯片列表提取目录
    
    Args:
        document_id: 文档ID
        slides: 幻灯片列表，格式：[{"number": 1, "title": "标题", "layout": "Title Slide", ...}, ...]
    
    Returns:
        目录项列表
    """
    try:
        toc_items = []
        for slide in slides:
            title = slide.get('title', '').strip()
            if not title:
                continue
            
            slide_number = slide.get('number', 0)
            if slide_number <= 0:
                continue
            
            # 创建目录项（所有幻灯片为同一层级，level=1）
            toc_item = DocumentTOC(
                document_id=document_id,
                level=1,
                title=title[:500],  # 限制长度
                position=len(toc_items),
                parent_id=None,  # PPTX 目录暂不支持层级关系
                page_number=None,  # PPTX 无页码概念
                slide_number=slide_number,  # PPTX 特有：幻灯片编号
            )
            toc_items.append(toc_item)
        
        # 批量保存
        if toc_items:
            self.db.add_all(toc_items)
            self.db.commit()
            logger.info(f"PPTX目录提取成功: 文档ID={document_id}, 目录项数={len(toc_items)}")
        
        return toc_items
    except Exception as e:
        logger.error(f"PPTX目录提取失败: {e}", exc_info=True)
        self.db.rollback()
        return []
```

**在 `document_tasks.py` 中调用**（在索引阶段，步骤 6/7）：
```python
# 在目录提取部分添加
if is_pptx and document.file_path:
    doc_meta = document.meta or {}
    if isinstance(doc_meta, str):
        import json as _json
        try:
            doc_meta = _json.loads(doc_meta)
        except Exception:
            doc_meta = {}
    slides = doc_meta.get('slides', [])
    if slides:
        toc_items = asyncio.run(toc_service.extract_toc_from_pptx(document_id, slides))
        if toc_items:
            logger.info(f"[任务ID: {task_id}] PPTX目录提取成功，共 {len(toc_items)} 个目录项")
    else:
        logger.debug(f"[任务ID: {task_id}] PPTX文件无幻灯片信息，跳过目录提取")
```

## 9. 测试用例建议

### 9.1 单元测试

- 测试单张幻灯片的文本提取
- 测试表格提取和转换
- 测试图片提取和存储
- 测试备注提取
- 测试空幻灯片处理

### 9.2 集成测试

- 测试完整的 PPTX 文档解析流程
- 测试不同布局类型的幻灯片
- 测试包含大量图片的 PPTX 文件
- 测试受损文件的容错处理

### 9.3 边界情况测试

- 空 PPTX 文件（只有空白幻灯片）
- 超大 PPTX 文件（> 100 MB）
- 包含特殊字符的文本
- 包含大量表格的幻灯片
- 备注页为空的情况

## 10. 性能优化建议

1. **流式处理**：逐张幻灯片处理，避免一次性加载所有内容到内存
2. **图片延迟加载**：先提取图片元信息，需要时再下载二进制数据
3. **并行处理**：对于多张幻灯片的文本提取，可以并行处理（但需注意线程安全）
4. **缓存机制**：对于重复解析的 PPTX 文件，可以缓存解析结果

## 11. 与其他格式的一致性

确保 PPTX 解析器的输出格式与 DOCX、PDF 等解析器保持一致：

- ✅ `text_content`: 完整的文本内容（字符串）
- ✅ `ordered_elements`: 有序元素列表（统一格式）
  - 每个元素必须包含 `type`（`text`、`table`、`image`）、`element_index`、`doc_order`
  - 文本元素包含 `text` 字段
  - 表格元素包含 `table_data` 引用
  - 图片元素包含图片引用信息
- ✅ `filtered_elements_light`: 轻量过滤元素列表
  - 格式：`[{"category": str, "text": str, "element_index": int, "doc_order": int}]`
- ✅ `text_element_index_map`: 文本元素索引映射
  - 格式：`[{"element_index": int, "element_type": str, "doc_order": int, "page_number": None, "coordinates": None}]`
- ✅ `tables`: 表格列表（统一格式）
  - 每个表格包含 `element_index`、`table_data`（含 `cells`、`rows`、`columns`、`structure`、`html`）、`table_text`、`page_number`（PPTX 为 `None`）、`doc_order`、`slide_number`（PPTX 特有）
  - `table_data.cells` 是二维数组，第一行通常是表头
  - `table_text` 是制表符分隔的文本，用于检索和向量化
  - 表格数据会在 `document_tasks.py` 中写入 `document_tables` 表，生成 `table_uid` 和 `table_group_uid`
- ✅ `images`: 图片列表（统一格式）
  - 每个图片必须包含 `data` 和 `bytes` 字段（二进制数据）
  - 必须包含 `element_index`（用于关联图片分块）
  - 包含 `doc_order`、`page_number`（PPTX 为 `None`）、`slide_number`（PPTX 特有）
- ✅ `images_binary`: 图片二进制列表（可选，用于兼容）
- ✅ `metadata`: 元数据字典
  - 必须包含 `element_count` 字段
  - 可包含 PPTX 特有的元数据（如 `slide_count`、`layout_types` 等）

**关键一致性要求**：
1. 所有元素必须有唯一的 `element_index`，从 1 开始递增
2. 所有元素必须有 `doc_order`，用于排序
3. 图片必须同时包含 `data` 和 `bytes` 字段
4. 表格必须包含完整的 `table_data` 结构
5. 分块元数据必须包含 `element_index_start/end` 和 `doc_order_start/end`

这样可以确保后续的分块、向量化、索引等流程无需修改即可支持 PPTX 格式。

## 12. 后续扩展

### 12.1 支持旧版 PPT 格式（可选）

如果需要支持 `.ppt` 格式（PowerPoint 97-2003），可以考虑：
- 使用 `pywin32` 在 Windows 环境下通过 COM 接口转换
- 或使用 LibreOffice 命令行工具转换为 PPTX
- 或使用在线转换服务

### 12.2 支持 ODP 格式（可选）

OpenDocument Presentation 格式：
- 使用 `odfpy` 库解析
- 或转换为 PPTX 后处理

### 12.3 动画效果提取（可选）

如果需要保留动画信息：
- 提取动画序列
- 记录动画类型和参数
- 在 metadata 中标记

## 13. 总结

PPTX 解析器的实现将：
1. ✅ 完整提取幻灯片内容（文本、表格、图片、备注）
2. ✅ 保持与现有文档解析流程的一致性
3. ✅ 充分利用幻灯片结构进行智能分块
4. ✅ 提供丰富的元数据支持检索和展示
5. ✅ 具备良好的错误处理和容错能力

通过实现 PPTX 解析器，系统将支持更多类型的办公文档，提升知识库的覆盖范围和使用价值。

