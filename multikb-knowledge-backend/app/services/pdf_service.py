from __future__ import annotations

import io
import os
from dataclasses import dataclass
from statistics import mean
from collections import Counter
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.logging import logger


def _table_has_data(cells: List[List[str]], debug: bool = False) -> Tuple[bool, Optional[str]]:
    """
    验证是否为真正的表格数据
    
    判断标准：
    1. 至少2行数据（不包括表头）
    2. 至少2列
    3. 单元格平均长度较短（表格单元格通常<50字符，文本段落通常>100字符）
    4. 行数>=3或单元格平均长度<30（更严格的验证）
    
    Returns:
        (is_valid, reason): 是否为有效表格，以及失败原因（如果失败）
    """
    if not cells:
        return False, "cells为空"
    
    # 至少需要2行
    if len(cells) <= 1:
        return False, f"行数不足: {len(cells)}行（需要至少2行）"
    
    # 检查列数：至少2列才可能是表格
    max_cols = max(len(row) for row in cells) if cells else 0
    if max_cols < 2:
        return False, f"列数不足: {max_cols}列（需要至少2列）"
    
    # 计算所有非空单元格的平均长度
    total_length = 0
    cell_count = 0
    non_empty_rows = 0
    
    for row in cells:
        row_has_content = False
        for cell in row:
            cell_text = (cell or "").strip()
            if cell_text:
                total_length += len(cell_text)
                cell_count += 1
                row_has_content = True
        if row_has_content:
            non_empty_rows += 1
    
    # 至少需要2行有内容
    if non_empty_rows < 2:
        return False, f"有内容的行数不足: {non_empty_rows}行（需要至少2行）"
    
    # 如果单元格数量太少，可能是误识别
    if cell_count < 4:  # 至少4个单元格（2行x2列）
        return False, f"单元格数量太少: {cell_count}个（需要至少4个）"
    
    # 计算平均单元格长度
    avg_cell_length = total_length / cell_count if cell_count > 0 else 0
    
    # 表格特征：
    # 1. 单元格平均长度较短（<50字符）且行数>=3，很可能是表格
    # 2. 单元格平均长度<30，即使只有2行也可能是表格（如简单的两列表格）
    # 3. 如果平均长度>100，很可能是文本段落被误识别
    if avg_cell_length > 100:
        # 平均单元格长度>100，很可能是文本段落，不是表格
        return False, f"平均单元格长度过长: {avg_cell_length:.1f}字符（>100，可能是文本段落）"
    
    if len(cells) >= 3 and avg_cell_length < 50:
        # 3行以上且平均长度<50，很可能是表格
        if debug:
            logger.debug(f"[表格验证] 通过: 行数={len(cells)}, 平均长度={avg_cell_length:.1f}, 列数={max_cols}")
        return True, None
    
    if avg_cell_length < 30:
        # 平均长度<30，即使只有2行也可能是表格
        if debug:
            logger.debug(f"[表格验证] 通过: 平均长度={avg_cell_length:.1f}<30, 行数={len(cells)}, 列数={max_cols}")
        return True, None
    
    # 其他情况：2行且平均长度在30-100之间，需要更严格判断
    # 检查是否有明显的表格特征：数字、日期、对齐等
    # 如果大部分单元格都很短（<20字符），可能是表格
    short_cells = sum(1 for row in cells for cell in row if cell and len(cell.strip()) < 20)
    short_cell_ratio = short_cells / cell_count if cell_count > 0 else 0
    if short_cell_ratio >= 0.6:  # 60%以上单元格都很短
        if debug:
            logger.debug(f"[表格验证] 通过: 短单元格比例={short_cell_ratio:.1%}>=60%, 行数={len(cells)}, 列数={max_cols}")
        return True, None
    
    # 默认不认为是表格（保守策略）
    reason = f"不满足表格特征: 行数={len(cells)}, 列数={max_cols}, 平均长度={avg_cell_length:.1f}, 短单元格比例={short_cell_ratio:.1%}"
    return False, reason


