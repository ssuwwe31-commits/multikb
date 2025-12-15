# Excel 表格上传解析与分块方案

> 目标：为 `.xls` / `.xlsx` / `.xlsb` / `.csv`（Excel 体系）文件提供稳定的上传、解析、分块与索引闭环，实现与 PDF / Word / TXT 一致的文档入库体验，并针对表格结构提供额外的结构化 chunk。

## 1. 适用场景与输入约束

| 项目 | 建议 |
| --- | --- |
| 支持的后缀 | `.xlsx`（首选）、`.xls`、`.xlsb`（可选，依赖 pyxlsb）、`.csv`（作为单表 Excel） |
| 文件大小 | 默认 30 MB；若工作表 > 20 万行建议拆分 |
| 工作表数 | 默认上限 20，可配置；超过后提示选择部分 Sheet |
| 单元格格式 | 读取值与格式（数值/日期/百分比），可配置是否保留样式 |
| 公式支持 | 默认取公式计算值，保留公式文本到 metadata |
| 编码 | `.csv` 需自动探测编码（UTF-8、GBK 等），统一转 UTF-8 |

## 2. 解析流程

1. **上传**：沿用 `POST /api/documents/upload`，`doc_type = excel`，写入原始文件至对象存储。
2. **元信息预填**：记录文件名、大小、扩展名、上传人、知识库 ID。
3. **工作表扫描**：
   - 利用 `openpyxl`（xlsx/xlsm）、`xlrd`（xls，若需）或 `pyxlsb`（xlsb）统一抽象。
   - 统计 sheet 名称、行列数量、是否存在合并单元格/公式。
4. **数据加载**：
   - 按 sheet 流式读取，避免一次性加载超大表。
   - 对 `.csv` 使用 `pandas.read_csv` chunk 模式或 `csv` 原生 reader。
5. **预处理**：
   - 去除全空行/空列；
   - 识别表头行（通过粗糙启发式：前 5 行非空占比、是否包含文本字段）；
   - 对合并单元格执行“向下/向右填充”。
6. **归一化**：
   - 值统一转字符串，日期格式化为 ISO8601，数字保留原本精度；
   - 记录原格式信息（`cell_type`、`number_format`、`formula`）。

## 3. 分块策略

| Chunk 类型 | 场景 | 构造方式 |
| --- | --- | --- |
| **Structured Tabular Chunk** | 面向问答/检索需要结构信息 | 按 sheet 将表格切成「表头 + N 行记录」的窗口，默认 `window_rows = 50`，`overlap_rows = 10`，输出 JSON/Markdown 表；metadata 写入 `sheet_name`、`row_start`、`row_end`、`header_hash`。 |
| **Flattened Text Chunk** | 兼容全文检索 | 将每个 Sheet 转成 Markdown 表文本，再按 1000 字滑窗切分，`overlap = 200`。 |
| **Summary Chunk（可选）** | 大表概览 | 对包含 >5k 行的 sheet 先生成统计摘要（行数、列数、数值字段 min/max/avg、枚举字段样本），作为额外 chunk，提升问答可解释性。 |

### Sheet 级处理顺序

1. 读取表头并标准化（去空格/特殊字符，生成 slug）。
2. 将数据转换为 `List[Dict[str, str]]`。CSV 视为单 sheet，`sheet_name = "__csv__"`，并统一输出 `header_detected` 等 metadata，确保与多 sheet Excel 一致。
3. 判定 sheet 类型：
   - 若 `header_detected = true` 且列宽/行高在合理范围内，则标记为 `sheet_type = "tabular"`；
   - 若存在大量合并单元格、跨行标题、图表/图片或仪表盘布局，则标记为 `sheet_type = "layout"`，并记录 `layout_features`。
