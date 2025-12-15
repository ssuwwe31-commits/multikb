# Markdown 文档上传解析方案

> 目标：在现有 PDF / Word / TXT 流程基础上，为 `.md` / `.markdown` 文件提供结构化的上传、解析、分块与索引体验，充分利用 Markdown 的语法结构（标题层级、代码块、列表、表格等）提升分块质量和检索准确性。

## 1. 适用场景 & 输入约束

| 项目 | 建议 |
| --- | --- |
| 支持的后缀 | `.md`、`.markdown`、`.mkd`（可配置白名单） |
| 最大文件大小 | 默认 10 MB，可在配置中调整 |
| 编码 | 自动检测 UTF-8 / UTF-16 / GBK 等，统一转 UTF-8 处理 |
| 行数限制 | 可选：>50 万行提前提示拆分，避免极端文件 |
| Markdown 方言 | 支持标准 CommonMark / GitHub Flavored Markdown (GFM)，包括：表格、代码块、任务列表、删除线等 |

## 2. 解析流程

1. **上传**：沿用现有上传接口，记录文件类型 `md`。
2. **编码探测**（chardet/uchardet）：识别 BOM、fallback UTF-8。保留原始编码到 metadata。
3. **Markdown 解析**（使用 `markdown` 或 `mistune` 库）：
   - 解析 AST（抽象语法树），提取标题层级、段落、列表、代码块、表格、链接等结构元素。
   - 保留原始 Markdown 源码与渲染后的纯文本双版本。
4. **结构化提取**：
   - **标题层级**（`# H1`、`## H2` 等）：作为章节分隔点，记录标题路径（如 `["文档标题", "第一章", "1.1 小节"]`）。
   - **代码块**（` ``` ` 包裹）：提取语言类型、代码内容，保留到 `code_block` 元数据。
   - **表格**：转换为结构化数据（表头 + 行），便于后续检索。表格单独成块，转换为 Markdown 表格格式存储。
   - **列表**（有序/无序）：保留列表层级与缩进关系。
   - **链接**：提取 `[text](url)` 中的链接，记录到 metadata（暂不处理）。
   - **引用块**（`> quote`）：识别并标记为特殊块类型。
5. **预清洗**：
   - 统一换行符 `\n`；
   - 去除 BOM、控制字符；
   - 可选：合并连续的空白行（>3 行收敛为 2 行）；
   - 保留代码块内的原始格式（不做清洗）。

## 3. 分块策略

充分利用 Markdown 的语义结构，提供更精准的分块：

| 步骤 | 说明 |
| --- | --- |
| **语义分块** | 优先按标题层级（H1/H2/H3）切分，每个章节作为独立分块候选 |
| **段落合并** | 同一标题下的连续段落合并，避免过度碎片化 |
| **代码块处理** | 代码块单独成块或与前后段落合并（根据代码块长度决定），metadata 记录 `chunk_type: "code"` |
| **表格处理** | 表格单独成块，转换为 Markdown 表格格式存储，metadata 记录 `chunk_type: "table"` |
| **滑动窗口** | 对于超大章节（> `chunk_max`），使用滑动窗口（默认 1000 字，overlap 200 字）进一步切分 |
| **元数据填充** | 记录 `heading_path`（标题路径）、`heading_level`、`line_start` / `line_end`、`chunk_type`（text/code/table/list/quote）、`code_language`（如适用） |
| **空白块过滤** | 去除长度 < 10 的块，并尝试与相邻块合并 |

### 3.1 分块优先级（由高到低）

1. **标题边界**：`#` 级标题（H1/H2）强制分块边界
2. **代码块边界**：独立的代码块（>50 行）单独成块
3. **表格边界**：每个表格单独成块
4. **段落边界**：空行分隔的段落
5. **滑动窗口**：超大内容使用窗口切分

## 4. 元信息与存储

