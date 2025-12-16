"""
Markdown Document Service
根据设计文档实现 Markdown 文档解析服务
"""

import os
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from charset_normalizer import from_bytes

from app.core.logging import logger

try:
    import mistune
    from mistune import create_markdown
    # mistune 3.x 使用字符串列表指定插件，不需要直接导入插件对象
    MISTUNE_AVAILABLE = True
except ImportError:
    MISTUNE_AVAILABLE = False
    # 不在这里输出警告，只在真正使用 MarkdownService 时检查


class MarkdownService:
    """Markdown 文档解析服务，输出结构与 DOCX/PDF/TXT 解析保持一致。"""

    def __init__(self, db: Session):
        self.db = db
        self.detected_encoding: Optional[str] = None
        self.encoding_confidence: Optional[float] = None
        
        if not MISTUNE_AVAILABLE:
            raise RuntimeError("缺少依赖 mistune，请先安装: pip install mistune")

    def parse_document(self, file_path: str) -> Dict[str, Any]:
        """解析 Markdown 文档"""
        logger.info(f"[MD] 开始解析 Markdown 文件: {file_path}")
        
        # 1. 加载文件并检测编码
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
        
        self._detect_encoding(raw_bytes)
        normalized_text = self._decode_and_normalize(raw_bytes)
        
        # 2. 解析 Markdown AST
        try:
            # mistune 3.x 使用字符串列表指定插件（'table' 是内置插件名）
            md = create_markdown(
                renderer='ast',
                plugins=['table']  # 表格插件，strikethrough 等功能已内置在基础解析器中
            )
            ast = md(normalized_text)
        except Exception as e:
            logger.warning(f"[MD] Markdown 解析失败，降级为纯文本处理: {e}")
            # 降级为纯文本处理
            return self._fallback_to_text(normalized_text)
        
        # 3. 提取结构信息（用于元数据统计）
        # 传递原始文本以便计算行号
        heading_structure = self._extract_headings(ast, normalized_text)
        code_blocks = self._extract_code_blocks(ast)
        
        # 4. 构建有序元素列表
        ordered_elements: List[Dict[str, Any]] = []
        filtered_elements: List[Dict[str, Any]] = []
        text_element_index_map: List[Dict[str, Any]] = []
        tables: List[Dict[str, Any]] = []  # 表格列表，在处理 ordered_elements 时填充
        
        element_index = 0
        doc_order = 0
        current_heading_path: List[str] = []
        line_counter = 1
        
        for element in ast:
            element_type = element.get('type', '')
            
            if element_type == 'heading':
                level = element.get('attrs', {}).get('level', 1)
                heading_text = self._extract_text_from_element(element)
                # 更新标题路径
                current_heading_path = self._update_heading_path(
                    current_heading_path, level, heading_text
                )
                
                elem = {
                    "type": "text",
                    "text": heading_text,
                    "element_index": element_index,
                    "doc_order": doc_order,
                    "heading_level": level,
                    "heading_path": current_heading_path.copy(),
                }
                ordered_elements.append(elem)
                filtered_elements.append({
                    "category": "heading",
                    "text": heading_text,
                    "element_index": element_index,
                })
                text_element_index_map.append({
                    "element_index": element_index,
                    "element_type": "heading",
                    "heading_level": level,
                    "heading_path": current_heading_path.copy(),
                })
                element_index += 1
                doc_order += 1
                
            elif element_type == 'code_block':
                code_content = element.get('raw', '')
                language = element.get('attrs', {}).get('language', '')
                
                elem = {
                    "type": "code",
                    "text": code_content,
                    "element_index": element_index,
                    "doc_order": doc_order,
                    "code_language": language,
                    "heading_path": current_heading_path.copy(),
                }
                ordered_elements.append(elem)
                filtered_elements.append({
                    "category": "code",
                    "text": code_content,
                    "element_index": element_index,
                })
                text_element_index_map.append({
                    "element_index": element_index,
                    "element_type": "code",
                    "code_language": language,
                    "heading_path": current_heading_path.copy(),
                })
                element_index += 1
                doc_order += 1
                
            elif element_type == 'table':
                table_data_raw = self._extract_table_data(element)
                # 转换为标准格式
                headers = table_data_raw.get('headers', [])
                rows = table_data_raw.get('rows', [])
                # 构建 cells 数组（表头 + 数据行）
                cells = []
                if headers:
                    cells.append(headers)
                cells.extend(rows)
                
                # 构建标准 table_data 格式
                table_data_standard = {
                    'cells': cells,
                    'rows': len(cells),
                    'columns': len(headers) if headers else (len(rows[0]) if rows else 0),
                    'structure': 'markdown_extracted',
                    'html': None,
                }
                # 生成制表符分隔的文本（用于检索）
                table_text = '\n'.join('\t'.join(str(cell or '') for cell in row) for row in cells)
                table_markdown = self._table_to_markdown(table_data_raw)
                
                # 添加到 tables 列表（用于后续处理）
                tables.append({
                    'element_index': element_index,
                    'table_data': table_data_standard,
                    'table_text': table_text,
                    'page_number': None,
                    'doc_order': doc_order,
                })
                
                elem = {
                    "type": "table",
                    "text": table_markdown,
                    "element_index": element_index,
                    "doc_order": doc_order,
                    "table_data": table_data_standard,
                    "table_text": table_text,
                    "heading_path": current_heading_path.copy(),
                }
                ordered_elements.append(elem)
                filtered_elements.append({
                    "category": "Table",
                    "text": table_text,
                    "element_index": element_index,
                })
                text_element_index_map.append({
                    "element_index": element_index,
                    "element_type": "table",
                    "heading_path": current_heading_path.copy(),
                })
                element_index += 1
                doc_order += 1
                
            else:
                # 其他元素（段落、列表等）转换为文本
                text_content = self._extract_text_from_element(element)
                if not text_content.strip():
                    continue
                
                elem = {
                    "type": "text",
                    "text": text_content,
                    "element_index": element_index,
                    "doc_order": doc_order,
                    "heading_path": current_heading_path.copy(),
                }
                ordered_elements.append(elem)
                filtered_elements.append({
                    "category": "text",
                    "text": text_content,
                    "element_index": element_index,
                })
                text_element_index_map.append({
                    "element_index": element_index,
                    "element_type": "text",
                    "heading_path": current_heading_path.copy(),
                })
                element_index += 1
                doc_order += 1
        
        # 5. 构建元数据
        metadata = {
            "element_count": len(ordered_elements),
            "line_count": len(normalized_text.splitlines()),
            "original_encoding": self.detected_encoding,
            "encoding_confidence": self.encoding_confidence,
            "markdown_version": "GFM",
            "has_code_blocks": len(code_blocks) > 0,
            "has_tables": len(tables) > 0,
            "code_languages": list(set(block.get('language', '') for block in code_blocks if block.get('language'))),
            "table_count": len(tables),
            "heading_structure": heading_structure,
        }
        
        logger.info(
            f"[MD] 解析完成: 行数={metadata['line_count']}, "
            f"元素={len(ordered_elements)}, 代码块={len(code_blocks)}, 表格={len(tables)}"
        )
        
        return {
            "text_content": normalized_text,
            "ordered_elements": ordered_elements,
            "filtered_elements_light": filtered_elements,
            "text_element_index_map": text_element_index_map,
            "tables": tables,
            "images": [],
            "metadata": metadata,
        }

    def _detect_encoding(self, raw_bytes: bytes) -> None:
        """检测文件编码"""
        match = from_bytes(raw_bytes).best()
        if match:
            self.detected_encoding = match.encoding
            if hasattr(match, 'confidence'):
                self.encoding_confidence = match.confidence
            elif hasattr(match, 'percent_coherence'):
                self.encoding_confidence = match.percent_coherence / 100.0
            elif hasattr(match, 'coherence'):
                self.encoding_confidence = match.coherence
            else:
                self.encoding_confidence = None
        else:
            self.detected_encoding = "utf-8"
            self.encoding_confidence = None

    def _decode_and_normalize(self, raw_bytes: bytes) -> str:
        """解码并规范化文本"""
        encoding = self.detected_encoding or "utf-8"
        try:
            text = raw_bytes.decode(encoding, errors="replace")
        except Exception:
            logger.warning(f"[MD] 使用编码 {encoding} 解码失败，回退 UTF-8")
            encoding = "utf-8"
            text = raw_bytes.decode(encoding, errors="replace")
            self.detected_encoding = encoding
        
        # 统一换行符并去除 BOM
        normalized = (
            text.replace("\r\n", "\n")
            .replace("\r", "\n")
            .replace("\ufeff", "")
        )
        return normalized.strip("\n")

    def _extract_headings(self, ast: List[Dict[str, Any]], normalized_text: str = '') -> List[Dict[str, Any]]:
        """提取标题结构"""
        headings = []
        lines = normalized_text.split('\n') if normalized_text else []
        
        for element in ast:
            if element.get('type') == 'heading':
                level = element.get('attrs', {}).get('level', 1)
                text = self._extract_text_from_element(element)
                
                # 尝试计算行号：在原始文本中查找标题位置
                line_number = 0
                if normalized_text and text:
                    # 查找标题文本在原始文本中的位置
                    try:
                        # 使用标题文本的前20个字符来匹配（避免特殊字符问题）
                        search_text = text[:50].strip()
                        if search_text:
                            for i, line in enumerate(lines, start=1):
                                # 检查行是否包含标题文本（去除 Markdown 标记）
                                line_stripped = line.lstrip('#').strip()
                                if search_text in line_stripped or line_stripped in search_text:
                                    line_number = i
                                    break
                    except Exception as e:
                        logger.debug(f"[MD] 计算标题行号失败: {e}")
                
                # 如果还是找不到，尝试从元素属性获取
                if line_number == 0:
                    line_number = (
                        element.get('lineno') or
                        element.get('line_number') or
                        element.get('attrs', {}).get('lineno') or
                        0
                    )
                
                headings.append({
                    "level": level,
                    "text": text,
                    "line": line_number,
                })
                
                if text:
                    logger.debug(f"[MD] 提取标题: H{level} '{text[:30]}...' (行 {line_number})")
                else:
                    logger.warning(f"[MD] 提取到空标题: H{level} (行 {line_number})")
        
        logger.info(f"[MD] 共提取 {len(headings)} 个标题，其中 {sum(1 for h in headings if h['text'])} 个有文本内容")
        return headings

    def _extract_code_blocks(self, ast: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取代码块"""
        code_blocks = []
        for element in ast:
            if element.get('type') == 'code_block':
                code_blocks.append({
                    "language": element.get('attrs', {}).get('language', ''),
                    "content": element.get('raw', ''),
                })
        return code_blocks

    def _extract_tables(self, ast: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取表格"""
        tables = []
        for element in ast:
            if element.get('type') == 'table':
                table_data = self._extract_table_data(element)
                tables.append(table_data)
        return tables

    def _extract_table_data(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """提取表格数据"""
        children = element.get('children', [])
        headers = []
        rows = []
        
        # 查找表头
        for child in children:
            if child.get('type') == 'thead':
                thead_children = child.get('children', [])
                if thead_children:
                    header_row = thead_children[0]
                    if header_row.get('type') == 'table_row':
                        for cell in header_row.get('children', []):
                            if cell.get('type') == 'table_cell':
                                headers.append(self._extract_text_from_element(cell))
        
        # 查找表体
        for child in children:
            if child.get('type') == 'tbody':
                for row in child.get('children', []):
                    if row.get('type') == 'table_row':
                        row_data = []
                        for cell in row.get('children', []):
                            if cell.get('type') == 'table_cell':
                                row_data.append(self._extract_text_from_element(cell))
                        if row_data:
                            rows.append(row_data)
        
        return {
            "headers": headers,
            "rows": rows,
        }

    def _table_to_markdown(self, table_data: Dict[str, Any]) -> str:
        """将表格数据转换为 Markdown 格式"""
        headers = table_data.get('headers', [])
        rows = table_data.get('rows', [])
        
        if not headers:
            return ""
        
        # 表头
        lines = ["| " + " | ".join(headers) + " |"]
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        
        # 表格行
        for row in rows:
            # 确保行数据与表头列数一致
            while len(row) < len(headers):
                row.append("")
            lines.append("| " + " | ".join(row[:len(headers)]) + " |")
        
        return "\n".join(lines)

    def _extract_text_from_element(self, element: Dict[str, Any]) -> str:
        """从元素中提取纯文本"""
        element_type = element.get('type', '')
        
        # 对于 heading，需要从 children 中提取文本（mistune 3.x AST 结构）
        if element_type == 'heading':
            if 'children' in element:
                text_parts = []
                for child in element.get('children', []):
                    if child.get('type') == 'text':
                        text_parts.append(child.get('raw', child.get('text', '')))
                    elif child.get('type') == 'code':
                        text_parts.append(child.get('raw', ''))
                    else:
                        # 递归提取
                        text_parts.append(self._extract_text_from_element(child))
                return "".join(text_parts)
            # fallback: 尝试直接获取 raw
            return element.get('raw', '')
        
        # 其他类型优先使用 raw
        if element_type in ('paragraph', 'block_code', 'code_block'):
            raw_text = element.get('raw', '')
            if raw_text:
                return raw_text
        
        # 通用处理：从 children 中提取
        if 'children' in element:
            text_parts = []
            for child in element.get('children', []):
                if child.get('type') == 'text':
                    text_parts.append(child.get('raw', child.get('text', '')))
                elif child.get('type') == 'code':
                    text_parts.append(child.get('raw', ''))
                else:
                    # 递归提取
                    text_parts.append(self._extract_text_from_element(child))
            return "".join(text_parts)
        
        return element.get('raw', element.get('text', ''))

    def _update_heading_path(
        self, current_path: List[str], level: int, heading_text: str
    ) -> List[str]:
        """更新标题路径"""
        new_path = current_path.copy()
        # 保持路径长度与当前层级一致
        new_path = new_path[:level - 1]
        new_path.append(heading_text)
        return new_path

    def _fallback_to_text(self, text: str) -> Dict[str, Any]:
        """降级为纯文本处理"""
        logger.info("[MD] 使用纯文本降级处理")
        lines = text.split("\n")
        line_count = len(lines)
        
        ordered_elements: List[Dict[str, Any]] = []
        filtered_elements: List[Dict[str, Any]] = []
        text_element_index_map: List[Dict[str, Any]] = []
        
        segments = self._split_paragraphs(lines)
        if not segments and text.strip():
            segments = [{
                "line_start": 1,
                "line_end": line_count,
                "content": text.strip()
            }]
        
        for idx, segment in enumerate(segments):
            content = segment.get("content", "").strip()
            if not content:
                continue
            
            element = {
                "type": "text",
                "text": content,
                "element_index": idx,
                "doc_order": idx,
                "line_start": segment.get("line_start"),
                "line_end": segment.get("line_end"),
            }
            ordered_elements.append(element)
            filtered_elements.append({
                "category": "text",
                "text": content,
                "element_index": idx,
            })
            text_element_index_map.append({
                "element_index": idx,
                "element_type": "text",
                "line_start": segment.get("line_start"),
                "line_end": segment.get("line_end"),
            })
        
        metadata = {
            "element_count": len(ordered_elements),
            "line_count": line_count,
            "original_encoding": self.detected_encoding,
            "encoding_confidence": self.encoding_confidence,
            "markdown_version": "fallback",
            "has_code_blocks": False,
            "has_tables": False,
            "code_languages": [],
            "table_count": 0,
            "heading_structure": [],
        }
        
        return {
            "text_content": text,
            "ordered_elements": ordered_elements,
            "filtered_elements_light": filtered_elements,
            "text_element_index_map": text_element_index_map,
            "tables": [],
            "images": [],
            "metadata": metadata,
        }

    @staticmethod
    def _split_paragraphs(lines: List[str]) -> List[Dict[str, Any]]:
        """按段落分割文本（用于降级处理）"""
        segments: List[Dict[str, Any]] = []
        buffer: List[str] = []
        line_start = 1
        
        for idx, line in enumerate(lines, start=1):
            stripped = line.rstrip()
            if stripped.strip() == "":
                if buffer:
                    segments.append({
                        "line_start": line_start,
                        "line_end": idx - 1,
                        "content": "\n".join(buffer).strip(),
                    })
                    buffer = []
                line_start = idx + 1
                continue
            
            if not buffer:
                line_start = idx
            buffer.append(stripped)
        
        if buffer:
            segments.append({
                "line_start": line_start,
                "line_end": len(lines),
                "content": "\n".join(buffer).strip(),
            })
        
        return segments