4. `sheet_type = "tabular"`：使用流式窗口器生成 tabular chunk；若窗口内数据体积 > 4 KB，则按以下规则降采样列：优先保留非空率最高的前 10 列 + 必填字段 + 数值列，超出部分汇总为统计列（`col_name_summary`，包含 min/max/avg/distinct_cnt）。降采样后的 schema 需在 metadata 中记录 `columns_dropped` 以便回溯。
5. `sheet_type = "layout"`：将单元格网格转为 Markdown（保留单元格坐标），对图片/图表/形状等嵌入对象抽取为附件（保存到对象存储，返回 `object_url`），chunk 内容中使用 `![img](proxy://...)` 占位符，并在 metadata 写入 `embedded_objects`。
6. 将窗口的 Markdown 渲染结果送入文本分块器，保持与其他文档一致的分词/向量化流程。

## 4. 元信息与存储

| 字段 | 说明 |
| --- | --- |
| `sheet_count` | 工作表数量 |
| `sheets` | 列表，包含 `name`、`rows`、`columns`、`has_merge`、`has_formula`、`header_detected`、`sheet_type`、`layout_features` |
| `row_limit_hit` | 是否触达可配置的行数上限 |
| `numeric_columns` | 每个 sheet 中数字列名称集合 |
| `datetime_columns` | 日期列集合 |
| `preview_samples` | 每个 sheet 前 3 行示例，供前端预览 |
| `csv_encoding` | 针对 CSV 的编码记录 |
| `embedded_objects` | sheet 中图片/图表/形状的列表（`type`、`range`、`object_url`） |

所有元信息写入 `documents.metadata`，同时在 `chunks.metadata` 中附带 `sheet_name`、`row_range`、`column_headers`、`chunk_type` 等字段。

## 5. 错误处理与用户提示

| 场景 | 行为 |
| --- | --- |
| 不支持的格式/受损文件 | 在解析阶段抛出 `DocumentParseError`，前端提示“请另存为 xlsx 后重试” |
| 单 sheet 超行限制 | 提示用户拆分，或允许选择“仅采样前 N 行” |
| 公式计算失败 | 回退到公式文本，chunk metadata 标记 `formula_fallback = true` |
| 合并单元格过大 | 将合并信息写入 metadata，并提示可能导致上下文重复 |
| CSV 编码失败 | 回退 UTF-8，失败则提示上传 UTF-8 版本 |

## 6. API / 任务设计

### 6.1 上传入口 `POST /api/documents/upload`

- `metadata.doc_type = "excel"`
- 可选参数：`sheet_whitelist`（列表）、`row_limit_per_sheet`、`window_rows`
- 上传前执行知识库权限校验（上传者需具备写权限），任务上下文写入 `tenant_id`、`project_id`，用于后续解析任务隔离。

### 6.2 解析任务

`document_tasks.process_document_task` 新增 `ExcelDocumentParser`，其输出必须包含：

- `chunks`: `List[ChunkPayload]`，其中 `ChunkPayload` 包含 `content`, `chunk_type`, `metadata`；
- `document_metadata`: 上文定义的 sheet 元信息；
- `audit_trail`: 记录解析阶段的关键事件（库选择、降采样、错误）。

```python
class ExcelDocumentParser:
    def parse(self, file_path: str, options: ExcelParseOptions) -> ParsedDocument:
        workbook = self._load_workbook(file_path, options)
        for sheet in workbook.sheets:
            rows = self._iter_rows(sheet, options)
            header = detect_header(rows)
            tabular_chunks = build_tabular_chunks(rows, header, options)
            text_chunks = render_markdown_chunks(tabular_chunks, options)
            yield from tabular_chunks + text_chunks
```

### 6.3 任务状态与重解析

- `POST /api/documents/{id}/reprocess` 允许指定 `sheet_whitelist`、`row_limit_per_sheet`、`window_rows`；后端需校验参数与原文档权限一致。
- 任务状态接口 `GET /api/documents/{id}` 新增 `parse_audit` 字段，展示最近一次 Excel 解析日志与降采样信息。

### 6.4 Sheet 预览与 Chunk 查询

- `GET /api/documents/{id}/sheets`
  - 响应字段：`items: [{name, rows, columns, preview_samples, header_detected, has_merge, has_formula}]`
  - 权限：同文档查看权限。