| 字段 | 说明 |
| --- | --- |
| `original_encoding` | 探测到的编码（UTF-8 / GBK / …） |
| `line_count` | 原文本行数 |
| `markdown_version` | 使用的 Markdown 方言（如 "GFM", "CommonMark"） |
| `has_code_blocks` | 是否包含代码块 |
| `has_tables` | 是否包含表格 |
| `heading_structure` | 文档标题层级树（JSON），用于生成目录 |
| `code_languages` | 代码块中出现的语言列表（如 `["python", "javascript", "bash"]`） |
| `link_count` | 文档内链接数量 |
| `table_count` | 文档内表格数量 |

所有元信息写入 `documents.metadata` 与 `chunks.metadata`，便于前端展示与诊断。

### 4.1 Chunk 元数据示例

```json
{
  "chunk_id": 12345,
  "content": "这是一个段落内容...",
  "metadata": {
    "heading_path": ["文档标题", "第一章", "1.1 小节"],
    "heading_level": 3,
    "chunk_type": "text",
    "line_start": 42,
    "line_end": 58,
    "code_language": null
  }
}
```

对于代码块：
```json
{
  "chunk_id": 12346,
  "content": "```python\ndef hello():\n    print('Hello')\n```",
  "metadata": {
    "heading_path": ["文档标题", "代码示例"],
    "heading_level": 2,
    "chunk_type": "code",
    "code_language": "python",
    "line_start": 100,
    "line_end": 105
  }
}
```

对于表格：
```json
{
  "chunk_id": 12347,
  "content": "| 列1 | 列2 |\n|-----|-----|\n| 值1 | 值2 |",
  "metadata": {
    "heading_path": ["文档标题", "数据表格"],
    "heading_level": 2,
    "chunk_type": "table",
    "line_start": 110,
    "line_end": 115,
    "table_headers": ["列1", "列2"],
    "table_rows": 2
  }
}
```

## 5. 错误处理 & 用户提示

| 场景 | 处理 |
| --- | --- |
| 编码识别失败 | 回退 UTF-8，若仍失败则提示"请确认文件编码" |
| 文件过大 | 在上传阶段直接拒绝并给出建议阈值 |
| 文本过短 | <50 字时提示无需建库或继续处理 |
| Markdown 解析失败 | 降级为纯文本处理，记录警告到 metadata |
| 结构提取失败 | 使用基础段落分块策略，记录错误日志 |

## 6. 可选优化（分阶段）

1. **代码块语法高亮**：在前端预览时支持代码块语法高亮（使用 `highlight.js` 或 `prism`）。
2. **目录自动生成**：基于 `heading_structure` 自动生成文档目录（TOC），提升导航体验。
3. **链接有效性检测**：批量检测文档内链接是否有效（HTTP 状态码），记录到 metadata。
4. **数学公式支持**：识别 LaTeX 数学公式（`$$ ... $$` 或 `$ ... $`），单独提取并标记为 `chunk_type: "math"`。
5. **版本对比**：基于 Markdown 结构支持文档版本间的语义对比（而非纯文本 diff）。

## 7. 接口设计与示例

MD 支持尽量复用现有文档接口，仅需在参数和解析器中识别 `md` 类型。

### 7.1 上传入口 `POST /api/documents/upload`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `file` | `multipart/form-data` | MD 文件，`Content-Type: text/markdown` 或根据扩展名识别 |
| `metadata` | JSON 字符串 | 包含 `knowledge_base_id`、`doc_type: "md"`、可选 `tags`、`markdown_version`（如 "GFM"）、`encoding` 等 |

```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F 'file=@/path/to/readme.md;type=text/markdown' \
  -F 'metadata={
        "knowledge_base_id": 1,
        "doc_type": "md",
        "tags": ["documentation", "readme"],
        "meta": {
          "markdown_version": "GFM",
          "encoding": "auto",
          "skip_preview": false
        }
      }'
```

上传成功后 `document_tasks.process_document_task` 会根据 `file_type` 走 MD 解析器。

### 7.2 文档详情 `GET /api/documents/{document_id}`

