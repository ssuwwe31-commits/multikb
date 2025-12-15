# TXT 文档上传解析方案

> 目标：在现有 PDF / Word 流程基础上，为 `.txt` 纯文本文件提供一致的上传、解析、分块与索引体验，避免额外的代码复杂度，同时保证性能与用户体验。

## 1. 适用场景 & 输入约束

| 项目 | 建议 |
| --- | --- |
| 支持的后缀 | `.txt`、`.log`（可配置白名单） |
| 最大文件大小 | 默认 10 MB，可在配置中调整（防止超大日志拖垮解析） |
| 编码 | 自动检测 UTF-8 / UTF-16 / GBK 等，统一转 UTF-8 处理 |
| 行数限制 | 可选：>50 万行提前提示拆分，避免极端文件 |

## 2. 解析流程

1. **上传**：沿用现有上传接口，记录文件类型 `txt`。
2. **编码探测**（chardet/uchardet）：识别 BOM、fallback UTF-8。保留原始编码到 metadata，方便回显。
3. **预清洗**：
   - 统一换行符 `\n`；
   - 去 BOM、控制字符；
   - 可选：去掉连续的空行（>3 行收敛为 2 行）。
4. **结构化 hint**（可选规则）：
   - 通过正则识别标题（如 `^# `、`^===`、全大写行）；
   - 识别列表/代码块（`^-`、`*`、`    `）。
   - 结果作为 chunk 元信息 `section_hint`，提高召回解释力。

## 3. 分块策略

与 DOCX/PDF 共用逻辑，重点关注：

| 步骤 | 说明 |
| --- | --- |
| 文本切分 | 先按「段落/空行」粗切，再按 `chunk_max`（默认 1000 字）进行滑动窗口分块 |
| chunk_overlap | 保持 200 字，避免句子被切断 |
| 元数据 | 由于无页码/章节，填充 `line_start` / `line_end`、 `section_hint`（若有） |
| 空白块过滤 | 去除长度 < 10 的块，并尝试与相邻块合并 |

## 4. 元信息与存储

| 字段 | 说明 |
| --- | --- |
| `original_encoding` | 探测到的编码（UTF-8 / GBK / …） |
| `line_count` | 原文本行数 |
| `has_tabs` / `has_codeblock` | 通过 `\t`、反引号等简单判断 |
| `language_hint` | 复用 LangDetect，帮助后续检索权重 |

所有元信息写入 `documents.metadata` 与 `chunks.metadata`，便于前端展示与诊断。

## 5. 错误处理 & 用户提示

| 场景 | 处理 |
| --- | --- |
| 编码识别失败 | 回退 UTF-8，若仍失败则提示“请确认文件编码” |
| 文件过大 | 在上传阶段直接拒绝并给出建议阈值 |
| 文本过短 | <50 字时提示无需建库或继续处理 |

## 6. 可选优化（分阶段）

1. **轻量语义分段**：针对 Markdown/日志格式提供额外的 chunk 标签，提升问答可解释性。
2. **样例预览**：在解析结果里截取首尾 200 字预览，方便运维核对内容。
3. **去重/压缩**：对重复行较多的日志，可选择性摘要或截断（可配置），避免向量库冗余。

## 7. 接口设计与示例

TXT 支持尽量复用现有文档接口，仅需在参数和解析器中识别 `txt` 类型。

### 7.1 上传入口 `POST /api/documents/upload`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `file` | `multipart/form-data` | TXT 文件，`Content-Type: text/plain` 或根据扩展名识别 |
| `metadata` | JSON 字符串 | 包含 `knowledge_base_id`、`doc_type: "txt"`、可选 `tags`、`language_hint`、`encoding` 等 |

```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F 'file=@/path/to/sample.txt;type=text/plain' \
  -F 'metadata={
        "knowledge_base_id": 1,
        "doc_type": "txt",
        "tags": ["log", "txt"],
        "meta": {
          "encoding": "auto",
          "skip_preview": false
        }
      }'
```

上传成功后 `document_tasks.process_document_task` 会根据 `file_type` 走 TXT 解析器。

### 7.2 文档详情 `GET /api/documents/{document_id}`

用于查看解析状态和元信息，无需新增字段，只需确保 metadata 中写入 `original_encoding`、`line_count` 等：

```json
{
  "id": 138,
  "name": "应用日志.txt",
  "status": "chunked",
  "file_type": "txt",
  "metadata": {
    "original_filename": "app-log.txt",
    "original_encoding": "GBK",
    "line_count": 4280,
    "language_hint": "zh"
  }
}
```

### 7.3 重新解析 `POST /api/documents/{document_id}/reprocess`

沿用现有接口，后端在 `reprocess_document` 中识别 `txt` 并复用 TXT 解析器：

```bash
curl -X POST http://localhost:8000/api/documents/138/reprocess \
  -H "Authorization: Bearer <token>"
```

### 7.4 分块查询 `GET /api/documents/{document_id}/chunks`

用于前端预览分块结果，TXT 解析阶段会写入 `line_start/line_end` 与 `section_hint`，接口响应示例：

```json
{
  "total": 120,
  "items": [
    {
      "id": 9871,
      "content": "2025-01-23 10:00:01 INFO start service...",
      "metadata": {
        "line_start": 1,
        "line_end": 15,
        "section_hint": "日志段落",
        "original_encoding": "GBK"
      }
    }
  ]
}
```

### 7.5 解析器伪代码（供实现参考）

```python
class TxtDocumentParser:
    def parse(self, file_path: str, encoding: str | None = None) -> ParsedDocument:
        text = self._load_text(file_path, encoding)
        cleaned = normalize_whitespace(text)
        segments = split_by_paragraph(cleaned)
        chunks = sliding_window(
            segments,
            chunk_size=settings.CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP,
        )
        return ParsedDocument(
            full_text=cleaned,
            chunks=chunks,
            metadata={
                "original_encoding": self.detected_encoding,
                "line_count": len(cleaned.splitlines()),
            },
        )
```

---

以上方案基于现有解析框架，只需在处理管线中增加 TXT 的编码探测与清洗，就能实现「PDF/Word/TXT 一致体验」。后续如需扩展 Markdown、日志等格式，可在此基础上做更细粒度的结构识别。