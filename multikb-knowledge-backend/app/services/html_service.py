"""
HTML Document Service
根据设计文档实现 HTML 文档解析服务
"""

import base64
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin

from sqlalchemy.orm import Session
from charset_normalizer import from_bytes

from app.core.logging import logger

try:
    from bs4 import BeautifulSoup, Tag, NavigableString  # type: ignore
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    import lxml  # noqa: F401
    HAS_LXML = True
except ImportError:
    HAS_LXML = False


class HtmlService:
    """HTML 文档解析服务，输出结构与 DOCX/PDF 解析保持一致。"""

    HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
    BLOCK_TEXT_TAGS = {"p", "blockquote"}
    LIST_TAGS = {"ul", "ol", "dl"}
    CODE_TAGS = {"pre"}
    LIST_ITEM_TAGS = {"li", "dt", "dd"}
    TABLE_TAG = "table"
    IMAGE_TAG = "img"
    TEXT_FALLBACK_TAGS = {"div"}
    SEMANTIC_TAGS = {"article", "section", "header", "footer", "nav", "main", "aside"}
    BLOCK_LEVEL_TAGS = {
        "p",
        "div",
        "section",
        "article",
        "header",
        "footer",
        "nav",
        "main",
        "aside",
        "ul",
        "ol",
        "dl",
        "table",
        "pre",
        "blockquote",
        "figure",
    }

    def __init__(self, db: Session):
        self.db = db
        if not BS4_AVAILABLE:
            raise RuntimeError("缺少依赖 beautifulsoup4，请先安装: pip install beautifulsoup4")

        self.detected_encoding: Optional[str] = None
        self.encoding_confidence: Optional[float] = None
        self.parser = "lxml" if HAS_LXML else "html.parser"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def parse_document(self, file_path: str) -> Dict[str, Any]:
        """解析 HTML 文档"""
        logger.info(f"[HTML] 开始解析 HTML 文件: {file_path}")

        with open(file_path, "rb") as f:
            raw_bytes = f.read()

        html_text = self._decode_html(raw_bytes)
        soup = self._parse_html(html_text)

        ordered_elements: List[Dict[str, Any]] = []
        filtered_elements: List[Dict[str, Any]] = []
        text_element_index_map: List[Dict[str, Any]] = []
        tables_payload: List[Dict[str, Any]] = []
        images_payload: List[Dict[str, Any]] = []
        images_binary: List[Dict[str, Any]] = []
        text_content_parts: List[str] = []

        element_index = 0
        doc_order = 0
        heading_structure: List[Dict[str, Any]] = []
        heading_count: Dict[str, int] = {f"h{i}": 0 for i in range(1, 7)}
        semantic_tags_found: Set[str] = set()
        list_count = 0
        code_block_count = 0
        table_count = 0
        base_url = self._extract_base_url(soup)
        has_forms = soup.find("form") is not None
        image_refs: List[Dict[str, Any]] = []
        link_refs = self._extract_links(soup, base_url)
        link_count = len(link_refs)

        current_heading_path: List[str] = []
        semantic_stack: List[str] = []
        root = soup.body or soup

        def next_indices() -> Tuple[int, int]:
            nonlocal element_index, doc_order
            element_index += 1
            current_index = element_index
            current_order = doc_order
            doc_order += 1
            return current_index, current_order

        def add_text_element(
            text: str,
            category: str,
            elem_type: str = "text",
            map_type: Optional[str] = None,
            extra: Optional[Dict[str, Any]] = None,
        ) -> None:
            nonlocal text_content_parts
            normalized = (text or "").strip()
            if not normalized:
                return
            idx, order = next_indices()
            semantic_tag = semantic_stack[-1] if semantic_stack else None
            element = {
                "type": elem_type,
                "text": normalized,
                "element_index": idx,
                "doc_order": order,
                "heading_path": current_heading_path.copy(),
            }
            if semantic_tag:
                element["semantic_tag"] = semantic_tag
            if extra:
                element.update(extra)
            ordered_elements.append(element)
            filtered_elements.append(
                {
                    "category": category,
                    "text": normalized,
                    "element_index": idx,
                }
            )
            text_element_index_map.append(
                {
                    "element_index": idx,
                    "element_type": map_type or elem_type,
                    "doc_order": order,
                    "heading_path": current_heading_path.copy(),
                }
            )
            text_content_parts.append(normalized)

        def handle_heading(tag: Tag, level: int) -> None:
            nonlocal current_heading_path
            heading_text = tag.get_text(" ", strip=True)
            if not heading_text:
                return
            heading_count[f"h{level}"] += 1
            heading_structure.append(
                {
                    "level": level,
                    "title": heading_text,
                    "position": len(heading_structure),
                    "tag_name": tag.name,  # 添加 tag_name 字段
                }
            )
            current_heading_path = self._update_heading_path(current_heading_path, level, heading_text)
            add_text_element(
                heading_text,
                category="heading",
                elem_type="text",
                map_type="heading",
                extra={
                    "heading_level": level,
                    "heading_path": current_heading_path.copy(),
                },
            )

        def handle_table(tag: Tag) -> None:
            nonlocal table_count
            table_data = self._extract_table_data(tag)
            if not table_data.get("cells"):
                return
            table_count += 1
            cells = table_data["cells"]
            table_text = "\n".join("\t".join(row) for row in cells)
            idx, order = next_indices()
            table_entry = {
                "element_index": idx,
                "doc_order": order,
                "table_data": table_data,
                "table_text": table_text,
                "page_number": None,
            }
            tables_payload.append(table_entry)
            ordered_elements.append(
                {
                    "type": "table",
                    "element_index": idx,
                    "doc_order": order,
                    "table_data": table_data,
                    "table_text": table_text,
                }
            )
            filtered_elements.append(
                {
                    "category": "table",
                    "text": table_text,
                    "element_index": idx,
                }
            )

        def handle_list(tag: Tag) -> None:
            nonlocal list_count
            list_text = self._extract_list_text(tag)
            if not list_text.strip():
                return
            list_count += 1
            add_text_element(
                list_text,
                category="list",
                elem_type="text",
                map_type="list",
                extra={"list_type": tag.name},
            )

        def handle_code(tag: Tag) -> None:
            nonlocal code_block_count
            code_text = tag.get_text("\n", strip=False)
            if not code_text.strip():
                return
            code_block_count += 1
            class_attr = tag.get("class")
            if isinstance(class_attr, list):
                language = " ".join(class_attr)
            else:
                language = class_attr or tag.get("data-language") or ""
            add_text_element(
                code_text,
                category="code",
                elem_type="code",
                map_type="code",
                extra={"code_language": language},
            )

        def handle_image(tag: Tag) -> None:
            src = (tag.get("src") or "").strip()
            if not src:
                return
            alt_text = tag.get("alt") or ""
            resolved = self._resolve_url(src, base_url)
            if src.startswith("data:"):
                try:
                    mime_match = re.match(r"data:(.*?);base64,", src, re.IGNORECASE)
                    mime_type = mime_match.group(1) if mime_match else "image/png"
                    b64_data = src.split(",", 1)[1]
                    data = base64.b64decode(b64_data)
                    idx, order = next_indices()
                    image_ext = self._guess_image_extension(mime_type)
                    image_item = {
                        "data": data,
                        "bytes": data,
                        "element_index": idx,
                        "doc_order": order,
                        "page_number": None,
                        "image_ext": image_ext,
                        "width": tag.get("width"),
                        "height": tag.get("height"),
                    }
                    images_payload.append(image_item)
                    images_binary.append(
                        {
                            "binary": data,
                            "element_index": idx,
                            "doc_order": order,
                            "page_number": None,
                        }
                    )
                    ordered_elements.append(
                        {
                            "type": "image",
                            "element_index": idx,
                            "doc_order": order,
                            "image_ext": image_ext,
                        }
                    )
                    filtered_elements.append(
                        {
                            "category": "image",
                            "text": alt_text or image_ext,
                            "element_index": idx,
                        }
                    )
                except Exception as exc:
                    logger.warning(f"[HTML] Base64 图片解析失败: {exc}")
            else:
                image_refs.append(
                    {
                        "src": resolved,
                        "alt": alt_text,
                    }
                )

        def traverse(tag: Tag) -> None:
            for child in tag.children:
                if isinstance(child, NavigableString):
                    continue
                if not isinstance(child, Tag):
                    continue
                name = child.name.lower()
                is_semantic = name in self.SEMANTIC_TAGS
                if is_semantic:
                    semantic_stack.append(name)
                    semantic_tags_found.add(name)

                handled = False
                if name in self.HEADING_TAGS:
                    level = int(name[1]) if len(name) == 2 and name[1].isdigit() else 1
                    handle_heading(child, level)
                    handled = True
                elif name == self.TABLE_TAG:
                    handle_table(child)
                    handled = True
                elif name in self.LIST_TAGS:
                    handle_list(child)
                    handled = True
                elif name in self.CODE_TAGS:
                    handle_code(child)
                    handled = True
                elif name == self.IMAGE_TAG:
                    handle_image(child)
                    handled = True
                elif name in self.BLOCK_TEXT_TAGS:
                    add_text_element(child.get_text(" ", strip=True), category="text")
                    handled = True
                elif self._should_extract_text(child):
                    add_text_element(child.get_text(" ", strip=True), category="text")
                    handled = True

                if not handled:
                    traverse(child)

                if is_semantic:
                    semantic_stack.pop()

        traverse(root)

        metadata = {
            "element_count": len(ordered_elements),
            "line_count": len(html_text.splitlines()),
            "original_encoding": self.detected_encoding,
            "encoding_confidence": self.encoding_confidence,
            "heading_structure": heading_structure,
            "heading_count": heading_count,
            "table_count": table_count,
            "image_count": len(images_payload) + len(image_refs),
            "link_count": link_count,
            "code_block_count": code_block_count,
            "list_count": list_count,
            "semantic_tags": sorted(semantic_tags_found),
            "has_forms": has_forms,
            "html_version": self._detect_html_version(html_text),
            "encoding": self.detected_encoding,
            "base_url": base_url,
            "has_code_blocks": code_block_count > 0,
            "has_tables": table_count > 0,
            "link_refs": link_refs,
            "image_refs": image_refs,
        }

        logger.info(
            f"[HTML] 解析完成: 元素={metadata['element_count']}, "
            f"标题={sum(heading_count.values())}, 表格={table_count}, 图片={metadata['image_count']}, 链接={link_count}"
        )

        return {
            "text_content": "\n".join(text_content_parts).strip(),
            "ordered_elements": ordered_elements,
            "filtered_elements_light": filtered_elements,
            "text_element_index_map": text_element_index_map,
            "tables": tables_payload,
            "images": images_payload,
            "images_binary": images_binary,
            "metadata": metadata,
            "is_converted_pdf": False,
            "converted_pdf_path": None,
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _decode_html(self, raw_bytes: bytes) -> str:
        self._detect_encoding(raw_bytes)
        encoding = self.detected_encoding or "utf-8"
        try:
            text = raw_bytes.decode(encoding, errors="replace")
        except Exception:
            logger.warning(f"[HTML] 使用编码 {encoding} 解码失败，回退 UTF-8")
            text = raw_bytes.decode("utf-8", errors="replace")
            self.detected_encoding = "utf-8"
        normalized = (
            text.replace("\r\n", "\n")
            .replace("\r", "\n")
            .replace("\ufeff", "")
        )
        return normalized

    def _detect_encoding(self, raw_bytes: bytes) -> None:
        snippet = raw_bytes[:2048].decode("ascii", errors="ignore")
        meta_match = re.search(r"charset=['\"]?([a-zA-Z0-9_-]+)", snippet, re.IGNORECASE)
        if meta_match:
            self.detected_encoding = meta_match.group(1).lower()
            self.encoding_confidence = 1.0
            return
        match = from_bytes(raw_bytes).best()
        if match:
            self.detected_encoding = match.encoding
            self.encoding_confidence = getattr(match, "confidence", None)
        else:
            self.detected_encoding = "utf-8"
            self.encoding_confidence = None

    def _parse_html(self, html_text: str) -> BeautifulSoup:
        try:
            return BeautifulSoup(html_text, self.parser)
        except Exception as exc:
            logger.warning(f"[HTML] 使用解析器 {self.parser} 失败，回退 html.parser: {exc}")
            return BeautifulSoup(html_text, "html.parser")

    def _extract_base_url(self, soup: BeautifulSoup) -> Optional[str]:
        base_tag = soup.find("base")
        if base_tag and base_tag.get("href"):
            return base_tag["href"]
        return None

    def _resolve_url(self, url: str, base_url: Optional[str]) -> str:
        if not base_url:
            return url
        try:
            return urljoin(base_url, url)
        except Exception:
            return url

    def _extract_links(self, soup: BeautifulSoup, base_url: Optional[str]) -> List[Dict[str, Any]]:
        links = []
        for link in soup.find_all("a"):
            href = link.get("href")
            if not href:
                continue
            links.append(
                {
                    "text": link.get_text(" ", strip=True),
                    "url": self._resolve_url(href, base_url),
                }
            )
        return links

    def _extract_table_data(self, table: Tag) -> Dict[str, Any]:
        rows: List[List[str]] = []
        headers: List[str] = []
        for row in table.find_all("tr"):
            row_data = []
            cells = row.find_all(["th", "td"])
            if not cells:
                continue
            for cell in cells:
                row_data.append(cell.get_text(" ", strip=True))
            if row.find("th") and not headers:
                headers = row_data
            else:
                rows.append(row_data)
        cells: List[List[str]] = []
        if headers:
            cells.append(headers)
        cells.extend(rows)
        max_columns = max((len(row) for row in cells), default=0)
        for row in cells:
            while len(row) < max_columns:
                row.append("")
        return {
            "cells": cells,
            "rows": len(cells),
            "columns": max_columns,
            "structure": "html_extracted",
            "html": str(table),
        }

    def _extract_list_text(self, tag: Tag) -> str:
        if tag.name == "dl":
            items = []
            terms = tag.find_all("dt")
            for term in terms:
                dd = term.find_next_sibling("dd")
                combined = f"{term.get_text(' ', strip=True)}: {dd.get_text(' ', strip=True) if dd else ''}"
                items.append(combined.strip())
            return "\n".join(items)
        else:
            bullets = []
            for idx, li in enumerate(tag.find_all("li", recursive=False), start=1):
                text = li.get_text(" ", strip=True)
                if not text:
                    continue
                marker = "-" if tag.name == "ul" else f"{idx}."
                bullets.append(f"{marker} {text}")
            return "\n".join(bullets)

    def _should_extract_text(self, tag: Tag) -> bool:
        name = tag.name.lower()
        if name not in self.TEXT_FALLBACK_TAGS:
            return False
        if any(child.name and child.name.lower() in self.BLOCK_LEVEL_TAGS for child in tag.find_all(True, recursive=False)):
            return False
        return bool(tag.get_text(" ", strip=True))

    @staticmethod
    def _update_heading_path(current_path: List[str], level: int, text: str) -> List[str]:
        new_path = current_path[: level - 1]
        new_path.append(text)
        return new_path

    @staticmethod
    def _guess_image_extension(mime_type: Optional[str]) -> str:
        mapping = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/bmp": ".bmp",
            "image/svg+xml": ".svg",
        }
        if mime_type and mime_type.lower() in mapping:
            return mapping[mime_type.lower()]
        return ".png"

    @staticmethod
    def _detect_html_version(html_text: str) -> Optional[str]:
        lowered = html_text.lstrip().lower()
        if lowered.startswith("<!doctype html"):
            return "HTML5"
        if "<!doctype xhtml" in lowered:
            return "XHTML"
        return None