用于查看解析状态和元信息，确保 metadata 中写入 `heading_structure`、`code_languages` 等：

```json
{
  "id": 139,
  "name": "API文档.md",
  "status": "chunked",
  "file_type": "md",
  "metadata": {
    "original_filename": "api-docs.md",
    "original_encoding": "UTF-8",
    "line_count": 1250,
    "markdown_version": "GFM",
    "has_code_blocks": true,
    "has_tables": true,
    "code_languages": ["python", "javascript", "bash"],
    "table_count": 3,
    "heading_structure": [
      {
        "level": 1,
        "text": "API 文档",
        "line": 1,
        "children": [
          {
            "level": 2,
            "text": "快速开始",
            "line": 10,
            "children": []
          }
        ]
      }
    ]
  }
}
```

### 7.3 重新解析 `POST /api/documents/{document_id}/reprocess`

沿用现有接口，后端在 `reprocess_document` 中识别 `md` 并复用 MD 解析器：

```bash
curl -X POST http://localhost:8000/api/documents/139/reprocess \
  -H "Authorization: Bearer <token>"
```

### 7.4 分块查询 `GET /api/documents/{document_id}/chunks`

用于前端预览分块结果，MD 解析阶段会写入 `heading_path`、`chunk_type`、`code_language` 等，接口响应示例：

```json
{
  "total": 85,
  "items": [
    {
      "id": 12401,
      "content": "这是一个普通段落内容...",
      "metadata": {
        "heading_path": ["API 文档", "快速开始"],
        "heading_level": 2,
        "chunk_type": "text",
        "line_start": 15,
        "line_end": 32
      }
    },
    {
      "id": 12402,
      "content": "```python\nfrom api import Client\nclient = Client()\n```",
      "metadata": {
        "heading_path": ["API 文档", "快速开始", "代码示例"],
        "heading_level": 3,
        "chunk_type": "code",
        "code_language": "python",
        "line_start": 35,
        "line_end": 40
      }
    }
  ]
}
```

### 7.5 解析器伪代码（供实现参考）

```python
import mistune
from mistune import markdown
from mistune.plugins import plugin_table, plugin_strikethrough

class MarkdownDocumentParser:
    def __init__(self):
        # 使用 mistune 解析器（支持 GFM）
        self.md = markdown.Markdown(renderer=mistune.create_markdown(
            renderer='ast',
            plugins=[plugin_table, plugin_strikethrough]
        ))
    
    def parse(self, file_path: str, encoding: str | None = None) -> ParsedDocument:
        # 1. 加载文件并检测编码
        text = self._load_text(file_path, encoding)
        
        # 2. 解析 Markdown AST
        ast = self.md(text)
        
        # 3. 提取结构信息
        heading_structure = self._extract_headings(ast)
        code_blocks = self._extract_code_blocks(ast)
        tables = self._extract_tables(ast)
        
        # 4. 按语义结构分块
        chunks = self._chunk_by_structure(
            ast,
            heading_structure,
            chunk_size=settings.CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP
        )
        
        # 5. 构建元数据
        metadata = {
            "original_encoding": self.detected_encoding,
            "line_count": len(text.splitlines()),
            "markdown_version": "GFM",
            "heading_structure": heading_structure,
            "code_languages": list(set(block.get("language") for block in code_blocks)),
            "table_count": len(tables),
            "has_code_blocks": len(code_blocks) > 0,
            "has_tables": len(tables) > 0
        }
        
        return ParsedDocument(
            full_text=text,
            chunks=chunks,
            metadata=metadata
        )
    
    def _chunk_by_structure(self, ast, heading_structure, chunk_size, overlap):
        """按标题层级和语义结构分块"""
        chunks = []
        current_chunk = []
        current_heading_path = []
        
        for element in ast:
            if element['type'] == 'heading':
                # 遇到标题，先保存当前块
                if current_chunk:
                    chunks.extend(self._split_large_chunk(
                        current_chunk, chunk_size, overlap
                    ))
                    current_chunk = []
                
                # 更新标题路径
                level = element['attrs']['level']
                current_heading_path = self._update_heading_path(
                    current_heading_path, level, element['raw']
                )
            
            elif element['type'] == 'code_block':
                # 代码块单独处理
                code_content = element['raw']
                if len(code_content.split('\n')) > 50:
                    # 大代码块单独成块
                    if current_chunk:
                        chunks.append(self._create_chunk(current_chunk, current_heading_path))
                        current_chunk = []
                    chunks.append(self._create_code_chunk(
                        code_content, element.get('attrs', {}).get('language'),
                        current_heading_path
                    ))
                else:
                    # 小代码块与上下文合并
                    current_chunk.append(element)
            
            elif element['type'] == 'table':
                # 表格单独成块
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, current_heading_path))
                    current_chunk = []
                chunks.append(self._create_table_chunk(element, current_heading_path))
            
            else:
                # 其他元素加入当前块
                current_chunk.append(element)
        
        # 处理最后一个块
        if current_chunk:
            chunks.extend(self._split_large_chunk(current_chunk, chunk_size, overlap))
        
        return chunks
```

