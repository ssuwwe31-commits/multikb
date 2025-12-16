import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from charset_normalizer import from_bytes

from app.core.logging import logger


class TxtService:
    """TXT 文档解析服务，输出结构与 DOCX/PDF 解析保持一致。"""

    def __init__(self, db: Session):
        self.db = db
        self.detected_encoding: Optional[str] = None
        self.encoding_confidence: Optional[float] = None

    def parse_document(self, file_path: str) -> Dict[str, Any]:
        logger.info(f"[TXT] 开始解析纯文本文件: {file_path}")
        with open(file_path, "rb") as f:
            raw_bytes = f.read()

        self._detect_encoding(raw_bytes)
        normalized_text = self._decode_and_normalize(raw_bytes)
        lines = normalized_text.split("\n")
        line_count = len(lines)

        segments = self._split_paragraphs(lines)
        if not segments and normalized_text:
            segments = [{
                "line_start": 1,
                "line_end": line_count,
                "content": normalized_text.strip()
            }]

        ordered_elements: List[Dict[str, Any]] = []
        filtered_elements: List[Dict[str, Any]] = []
        text_element_index_map: List[Dict[str, Any]] = []

        for idx, segment in enumerate(segments):
            content = segment.get("content", "").strip()
            if not content:
                continue
            section_hint = self._infer_section_hint(content)
            element = {
                "type": "text",
                "text": content,
                "element_index": idx,
                "doc_order": idx,
                "line_start": segment.get("line_start"),
                "line_end": segment.get("line_end"),
                "section_hint": section_hint,
            }
            ordered_elements.append(element)
            filtered_elements.append(
                {
                    "category": section_hint if section_hint != "paragraph" else "text",
                    "text": content,
                    "element_index": idx,
                }
            )
            text_element_index_map.append(
                {
                    "element_index": idx,
                    "element_type": "text",
                    "line_start": segment.get("line_start"),
                    "line_end": segment.get("line_end"),
                    "section_hint": section_hint,
                }
            )

        metadata = {
            "element_count": len(ordered_elements),
            "line_count": line_count,
            "original_encoding": self.detected_encoding,
            "encoding_confidence": self.encoding_confidence,
            "segment_count": len(segments),
        }

        logger.info(
            f"[TXT] 解析完成: 行数={line_count}, 段落={len(segments)}, 元素={len(ordered_elements)}"
        )

        return {
            "text_content": normalized_text,
            "ordered_elements": ordered_elements,
            "filtered_elements_light": filtered_elements,
            "text_element_index_map": text_element_index_map,
            "tables": [],
            "images": [],
            "metadata": metadata,
        }

    def _detect_encoding(self, raw_bytes: bytes) -> None:
        match = from_bytes(raw_bytes).best()
        if match:
            self.detected_encoding = match.encoding
            # 兼容不同版本的 charset-normalizer
            # 新版本使用 coherence 或 percent_coherence，旧版本可能有 confidence
            if hasattr(match, 'confidence'):
                self.encoding_confidence = match.confidence
            elif hasattr(match, 'percent_coherence'):
                # percent_coherence 是 0-100 的值，转换为 0-1 的置信度
                self.encoding_confidence = match.percent_coherence / 100.0
            elif hasattr(match, 'coherence'):
                self.encoding_confidence = match.coherence
            else:
                self.encoding_confidence = None  # 如果都没有，设为 None
        else:
            self.detected_encoding = "utf-8"
            self.encoding_confidence = None

    def _decode_and_normalize(self, raw_bytes: bytes) -> str:
        encoding = self.detected_encoding or "utf-8"
        try:
            text = raw_bytes.decode(encoding, errors="replace")
        except Exception:
            logger.warning(f"[TXT] 使用编码 {encoding} 解码失败，回退 UTF-8")
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

    @staticmethod
    def _split_paragraphs(lines: List[str]) -> List[Dict[str, Any]]:
        segments: List[Dict[str, Any]] = []
        buffer: List[str] = []
        line_start = 1

        for idx, line in enumerate(lines, start=1):
            stripped = line.rstrip()
            if stripped.strip() == "":
                if buffer:
                    segments.append(
                        {
                            "line_start": line_start,
                            "line_end": idx - 1,
                            "content": "\n".join(buffer).strip(),
                        }
                    )
                    buffer = []
                line_start = idx + 1
                continue

            if not buffer:
                line_start = idx
            buffer.append(stripped)

        if buffer:
            segments.append(
                {
                    "line_start": line_start,
                    "line_end": len(lines),
                    "content": "\n".join(buffer).strip(),
                }
            )

        return segments

    @staticmethod
    def _infer_section_hint(text: str) -> str:
        stripped = text.strip()
        if not stripped:
            return "paragraph"
        if stripped.startswith("#"):
            return "heading"
        if re.match(r"^[=\-]{3,}\s*$", stripped):
            return "divider"
        if re.match(r"^\d+(\.\d+)*\s", stripped):
            return "heading"
        if len(stripped) <= 80 and stripped.isupper():
            return "heading"
        if stripped.endswith(":") and len(stripped) <= 60:
            return "heading"
        return "paragraph"