- `GET /api/documents/{id}/chunks`
  - 支持 `chunk_type` 过滤（`tabular/text/summary`）。
  - 响应示例：

```json
{
  "total": 42,
  "items": [
    {
      "id": 9012,
      "chunk_type": "tabular",
      "content": "| 日期 | 销售额 |\n| --- | --- |\n| 2025-01-01 | 1200 |",
      "metadata": {
        "sheet_name": "Sales",
        "sheet_type": "tabular",
        "row_start": 1,
        "row_end": 50,
        "column_headers": ["日期", "销售额"],
        "columns_dropped": ["备注"],
        "summary_stats": {
          "销售额": {"min": 100, "max": 2000, "avg": 890.5}
        }
      }
    },
    {
      "id": 9013,
      "chunk_type": "text",
      "content": "![img](proxy://excel/object/123)\n区域 A1:C5 展示 KPI 看板...",
      "metadata": {
        "sheet_name": "Dashboard",
        "sheet_type": "layout",
        "embedded_objects": [
          {
            "type": "image",
            "range": "B2:C6",
            "object_url": "/api/documents/901/objects/123"
          }
        ],
        "layout_features": ["merged_cells", "charts"]
      }
    }
  ]
}
```

前端在上传完成后基于 `/sheets` 接口展示表格预览，并在 chunk 预览页新增列视图，区分不同 `chunk_type`。

### 6.5 复用 Word 视图与图片处理能力

- **前端展示/编辑复用**：Excel 的 chunk 接口字段与 Word 文档保持一致（`chunk_type`、`content`、`metadata`），因此前端可直接复用已有的 Word `DocumentPreview`、`ChunkEditModal`、`TableViewer` 等组件，仅需在 `sheet_type = layout` 时启用网格视图。Tabular chunk 输出 Markdown 表格，可由现有 Word 表格渲染逻辑直接展示；文本 chunk 编辑沿用 Word 的 Markdown/纯文本编辑器。
- **图片代理与预览**：Excel 解析产生的 `embedded_objects` 存储到 `document_images` 与 MinIO，与 Word 完全相同，可继续使用 `GET /api/images/file?object=...` 代理接口和前端现有的图片 lightbox 组件。
- **修改/批注复用**：若需在前端对 chunk 进行标注或重新分块，可沿用 Word 的 `chunk_update` 接口和审计逻辑，只需在提交 payload 时附带 `sheet_name`、`sheet_type`，以便后端回写 Excel 元数据。
- **服务层复用**：图片 OCR、向量化、MinIO 存储沿用 Word 的 `DocumentImageService`；表格渲染可以调用 Word 的 `DocxTableFormatter` 以保持一致的 Markdown 输出风格。

## 7. 性能与扩展

1. **流式解析**：使用生成器逐行产出，避免一次性加载全部行。
2. **多进程/并发**：Sheet 级别可并行解析，但需限制最大并发以控制内存。
3. **缓存**：对重复表头（通过 hash）可使用共享 embedding，减少向量化次数。
4. **可插拔抽取器**：未来支持“关键列检测”“数据透视表解析”时，只需在 `ExcelDocumentParser` 中扩展 hook。
5. **数据脱敏**：可选在解析时应用列级脱敏规则（例如手机号、身份证号自动掩码）。
6. **可观测性**：暴露解析耗时、单 sheet 最大内存、降采样次数、公式回退次数等指标，写入 Prometheus / 日志，方便运维排查。
7. **测试矩阵**：
   - 覆盖 `.xlsx/.xls/.xlsb/.csv`，包含合并单元格、公式、日期列、超宽表；
   - 针对权限校验、参数校验的单测；
   - 端到端回归：上传 → 解析 → `/sheets` → `/chunks` → 重解析，确保 metadata/内容一致。

---

该方案在保持与现有文档管线一致性的基础上，针对 Excel 的结构化特性提供了双通道 chunk（结构化 + 文本），兼顾检索效果与用户可解释性，并为后续的表格问答、统计摘要等能力预留扩展点。***