def _normalize_noise_text(text: str) -> str:
    cleaned = re.sub(r"\d+", "", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip().lower()


def _is_decorative_text(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return True
    if len(set(stripped)) <= 2 and len(stripped) >= 3:
        return True
    if len(stripped) <= 2:
        return True
    return False


_TOC_PREFIXES = ["目录", "table of contents"]
_TOC_LINE_REGEX = re.compile(r"[\.·\u2026]{2,}\s*\d+")


def _is_toc_text(text: Optional[str]) -> bool:
    if not text:
        return False
    raw = str(text)
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        return False
    first_line_normalized = lines[0].replace(" ", "").lower()
    for prefix in _TOC_PREFIXES:
        if first_line_normalized.startswith(prefix.replace(" ", "")):
            return True
    dotted_lines = sum(1 for line in lines if _TOC_LINE_REGEX.search(line))
    if dotted_lines >= 2:
        return True
    if len(lines) >= 1 and _TOC_LINE_REGEX.search(lines[0]):
        return True
    return False


def _append_or_merge_table(items: List[_LayoutItem], new_table: _LayoutItem, merge_tolerance: float = 8.0) -> None:
    for existing in reversed(items):
        if existing.type != "table" or existing.page_index != new_table.page_index:
            continue
        ex_left, ex_top, ex_right, ex_bottom = existing.bbox
        new_left, new_top, new_right, new_bottom = new_table.bbox
        column_width = max(1.0, max(existing.page_width, new_table.page_width))
        same_column = abs(ex_left - new_left) <= column_width * 0.05 and abs(ex_right - new_right) <= column_width * 0.05
        vertical_gap = new_top - ex_bottom
        vertically_adjacent = -merge_tolerance <= vertical_gap <= merge_tolerance * 4
        vertical_overlap = min(ex_bottom, new_bottom) - max(ex_top, new_top)
        has_overlap = vertical_overlap >= -merge_tolerance
        if same_column and (vertically_adjacent or has_overlap):
            if existing.table_cells and new_table.table_cells:
                if existing.table_cells[-1] == new_table.table_cells[0]:
                    new_body = new_table.table_cells[1:]
                else:
                    new_body = new_table.table_cells
            else:
                new_body = new_table.table_cells or []
            existing.table_cells.extend(new_body)
            existing.bbox = (
                min(ex_left, new_left),
                min(ex_top, new_top),
                max(ex_right, new_right),
                max(ex_bottom, new_bottom),
            )
            return
    items.append(new_table)


def _merge_short_text_items(items: List[_LayoutItem], length_threshold: int = 60) -> List[_LayoutItem]:
    merged: List[_LayoutItem] = []
    for item in items:
        if item.type != "text" or not item.text:
            merged.append(item)
            continue
        if not merged:
            merged.append(item)
            continue
        prev = merged[-1]
        if (
            prev.type == "text"
            and len(prev.text or "") <= length_threshold
            and len(item.text or "") <= length_threshold
            and prev.page_index == item.page_index
            and abs(prev.bbox[2] - item.bbox[0]) <= (item.page_width or 1.0) * 0.05
        ):
            combined_text = f"{prev.text} {item.text}".strip()
            merged[-1] = _LayoutItem(
                type="text",
                page_index=prev.page_index,
                bbox=(
                    min(prev.bbox[0], item.bbox[0]),
                    min(prev.bbox[1], item.bbox[1]),
                    max(prev.bbox[2], item.bbox[2]),
                    max(prev.bbox[3], item.bbox[3]),
                ),
                page_width=item.page_width,
                page_height=item.page_height,
                text=combined_text,
                max_font_size=max(prev.max_font_size or 0.0, item.max_font_size or 0.0),
            )
        else:
            merged.append(item)
    return merged


@dataclass
class _LayoutItem:
    type: str  # 'text' | 'table' | 'image'
    page_index: int
    bbox: tuple[float, float, float, float]
    page_width: float
    page_height: float
    text: Optional[str] = None
    max_font_size: Optional[float] = None
    table_cells: Optional[List[List[str]]] = None
    image_index: Optional[int] = None


class PdfService:
    """PDF 文档解析服务，输出结构与 DocxService.parse_document 对齐"""

    def __init__(self, db: Session):
        self.db = db

    def parse_document(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        try:
            import pdfplumber
        except ImportError as exc:  # pragma: no cover - 运行时提示
            raise RuntimeError("缺少依赖 pdfplumber，请先安装: pip install pdfplumber") from exc

        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise RuntimeError("缺少依赖 PyMuPDF，请先安装: pip install pymupdf") from exc

        logger.info(f"[PDF] 开始解析: {file_path}")

        layout_items: List[_LayoutItem] = []
        images_payload: List[Dict[str, Any]] = []
        page_font_stats: Dict[int, Dict[str, float]] = {}
        page_dimensions: Dict[int, Tuple[float, float]] = {}
        pages_with_tables: set[int] = set()

        try:
            import camelot
            camelot_available = True
        except ImportError:
            camelot_available = False

        header_candidates: Dict[str, set[int]] = {}
        footer_candidates: Dict[str, set[int]] = {}

        with pdfplumber.open(file_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                page_width = float(page.width or 1.0)
                page_height = float(page.height or 1.0)

                page_dimensions[page_idx] = (page_width, page_height)

                words = page.extract_words(
                    use_text_flow=True,
                    keep_blank_chars=False,
                    extra_attrs=["size", "fontname"],
                )
                if not words:
                    continue

                words = sorted(words, key=lambda w: (w.get("top", 0.0), w.get("x0", 0.0)))
                line_tolerance = 3.0
                paragraph_tolerance = 10.0

                lines: List[List[Dict[str, Any]]] = []
                for word in words:
                    if not word.get("text"):
                        continue
                    if not lines:
                        lines.append([word])
                        continue
                    last_line = lines[-1]
                    if abs(word.get("top", 0.0) - last_line[-1].get("top", 0.0)) <= line_tolerance:
                        last_line.append(word)
                    else:
                        lines.append([word])

                paragraphs: List[List[Dict[str, Any]]] = []
                current_block: List[List[Dict[str, Any]]] = []
                for line in lines:
                    if not current_block:
                        current_block.append(line)
                        continue
                    prev_line = current_block[-1]
                    gap = line[0].get("top", 0.0) - prev_line[-1].get("bottom", prev_line[-1].get("top", 0.0))
                    if gap > paragraph_tolerance:
                        paragraphs.append([w for ln in current_block for w in ln])
                        current_block = [line]
                    else:
                        current_block.append(line)
                if current_block:
                    paragraphs.append([w for ln in current_block for w in ln])

                font_sizes = [float(w.get("size", 0.0)) for w in words if w.get("size")]
                avg_font = mean(font_sizes) if font_sizes else 0.0
                page_font_stats[page_idx] = {
                    "avg": avg_font,
                    "max": max(font_sizes) if font_sizes else 0.0,
                }

                for para_words in paragraphs:
                    text = " ".join(w.get("text", "") for w in para_words).strip()
                    if not text:
                        continue
                    x0 = min(float(w.get("x0", 0.0)) for w in para_words)
                    x1 = max(float(w.get("x1", 0.0)) for w in para_words)
                    top = min(float(w.get("top", 0.0)) for w in para_words)
                    bottom = max(float(w.get("bottom", top)) for w in para_words)
                    max_font_size = max(float(w.get("size", 0.0)) for w in para_words if w.get("size"))
                    layout_items.append(
                        _LayoutItem(
                            type="text",
                            page_index=page_idx,
                            bbox=(x0, top, x1, bottom),
                            page_width=page_width,
                            page_height=page_height,
                            text=text,
                            max_font_size=max_font_size,
                        )
                    )

                    # 记录潜在页眉页脚文本（用于后续调试与过滤）
                    top_ratio = top / page_height if page_height else 0.0
                    bottom_ratio = (page_height - bottom) / page_height if page_height else 0.0
                    normalized = _normalize_noise_text(text)
                    if normalized:
                        if top_ratio < 0.08:
                            header_candidates.setdefault(normalized, set()).add(page_idx + 1)
                        elif bottom_ratio < 0.08:
                            footer_candidates.setdefault(normalized, set()).add(page_idx + 1)

                try:
                    # 优化表格检测策略：优先使用严格的线条检测，避免误识别文本为表格
                    # 策略1: 使用线条检测（最严格，适合有边框的表格）
                    table_settings_lines = {
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                        "snap_tolerance": 3,  # 线条对齐容差
                        "join_tolerance": 3,  # 线条连接容差
                    }
                    table_objs = page.find_tables(table_settings=table_settings_lines) or []
                    
                    # 策略2: 如果线条检测没找到，尝试显式线条策略（适合有明显边框的表格）
                    if not table_objs:
                        try:
                            # 获取页面上的所有线条
                            lines = page.lines
                            if lines:
                                vertical_lines = [l for l in lines if abs(l["x0"] - l["x1"]) < 1]
                                horizontal_lines = [l for l in lines if abs(l["top"] - l["bottom"]) < 1]
                                
                                # 只有当有足够的线条时才尝试（至少2条垂直线和2条水平线，表示可能是表格）
                                if len(vertical_lines) >= 2 and len(horizontal_lines) >= 2:
                                    table_settings_explicit = {
                                        "vertical_strategy": "explicit",
                                        "horizontal_strategy": "explicit",
                                        "explicit_vertical_lines": [l["x0"] for l in vertical_lines] if vertical_lines else None,
                                        "explicit_horizontal_lines": [l["top"] for l in horizontal_lines] if horizontal_lines else None,
                                    }
                                    table_objs = page.find_tables(table_settings=table_settings_explicit) or []
                        except Exception:
                            pass
                    
                    # 策略3: 文本对齐策略（最宽松，容易误识别，仅在明确需要时使用）
                    # 注意：此策略已被禁用，因为它容易将文本段落误识别为表格
                    # 如果需要支持无边框表格，可以考虑启用，但需要更严格的验证
                    # if not table_objs:
                    #     try:
                    #         table_settings_text = {
                    #             "vertical_strategy": "text",
                    #             "horizontal_strategy": "text",
                    #         }
                    #         table_objs = page.find_tables(table_settings=table_settings_text) or []
                    #     except Exception:
                    #         pass
                            
                except Exception as e:
                    logger.debug(f"[PDF] 表格检测异常 page={page_idx + 1}: {e}")
                    table_objs = []
                for table in table_objs:
                    try:
                        cells = table.extract()
                    except Exception:
                        cells = table.extract(x_tolerance=3, y_tolerance=3) if hasattr(table, "extract") else None
                    if not cells:
                        continue
                    x0, top, x1, bottom = table.bbox
                    cleaned_cells = [[str(cell or "").strip() for cell in row] for row in cells]
                    
                    # 验证是否为真正的表格
                    is_valid_table, reason = _table_has_data(cleaned_cells, debug=True)
                    
                    if is_valid_table:
                        pages_with_tables.add(page_idx)
                        _append_or_merge_table(layout_items, _LayoutItem(
                            type="table",
                            page_index=page_idx,
                            bbox=(float(x0), float(top), float(x1), float(bottom)),
                            page_width=page_width,
                            page_height=page_height,
                            table_cells=cleaned_cells,
                        ))
                        logger.debug(
                            f"[PDF] 检测到表格 page={page_idx + 1}, rows={len(cleaned_cells)}, cols={max(len(row) for row in cleaned_cells) if cleaned_cells else 0}"
                        )
                    else:
                        # 不是表格，转换为文本
                        # 合并所有单元格内容为文本段落
                        text_lines = []
                        for row in cleaned_cells:
                            row_text = " ".join(cell for cell in row if cell.strip())
                            if row_text:
                                text_lines.append(row_text)
                        
                        if text_lines:
                            combined_text = "\n".join(text_lines)
                            max_cols = max(len(row) for row in cleaned_cells) if cleaned_cells else 0
                            logger.debug(
                                f"[PDF] 表格检测失败，转换为文本 page={page_idx + 1}, "
                                f"rows={len(cleaned_cells)}, cols={max_cols}, text_len={len(combined_text)}, "
                                f"原因: {reason}, preview={combined_text[:50]}..."
                            )
                            layout_items.append(
                                _LayoutItem(
                                    type="text",
                                    page_index=page_idx,
                                    bbox=(float(x0), float(top), float(x1), float(bottom)),
                                    page_width=page_width,
                                    page_height=page_height,
                                    text=combined_text,
                                    max_font_size=None,
                                )
                            )

        doc = fitz.open(file_path)
        try:
            for page_idx, page in enumerate(doc):
                page_rect = page.rect
                page_width = float(page_rect.width or 1.0)
                page_height = float(page_rect.height or 1.0)
                for img_index, img in enumerate(page.get_images(full=True)):
                    xref = img[0]
                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image.get("image")
                        if not image_bytes:
                            continue
                        rects = page.get_image_rects(xref)
                        if not rects:
                            continue
                        rect = rects[0]
                        bbox = (float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))
                    except Exception:
                        continue

                    images_payload.append(
                        {
                            "data": image_bytes,
                            "bytes": image_bytes,
                            "element_index": None,
                            "page_number": page_idx + 1,
                            "coordinates": None,
                            "bbox": bbox,
                            "page_width": page_width,
                            "page_height": page_height,
                        }
                    )
                    layout_items.append(
                        _LayoutItem(
                            type="image",
                            page_index=page_idx,
                            bbox=bbox,
                            page_width=page_width,
                            page_height=page_height,
                            image_index=len(images_payload) - 1,
                        )
                    )
        finally:
            doc.close()

        # 使用 Camelot 补充缺失表格（仅在pdfplumber未检测到表格时使用）
        if camelot_available:
            total_pages = len(page_dimensions)
            for page_idx in range(total_pages):
                # 如果pdfplumber已经检测到表格，跳过Camelot（避免重复）
                if page_idx in pages_with_tables:
                    continue
                    
                page_dim = page_dimensions.get(page_idx, (0.0, 0.0))
                page_width, page_height = page_dim
                try:
                    # 优先使用lattice模式（适合有边框的表格，更严格，不易误识别）
                    tables = camelot.read_pdf(
                        file_path, 
                        pages=str(page_idx + 1), 
                        flavor="lattice",
                        line_scale=40,  # 线条检测敏感度
                        copy_text=['v', 'h'],  # 复制垂直和水平文本
                    )
                    
                    # 注意：stream模式已被禁用，因为它容易将文本段落误识别为表格
                    # 如果需要支持无边框表格，可以考虑启用，但需要更严格的验证
                    # 如果lattice没找到，尝试stream模式（适合无边框表格）
                    # if tables.n == 0:
                    #     tables = camelot.read_pdf(
                    #         file_path, 
                    #         pages=str(page_idx + 1), 
                    #         flavor="stream",
                    #         row_tol=10,  # 行容差
                    #         columns=['1'],  # 列检测
                    #     )
                    
                    if tables.n > 0:
                        logger.debug(f"[PDF][Camelot] 在page={page_idx + 1}检测到{tables.n}个表格候选")
                        
                except Exception as exc:
                    logger.debug(f"[PDF] Camelot 解析失败 page={page_idx + 1}: {exc}")
                    continue
                for cam_table in tables:
                    try:
                        df = cam_table.df
                        cells = [[str(cell or "").strip() for cell in row] for row in df.values.tolist()]
                        bbox = getattr(cam_table, "_bbox", None)
                        if not bbox and hasattr(cam_table, "_bbox_coords"):
                            bbox = cam_table._bbox_coords
                        if not bbox:
                            bbox = (0.0, 0.0, page_width, page_height)
                        x1, y1, x2, y2 = map(float, bbox)
                        # Camelot 使用 PDF 坐标系（原点在左下），需转换为 top-based 坐标
                        y_bottom = min(y1, y2)
                        y_top = max(y1, y2)
                        top = max(0.0, page_height - y_top)
                        bottom = max(0.0, page_height - y_bottom)
                        left = min(x1, x2)
                        right = max(x1, x2)
                        
                        # 验证是否为真正的表格
                        is_valid_table, reason = _table_has_data(cells, debug=True)
                        
                        if is_valid_table:
                            pages_with_tables.add(page_idx)
                            _append_or_merge_table(layout_items, _LayoutItem(
                                type="table",
                                page_index=page_idx,
                                bbox=(left, top, right, bottom),
                                page_width=page_width or 1.0,
                                page_height=page_height or 1.0,
                                table_cells=cells,
                            ))
                            logger.debug(
                                f"[PDF][Camelot] 检测到表格 page={page_idx + 1}, rows={len(cells)}, cols={max(len(row) for row in cells) if cells else 0}"
                            )
                        else:
                            # 不是表格，转换为文本
                            text_lines = []
                            for row in cells:
                                row_text = " ".join(cell for cell in row if cell.strip())
                                if row_text:
                                    text_lines.append(row_text)
                            
                            if text_lines:
                                combined_text = "\n".join(text_lines)
                                max_cols = max(len(row) for row in cells) if cells else 0
                                logger.debug(
                                    f"[PDF][Camelot] 表格检测失败，转换为文本 page={page_idx + 1}, "
                                    f"rows={len(cells)}, cols={max_cols}, text_len={len(combined_text)}, "
                                    f"原因: {reason}, preview={combined_text[:50]}..."
                                )
                                layout_items.append(
                                    _LayoutItem(
                                        type="text",
                                        page_index=page_idx,
                                        bbox=(left, top, right, bottom),
                                        page_width=page_width or 1.0,
                                        page_height=page_height or 1.0,
                                        text=combined_text,
                                    )
                                )
                    except Exception as exc:
                        logger.debug(f"[PDF] Camelot 表格转换失败 page={page_idx + 1}: {exc}")

        # 对布局元素按页 & top 排序
        layout_items.sort(key=lambda item: (item.page_index, item.bbox[1]))

        # 记录疑似页眉/页脚供调试
        header_debug = {text: sorted(list(pages)) for text, pages in header_candidates.items() if len(pages) >= 2}
        footer_debug = {text: sorted(list(pages)) for text, pages in footer_candidates.items() if len(pages) >= 2}
        if header_debug:
            logger.debug(f"[PDF][HeaderCandidates] {header_debug}")
        if footer_debug:
            logger.debug(f"[PDF][FooterCandidates] {footer_debug}")

        header_counter: Counter[str] = Counter({text: len(pages) for text, pages in header_candidates.items()})
        footer_counter: Counter[str] = Counter({text: len(pages) for text, pages in footer_candidates.items()})

        # 合并短文本段落（避免碎片化）
        layout_items = _merge_short_text_items(layout_items)

        filtered_elements: List[Dict[str, Any]] = []
        text_element_map: List[Dict[str, Any]] = []
        tables_payload: List[Dict[str, Any]] = []
        text_parts: List[str] = []
        ordered_elements: List[Dict[str, Any]] = []  # ✅ 新增：统一顺序元素列表（类似Word的ordered_elements）
        element_index = 0

        def _normalize(bbox: tuple[float, float, float, float], width: float, height: float) -> Dict[str, float]:
            x0, top, x1, bottom = bbox
            width = width or 1.0
            height = height or 1.0
            return {
                "x": max(0.0, min(1.0, x0 / width)),
                "y": max(0.0, min(1.0, top / height)),
                "width": max(0.0, min(1.0, (x1 - x0) / width)),
                "height": max(0.0, min(1.0, (bottom - top) / height)),
            }

        toc_text_skipped = 0
        toc_table_skipped = 0

        for item in layout_items:
            page_stats = page_font_stats.get(item.page_index, {"avg": 0.0, "max": 0.0})
            if item.type == "text" and item.text:
                normalized = _normalize_noise_text(item.text)
                if (_is_decorative_text(item.text)
                        or (normalized and header_counter.get(normalized, 0) >= 2 and len(normalized) <= 80)
                        or (normalized and footer_counter.get(normalized, 0) >= 2 and len(normalized) <= 80)
                        or _is_toc_text(item.text)):
                    if _is_toc_text(item.text):
                        toc_text_skipped += 1
                        logger.debug(
                            "[PDF] 跳过目录段落 page=%s bbox=%s text=%.50s...",
                            item.page_index + 1,
                            item.bbox,
                            item.text.replace("\n", " ")
                        )
                    continue
                is_title = False
                if item.max_font_size and page_stats["avg"]:
                    is_title = item.max_font_size >= page_stats["avg"] * 1.2
                category = "Title" if is_title else "NarrativeText"

                filtered_elements.append(
                    {
                        "category": category,
                        "text": item.text,
                        "element_index": element_index,
                    }
                )
                text_element_map.append(
                    {
                        "element_index": element_index,
                        "element_type": category,
                        "page_number": item.page_index + 1,
                        "coordinates": _normalize(item.bbox, item.page_width, item.page_height),
                    }
                )
                # ✅ 添加到 ordered_elements（统一顺序）
                ordered_elements.append({
                    "type": "text",
                    "text": item.text,
                    "element_index": element_index,
                    "doc_order": element_index,  # PDF使用element_index作为doc_order
                })
                text_parts.append(item.text)
                element_index += 1
            elif item.type == "table" and item.table_cells:
                table_text = "\n".join("\t".join(row) for row in item.table_cells if row)
                if _is_toc_text(table_text):
                    toc_table_skipped += 1
                    logger.debug(
                        "[PDF] 跳过目录表格 page=%s rows=%s cols=%s text=%.50s...",
                        item.page_index + 1,
                        len(item.table_cells),
                        len(item.table_cells[0]) if item.table_cells else 0,
                        table_text.replace("\n", " ")
                    )
                    continue
                tables_payload.append(
                    {
                        "element_index": element_index,
                        "table_data": {
                            "cells": item.table_cells,
                            "rows": len(item.table_cells),
                            "columns": len(item.table_cells[0]) if item.table_cells and item.table_cells[0] else 0,
                            "structure": "pdf_extracted",
                            "html": None,
                        },
                        "table_text": table_text,
                        "page_number": item.page_index + 1,
                    }
                )
                filtered_elements.append(
                    {
                        "category": "Table",
                        "text": table_text,
                        "element_index": element_index,
                    }
                )
                # ✅ 添加到 ordered_elements（统一顺序）
                ordered_elements.append({
                    "type": "table",
                    "element_index": element_index,
                    "doc_order": element_index,  # PDF使用element_index作为doc_order
                })
                element_index += 1
            elif item.type == "image" and item.image_index is not None:
                img_meta = images_payload[item.image_index]
                img_meta["element_index"] = element_index
                img_meta["coordinates"] = _normalize(item.bbox, item.page_width, item.page_height)
                # ✅ 添加到 ordered_elements（统一顺序）
                ordered_elements.append({
                    "type": "image",
                    "element_index": element_index,
                    "doc_order": element_index,  # PDF使用element_index作为doc_order
                    "page_number": item.page_index + 1,
                    "coordinates": img_meta["coordinates"],
                })
                element_index += 1

        if toc_text_skipped or toc_table_skipped:
            logger.info(
                "[PDF] 目录过滤: 文本段落 %s 条, 表格 %s 个",
                toc_text_skipped,
                toc_table_skipped,
            )

        logger.info(
            "[PDF] 布局统计: 文本元素=%s, 表格=%s, 图片=%s, 页面=%s",
            sum(1 for item in layout_items if item.type == "text"),
            sum(1 for item in layout_items if item.type == "table"),
            len(images_payload),
            len(page_dimensions),
        )

        if filtered_elements:
            preview_elements = [
                {
                    "idx": idx,
                    "type": elem.get("category"),
                    "element_index": elem.get("element_index"),
                    "text_preview": (elem.get("text") or "")[:40],
                }
                for idx, elem in enumerate(filtered_elements[:5])
            ]
            logger.debug(f"[PDF] 文本元素预览(前5个): {preview_elements}")

        parse_result: Dict[str, Any] = {
            "text_content": "\n".join(text_parts).strip(),
            "tables": tables_payload,
            "images": images_payload,
            "images_binary": [
                {
                    "binary": img.get("data"),
                    "element_index": img.get("element_index"),
                    "page_number": img.get("page_number"),
                    "coordinates": img.get("coordinates"),
                }
                for img in images_payload
            ],
            "text_element_index_map": text_element_map,
            "filtered_elements_light": filtered_elements,
            "ordered_elements": ordered_elements,  # ✅ 新增：统一顺序元素列表（类似Word）
            "metadata": {
                "element_count": len(filtered_elements),
                "images_count": len(images_payload),
                "source": "pdf",
            },
        }

        # 统计表格识别情况
        total_table_candidates = sum(1 for item in layout_items if item.type == "table")
        valid_tables = len(tables_payload)
        table_conversion_count = total_table_candidates - valid_tables
        
        logger.info(
            f"[PDF] 解析完成: 文本块={len([f for f in filtered_elements if f['category'] != 'Table'])}, "
            f"表格候选={total_table_candidates}, 有效表格={valid_tables}, "
            f"转换为文本={table_conversion_count}, 图片={len(images_payload)}"
        )
        
        if table_conversion_count > 0:
            logger.info(
                f"[PDF] 表格识别说明: 检测到{total_table_candidates}个表格候选，"
                f"其中{valid_tables}个通过验证，{table_conversion_count}个因不符合表格特征已转换为文本"
            )
        return parse_result
