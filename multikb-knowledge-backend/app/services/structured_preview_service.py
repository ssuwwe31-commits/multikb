"""
Structured Preview Service
结构化预览服务 - 根据设计文档实现
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.document import Document
from app.services.excel_service import ExcelService
from app.core.logging import logger
import json
import xml.etree.ElementTree as ET
from pathlib import Path

class StructuredPreviewService:
    """结构化预览服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.excel_service = ExcelService(db)
    
    def get_preview(self, document_id: int) -> Optional[Dict[str, Any]]:
        """获取结构化预览"""
        document = self.db.query(Document).filter(
            Document.id == document_id,
            Document.is_deleted == False
        ).first()
        
        if not document:
            return None
        
        # 从metadata中获取structured_type
        metadata = document.meta or {}
        structured_type = metadata.get("structured_type")
        
        if not structured_type:
            # 尝试从文件扩展名推断
            filename = document.original_filename or ""
            ext = Path(filename).suffix.lower()
            if ext == ".json":
                structured_type = "json"
            elif ext == ".xml":
                structured_type = "xml"
            elif ext in [".csv", ".xlsx", ".xls"]:
                structured_type = "csv"
            else:
                return None
        
        # 从metadata中读取缓存的预览数据
        preview_samples = metadata.get("preview_samples")
        
        if preview_samples:
            # CSV格式：{"__csv__": [...]}，需要提取数组
            if isinstance(preview_samples, dict) and "__csv__" in preview_samples:
                preview_samples = preview_samples["__csv__"]
            
            # 生成raw_snippet（原文片段，前500字符）
            raw_snippet = None
            if structured_type == "json":
                import json
                raw_snippet = json.dumps(preview_samples, ensure_ascii=False, indent=2)[:500]
            elif structured_type == "xml":
                import json
                raw_snippet = json.dumps(preview_samples, ensure_ascii=False, indent=2)[:500]
            elif structured_type == "csv" and isinstance(preview_samples, list) and len(preview_samples) > 0:
                # CSV的raw_snippet：第一行数据
                first_row = preview_samples[0]
                raw_snippet = ", ".join([f"{k}: {v}" for k, v in first_row.items()])[:500]
            
            # 生成schema（JSON结构分析，仅对JSON）
            schema = None
            if structured_type == "json" and isinstance(preview_samples, dict):
                def analyze_schema(obj, path=""):
                    """递归分析JSON结构"""
                    if isinstance(obj, dict):
                        schema_obj = {"type": "object", "properties": {}}
                        for key, value in obj.items():
                            current_path = f"{path}.{key}" if path else key
                            schema_obj["properties"][key] = analyze_schema(value, current_path)
                        return schema_obj
                    elif isinstance(obj, list):
                        if len(obj) > 0:
                            return {"type": "array", "items": analyze_schema(obj[0], path)}
                        return {"type": "array"}
                    else:
                        return {"type": type(obj).__name__}
                try:
                    schema = analyze_schema(preview_samples)
                except Exception as e:
                    logger.warning(f"生成JSON schema失败: {e}")
            
            # 返回缓存的预览数据
            return {
                "type": structured_type,
                "content": preview_samples,
                "raw_snippet": raw_snippet,
                "schema": schema,
                "total_size": document.file_size or 0,
                "preview_rows": len(preview_samples) if isinstance(preview_samples, list) else None
            }
        
        # 如果没有缓存，尝试实时解析（仅对小于10MB的文件）
        if document.file_size and document.file_size > 10 * 1024 * 1024:
            return {
                "type": structured_type,
                "content": None,
                "raw_snippet": None,
                "schema": None,
                "message": "文件过大，仅支持预览小于10MB的文件",
                "total_size": document.file_size
            }
        
        # 实时解析（这里需要从MinIO读取文件，简化处理）
        # 实际实现中应该从MinIO读取文件内容
        return {
            "type": structured_type,
            "content": None,
            "raw_snippet": None,
            "schema": None,
            "message": "预览数据生成中，请稍后刷新",
            "total_size": document.file_size or 0
        }
    
    def detect_structured_type(self, filename: str, content_preview: Optional[bytes] = None) -> Optional[str]:
        """检测结构化文件类型"""
        ext = Path(filename).suffix.lower()
        
        if ext == ".json":
            return "json"
        elif ext == ".xml":
            return "xml"
        elif ext in [".csv", ".xlsx", ".xls"]:
            return "csv"
        elif ext == ".txt" and content_preview:
            # 尝试解析前1KB内容判断是否为JSON/XML
            try:
                text = content_preview[:1024].decode('utf-8', errors='ignore')
                text = text.strip()
                if text.startswith('{') or text.startswith('['):
                    try:
                        json.loads(text)
                        return "json"
                    except:
                        pass
                if text.startswith('<'):
                    try:
                        ET.fromstring(text)
                        return "xml"
                    except:
                        pass
            except:
                pass
        
        return None