---

## 8. 表格存储详解

### 8.1 表格存储流程

MD 文档中的表格通过以下流程处理：

1. **表格提取**：
   - 从 Markdown AST 中提取表格元素（GFM 表格语法）
   - 解析表头和表格行数据

2. **表格结构化**：
   - 转换为结构化数据：`{"headers": [...], "rows": [[...], [...]]}`
   - 保留原始 Markdown 表格格式（用于前端渲染）

3. **表格存储**：
   - 表格单独成块，标记 `chunk_type: "table"`
   - 内容存储为 Markdown 表格格式（便于检索和渲染）
   - metadata 记录：`table_headers`、`table_rows`、`line_start`、`line_end`
   - 表格数据写入 chunk 的 `content` 字段
   - 可选：将表格转换为 JSON 格式存储在 metadata 中（便于后续结构化查询）

4. **表格分块**：
   - 小表格（<50行）：直接作为单个 chunk
   - 大表格（>50行）：按窗口切分（每窗口 50 行，overlap 10 行）
   - 每个窗口包含表头，确保上下文完整

### 8.2 存储位置汇总

| 数据类型 | 存储位置 | 说明 |
| --- | --- | --- |
| **原始 MD 文件** | MinIO: `documents/{year}/{month}/{document_id}/original/{filename}` | 上传的原始文件 |
| **解析结果** | MinIO: `documents/{year}/{month}/{document_id}/parsed/parsed_content.json` | 结构化解析结果 |
| **分块数据** | MinIO: `documents/{year}/{month}/{document_id}/parsed/chunks/chunks.jsonl.gz` | 压缩的 chunk 列表 |
| **文本分块向量** | OpenSearch: `document_chunks` 索引 | 文本/表格/代码块向量 |

---

## 9. 与现有系统的集成

### 9.1 复用 TXT 解析基础

- 编码检测逻辑可直接复用 `TxtService` 的 `_detect_encoding` 方法
- 文件上传、存储、任务调度流程完全一致

### 9.2 扩展 DocxService 分块逻辑

- 可以在 `DocxService.chunk_text` 基础上扩展，添加 Markdown 特定的语义分块规则
- 或创建独立的 `MarkdownService`，但复用公共的分块基础设施

### 9.3 前端预览支持

- 文档详情页的预览区域支持渲染 Markdown（使用 `marked` 或 `markdown-it`）
- 代码块支持语法高亮
- **表格渲染**：Markdown 表格转换为 HTML 表格，支持排序、筛选（可选）
- 支持目录（TOC）导航，点击标题跳转到对应位置

---


以上方案基于现有解析框架，通过利用 Markdown 的语义结构（标题层级、代码块、表格等），能够实现更精准的分块和更好的检索体验。与 TXT 解析器共享编码检测与基础清洗逻辑，同时提供结构化的分块策略，提升问答与检索的准确性。

