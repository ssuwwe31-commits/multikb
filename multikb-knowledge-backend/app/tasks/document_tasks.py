"""Document Processing Tasks (DOCX / PDF / TXT, no Unstructured)"""

import os
import tempfile
import time
import hashlib
import datetime
import shutil
import io
from typing import Any, Dict, List, Optional
from celery import current_task
from app.tasks.celery_app import celery_app
from app.services.docx_service import DocxService
from app.services.pdf_service import PdfService
from app.services.txt_service import TxtService
from app.services.markdown_service import MarkdownService
from app.services.excel_service import ExcelService, ExcelParseOptions
from app.services.pptx_service import PptxService
from app.services.html_service import HtmlService
from app.services.vector_service import VectorService
from app.services.cache_service import CacheService
from app.services.opensearch_service import OpenSearchService
from app.services.minio_storage_service import MinioStorageService
from app.services.image_service import ImageService
from app.services.office_converter import convert_office_to_pdf, convert_office_to_html, compress_pdf
from app.config.settings import settings
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.models.image import DocumentImage
from sqlalchemy.orm import Session
from app.config.database import SessionLocal
from app.core.logging import logger
from app.core.constants import DOC_STATUS_PARSING, DOC_STATUS_CHUNKING, DOC_STATUS_VECTORIZING, DOC_STATUS_INDEXING, DOC_STATUS_COMPLETED, DOC_STATUS_FAILED

# 确保在Celery进程中注册所有模型，解决字符串关系解析问题
import app.models  # noqa: F401

@celery_app.task(bind=True, ignore_result=True)
def process_document_task(self, document_id: int):
    """处理文档任务（DOCX / PDF，完全不使用 Unstructured）"""
    db = SessionLocal()
    document = None
    task_id = self.request.id if self else "unknown"
    
    try:
        logger.info(f"[任务ID: {task_id}] ========== 开始处理文档 {document_id} ==========")
        
        # 更新任务状态
        current_task.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "开始处理文档"}
        )
        
        # 获取文档
        logger.debug(f"[任务ID: {task_id}] 步骤1/7: 从数据库获取文档信息 (document_id={document_id})")
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"[任务ID: {task_id}] 文档 {document_id} 不存在于数据库中")
            raise Exception(f"文档 {document_id} 不存在")
        
        logger.info(f"[任务ID: {task_id}] 文档信息: ID={document.id}, 文件名={document.original_filename}, "
                   f"文件类型={document.file_type}, 文件路径={document.file_path}, "
                   f"知识库ID={document.knowledge_base_id}, 文件大小={document.file_size or '未知'} bytes")
        
        file_suffix = (document.original_filename or '').split('.')[-1].lower()
        file_type = (document.file_type or '').lower()
        is_docx = file_suffix == 'docx' or file_type == 'docx'
        is_pdf = file_suffix == 'pdf' or file_type == 'pdf'
        is_txt = file_suffix in ('txt', 'log') or file_type == 'txt'
        is_md = file_suffix in ('md', 'markdown', 'mkd') or file_type in ('md', 'markdown')
        is_excel = file_suffix in ('xlsx', 'xls', 'xlsb', 'csv') or file_type in ('excel', 'xlsx', 'xls', 'csv')
        is_pptx = file_suffix == 'pptx' or file_type == 'pptx'
        is_html = file_suffix in ('html', 'htm') or file_type in ('html', 'htm')
        if not (is_docx or is_pdf or is_txt or is_md or is_excel or is_pptx or is_html):
            raise Exception("当前处理流程仅支持 DOCX / PDF / TXT / MD / Excel / PPTX / HTML 文档")
        
        # 更新文档状态为解析中
        logger.debug(f"[任务ID: {task_id}] 步骤2/7: 更新文档状态为解析中")
        document.status = DOC_STATUS_PARSING
        document.processing_progress = 10.0
        db.commit()
        
        current_task.update_state(
            state="PROGRESS",
            meta={"current": 10, "total": 100, "status": "下载文件到临时目录"}
        )
        
        # 1. 下载文件到临时目录
        logger.info(f"[任务ID: {task_id}] 步骤3/7: 开始从MinIO下载文件 (file_path={document.file_path})")
        download_start = time.time()
        
        try:
            minio_service = MinioStorageService()
            file_content = minio_service.download_file(document.file_path)
            download_time = time.time() - download_start
            logger.info(f"[任务ID: {task_id}] MinIO文件下载成功: 大小={len(file_content)} bytes, 耗时={download_time:.2f}秒")
        except Exception as e:
            logger.error(f"[任务ID: {task_id}] MinIO文件下载失败: {e}", exc_info=True)
            raise
        
        # 创建临时文件
        logger.debug(f"[任务ID: {task_id}] 步骤3.1/7: 创建临时文件目录")
        temp_dir = tempfile.mkdtemp()
        file_extension = os.path.splitext(document.original_filename)[1].lstrip('.')
        temp_file_path = os.path.join(temp_dir, f"{document_id}.{file_extension}")
        
        try:
            with open(temp_file_path, 'wb') as f:
                f.write(file_content)
            logger.info(f"[任务ID: {task_id}] 临时文件创建成功: {temp_file_path}, 大小={os.path.getsize(temp_file_path)} bytes")
        except Exception as e:
            logger.error(f"[任务ID: {task_id}] 临时文件创建失败: {e}", exc_info=True)
            raise
        
        current_task.update_state(
            state="PROGRESS",
            meta={"current": 15, "total": 100, "status": "开始解析文档"}
        )
        
        # 2. 解析文档（DOCX/PDF 本地解析）
        parse_start = time.time()
        parse_result = None
        parser = None
        parsed_file_path = temp_file_path
        cleanup_paths = []
        if is_docx:
            sanitized_docx_path = DocxService.sanitize_docx(temp_file_path)
            if sanitized_docx_path and os.path.exists(sanitized_docx_path):
                parsed_file_path = sanitized_docx_path
                if sanitized_docx_path != temp_file_path:
                    logger.info(f"[任务ID: {task_id}] 已生成 DOCX 降噪副本供解析使用: {sanitized_docx_path}")
                try:
                    artifact_object = minio_service.upload_debug_artifact(
                        document.id,
                        "sanitized.docx",
                        sanitized_docx_path,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                    if artifact_object:
                        cleanup_paths.append({'type': 'minio', 'object_name': artifact_object})
                except Exception as upload_exc:
                        logger.warning(f"[任务ID: {task_id}] 上传降噪 DOCX 失败: {upload_exc}")
                if sanitized_docx_path != temp_file_path:
                    cleanup_paths.append({'type': 'local', 'path': sanitized_docx_path})
            else:
                parsed_file_path = temp_file_path
                logger.debug(f"[任务ID: {task_id}] DOCX 降噪未生成新文件，继续使用原始文件解析")

            logger.info(f"[任务ID: {task_id}] 步骤4/7: 使用 DocxService 解析文档 (DOCX 本地解析)")
            parser = DocxService(db)
            parse_result = parser.parse_document(parsed_file_path)
        elif is_pdf:
            logger.info(f"[任务ID: {task_id}] 步骤4/7: 使用 PdfService 解析文档 (PDF 本地解析)")
            parser = PdfService(db)
            parse_result = parser.parse_document(parsed_file_path)
        elif is_excel:
            logger.info(f"[任务ID: {task_id}] 步骤4/7: 使用 ExcelService 解析 Excel 文档")
            parser = ExcelService(db)
            # Excel 需要解析选项，注意 Document.meta 才是元数据字段
            excel_meta = document.meta or {}
            if isinstance(excel_meta, str):
                try:
                    import json as _json
                    excel_meta = _json.loads(excel_meta)
                except Exception:
                    excel_meta = {}
            # 从配置读取 chunk_max，确保与 TEXT_EMBED_MAX_CHARS 一致
            chunk_max = int(getattr(settings, 'TEXT_EMBED_MAX_CHARS', 1024))
            parse_options = ExcelParseOptions(
                sheet_whitelist=excel_meta.get('sheet_whitelist'),
                row_limit_per_sheet=excel_meta.get('row_limit_per_sheet'),
                window_rows=excel_meta.get('window_rows', 50),
                overlap_rows=excel_meta.get('overlap_rows', 10),
                chunk_max=chunk_max,  # 使用配置值，与文本分块保持一致
            )
            parse_result = parser.parse_document(parsed_file_path, parse_options)
        elif is_md:
            logger.info(f"[任务ID: {task_id}] 步骤4/7: 使用 MarkdownService 解析 Markdown 文档")
            parser = MarkdownService(db)
            parse_result = parser.parse_document(parsed_file_path)
        elif is_pptx:
            logger.info(f"[任务ID: {task_id}] 步骤4/7: 使用 PptxService 解析 PowerPoint 文档")
            parser = PptxService(db)
            parse_result = parser.parse_document(parsed_file_path)
        elif is_html:
            logger.info(f"[任务ID: {task_id}] 步骤4/7: 使用 HtmlService 解析 HTML 文档")
            parser = HtmlService(db)
            parse_result = parser.parse_document(parsed_file_path)
        else:
            logger.info(f"[任务ID: {task_id}] 步骤4/7: 使用 TxtService 解析纯文本文档")
            parser = TxtService(db)
            parse_result = parser.parse_document(parsed_file_path)
        parse_time = time.time() - parse_start
        
        # 检查解析结果
        if parse_result is None:
            error_msg = f"文档解析失败: parse_document 返回 None (文件类型: {file_suffix or file_type})"
            logger.error(f"[任务ID: {task_id}] {error_msg}")
            raise Exception(error_msg)
        
        text_content = parse_result.get('text_content', '')
        elements_count = int(parse_result.get('metadata', {}).get('element_count', 0) or 0)
        logger.info(f"[任务ID: {task_id}] 解析完成: 耗时={parse_time:.2f}秒, 提取元素数={elements_count}, 文本长度={len(text_content)} 字符")

        parse_metadata = parse_result.get('metadata', {}) or {}
        doc_meta = document.meta or {}
        doc_meta = doc_meta.copy() if isinstance(doc_meta, dict) else {}
        doc_meta.update(
            {
                "text_length": len(text_content),
                "element_count": elements_count,
            }
        )
        for key in ("original_encoding", "line_count", "encoding_confidence", "segment_count", 
                    "markdown_version", "has_code_blocks", "has_tables", "code_languages", 
                    "table_count", "heading_structure", "heading_count", "link_count",
                    "code_block_count", "list_count", "semantic_tags", "has_forms",
                    "html_version", "encoding", "base_url", "link_refs", "image_refs",
                    "slide_count", "layout_types", "has_notes", "image_count",
                    "presentation_size", "slides"):
            if parse_metadata.get(key) is not None:
                doc_meta[key] = parse_metadata[key]
        
        # 生成JSON/XML预览数据（如果文件类型是JSON或XML）
        structured_type = doc_meta.get("structured_type")
        if structured_type in ("json", "xml") and not doc_meta.get("preview_samples"):
            try:
                from app.services.structured_preview_service import StructuredPreviewService
                preview_service = StructuredPreviewService(db)
                
                # 读取文件内容（限制1MB）
                max_preview_size = 1024 * 1024  # 1MB
                file_size = os.path.getsize(temp_file_path) if os.path.exists(temp_file_path) else 0
                
                if file_size > 0 and file_size <= max_preview_size:
                    with open(temp_file_path, 'rb') as f:
                        file_content = f.read()
                    
                    if structured_type == "json":
                        try:
                            import json
                            # 解析JSON
                            json_data = json.loads(file_content.decode('utf-8', errors='ignore'))
                            doc_meta["preview_samples"] = json_data
                            logger.info(f"[任务ID: {task_id}] JSON预览数据生成成功")
                        except Exception as e:
                            logger.warning(f"[任务ID: {task_id}] JSON预览数据生成失败: {e}")
                    elif structured_type == "xml":
                        try:
                            import xml.etree.ElementTree as ET
                            # 解析XML
                            xml_tree = ET.parse(io.BytesIO(file_content))
                            xml_root = xml_tree.getroot()
                            # 转换为字典（简化处理）
                            def xml_to_dict(element):
                                result = {}
                                if element.text and element.text.strip():
                                    result['_text'] = element.text.strip()
                                if element.attrib:
                                    result['_attributes'] = element.attrib
                                for child in element:
                                    child_dict = xml_to_dict(child)
                                    if child.tag in result:
                                        if not isinstance(result[child.tag], list):
                                            result[child.tag] = [result[child.tag]]
                                        result[child.tag].append(child_dict)
                                    else:
                                        result[child.tag] = child_dict
                                return result
                            xml_dict = xml_to_dict(xml_root)
                            doc_meta["preview_samples"] = xml_dict
                            logger.info(f"[任务ID: {task_id}] XML预览数据生成成功")
                        except Exception as e:
                            logger.warning(f"[任务ID: {task_id}] XML预览数据生成失败: {e}")
                else:
                    logger.info(f"[任务ID: {task_id}] 文件过大（{file_size} bytes > {max_preview_size} bytes），跳过预览数据生成")
            except Exception as e:
                logger.warning(f"[任务ID: {task_id}] 生成预览数据时出错（不影响主流程）: {e}", exc_info=True)
        
        document.meta = doc_meta
        db.commit()
        
        # 3.5. 生成预览（如果启用且是Office文档）
        is_office = file_suffix in {'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'} or file_type in {'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}
        is_excel_for_preview = file_suffix in {'xls', 'xlsx'} or file_type in {'xls', 'xlsx'}
        logger.debug(f"[任务ID: {task_id}] 预览生成检查: ENABLE_PREVIEW_GENERATION={settings.ENABLE_PREVIEW_GENERATION}, is_office={is_office}, is_excel={is_excel_for_preview}, temp_file_exists={os.path.exists(temp_file_path) if temp_file_path else False}")
        if settings.ENABLE_PREVIEW_GENERATION and is_office and os.path.exists(temp_file_path):
            try:
                logger.info(f"[任务ID: {task_id}] 步骤3.5/7: 开始生成Office文档预览 (文件类型: {file_suffix or file_type})")
                current_task.update_state(
                    state="PROGRESS",
                    meta={"current": 25, "total": 100, "status": "生成文档预览"}
                )
                
                # 构建预览对象路径
                created: datetime.datetime = getattr(document, 'created_at', None) or datetime.datetime.utcnow()
                year = created.strftime('%Y')
                month = created.strftime('%m')
                preview_base = f"documents/{year}/{month}/{document.id}/preview"
                preview_object = f"{preview_base}/preview.pdf"
                preview_object_screen = f"{preview_base}/preview_screen.pdf"
                preview_object_html = f"{preview_base}/preview.html"
                
                # 生成PDF预览
                pdf_path = None
                pdf_temp_dir = None
                try:
                    logger.info(f"[任务ID: {task_id}] 开始转换PDF预览: {temp_file_path}")
                    pdf_path = convert_office_to_pdf(temp_file_path)
                    if pdf_path:
                        pdf_temp_dir = os.path.dirname(pdf_path)
                        logger.info(f"[任务ID: {task_id}] PDF转换成功: {pdf_path}, 大小={os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0} bytes")
                    else:
                        logger.warning(f"[任务ID: {task_id}] PDF转换失败: convert_office_to_pdf 返回 None")
                    if pdf_path and os.path.exists(pdf_path):
                        try:
                            # 检查PDF大小，决定是否压缩
                            size_bytes = os.path.getsize(pdf_path)
                            threshold_mb = 10  # 10MB 阈值
                            use_screen = size_bytes > threshold_mb * 1024 * 1024
                            
                            if use_screen:
                                # 生成压缩版本
                                logger.info(f"[任务ID: {task_id}] PDF文件较大 ({size_bytes / 1024 / 1024:.2f}MB > {threshold_mb}MB)，开始压缩")
                                screen_pdf = os.path.join(temp_dir, 'preview_screen.pdf')
                                if compress_pdf(pdf_path, screen_pdf, quality='screen') and os.path.exists(screen_pdf):
                                    screen_size = os.path.getsize(screen_pdf)
                                    logger.info(f"[任务ID: {task_id}] PDF压缩成功: 原始={size_bytes / 1024 / 1024:.2f}MB, 压缩后={screen_size / 1024 / 1024:.2f}MB")
                                    with open(screen_pdf, 'rb') as pf:
                                        minio_service.client.put_object(
                                            minio_service.bucket_name,
                                            preview_object_screen,
                                            data=pf,
                                            length=screen_size,
                                            content_type='application/pdf'
                                        )
                                    document.converted_pdf_url = preview_object_screen
                                    logger.info(f"[任务ID: {task_id}] 已上传压缩PDF预览到MinIO: {preview_object_screen}")
                                else:
                                    # 压缩失败，使用原始PDF
                                    logger.warning(f"[任务ID: {task_id}] PDF压缩失败，使用原始PDF上传")
                                    with open(pdf_path, 'rb') as pf:
                                        minio_service.client.put_object(
                                            minio_service.bucket_name,
                                            preview_object,
                                            data=pf,
                                            length=os.path.getsize(pdf_path),
                                            content_type='application/pdf'
                                        )
                                    document.converted_pdf_url = preview_object
                                    logger.info(f"[任务ID: {task_id}] 已上传原始PDF预览到MinIO: {preview_object}")
                            else:
                                # 直接上传原始PDF
                                logger.info(f"[任务ID: {task_id}] PDF文件较小 ({size_bytes / 1024 / 1024:.2f}MB <= {threshold_mb}MB)，直接上传")
                                with open(pdf_path, 'rb') as pf:
                                    minio_service.client.put_object(
                                        minio_service.bucket_name,
                                        preview_object,
                                        data=pf,
                                        length=os.path.getsize(pdf_path),
                                        content_type='application/pdf'
                                    )
                                document.converted_pdf_url = preview_object
                                logger.info(f"[任务ID: {task_id}] 已上传PDF预览到MinIO: {preview_object}")
                            
                            db.commit()
                            logger.info(f"[任务ID: {task_id}] PDF预览路径已更新到数据库: {document.converted_pdf_url}")
                        except Exception as pdf_err:
                            logger.warning(f"[任务ID: {task_id}] 上传PDF预览失败: {pdf_err}", exc_info=True)
                            db.rollback()
                finally:
                    # 清理PDF转换产生的临时文件
                    if pdf_temp_dir and os.path.isdir(pdf_temp_dir):
                        try:
                            shutil.rmtree(pdf_temp_dir)
                            logger.debug(f"[任务ID: {task_id}] 已清理PDF转换临时目录: {pdf_temp_dir}")
                        except Exception as cleanup_err:
                            logger.warning(f"[任务ID: {task_id}] 清理PDF转换临时目录失败: {cleanup_err}")
                
                # 生成HTML预览（仅Excel需要，Word/PPT使用PDF即可）
                html_path = None
                html_temp_dir = None
                if is_excel_for_preview:
                    try:
                        logger.info(f"[任务ID: {task_id}] 开始转换HTML预览（Excel需要）: {temp_file_path}")
                        html_path = convert_office_to_html(temp_file_path)
                        if html_path:
                            html_temp_dir = os.path.dirname(html_path)
                            logger.info(f"[任务ID: {task_id}] HTML转换成功: {html_path}, 大小={os.path.getsize(html_path) if os.path.exists(html_path) else 0} bytes")
                        else:
                            logger.warning(f"[任务ID: {task_id}] HTML转换失败: convert_office_to_html 返回 None")
                        if html_path and os.path.exists(html_path):
                            try:
                                html_size = os.path.getsize(html_path)
                                logger.info(f"[任务ID: {task_id}] 开始上传HTML预览到MinIO: {preview_object_html}, 大小={html_size} bytes")
                                with open(html_path, 'rb') as hf:
                                    minio_service.client.put_object(
                                        minio_service.bucket_name,
                                        preview_object_html,
                                        data=hf,
                                        length=html_size,
                                        content_type='text/html'
                                    )
                                logger.info(f"[任务ID: {task_id}] HTML预览已上传到MinIO: {preview_object_html}")
                                # 更新文档元数据
                                updated_meta = document.meta or {}
                                updated_meta = updated_meta.copy() if isinstance(updated_meta, dict) else {}
                                updated_meta["converted_html_url"] = preview_object_html
                                document.meta = updated_meta
                                db.commit()
                                logger.info(f"[任务ID: {task_id}] HTML预览路径已更新到数据库: {preview_object_html}")
                            except Exception as html_err:
                                logger.warning(f"[任务ID: {task_id}] 上传HTML预览失败: {html_err}", exc_info=True)
                                db.rollback()
                    finally:
                        # 清理HTML转换产生的临时文件
                        if html_temp_dir and os.path.isdir(html_temp_dir):
                            try:
                                shutil.rmtree(html_temp_dir)
                                logger.debug(f"[任务ID: {task_id}] 已清理HTML转换临时目录: {html_temp_dir}")
                            except Exception as cleanup_err:
                                logger.warning(f"[任务ID: {task_id}] 清理HTML转换临时目录失败: {cleanup_err}")
                else:
                    logger.debug(f"[任务ID: {task_id}] 跳过HTML预览生成（仅Excel需要，当前文件类型: {file_suffix or file_type}）")
                
                logger.info(f"[任务ID: {task_id}] 预览生成完成")
            except Exception as preview_err:
                logger.warning(f"[任务ID: {task_id}] 生成预览时发生异常: {preview_err}", exc_info=True)
                # 预览生成失败不影响主流程，继续执行
        
        # 3. 清理临时文件
        logger.debug(f"[任务ID: {task_id}] 步骤4.1/7: 清理临时文件")
        try:
            if os.path.exists(temp_file_path):
                last_exc = None
                # Excel文件需要更多重试次数，因为LibreOffice可能还在占用
                max_attempts = 5 if is_excel else 3
                for attempt in range(max_attempts):
                    try:
                        os.remove(temp_file_path)
                        last_exc = None
                        logger.debug(f"[任务ID: {task_id}] 临时文件删除成功: {temp_file_path}")
                        break
                    except (PermissionError, OSError) as pe:
                        last_exc = pe
                        # Excel文件等待时间更长
                        wait_time = 0.5 * (attempt + 1) if is_excel else 0.1 * (attempt + 1)
                        logger.debug(f"[任务ID: {task_id}] 临时文件删除失败（尝试 {attempt + 1}/{max_attempts}），等待 {wait_time:.1f}秒后重试: {pe}")
                        time.sleep(wait_time)
                if last_exc:
                    logger.warning(f"[任务ID: {task_id}] 临时文件删除最终失败（已重试{max_attempts}次）: {last_exc}, 路径={temp_file_path}")
            # 清理临时目录
            if os.path.isdir(temp_dir):
                try:
                    os.rmdir(temp_dir)
                    logger.debug(f"[任务ID: {task_id}] 临时目录删除成功: {temp_dir}")
                except OSError:
                    try:
                        shutil.rmtree(temp_dir)
                        logger.debug(f"[任务ID: {task_id}] 临时目录强制删除成功: {temp_dir}")
                    except Exception as rmtree_err:
                        logger.warning(f"[任务ID: {task_id}] 临时目录删除失败: {rmtree_err}, 路径={temp_dir}")
        except Exception as e:
            logger.warning(f"[任务ID: {task_id}] 清理临时文件失败: {e}, 路径={temp_file_path}")

        for artifact in cleanup_paths:
            try:
                if isinstance(artifact, dict):
                    if artifact.get('type') == 'local':
                        extra_path = artifact.get('path')
                        if extra_path and os.path.isfile(extra_path):
                            os.remove(extra_path)
                        extra_dir = os.path.dirname(extra_path) if extra_path else None
                        if extra_dir and os.path.isdir(extra_dir):
                            try:
                                os.rmdir(extra_dir)
                            except OSError:
                                try:
                                    shutil.rmtree(extra_dir)
                                except Exception:
                                    pass
                    elif artifact.get('type') == 'minio':
                        try:
                            bucket = minio_service.bucket_name
                            object_name = artifact.get('object_name') or artifact.get('artifact')
                            if object_name:
                                minio_service.client.remove_object(bucket, object_name)
                                logger.debug(f"[任务ID: {task_id}] 已删除 MinIO 调试产物: {object_name}")
                        except Exception as minio_err:
                            logger.debug(f"[任务ID: {task_id}] 删除 MinIO 调试产物失败: {minio_err}")
                else:
                    extra_path = artifact
                    if extra_path and os.path.isfile(extra_path):
                        os.remove(extra_path)
                    extra_dir = os.path.dirname(extra_path) if extra_path else None
                    if extra_dir and os.path.isdir(extra_dir):
                        try:
                            os.rmdir(extra_dir)
                        except OSError:
                            try:
                                shutil.rmtree(extra_dir)
                            except Exception:
                                pass
            except Exception as e:
                logger.warning(f"[任务ID: {task_id}] 清理临时产物失败: {e}, 路径={artifact}")
        
        current_task.update_state(
            state="PROGRESS",
            meta={"current": 30, "total": 100, "status": "文档解析完成"}
        )
        
        # 更新文档状态为分块中
        logger.debug(f"[任务ID: {task_id}] 步骤5/7: 开始文档分块处理")
        document.status = DOC_STATUS_CHUNKING
        document.processing_progress = 40.0
        db.commit()
        
        # 3. 分块（结构分块）
        chunk_start = time.time()
        text_element_index_map = parse_result.get("text_element_index_map", [])
        filtered_elements_light = parse_result.get("filtered_elements_light", [])

        # 分块大小配置（docx/pdf 统一使用）
        try:
            from app.config.settings import settings as _settings
            chunk_max = min(
                int(getattr(_settings, 'CHUNK_SIZE', 1000)),
                int(getattr(_settings, 'TEXT_EMBED_MAX_CHARS', 1024))
            )
        except Exception:
            chunk_max = 1024

        if chunk_max <= 0:
            chunk_max = 1024

        docx_like_processing = is_docx or is_txt or is_md or is_excel or is_pptx or is_html
        if docx_like_processing:

            ordered_elements = parse_result.get('ordered_elements', []) or []
            merged_items: List[Dict[str, Any]] = []
            text_chunks_entries: List[Dict[str, Any]] = []
            tables_meta = parse_result.get('tables', []) or []
            chunks = []
            chunks_metadata = []
            chunk_counter = 0
            text_buffer: List[Dict[str, Any]] = []
            image_chunks: List[Dict[str, Any]] = []

            def flush_text_buffer():
                nonlocal text_buffer, chunk_counter
                if not text_buffer:
                    return
                current_parts: List[str] = []
                current_len = 0
                chunk_start_idx: Optional[int] = None
                chunk_start_order: Optional[int] = None
                chunk_end_idx: Optional[int] = None
                chunk_end_order: Optional[int] = None
                chunk_line_start: Optional[int] = None
                chunk_line_end: Optional[int] = None
                chunk_section_hint: Optional[str] = None
                # HTML 特有字段
                chunk_heading_level: Optional[int] = None
                chunk_heading_path: Optional[List[str]] = None
                chunk_semantic_tag: Optional[str] = None
                chunk_list_type: Optional[str] = None
                chunk_code_language: Optional[str] = None

                def determine_html_chunk_type(entries: List[Dict[str, Any]]) -> Optional[str]:
                    """确定 HTML 分块类型"""
                    if not is_html:
                        return None
                    # 检查第一个元素确定分块类型
                    if entries:
                        first_entry = entries[0]
                        if first_entry.get('code_language'):
                            return 'code_block'
                        if first_entry.get('list_type'):
                            return 'list'
                        if first_entry.get('semantic_tag'):
                            return 'semantic_block'
                        if first_entry.get('heading_level'):
                            return 'heading_section'
                    return 'paragraph'

                def emit_chunk():
                    nonlocal current_parts, current_len, chunk_start_idx, chunk_end_idx, chunk_start_order, chunk_end_order, chunk_counter, chunk_line_start, chunk_line_end, chunk_section_hint
                    nonlocal chunk_heading_level, chunk_heading_path, chunk_semantic_tag, chunk_list_type, chunk_code_language
                    content = ''.join(current_parts).strip()
                    if not content:
                        current_parts = []
                        current_len = 0
                        chunk_start_idx = None
                        chunk_start_order = None
                        chunk_end_idx = None
                        chunk_end_order = None
                        chunk_line_start = None
                        chunk_line_end = None
                        chunk_section_hint = None
                        chunk_heading_level = None
                        chunk_heading_path = None
                        chunk_semantic_tag = None
                        chunk_list_type = None
                        chunk_code_language = None
                        return
                    base_order = chunk_start_order or 0
                    pos_value = base_order * 1000 + chunk_counter
                    
                    # 确定 HTML 分块类型
                    html_chunk_type = None
                    if is_html:
                        html_chunk_type = determine_html_chunk_type(text_buffer)
                    
                    chunk_meta = {
                        'element_index_start': chunk_start_idx,
                        'element_index_end': chunk_end_idx,
                        'doc_order_start': chunk_start_order,
                        'doc_order_end': chunk_end_order,
                        'page_number': None,
                        'coordinates': None,
                        'chunk_index': chunk_counter,
                        'line_start': chunk_line_start,
                        'line_end': chunk_line_end,
                        'section_hint': chunk_section_hint,
                    }
                    
                    # 添加 HTML 特有字段
                    if is_html:
                        if html_chunk_type:
                            chunk_meta['chunk_type'] = html_chunk_type
                        if chunk_heading_level is not None:
                            chunk_meta['heading_level'] = chunk_heading_level
                        if chunk_heading_path:
                            chunk_meta['heading_path'] = chunk_heading_path
                        if chunk_semantic_tag:
                            chunk_meta['semantic_tag'] = chunk_semantic_tag
                        if chunk_list_type:
                            chunk_meta['list_type'] = chunk_list_type
                        if chunk_code_language:
                            chunk_meta['code_language'] = chunk_code_language
                    chunk_item = {
                        'type': 'text',
                        'content': content,
                        'pos': pos_value,
                        'meta': chunk_meta,
                    }
                    text_chunks_entries.append(chunk_item)
                    merged_items.append(chunk_item)
                    chunks.append(content)
                    chunks_metadata.append(chunk_meta)
                    chunk_counter += 1
                    current_parts = []
                    current_len = 0
                    chunk_start_idx = None
                    chunk_start_order = None
                    chunk_end_idx = None
                    chunk_end_order = None
                    chunk_line_start = None
                    chunk_line_end = None
                    chunk_section_hint = None
                    chunk_heading_level = None
                    chunk_heading_path = None
                    chunk_semantic_tag = None
                    chunk_list_type = None
                    chunk_code_language = None

                for idx, entry in enumerate(text_buffer):
                    text_value = entry.get('text') or ''
                    if idx < len(text_buffer) - 1:
                        text_value = text_value + '\n'
                    doc_order = entry.get('doc_order')
                    element_index_entry = entry.get('element_index')
                    pointer = 0
                    length = len(text_value)
                    while pointer < length:
                        if current_len == 0:
                            chunk_start_idx = element_index_entry
                            chunk_start_order = doc_order
                            chunk_line_start = entry.get('line_start', chunk_line_start)
                            if chunk_section_hint is None:
                                chunk_section_hint = entry.get('section_hint')
                            # HTML 特有字段：从第一个元素获取
                            if is_html:
                                if chunk_heading_level is None:
                                    chunk_heading_level = entry.get('heading_level')
                                if chunk_heading_path is None:
                                    chunk_heading_path = entry.get('heading_path')
                                if chunk_semantic_tag is None:
                                    chunk_semantic_tag = entry.get('semantic_tag')
                                if chunk_list_type is None:
                                    chunk_list_type = entry.get('list_type')
                                if chunk_code_language is None:
                                    chunk_code_language = entry.get('code_language')
                        remain = chunk_max - current_len
                        take = min(remain, length - pointer)
                        piece = text_value[pointer:pointer + take]
                        current_parts.append(piece)
                        current_len += take
                        chunk_end_idx = element_index_entry
                        chunk_end_order = doc_order
                        line_end_candidate = entry.get('line_end')
                        if line_end_candidate is not None:
                            chunk_line_end = line_end_candidate
                        if chunk_section_hint is None:
                            chunk_section_hint = entry.get('section_hint')
                        # HTML 特有字段：更新到最后处理的元素
                        if is_html:
                            heading_level_candidate = entry.get('heading_level')
                            if heading_level_candidate is not None:
                                chunk_heading_level = heading_level_candidate
                            heading_path_candidate = entry.get('heading_path')
                            if heading_path_candidate:
                                chunk_heading_path = heading_path_candidate
                            semantic_tag_candidate = entry.get('semantic_tag')
                            if semantic_tag_candidate:
                                chunk_semantic_tag = semantic_tag_candidate
                            list_type_candidate = entry.get('list_type')
                            if list_type_candidate:
                                chunk_list_type = list_type_candidate
                            code_language_candidate = entry.get('code_language')
                            if code_language_candidate:
                                chunk_code_language = code_language_candidate
                        pointer += take
                        if current_len >= chunk_max:
                            emit_chunk()

                if current_parts:
                    emit_chunk()

                text_buffer = []

            for element in ordered_elements:
                elem_type = element.get('type')
                if elem_type == 'text' or elem_type == 'code':
                    # 代码块也当作文本处理，保留 code_language 元数据
                    text_value = (element.get('text') or '').strip()
                    if not text_value:
                        continue
                    buffer_entry = {
                        'text': text_value,
                        'element_index': element.get('element_index'),
                        'doc_order': element.get('doc_order'),
                        'line_start': element.get('line_start'),
                        'line_end': element.get('line_end'),
                        'section_hint': element.get('section_hint'),
                        'code_language': element.get('code_language') if elem_type == 'code' else None,
                    }
                    # HTML 特有字段：传递到 text_buffer
                    if is_html:
                        buffer_entry['heading_level'] = element.get('heading_level')
                        buffer_entry['heading_path'] = element.get('heading_path')
                        buffer_entry['semantic_tag'] = element.get('semantic_tag')
                        buffer_entry['list_type'] = element.get('list_type')
                        # code_language 已经在上面处理，但如果是 code 类型，确保传递
                        if elem_type == 'code':
                            buffer_entry['code_language'] = element.get('code_language')
                    text_buffer.append(buffer_entry)
                elif elem_type == 'table':
                    flush_text_buffer()
                    continue
                elif elem_type == 'image':
                    flush_text_buffer()
                    doc_order = element.get('doc_order') or 0
                    elem_idx = element.get('element_index')
                    # ✅ 验证：图片元素必须有 element_index
                    if elem_idx is None:
                        logger.warning(
                            f"[任务ID: {task_id}] ⚠️ 图片元素缺少 element_index: doc_order={doc_order}, "
                            f"element_keys={list(element.keys())}"
                        )
                    image_chunk = {
                        'type': 'image',
                        'content': '',
                        'pos': doc_order * 1000,
                        'meta': {
                            'element_index': elem_idx,
                            'doc_order': doc_order,
                            'rId': element.get('rId'),
                            'image_id': None,
                            'image_path': None,
                        }
                    }
                    merged_items.append(image_chunk)
                    image_chunks.append(image_chunk)
                    if elem_idx is not None:
                        logger.debug(
                            f"[任务ID: {task_id}] 创建图片分块: element_index={elem_idx}, doc_order={doc_order}, pos={doc_order * 1000}"
                        )
            flush_text_buffer()
            merged_items.sort(key=lambda item: item.get('pos', 0))
            # 去重：确保每个 element_index 仅生成一个 image/table 块
            deduped_items: List[Dict[str, Any]] = []
            used_table_indices = set()
            used_image_indices = set()
            for item in merged_items:
                item_type = item.get('type')
                meta = item.get('meta') or {}
                elem_idx = meta.get('element_index')
                if item_type == 'table' and elem_idx is not None:
                    key = (elem_idx, item.get('pos'))
                    if key in used_table_indices:
                        continue
                    used_table_indices.add(key)
                elif item_type == 'image' and elem_idx is not None:
                    if elem_idx in used_image_indices:
                        continue
                    used_image_indices.add(elem_idx)
                deduped_items.append(item)
            merged_items = deduped_items

            chunk_time = time.time() - chunk_start
            if is_docx:
                docx_like_name = "DOCX"
            elif is_excel:
                docx_like_name = "EXCEL"
            elif is_md:
                docx_like_name = "MD"
            elif is_pptx:
                docx_like_name = "PPTX"
            elif is_html:
                docx_like_name = "HTML"
            else:
                docx_like_name = "TXT"
            logger.info(
                f"[任务ID: {task_id}] {docx_like_name} 顺序分块完成: 耗时={chunk_time:.2f}秒, 文本块={len(text_chunks_entries)}, 表格={sum(1 for m in merged_items if m.get('type')=='table')}, 图片={sum(1 for m in merged_items if m.get('type')=='image')}"
            )
        else:
            # ✅ PDF处理：检查是否有ordered_elements（统一使用Word的处理逻辑）
            ordered_elements = parse_result.get('ordered_elements', []) or []
            if ordered_elements:
                # ✅ PDF也使用Word的处理逻辑（通过ordered_elements）
                file_type_name = "PDF" if is_pdf else "其他格式"
                logger.info(f"[任务ID: {task_id}] {file_type_name}使用ordered_elements统一处理: 共{len(ordered_elements)}个元素")
                merged_items: List[Dict[str, Any]] = []
                text_chunks_entries: List[Dict[str, Any]] = []
                tables_meta = parse_result.get('tables', []) or []
                chunks = []
                chunks_metadata = []
                chunk_counter = 0
                text_buffer: List[Dict[str, Any]] = []
                image_chunks: List[Dict[str, Any]] = []

                def flush_text_buffer():
                    nonlocal text_buffer, chunk_counter
                    if not text_buffer:
                        return
                    current_parts: List[str] = []
                    current_len = 0
                    chunk_start_idx: Optional[int] = None
                    chunk_start_order: Optional[int] = None
                    chunk_end_idx: Optional[int] = None
                    chunk_end_order: Optional[int] = None

                    def emit_chunk():
                        nonlocal current_parts, current_len, chunk_start_idx, chunk_end_idx, chunk_start_order, chunk_end_order, chunk_counter
                        content = ''.join(current_parts).strip()
                        if not content:
                            current_parts = []
                            current_len = 0
                            chunk_start_idx = None
                            chunk_start_order = None
                            chunk_end_idx = None
                            chunk_end_order = None
                            return
                        base_order = chunk_start_order or 0
                        pos_value = base_order * 1000 + chunk_counter
                        chunk_meta = {
                            'element_index_start': chunk_start_idx,
                            'element_index_end': chunk_end_idx,
                            'doc_order_start': chunk_start_order,
                            'doc_order_end': chunk_end_order,
                            'page_number': None,
                            'coordinates': None,
                            'chunk_index': chunk_counter,
                        }
                        chunk_item = {
                            'type': 'text',
                            'content': content,
                            'pos': pos_value,
                            'meta': chunk_meta,
                        }
                        text_chunks_entries.append(chunk_item)
                        merged_items.append(chunk_item)
                        chunks.append(content)
                        chunks_metadata.append(chunk_meta)
                        chunk_counter += 1
                        current_parts = []
                        current_len = 0
                        chunk_start_idx = None
                        chunk_start_order = None
                        chunk_end_idx = None
                        chunk_end_order = None

                    for idx, entry in enumerate(text_buffer):
                        text_value = entry.get('text') or ''
                        if idx < len(text_buffer) - 1:
                            text_value = text_value + '\n'
                        doc_order = entry.get('doc_order')
                        element_index_entry = entry.get('element_index')
                        pointer = 0
                        length = len(text_value)
                        while pointer < length:
                            if current_len == 0:
                                chunk_start_idx = element_index_entry
                                chunk_start_order = doc_order
                            remain = chunk_max - current_len
                            take = min(remain, length - pointer)
                            piece = text_value[pointer:pointer + take]
                            current_parts.append(piece)
                            current_len += take
                            chunk_end_idx = element_index_entry
                            chunk_end_order = doc_order
                            pointer += take
                            if current_len >= chunk_max:
                                emit_chunk()

                    if current_parts:
                        emit_chunk()

                    text_buffer = []

                for element in ordered_elements:
                    elem_type = element.get('type')
                    if elem_type == 'text' or elem_type == 'code':
                        # 代码块也当作文本处理
                        text_value = (element.get('text') or '').strip()
                        if not text_value:
                            continue
                        text_buffer.append({
                            'text': text_value,
                            'element_index': element.get('element_index'),
                            'doc_order': element.get('doc_order'),
                        })
                    elif elem_type == 'table':
                        flush_text_buffer()
                        continue
                    elif elem_type == 'image':
                        flush_text_buffer()
                        doc_order = element.get('doc_order') or 0
                        elem_idx = element.get('element_index')
                        if elem_idx is None:
                            logger.warning(
                                f"[任务ID: {task_id}] ⚠️ PDF图片元素缺少 element_index: doc_order={doc_order}, "
                                f"element_keys={list(element.keys())}"
                            )
                        image_chunk = {
                            'type': 'image',
                            'content': '',
                            'pos': doc_order * 1000,
                            'meta': {
                                'element_index': elem_idx,
                                'doc_order': doc_order,
                                'page_number': element.get('page_number'),
                                'coordinates': element.get('coordinates'),
                                'image_id': None,
                                'image_path': None,
                            }
                        }
                        merged_items.append(image_chunk)
                        image_chunks.append(image_chunk)
                        if elem_idx is not None:
                            logger.debug(
                                f"[任务ID: {task_id}] ✅ PDF图片分块创建（统一处理）: element_index={elem_idx}, doc_order={doc_order}, pos={doc_order * 1000}"
                            )
                flush_text_buffer()
                merged_items.sort(key=lambda item: item.get('pos', 0))
                # 去重：确保每个 element_index 仅生成一个 image/table 块
                deduped_items: List[Dict[str, Any]] = []
                used_table_indices = set()
                used_image_indices = set()
                for item in merged_items:
                    item_type = item.get('type')
                    meta = item.get('meta') or {}
                    elem_idx = meta.get('element_index')
                    if item_type == 'table' and elem_idx is not None:
                        key = (elem_idx, item.get('pos'))
                        if key in used_table_indices:
                            continue
                        used_table_indices.add(key)
                    elif item_type == 'image' and elem_idx is not None:
                        if elem_idx in used_image_indices:
                            continue
                        used_image_indices.add(elem_idx)
                    deduped_items.append(item)
                merged_items = deduped_items

                chunk_time = time.time() - chunk_start
                file_type_name = "PDF" if is_pdf else "其他格式"
                logger.info(f"[任务ID: {task_id}] {file_type_name}顺序分块完成（统一处理）: 耗时={chunk_time:.2f}秒, 文本块={len(text_chunks_entries)}, 表格={sum(1 for m in merged_items if m.get('type')=='table')}, 图片={sum(1 for m in merged_items if m.get('type')=='image')}")
            else:
                # ⚠️ 已废弃：原有PDF处理逻辑（如果没有ordered_elements，使用旧逻辑）
                # 注意：现在PDF解析已统一生成ordered_elements，此分支理论上不会执行
                # 保留作为向后兼容的备用逻辑
                logger.warning(
                    f"[任务ID: {task_id}] ⚠️ PDF未找到ordered_elements，使用旧的分块逻辑（已废弃）"
                )
                elements_for_chunking = None
                if filtered_elements_light:
                    class LightElement:
                        def __init__(self, category, text, element_index):
                            self.category = category
                            self.text = text
                            self.element_index = element_index
                    elements_for_chunking = [
                        LightElement(elem.get('category'), elem.get('text', ''), elem.get('element_index', i))
                        for i, elem in enumerate(filtered_elements_light)
                    ]

                chunks_with_index = DocxService(db).chunk_text(
                    text_content,
                    text_element_index_map=text_element_index_map,
                    elements=elements_for_chunking
                )
                chunk_time = time.time() - chunk_start

                logger.info(
                    f"[任务ID: {task_id}] PDF 分块初步完成（旧逻辑）: 原始块={len(chunks_with_index)}, "
                    f"文本元素={len(filtered_elements_light)}, 表格={len(parse_result.get('tables', []))}, "
                    f"图片={len(parse_result.get('images', []))}, 耗时={chunk_time:.2f}秒"
                )

                if chunks_with_index and isinstance(chunks_with_index[0], str):
                    chunks = chunks_with_index
                    chunks_metadata = []
                else:
                    chunks = [chunk.get('content', '') for chunk in chunks_with_index]
                    chunks_metadata = chunks_with_index

                logger.info(f"[任务ID: {task_id}] 文档分块完成（旧逻辑）: 耗时={chunk_time:.2f}秒, 共生成 {len(chunks)} 个分块")

                if chunks_metadata:
                    preview_meta = []
                    for idx, meta in enumerate(chunks_metadata[:5]):
                        preview_meta.append(
                            {
                                "chunk_index": idx,
                                "is_parent": bool(meta.get('is_parent')),
                                "element_index_start": meta.get('element_index_start'),
                                "element_index_end": meta.get('element_index_end'),
                                "page_number": meta.get('page_number'),
                                "section_id": meta.get('section_id'),
                            }
                        )
                    logger.info(f"[任务ID: {task_id}] PDF 分块元数据预览(前5个): {preview_meta}")

                merged_items = []
                tables_meta = parse_result.get('tables', [])
                image_chunks: List[Dict[str, Any]] = []
                # ⚠️ 已废弃：收集文本块（旧逻辑，不包含图片分块）
                # 注意：此逻辑不会创建图片分块，图片处理会失败
                for i, chunk_content in enumerate(chunks):
                    element_index_start = None
                    element_index_end = None
                    page_number = None
                    section_id = None
                    is_parent = False
                    if chunks_metadata and i < len(chunks_metadata):
                        element_index_start = chunks_metadata[i].get('element_index_start')
                        element_index_end = chunks_metadata[i].get('element_index_end')
                        section_id = chunks_metadata[i].get('section_id')
                        is_parent = bool(chunks_metadata[i].get('is_parent'))

                    page_numbers = []
                    coordinates_list = []
                    if text_element_index_map:
                        if element_index_start is not None and element_index_end is not None:
                            for map_item in text_element_index_map:
                                elem_idx = map_item.get('element_index')
                                if element_index_start <= elem_idx <= element_index_end:
                                    page_num = map_item.get('page_number')
                                    if page_num is not None and page_num not in page_numbers:
                                        page_numbers.append(page_num)
                                    coords = map_item.get('coordinates')
                                    if coords and isinstance(coords, dict):
                                        if coords.get('x', 0) > 0 or coords.get('y', 0) > 0:
                                            coordinates_list.append(coords)
                        elif element_index_start is not None:
                            for map_item in text_element_index_map:
                                if map_item.get('element_index') == element_index_start:
                                    page_num = map_item.get('page_number')
                                    if page_num is not None:
                                        page_numbers.append(page_num)
                                    coords = map_item.get('coordinates')
                                    if coords and isinstance(coords, dict):
                                        if coords.get('x', 0) > 0 or coords.get('y', 0) > 0:
                                            coordinates_list.append(coords)
                                    break
                        if page_numbers:
                            page_number = page_numbers[0]
                    chunk_coordinates = None
                    if coordinates_list:
                        if len(coordinates_list) == 1:
                            chunk_coordinates = coordinates_list[0]
                        else:
                            min_x = min(c.get('x', 0) for c in coordinates_list)
                            min_y = min(c.get('y', 0) for c in coordinates_list)
                            max_x = max((c.get('x', 0) + c.get('width', 0)) for c in coordinates_list)
                            max_y = max((c.get('y', 0) + c.get('height', 0)) for c in coordinates_list)
                            chunk_coordinates = {
                                'x': min_x,
                                'y': min_y,
                                'width': max_x - min_x,
                                'height': max_y - min_y
                            }
                    pos = element_index_start if element_index_start is not None else (10_000_000 + i)
                    chunk_meta = {
                        'chunk_index': i,
                        'element_index_start': element_index_start,
                        'element_index_end': element_index_end,
                        'page_number': page_number,
                        'coordinates': chunk_coordinates,
                        'section_id': section_id,
                        'is_parent': is_parent,
                    }
                    merged_items.append({
                        'type': 'text',
                        'content': chunk_content,
                        'pos': pos,
                        'meta': chunk_meta
                    })
                # ⚠️ 注意：旧逻辑不会处理图片分块，图片无法关联上下文

        # 收集表格块
        existing_table_keys = set()
        if is_docx:
            existing_table_keys = {
                (item.get('meta', {}).get('element_index'), item.get('pos'))
                for item in merged_items
                if item.get('type') == 'table'
            }

        for tbl in tables_meta:
            try:
                tbl_index = tbl.get('element_index')
                tbl_text = tbl.get('table_text') or ''
                tbl_data = tbl.get('table_data') or {}
                # ✅ 写入 document_tables 表，并生成 table_uid（UUID）
                import uuid, json as _json
                from sqlalchemy import text as _sql_text
                table_uid = uuid.uuid4().hex
                table_group_uid = table_uid  # 默认不分片时，group 与 part 相同
                n_rows = int(tbl_data.get('rows') or 0)
                n_cols = int(tbl_data.get('columns') or 0)
                headers_json = _json.dumps({'rows': 1, 'content': (tbl_data.get('cells')[:1] if n_rows else [])}, ensure_ascii=False)
                cells_list = tbl_data.get('cells') or []
                cells_json = _json.dumps(cells_list, ensure_ascii=False)
                spans_json = _json.dumps(tbl_data.get('spans') or [], ensure_ascii=False)
                stats_json = _json.dumps({}, ensure_ascii=False)
                
                # 分片阈值（基于行数的简单切分，可后续改为基于字节/单元格计数）
                MAX_ROWS_PER_PART = 400
                if n_rows > MAX_ROWS_PER_PART:
                    table_group_uid = uuid.uuid4().hex
                    total_parts = (n_rows + MAX_ROWS_PER_PART - 1) // MAX_ROWS_PER_PART
                    for p_idx in range(total_parts):
                        start_row = p_idx * MAX_ROWS_PER_PART
                        end_row = min((p_idx + 1) * MAX_ROWS_PER_PART, n_rows)
                        part_cells = cells_list[start_row:end_row]
                        part_cells_json = _json.dumps(part_cells, ensure_ascii=False)
                        row_range = f"{start_row}-{end_row-1}"
                        part_uid = uuid.uuid4().hex
                        db.execute(
                            _sql_text(
                                """
                                INSERT INTO document_tables (
                                    table_uid, table_group_uid, document_id, element_index,
                                    n_rows, n_cols, headers_json, cells_json, spans_json, stats_json,
                                    part_index, part_count, row_range
                                ) VALUES (
                                    :table_uid, :table_group_uid, :document_id, :element_index,
                                    :n_rows, :n_cols, :headers_json, :cells_json, :spans_json, :stats_json,
                                    :part_index, :part_count, :row_range
                                )
                                """
                            ),
                            {
                                "table_uid": part_uid,
                                "table_group_uid": table_group_uid,
                                "document_id": document_id,
                                "element_index": tbl_index,
                                "n_rows": end_row - start_row,
                                "n_cols": n_cols,
                                "headers_json": headers_json,
                                "cells_json": part_cells_json,
                                "spans_json": spans_json,
                                "stats_json": stats_json,
                                "part_index": p_idx,
                                "part_count": total_parts,
                                "row_range": row_range,
                            }
                        )
                    # 写入表块：改为第一分片的 uid，且在 meta 中补充 group_uid 与 part 信息
                    first_part_uid = db.execute(
                        _sql_text("SELECT table_uid FROM document_tables WHERE table_group_uid=:g AND part_index=0 LIMIT 1"),
                        {"g": table_group_uid}
                    ).fetchone()[0]
                    table_uid = first_part_uid
                    n_rows = min(n_rows, MAX_ROWS_PER_PART)
                else:
                    db.execute(
                        _sql_text(
                            """
                            INSERT INTO document_tables (
                                table_uid, table_group_uid, document_id, element_index,
                                n_rows, n_cols, headers_json, cells_json, spans_json, stats_json,
                                part_index, part_count, row_range
                            ) VALUES (
                                :table_uid, :table_group_uid, :document_id, :element_index,
                                :n_rows, :n_cols, :headers_json, :cells_json, :spans_json, :stats_json,
                                0, 1, NULL
                            )
                            """
                        ),
                        {
                            "table_uid": table_uid,
                            "table_group_uid": table_group_uid,
                            "document_id": document_id,
                            "element_index": tbl_index,
                            "n_rows": n_rows,
                            "n_cols": n_cols,
                            "headers_json": headers_json,
                            "cells_json": cells_json,
                            "spans_json": spans_json,
                            "stats_json": stats_json,
                        }
                    )
                # ✅ 控制表格可检索文本（TST）长度（使用 TEXT_EMBED_MAX_CHARS 配置，默认1024字符）
                max_chars = int(getattr(settings, 'TEXT_EMBED_MAX_CHARS', 1024))
                if tbl_text and len(tbl_text) > max_chars:
                    tbl_text = tbl_text[:max_chars]
                    logger.debug(f"[任务ID: {task_id}] 表格文本超过限制 ({len(tbl_text)} > {max_chars})，已截断")
                # 使用 table_uid 替代大 JSON 存入 chunk.meta
                tbl_page_number = tbl.get('page_number')
                append_table_chunk = True
                if is_docx:
                    doc_order = tbl.get('doc_order') or 0
                    table_pos = doc_order * 1000
                    if tbl_index is not None and (tbl_index, table_pos) in existing_table_keys:
                        append_table_chunk = False
                else:
                    table_pos = tbl_index if tbl_index is not None else 9_000_000
                if append_table_chunk:
                    merged_items.append({
                        'type': 'table',
                        'content': tbl_text,
                        'pos': table_pos,
                        'meta': {
                            'element_index': tbl_index,
                            'table_id': table_uid,
                            'table_group_uid': table_group_uid,
                            'n_rows': n_rows,
                            'n_cols': n_cols,
                            'page_number': tbl_page_number
                        }
                    })
            except Exception as e:
                logger.warning(f"[任务ID: {task_id}] 保存表格到 document_tables 失败: {e}")
                continue

        # 重新按 pos 排序并重建 chunk_index（保持原逻辑）
        merged_items.sort(key=lambda x: (x.get('pos') is None, x.get('pos')))
        
        # ✅ 验证：检查表格是否在正确位置（基于 element_index 验证）
        logger.info(f"[任务ID: {task_id}] 开始验证表格位置正确性...")
        validation_errors = []
        table_count = 0
        text_count = 0
        
        for idx, item in enumerate(merged_items):
            item_type = item.get('type', 'unknown')
            item_pos = item.get('pos')
            item_meta = item.get('meta', {})
            
            if item_type == 'table':
                table_count += 1
                table_elem_idx = item_meta.get('element_index')
                table_page = item_meta.get('page_number')
                
                # ✅ 验证：表格必须有 element_index
                if table_elem_idx is None:
                    validation_errors.append(f"表格块 (chunk_index={idx}) 缺少 element_index，无法验证位置")
                    logger.warning(f"[任务ID: {task_id}] 表格块 (chunk_index={idx}) 缺少 element_index")
                    continue
                
                # 检查前后的文本块，验证表格是否在正确位置
                prev_item = merged_items[idx - 1] if idx > 0 else None
                next_item = merged_items[idx + 1] if idx < len(merged_items) - 1 else None
                
                validation_info = {
                    'table_pos': item_pos,
                    'table_element_index': table_elem_idx,
                    'table_page': table_page,
                    'chunk_index_after_sort': idx
                }
                
                # 验证前一个块
                if prev_item:
                    prev_type = prev_item.get('type')
                    prev_pos = prev_item.get('pos')
                    prev_meta = prev_item.get('meta', {})
                    prev_elem_start = prev_meta.get('element_index_start') or prev_meta.get('element_index')
                    prev_elem_end = prev_meta.get('element_index_end')
                    
                    validation_info['prev_type'] = prev_type
                    validation_info['prev_pos'] = prev_pos
                    validation_info['prev_elem_start'] = prev_elem_start
                    validation_info['prev_elem_end'] = prev_elem_end
                    
                    # 验证：如果前一个块是文本块且有 element_index_end，检查排序是否正确
                    # 注意：表格可能在文本块的 element_index_end 之后，这是正确的
                    # 但如果表格的 element_index 小于文本块的 element_index_start，那就有问题
                    if prev_type == 'text' and prev_elem_start is not None and table_elem_idx is not None:
                        if table_elem_idx < prev_elem_start:
                            validation_errors.append(f"位置错误: 表格 element_index ({table_elem_idx}) 小于前一个文本块的 element_index_start ({prev_elem_start})")
                    elif prev_pos is not None and item_pos is not None and prev_pos >= item_pos:
                        validation_errors.append(f"位置错误: 表格 (pos={item_pos}) 应该在前一个块 (pos={prev_pos}) 之后")
                
                # 验证后一个块
                if next_item:
                    next_type = next_item.get('type')
                    next_pos = next_item.get('pos')
                    next_meta = next_item.get('meta', {})
                    next_elem_start = next_meta.get('element_index_start') or next_meta.get('element_index')
                    
                    validation_info['next_type'] = next_type
                    validation_info['next_pos'] = next_pos
                    validation_info['next_elem_start'] = next_elem_start
                    
                    # 验证：如果后一个块是文本块，表格的 element_index 应该在后一个块之前
                    if next_type == 'text' and next_elem_start is not None and table_elem_idx is not None:
                        if table_elem_idx >= next_elem_start:
                            validation_info['warning'] = f"表格 element_index ({table_elem_idx}) 应该在后一个文本块之前 ({next_elem_start})"
                    elif next_pos is not None and item_pos is not None and item_pos >= next_pos:
                        validation_errors.append(f"位置错误: 表格 (pos={item_pos}) 应该在后一个块 (pos={next_pos}) 之前")
                
                logger.info(f"[任务ID: {task_id}] 表格验证 (chunk_index={idx}): {validation_info}")
        
        # ✅ 验证：检查是否有表格丢失或重复
        parsed_table_count = len(tables_meta)
        if table_count != parsed_table_count:
            validation_errors.append(f"表格数量不匹配: 解析到 {parsed_table_count} 个表格，但合并后只有 {table_count} 个表格块")
            logger.warning(f"[任务ID: {task_id}] 表格数量不匹配: 解析={parsed_table_count}, 合并={table_count}")
        
        # ✅ 验证：检查表格的 element_index 是否有重复
        table_indices = [item.get('meta', {}).get('element_index') 
                         for item in merged_items 
                         if item.get('type') == 'table' and item.get('meta', {}).get('element_index') is not None]
        if len(table_indices) != len(set(table_indices)):
            duplicates = [idx for idx in table_indices if table_indices.count(idx) > 1]
            validation_errors.append(f"发现重复的表格 element_index: {duplicates}")
            logger.warning(f"[任务ID: {task_id}] 发现重复的表格 element_index: {duplicates}")
        
        if validation_errors:
            logger.warning(f"[任务ID: {task_id}] 表格位置验证发现 {len(validation_errors)} 个错误:")
            for error in validation_errors:
                logger.warning(f"[任务ID: {task_id}]   - {error}")
        else:
            logger.info(f"[任务ID: {task_id}] ✅ 表格位置验证通过: 所有表格都在正确位置 (共 {table_count} 个表格)")
        
        # ✅ 记录排序后的块顺序（前10个和后10个，用于调试）
        total_items = len(merged_items)
        log_items = merged_items[:10] + (merged_items[-10:] if total_items > 20 else [])
        logger.info(f"[任务ID: {task_id}] 排序后的块顺序（前10个{'和后10个' if total_items > 20 else ''}）:")
        for idx, item in enumerate(log_items):
            actual_idx = idx if idx < 10 else (total_items - 10 + (idx - 10))
            item_type = item.get('type')
            item_pos = item.get('pos')
            item_meta = item.get('meta', {})
            if item_type == 'table':
                elem_idx = item_meta.get('element_index')
                logger.info(f"[任务ID: {task_id}]   [{actual_idx}] {item_type}: pos={item_pos}, element_index={elem_idx}")
            elif item_type == 'image':
                elem_idx = item_meta.get('element_index')
                logger.info(f"[任务ID: {task_id}]   [{actual_idx}] {item_type}: pos={item_pos}, element_index={elem_idx}")
            else:
                elem_start = item_meta.get('element_index_start')
                elem_end = item_meta.get('element_index_end')
                logger.info(f"[任务ID: {task_id}]   [{actual_idx}] {item_type}: pos={item_pos}, element_index_range=({elem_start}, {elem_end})")
        
        # 保存分块到数据库（按配置决定是否存正文，同时保存 element_index 范围/表格数据）
        store_text = getattr(settings, 'STORE_CHUNK_TEXT_IN_DB', False)
        import json

        created_chunks = []  # 收集已创建的块（便于后续关系建立）
        element_index_to_chunk_row = {}
        chunk_index_to_row = {}
        image_chunk_rows = {}

        for new_index, item in enumerate(merged_items):
            # ✅ 重要：使用 copy() 创建 meta 的副本，避免修改原始数据
            original_meta = item.get('meta') or {}
            chunk_metadata = original_meta.copy() if isinstance(original_meta, dict) else {}
            chunk_metadata['chunk_index'] = new_index
            chunk_type = item.get('type', 'text')
            
            # ✅ 调试：记录图片分块的 element_index
            if chunk_type == 'image':
                elem_idx = chunk_metadata.get('element_index')
                if elem_idx is None:
                    logger.warning(
                        f"[任务ID: {task_id}] ⚠️ 图片分块缺少 element_index: chunk_index={new_index}, "
                        f"meta_keys={list(chunk_metadata.keys())}, original_meta={original_meta}"
                    )
                else:
                    logger.info(
                        f"[任务ID: {task_id}] 保存图片分块: chunk_index={new_index}, element_index={elem_idx}, "
                        f"meta_keys={list(chunk_metadata.keys())}"
                    )
            
            # ✅ 验证：确保 meta 可以正确序列化
            try:
                meta_json = json.dumps(chunk_metadata, ensure_ascii=False)
            except Exception as json_err:
                logger.warning(
                    f"[任务ID: {task_id}] ⚠️ 分块 meta 序列化失败: chunk_index={new_index}, "
                    f"chunk_type={chunk_type}, error={json_err}, meta={chunk_metadata}"
                )
                # 如果序列化失败，使用空字典
                chunk_metadata = {'chunk_index': new_index}
                meta_json = json.dumps(chunk_metadata, ensure_ascii=False)
            
            chunk = DocumentChunk(
                document_id=document_id,
                content=item.get('content', '') if store_text else "",
                chunk_index=new_index,
                chunk_type=chunk_type,
                meta=meta_json
            )
            db.add(chunk)
            created_chunks.append((chunk, chunk_metadata))
            chunk_index_to_row[new_index] = chunk
            if (new_index + 1) % 50 == 0:
                logger.debug(f"[任务ID: {task_id}] 已保存 {new_index + 1}/{len(merged_items)} 个分块到数据库")
        
        db.commit()
        
        # ✅ 建立父子关系（基于 section_id / is_parent）并回填 parent_chunk_id 到子块 meta
        # ✅ 同时构建 element_index 到 chunk_row 的映射（用于图片回填）
        try:
            # 重新查询含主键ID
            db_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index).all()
            # 构建索引: chunk_index -> row, 以及 meta 解析
            import json as _json
            idx_to_row = {}
            idx_to_meta = {}
            current_parent_chunk_id = None
            order_in_parent = 0
            
            for row in db_chunks:
                idx_to_row[row.chunk_index] = row
                chunk_index_to_row[row.chunk_index] = row
                meta_raw = getattr(row, 'meta', None)
                try:
                    meta = _json.loads(meta_raw) if isinstance(meta_raw, str) else (meta_raw or {})
                except Exception:
                    meta = {}
                idx_to_meta[row.chunk_index] = meta
                
                # ✅ 构建 element_index 到 chunk_row 的映射
                chunk_type = getattr(row, 'chunk_type', '').lower()
                elem_idx = meta.get('element_index')
                
                if elem_idx is not None:
                    # ✅ 有 element_index 的分块（图片、表格）
                    logger.info(
                        f"[任务ID: {task_id}] 分块映射: chunk_id={row.id}, chunk_index={row.chunk_index}, "
                        f"chunk_type={chunk_type}, element_index={elem_idx}, meta_keys={list(meta.keys())}"
                    )
                    element_index_to_chunk_row[elem_idx] = row
                    if chunk_type == 'image':
                        image_chunk_rows[elem_idx] = row
                        logger.info(
                            f"[任务ID: {task_id}] ✅ 图片分块映射成功: element_index={elem_idx} -> chunk_id={row.id}"
                        )
                else:
                    # ✅ 对于没有 element_index 的分块（如文本块），检查是否有 element_index_start/end
                    elem_start = meta.get('element_index_start')
                    elem_end = meta.get('element_index_end')
                    if chunk_type == 'image':
                        # ✅ 图片分块必须有 element_index，如果没有则记录警告
                        logger.warning(
                            f"[任务ID: {task_id}] ⚠️ 图片分块缺少 element_index: chunk_id={row.id}, "
                            f"chunk_index={row.chunk_index}, meta_keys={list(meta.keys())}, "
                            f"meta_content={meta}"
                        )
                    elif elem_start is None and elem_end is None:
                        logger.debug(
                            f"[任务ID: {task_id}] 文本分块无 element_index: chunk_id={row.id}, "
                            f"chunk_index={row.chunk_index}, meta_keys={list(meta.keys())}"
                        )
                
                # ✅ 建立父子关系（从 meta 中读取 is_parent 和 section_id）
                is_parent = bool(meta.get('is_parent', False))
                section_id = meta.get('section_id')
                
                if is_parent:
                    current_parent_chunk_id = row.id
                    order_in_parent = 0
                    # 标记父块自身（可选，不写关系表）
                else:
                    if current_parent_chunk_id is not None and section_id is not None:
                        order_in_parent += 1
                        # 插入关系表
                        try:
                            db.execute(
                                _sql_text(
                                    """
                                    INSERT INTO chunk_relations (document_id, relation_type, parent_chunk_id, child_chunk_id, order_in_parent)
                                    VALUES (:document_id, :relation_type, :parent_chunk_id, :child_chunk_id, :order_in_parent)
                                    """
                                ),
                                {
                                    'document_id': document_id,
                                    'relation_type': 'parent_child',
                                    'parent_chunk_id': current_parent_chunk_id,
                                    'child_chunk_id': row.id,
                                    'order_in_parent': order_in_parent,
                                }
                            )
                        except Exception as e:
                            logger.warning(f"[任务ID: {task_id}] 写入 chunk_relations 失败: child={row.id}, err={e}")
                        # 回填子块 meta 的 parent_chunk_id 与 section_id
                        meta['parent_chunk_id'] = current_parent_chunk_id
                        meta['section_id'] = section_id
                        try:
                            row.meta = _json.dumps(meta, ensure_ascii=False)
                        except Exception:
                            pass
            db.commit()
            logger.info(f"[任务ID: {task_id}] 父子关系建立完成，element_index映射已构建: {len(element_index_to_chunk_row)} 个映射，其中图片分块: {len(image_chunk_rows)} 个")
        except Exception as e:
            db.rollback()
            logger.warning(f"[任务ID: {task_id}] 父子关系建立阶段失败（不影响主流程）: {e}")
            import traceback
            logger.debug(f"[任务ID: {task_id}] 父子关系建立失败详情: {traceback.format_exc()}")
            # ✅ 即使映射建立失败，也尝试重新构建映射（仅用于图片回填）
            try:
                logger.info(f"[任务ID: {task_id}] 尝试重新构建 element_index 映射用于图片回填...")
                import json as retry_json
                db_chunks_retry = db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.chunk_type == 'image'
                ).all()
                retry_count = 0
                for row in db_chunks_retry:
                    meta_raw = getattr(row, 'meta', None)
                    try:
                        meta = retry_json.loads(meta_raw) if isinstance(meta_raw, str) else (meta_raw or {})
                    except Exception:
                        meta = {}
                    elem_idx = meta.get('element_index')
                    if elem_idx is not None:
                        element_index_to_chunk_row[elem_idx] = row
                        image_chunk_rows[elem_idx] = row
                        retry_count += 1
                        logger.info(f"[任务ID: {task_id}] 重新映射成功: element_index={elem_idx} -> chunk_id={row.id}")
                    else:
                        logger.warning(
                            f"[任务ID: {task_id}] 重新映射跳过: chunk_id={row.id} 缺少 element_index, "
                            f"meta_keys={list(meta.keys())}"
                        )
                logger.info(
                    f"[任务ID: {task_id}] 重新构建映射完成: 查询到 {len(db_chunks_retry)} 个图片分块, "
                    f"成功映射 {retry_count} 个, element_index_to_chunk_row={len(element_index_to_chunk_row)}, "
                    f"image_chunk_rows={len(image_chunk_rows)}"
                )
            except Exception as retry_err:
                logger.warning(f"[任务ID: {task_id}] 重新构建映射也失败: {retry_err}")
                import traceback
                logger.debug(f"[任务ID: {task_id}] 重新构建映射失败详情: {traceback.format_exc()}")
        
        # ✅ 统计信息
        text_chunks = sum(1 for item in merged_items if item.get('type') == 'text')
        table_chunks = sum(1 for item in merged_items if item.get('type') == 'table')
        logger.info(f"[任务ID: {task_id}] 分块数据已保存到数据库: 共 {len(merged_items)} 条记录（文本块={text_chunks}, 表格块={table_chunks}）")

        # 将全文分块归档到 MinIO（同时保存 element_index 信息）
        try:
            minio = MinioStorageService()
            # 保存带索引信息的分块数据（✅ 新增：包含 coordinates 和 page_number）
            chunks_for_storage = []
            for i, item in enumerate(merged_items):
                chunk_data = {
                    'index': i,
                    'content': item['content'],
                    'chunk_type': item['type']
                }
                meta = item.get('meta') or {}
                # 保存 element_index 信息
                if 'element_index_start' in meta:
                    chunk_data['element_index_start'] = meta.get('element_index_start')
                if 'element_index_end' in meta:
                    chunk_data['element_index_end'] = meta.get('element_index_end')
                if 'element_index' in meta:
                    chunk_data['element_index'] = meta.get('element_index')
                # ✅ 新增：保存 page_number 和 coordinates（用于坐标重叠度计算）
                if 'page_number' in meta:
                    chunk_data['page_number'] = meta.get('page_number')
                if 'coordinates' in meta and meta.get('coordinates'):
                    chunk_data['coordinates'] = meta.get('coordinates')
                chunks_for_storage.append(chunk_data)
            minio.upload_chunks(str(document_id), chunks_for_storage)
            logger.info(f"[任务ID: {task_id}] 分块JSON已归档到 MinIO（含element_index）")
        except Exception as e:
            logger.warning(f"[任务ID: {task_id}] 分块归档到 MinIO 失败: {e}")

        # ✅ 保存完整文档文本内容到 parsed/content.json（用于实体提取）
        try:
            minio = MinioStorageService()
            # 从parse_result中获取完整文本内容
            full_text_content = parse_result.get('text_content', '') if parse_result else ''
            if full_text_content:
                # 构建content.json数据结构
                content_data = {
                    'text_content': full_text_content,
                    'document_id': document_id,
                    'metadata': parse_result.get('metadata', {}) if parse_result else {},
                    'elements_count': elements_count,
                    'text_length': len(full_text_content)
                }
                minio.upload_parsed_content(str(document_id), content_data)
                logger.info(f"[任务ID: {task_id}] 完整文档文本内容已保存到 parsed/content.json，长度={len(full_text_content)} 字符")
            else:
                logger.warning(f"[任务ID: {task_id}] 未找到完整文本内容，跳过保存 parsed/content.json")
        except Exception as e:
            logger.warning(f"[任务ID: {task_id}] 保存完整文档文本内容到 parsed/content.json 失败: {e}")

        # 图片处理流水线（若解析结果包含图片二进制，则落 MinIO + 入库 + 向量化 + 索引）
        def _process_images():
            images_meta = parse_result.get('images', []) or []
            if not images_meta:
                return

            total_images = len(images_meta)
            try:
                with_data = sum(1 for _img in images_meta if (_img.get('data') or _img.get('bytes')))
            except Exception:
                with_data = 0
            logger.info(
                f"[任务ID: {task_id}] 解析到图片: {total_images} 张，其中含二进制数据: {with_data}/{total_images}"
            )
            if total_images and with_data == 0:
                logger.warning(
                    f"[任务ID: {task_id}] 警告：所有图片均缺少二进制数据(data/bytes)，将无法持久化。"
                )

            img_service = ImageService(db)
            vector_service = VectorService(db)
            os_service = OpenSearchService()
            saved = 0
            chunk_meta_dirty = False

            for img in images_meta:
                data = img.get('data') or img.get('bytes')
                if not data:
                    continue

                element_index = img.get('element_index')
                page_number = img.get('page_number')
                doc_order = img.get('doc_order')
                coordinates = img.get('coordinates')
                image_sha256 = hashlib.sha256(data).hexdigest()

                existing_image = db.query(DocumentImage).filter(
                    DocumentImage.sha256_hash == image_sha256,
                    DocumentImage.is_deleted == False,
                ).first()
                is_new_image = existing_image is None

                image_row = img_service.create_image_from_bytes(
                    document_id,
                    data,
                    image_ext=img.get('ext', '.png'),
                    image_type=img.get('image_type'),
                )

                # ✅ 更新图片 metadata（element_index, page_number, coordinates 等）
                if element_index is not None or page_number is not None or doc_order is not None or coordinates:
                    import json
                    try:
                        existing_meta = {}
                        if image_row.meta:
                            existing_meta = (
                                json.loads(image_row.meta)
                                if isinstance(image_row.meta, str)
                                else image_row.meta
                            )
                        if element_index is not None:
                            existing_meta['element_index'] = element_index
                        if page_number is not None:
                            existing_meta['page_number'] = page_number
                        if doc_order is not None:
                            existing_meta['doc_order'] = doc_order
                        if coordinates:
                            existing_meta['coordinates'] = coordinates
                        image_row.meta = json.dumps(existing_meta, ensure_ascii=False)
                        db.commit()
                        logger.debug(
                            f"[任务ID: {task_id}] 图片 {image_row.id} metadata 更新成功: "
                            f"element_index={element_index}, page_number={page_number}"
                        )
                    except Exception as meta_exc:
                        logger.warning(
                            f"[任务ID: {task_id}] 保存图片 metadata 失败 (image_id={image_row.id}): {meta_exc}"
                        )
                        db.rollback()

                image_vector = None
                if not is_new_image:
                    try:
                        response = os_service.client.get(
                            index=os_service.image_index,
                            id=f"image_{image_row.id}",
                        )
                        existing_vector = response.get("_source", {}).get("image_vector")
                        if existing_vector and len(existing_vector) == 512:
                            image_vector = existing_vector
                            logger.info(
                                f"[任务ID: {task_id}] 图片 {image_row.id} (SHA256: {image_sha256[:8]}...) 已存在，复用向量"
                            )
                    except Exception:
                        logger.debug(
                            f"[任务ID: {task_id}] 图片 {image_row.id} 未在OpenSearch中找到向量，将生成新向量"
                        )

                if image_vector is None:
                    image_vector = vector_service.generate_image_embedding_prefer_memory(data)
                    logger.info(
                        f"[任务ID: {task_id}] 图片 {image_row.id} 向量生成完成，维度: {len(image_vector)}"
                    )

                # ✅ 记录向量化结果到 MySQL，供前端状态展示
                try:
                    vector_dim = len(image_vector) if image_vector else None
                    if vector_dim:
                        image_row.vector_model = settings.CLIP_MODEL_NAME
                        image_row.vector_dim = vector_dim
                    image_row.last_processed_at = datetime.datetime.utcnow()
                    if image_row.status not in ("completed", "failed"):
                        image_row.status = "completed"
                    db.commit()
                except Exception as db_exc:
                    logger.warning(f"[任务ID: {task_id}] 回写图片向量信息失败 image_id={image_row.id}: {db_exc}")
                    db.rollback()

                try:
                    image_metadata = img.get('metadata', {}) or {}
                    if element_index is not None:
                        image_metadata['element_index'] = element_index
                    if doc_order is not None:
                        image_metadata['doc_order'] = doc_order
                    image_metadata['image_path'] = image_row.image_path
                    image_metadata['image_id'] = image_row.id

                    os_service.index_image_sync(
                        {
                            "image_id": image_row.id,
                            "document_id": document.id,
                            "knowledge_base_id": document.knowledge_base_id,
                            "category_id": getattr(document, 'category_id', None),
                            "image_path": image_row.image_path,
                            "page_number": page_number,
                            "coordinates": coordinates,
                            "width": image_row.width,
                            "height": image_row.height,
                            "image_type": image_row.image_type,
                            "ocr_text": image_row.ocr_text or "",
                            "description": img.get('description', ''),
                            "feature_tags": img.get('feature_tags', []),
                            "image_vector": image_vector,
                            "element_index": element_index,
                            "created_at": getattr(image_row, 'created_at', None).isoformat()
                            if getattr(image_row, 'created_at', None)
                            else None,
                            "updated_at": getattr(image_row, 'updated_at', None).isoformat()
                            if getattr(image_row, 'updated_at', None)
                            else None,
                            "metadata": image_metadata,
                            "processing_status": getattr(image_row, 'status', 'completed'),
                            "model_version": "1.0",
                        }
                    )
                    logger.info(
                        f"[任务ID: {task_id}] 图片 {image_row.id} 索引完成（element_index={element_index}）"
                    )
                except Exception as idx_exc:
                    logger.warning(
                        f"[任务ID: {task_id}] 图片索引失败 image_id={image_row.id}: {idx_exc}"
                    )

                saved += 1

                # ✅ 回填图片元数据到对应的 DocumentChunk
                if element_index is not None:
                    # 首先尝试从 image_chunk_rows 获取（这是专门为图片分块建立的映射）
                    chunk_row = image_chunk_rows.get(element_index)
                    # 如果没找到，再从通用的 element_index_to_chunk_row 获取
                    if chunk_row is None:
                        chunk_row = element_index_to_chunk_row.get(element_index)
                    
                    if chunk_row is not None:
                        chunk_type = getattr(chunk_row, 'chunk_type', '').lower()
                        chunk_id = getattr(chunk_row, 'id', None)
                        
                        # ✅ 只更新图片类型的分块
                        if chunk_type == 'image':
                            try:
                                import json
                                existing_meta_raw = getattr(chunk_row, 'meta', None)
                                if isinstance(existing_meta_raw, str):
                                    try:
                                        existing_meta = json.loads(existing_meta_raw)
                                    except Exception:
                                        existing_meta = {}
                                else:
                                    existing_meta = existing_meta_raw or {}
                                
                                # ✅ 合并更新，保留原有字段
                                existing_meta.update({
                                    'image_id': image_row.id,
                                    'image_path': image_row.image_path,
                                })
                                chunk_row.meta = json.dumps(existing_meta, ensure_ascii=False)
                                logger.info(
                                    f"[任务ID: {task_id}] ✅ 图片 {image_row.id} 回填成功: chunk_id={chunk_id}, chunk_index={getattr(chunk_row, 'chunk_index', None)}, element_index={element_index}, meta_keys={list(existing_meta.keys())}"
                                )
                                chunk_meta_dirty = True
                            except Exception as meta_err:
                                logger.warning(
                                    f"[任务ID: {task_id}] ❌ 更新图片分块元数据失败 (chunk_id={chunk_id}, element_index={element_index}): {meta_err}"
                                )
                                import traceback
                                logger.debug(f"[任务ID: {task_id}] 更新失败详情: {traceback.format_exc()}")
                        else:
                            logger.warning(
                                f"[任务ID: {task_id}] ⚠️ 目标分块类型不匹配: chunk_id={chunk_id}, element_index={element_index}, 期望类型=image, 实际类型={chunk_type}，跳过图片元数据回填"
                            )
                    else:
                        # ✅ 详细调试信息：列出所有已映射的 element_index 和图片分块
                        mapped_indices = list(element_index_to_chunk_row.keys())
                        mapped_image_indices = list(image_chunk_rows.keys())
                        logger.warning(
                            f"[任务ID: {task_id}] ⚠️ 图片 {image_row.id} 未找到 element_index={element_index} 对应的数据库分块。"
                            f" 可用映射数量: element_index_to_chunk_row={len(element_index_to_chunk_row)}, image_chunk_rows={len(image_chunk_rows)}"
                            f" 已映射的 element_index: {sorted(mapped_indices)}, 已映射的图片 element_index: {sorted(mapped_image_indices)}"
                        )
                else:
                    logger.warning(
                        f"[任务ID: {task_id}] ⚠️ 图片 {image_row.id} 缺少 element_index，无法回填到分块"
                    )

            logger.info(
                f"[任务ID: {task_id}] 图片持久化完成: {saved}/{len(images_meta)}"
            )
            if chunk_meta_dirty:
                try:
                    db.commit()
                except Exception as commit_err:
                    logger.warning(
                        f"[任务ID: {task_id}] 提交图片分块元数据失败: {commit_err}"
                    )
                    db.rollback()

        try:
            _process_images()
        except Exception as images_exc:
            logger.warning(f"[任务ID: {task_id}] 图片持久化失败: {images_exc}")

        current_task.update_state(
            state="PROGRESS",
            meta={"current": 60, "total": 100, "status": "文档分块完成"}
        )
        
        # 更新文档状态为向量化中
        logger.debug(f"[任务ID: {task_id}] 步骤6/7: 开始向量化和索引建立")
        document.status = DOC_STATUS_VECTORIZING
        document.processing_progress = 70.0
        db.commit()
        
        # 向量化处理
        vector_service = VectorService(db)
        db_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index).all()
        
        logger.info(f"[任务ID: {task_id}] 开始向量化: 共 {len(db_chunks)} 个分块需要处理")
        if len(db_chunks) == 0:
            logger.warning(f"[任务ID: {task_id}] 无分块可向量化，跳过向量化与索引阶段")
            document.status = DOC_STATUS_COMPLETED
            
            # 提取文档目录（同步执行，不影响主流程）
            # 注意：TXT 文件不提取目录（纯文本文件通常没有结构化目录）
            try:
                from app.services.document_toc_service import DocumentTOCService
                import asyncio
                toc_service = DocumentTOCService(db)
                if is_pdf and document.file_path:
                    asyncio.run(toc_service.extract_toc_from_pdf(document_id, document.file_path))
                elif is_docx and document.file_path:
                    asyncio.run(toc_service.extract_toc_from_docx(document_id, document.file_path))
                elif is_md:
                    # MD 文件从 metadata 中的 heading_structure 提取目录
                    doc_meta = document.meta or {}
                    if isinstance(doc_meta, str):
                        import json as _json
                        try:
                            doc_meta = _json.loads(doc_meta)
                        except Exception:
                            doc_meta = {}
                    heading_structure = doc_meta.get('heading_structure', [])
                    if heading_structure:
                        asyncio.run(toc_service.extract_toc_from_markdown(document_id, heading_structure))
                # TXT 文件跳过目录提取（纯文本文件通常没有结构化目录）
            except Exception as e:
                logger.warning(f"[任务ID: {task_id}] 提取文档目录失败（不影响主流程）: {e}")
            document.processing_progress = 100.0
            db.commit()
            total_time = time.time() - download_start
            current_task.update_state(state="SUCCESS", meta={"current": 100, "total": 100, "status": "文档无文本，流程结束"})
            return {
                "status": "success",
                "message": "文档无文本，流程结束",
                "document_id": document_id,
                "chunks_count": 0,
                "text_length": len(text_content),
                "processing_time": total_time,
            }
        vectorize_start = time.time()
        
        # 初始化OpenSearch服务
        opensearch_service = OpenSearchService()
        
        # 批量生成向量并存储到OpenSearch
        success_count = 0
        error_count = 0
        
        # 准备文本迭代器：当不在DB存正文时，从 MinIO 的 chunks.jsonl.gz 流式读取
        def _stream_chunk_texts_from_minio(doc_id: int):
            try:
                minio = MinioStorageService()
                files = minio.list_files("documents/")
                needle = f"/{doc_id}/parsed/chunks/chunks.jsonl.gz"
                target = None
                for fobj in files:
                    if fobj.get("object_name", "").endswith(needle):
                        target = fobj["object_name"]
                        break
                if not target:
                    logger.warning(f"[任务ID: {task_id}] 未找到 MinIO 分块归档，回退使用内存分块")
                    for t in chunks:
                        yield t
                    return
                import gzip, json
                response = minio.client.get_object(minio.bucket_name, target)
                try:
                    with gzip.GzipFile(fileobj=response, mode='rb') as gz:
                        for line in gz:
                            try:
                                item = json.loads(line)
                                yield item.get("content", "")
                            except Exception:
                                yield ""
                finally:
                    try:
                        response.close(); response.release_conn()
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"[任务ID: {task_id}] 从 MinIO 流式读取分块失败: {e}，回退内存分块")
                for t in chunks:
                    yield t

        store_text = getattr(settings, 'STORE_CHUNK_TEXT_IN_DB', False)
        text_iter = iter([c if isinstance(c, str) else str(c) for c in chunks]) if store_text else _stream_chunk_texts_from_minio(document_id)

        docs_to_index = []
        for i, chunk in enumerate(db_chunks):
            chunk_start = time.time()
            
            try:
                # ✅ 跳过图片分块：图片分块不进行文本向量化，图片向量化已在图片处理阶段完成
                if chunk.chunk_type == 'image':
                    logger.debug(f"[任务ID: {task_id}] 分块 {chunk.id} 是图片类型，跳过文本向量化（图片向量化已在图片处理阶段完成）")
                    continue
                
                # 获取对应文本，StopIteration 时置空
                try:
                    chunk_text = next(text_iter)
                except StopIteration:
                    chunk_text = ""
                
                # ✅ 优化：对于表格块，从 meta 中提取完整的表格数据并生成完整文本
                chunk_meta_dict = {}  # 确保在所有情况下都有定义
                if chunk.chunk_type == 'table' and chunk.meta:
                    try:
                        chunk_meta_dict = json.loads(chunk.meta) if isinstance(chunk.meta, str) else chunk.meta
                        table_data = chunk_meta_dict.get('table_data', {})
                        
                        # 优先使用结构化单元格数据生成完整文本
                        if table_data.get('cells'):
                            cells = table_data['cells']
                            text_lines = []
                            for row in cells:
                                if isinstance(row, (list, tuple)):
                                    # 使用制表符分隔，保持列对齐
                                    row_text = '\t'.join(str(cell) if cell is not None else '' for cell in row)
                                    text_lines.append(row_text)
                                else:
                                    text_lines.append(str(row))
                            chunk_text = '\n'.join(text_lines)
                            logger.debug(f"[任务ID: {task_id}] 表格块 {chunk.id}: 从结构化数据生成完整文本 ({len(text_lines)} 行)")
                        # 如果没有 cells，尝试使用 HTML（至少包含结构化信息）
                        elif table_data.get('html'):
                            # ✅ 修复：正确解析 HTML 表格结构，保持行列关系
                            try:
                                import re
                                html_text = table_data['html']
                                
                                # 方法1：使用 BeautifulSoup（如果可用）
                                try:
                                    from bs4 import BeautifulSoup
                                    soup = BeautifulSoup(html_text, 'html.parser')
                                    table = soup.find('table')
                                    if table:
                                        text_lines = []
                                        for tr in table.find_all('tr'):
                                            row_cells = []
                                            for td in tr.find_all(['td', 'th']):
                                                cell_text = td.get_text(strip=True)
                                                row_cells.append(cell_text)
                                            if row_cells:
                                                # 使用制表符分隔同一行的单元格
                                                text_lines.append('\t'.join(row_cells))
                                        
                                        if text_lines:
                                            # 使用换行符分隔不同行
                                            chunk_text = '\n'.join(text_lines)
                                            logger.debug(f"[任务ID: {task_id}] 表格块 {chunk.id}: 从 HTML (BeautifulSoup) 提取文本 ({len(text_lines)} 行)")
                                except ImportError:
                                    # 方法2：使用正则表达式解析（兜底方案）
                                    tr_pattern = r'<tr[^>]*>(.*?)</tr>'
                                    td_pattern = r'<t[dh][^>]*>(.*?)</t[dh]>'
                                    
                                    trs = re.findall(tr_pattern, html_text, re.DOTALL | re.IGNORECASE)
                                    if trs:
                                        text_lines = []
                                        for tr_content in trs:
                                            tds = re.findall(td_pattern, tr_content, re.DOTALL | re.IGNORECASE)
                                            if tds:
                                                row_cells = []
                                                for td in tds:
                                                    # 移除内嵌的 HTML 标签
                                                    cell_text = re.sub(r'<[^>]+>', '', td)
                                                    # 处理 HTML 实体
                                                    cell_text = cell_text.replace('&nbsp;', ' ').replace('&amp;', '&')
                                                    cell_text = ' '.join(cell_text.split()).strip()
                                                    row_cells.append(cell_text)
                                                
                                                if row_cells:
                                                    text_lines.append('\t'.join(row_cells))
                                        
                                        if text_lines:
                                            chunk_text = '\n'.join(text_lines)
                                            logger.debug(f"[任务ID: {task_id}] 表格块 {chunk.id}: 从 HTML (正则) 提取文本 ({len(text_lines)} 行)")
                            except Exception as e:
                                logger.warning(f"[任务ID: {task_id}] 表格块 {chunk.id}: 从 HTML 提取文本失败: {e}")
                                chunk_text = None  # 继续使用原始的 table_text
                        # 如果都没有，使用原始的 table_text（已在上面获取）
                        if chunk_text:
                            logger.debug(f"[任务ID: {task_id}] 表格块 {chunk.id} 最终文本长度: {len(chunk_text)}")
                    except Exception as e:
                        logger.warning(f"[任务ID: {task_id}] 表格块 {chunk.id} 提取完整内容失败: {e}，使用原始文本")
                        # 解析失败时确保 chunk_meta_dict 至少是空字典
                        chunk_meta_dict = {}
                
                # 跳过空内容分块
                if not (chunk_text or "").strip():
                    logger.warning(f"[任务ID: {task_id}] 分块 {chunk.id} 内容为空，跳过向量化与索引")
                    continue
                
                # ✅ 优化：记录表格块的处理信息
                if chunk.chunk_type == 'table':
                    logger.info(f"[任务ID: {task_id}] 表格块 {chunk.id} 向量化: 文本长度={len(chunk_text)}, "
                               f"包含单元格数据={bool(chunk_meta_dict.get('table_data', {}).get('cells'))}")
                
                # 生成向量（Ollama不可用时将返回空列表，允许继续索引文本）
                vector = vector_service.generate_embedding(chunk_text)
                vectorize_time = time.time() - chunk_start
                
                # 构建索引文档（✅ 新增：包含完整的 metadata 信息）
                # 从 chunk.meta 中提取完整的 metadata（包含 element_index、page_number、coordinates）
                # ✅ 注意：对于表格块，chunk_meta_dict 已经在上面提取过，需要确保已定义
                if chunk.chunk_type != 'table':
                    # 非表格块，需要重新解析 meta
                    chunk_meta_dict = {}
                    if chunk.meta:
                        try:
                            chunk_meta_dict = json.loads(chunk.meta) if isinstance(chunk.meta, str) else chunk.meta
                        except:
                            pass
                # 表格块的 chunk_meta_dict 已在上面提取，直接使用
                
                # 构建 metadata（包含所有关键信息）
                chunk_metadata = {
                    "chunk_index": i
                }
                # ✅ 添加 element_index 信息
                if chunk_meta_dict.get('element_index_start') is not None:
                    chunk_metadata['element_index_start'] = chunk_meta_dict.get('element_index_start')
                if chunk_meta_dict.get('element_index_end') is not None:
                    chunk_metadata['element_index_end'] = chunk_meta_dict.get('element_index_end')
                # ✅ 添加 page_number
                if chunk_meta_dict.get('page_number') is not None:
                    chunk_metadata['page_number'] = chunk_meta_dict.get('page_number')
                # ✅ 添加 coordinates
                if chunk_meta_dict.get('coordinates'):
                    chunk_metadata['coordinates'] = chunk_meta_dict.get('coordinates')
                
                chunk_doc = {
                    "document_id": document_id,
                    "chunk_id": chunk.id,
                    "knowledge_base_id": document.knowledge_base_id,
                    "category_id": document.category_id if hasattr(document, 'category_id') else None,
                    "content": chunk_text,
                    "chunk_type": chunk.chunk_type if hasattr(chunk, 'chunk_type') else "text",
                    "metadata": chunk_metadata,  # ✅ 使用完整的 metadata
                    "created_at": chunk.created_at.isoformat() if chunk.created_at else None
                }
                # 仅当有有效向量时写入
                if isinstance(vector, list) and len(vector) > 0:
                    chunk_doc["content_vector"] = vector
                docs_to_index.append(chunk_doc)
                
                index_time = 0.0
                
                success_count += 1
                
                if (i + 1) % 10 == 0 or i == len(db_chunks) - 1:  # 每10个或最后一个记录日志
                    logger.info(f"[任务ID: {task_id}] 向量化进度: {i+1}/{len(db_chunks)} "
                               f"(分块ID={chunk.id}, 向量维度={len(vector)}, "
                               f"向量化耗时={vectorize_time:.2f}秒, 索引耗时={index_time:.2f}秒)")
                else:
                    logger.debug(f"[任务ID: {task_id}] 分块 {chunk.id} 处理完成: "
                               f"向量维度={len(vector)}, 向量化={vectorize_time:.2f}秒, 索引={index_time:.2f}秒")
                
            except Exception as e:
                error_count += 1
                logger.error(f"[任务ID: {task_id}] 分块 {chunk.id} (索引 {i+1}/{len(chunks)}) 处理失败: {e}", exc_info=True)
                continue
            
            # 更新任务进度
            progress = 60 + (i / max(1, len(db_chunks))) * 30
            current_task.update_state(
                state="PROGRESS",
                meta={"current": int(progress), "total": 100, "status": f"向量化中 ({i+1}/{len(chunks)})"}
            )
        
        # 批量索引到 OpenSearch（默认不刷新，提升吞吐）
        try:
            bulk_index_start = time.time()
            opensearch_service.bulk_index_document_chunks_sync(docs_to_index)
            bulk_index_time = time.time() - bulk_index_start
            logger.info(f"[任务ID: {task_id}] 批量索引完成，耗时={bulk_index_time:.2f}秒，总文档={len(docs_to_index)}")
        except Exception as e:
            logger.error(f"[任务ID: {task_id}] 批量索引失败: {e}", exc_info=True)
            # 批量索引失败不再抛出，避免任务整体失败
            pass
        
        vectorize_total_time = time.time() - vectorize_start
        avg_time = (vectorize_total_time / len(db_chunks)) if len(db_chunks) else 0.0
        logger.info(f"[任务ID: {task_id}] 向量化完成: 成功={success_count}, 失败={error_count}, 总耗时={vectorize_total_time:.2f}秒, 平均耗时={avg_time:.2f}秒/分块")
        
        # 自动标签/摘要生成（向量化后、索引前，失败不阻塞）
        # 检查全局开关和知识库级别配置
        global_enabled = getattr(settings, 'ENABLE_AUTO_TAGGING', False)
        kb_enabled = getattr(document.knowledge_base, 'enable_auto_tagging', True) if document.knowledge_base else True
        
        if global_enabled and kb_enabled:
            try:
                logger.info(f"[任务ID: {task_id}] 开始生成自动标签/摘要（知识库ID={document.knowledge_base_id}, 知识库配置={kb_enabled}）")
                from app.services.auto_tagging_service import AutoTaggingService
                import asyncio
                tagging_service = AutoTaggingService(db)
                result = asyncio.run(tagging_service.generate_tags_and_summary(document_id))
                if result:
                    logger.info(f"[任务ID: {task_id}] 自动标签/摘要生成成功: keywords={result.get('keywords', [])}, summary={result.get('summary', '')[:50]}...")
                else:
                    logger.warning(f"[任务ID: {task_id}] 自动标签/摘要生成失败（不影响主流程）")
            except Exception as e:
                logger.warning(f"[任务ID: {task_id}] 自动标签/摘要生成异常（不影响主流程）: {e}", exc_info=True)
        else:
            logger.debug(f"[任务ID: {task_id}] 自动标签/摘要未启用（全局={global_enabled}, 知识库={kb_enabled}）")
        
        current_task.update_state(
            state="PROGRESS",
            meta={"current": 90, "total": 100, "status": "向量化完成，索引已建立"}
        )
        
        # 更新文档状态为索引中（OpenSearch索引已在上面的循环中建立）
        logger.debug(f"[任务ID: {task_id}] 步骤7/7: 完成处理，更新文档状态")
        document.status = DOC_STATUS_INDEXING
        
        # 提取文档目录（同步执行，不影响主流程）
        # 注意：TXT 文件不提取目录（纯文本文件通常没有结构化目录）
        try:
            from app.services.document_toc_service import DocumentTOCService
            import asyncio
            toc_service = DocumentTOCService(db)
            if is_pdf and document.file_path:
                toc_items = asyncio.run(toc_service.extract_toc_from_pdf(document_id, document.file_path))
                if toc_items:
                    logger.info(f"[任务ID: {task_id}] PDF目录提取成功，共 {len(toc_items)} 个目录项")
            elif is_docx and document.file_path:
                toc_items = asyncio.run(toc_service.extract_toc_from_docx(document_id, document.file_path))
                if toc_items:
                    logger.info(f"[任务ID: {task_id}] Word目录提取成功，共 {len(toc_items)} 个目录项")
            elif is_md:
                # MD 文件从 metadata 中的 heading_structure 提取目录
                doc_meta = document.meta or {}
                if isinstance(doc_meta, str):
                    import json as _json
                    try:
                        doc_meta = _json.loads(doc_meta)
                    except Exception:
                        doc_meta = {}
                heading_structure = doc_meta.get('heading_structure', [])
                if heading_structure:
                    toc_items = asyncio.run(toc_service.extract_toc_from_markdown(document_id, heading_structure))
                    if toc_items:
                        logger.info(f"[任务ID: {task_id}] Markdown目录提取成功，共 {len(toc_items)} 个目录项")
                else:
                    logger.debug(f"[任务ID: {task_id}] Markdown文件无标题结构，跳过目录提取")
            elif is_html:
                doc_meta = document.meta or {}
                if isinstance(doc_meta, str):
                    import json as _json
                    try:
                        doc_meta = _json.loads(doc_meta)
                    except Exception:
                        doc_meta = {}
                heading_structure = doc_meta.get('heading_structure', [])
                if heading_structure:
                    toc_items = asyncio.run(toc_service.extract_toc_from_html(document_id, heading_structure))
                    if toc_items:
                        logger.info(f"[任务ID: {task_id}] HTML目录提取成功，共 {len(toc_items)} 个目录项")
                else:
                    logger.debug(f"[任务ID: {task_id}] HTML文件无标题结构，跳过目录提取")
            elif is_pptx:
                # PPTX 文件从 metadata 中的 slides 列表提取目录
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
            # TXT 文件跳过目录提取（纯文本文件通常没有结构化目录）
        except Exception as e:
            logger.warning(f"[任务ID: {task_id}] 提取文档目录失败（不影响主流程）: {e}")
        document.processing_progress = 95.0
        db.commit()
        
        logger.info(f"[任务ID: {task_id}] OpenSearch索引建立完成: 共索引 {len(docs_to_index)} 个分块")
        
        # 更新文档状态为完成
        document.status = DOC_STATUS_COMPLETED
        document.processing_progress = 100.0
        db.commit()

        # 若不存在任何文档版本，则创建初始版本 v1（以原始文件为基准）
        try:
            from app.models.version import DocumentVersion
            existing_count = db.query(DocumentVersion).filter(
                DocumentVersion.document_id == document_id,
                DocumentVersion.is_deleted == False
            ).count()
            if existing_count == 0:
                initial_version = DocumentVersion(
                    document_id=document_id,
                    version_number=1,
                    version_type="auto",
                    description="初始版本",
                    file_path=document.file_path or "",
                    file_size=document.file_size,
                    file_hash=document.file_hash,
                )
                db.add(initial_version)
                db.commit()
                logger.info(f"[任务ID: {task_id}] 已创建文档初始版本 v1 (document_id={document_id})")
        except Exception as ver_err:
            logger.warning(f"[任务ID: {task_id}] 创建初始版本失败（不影响主流程）: {ver_err}")
        
        total_time = time.time() - download_start
        logger.info(f"[任务ID: {task_id}] ========== 文档 {document_id} 处理完成 ==========")
        logger.info(f"[任务ID: {task_id}] 处理统计: 总耗时={total_time:.2f}秒, "
                   f"文件大小={len(file_content)} bytes, 分块数={len(chunks)}, 已索引={len(docs_to_index)}条, "
                   f"文本长度={len(text_content)} 字符")
        
        # 实体提取已改为手动触发，不再自动执行
        # 用户可以在前端"知识图谱可视化"页面手动点击"提取实体"按钮触发
        
        current_task.update_state(
            state="SUCCESS",
            meta={"current": 100, "total": 100, "status": "文档处理完成"}
        )
        
        return {
            "status": "success",
            "message": "文档处理完成",
            "document_id": document_id,
            "chunks_count": len(chunks),
            "text_length": len(text_content),
            "processing_time": total_time
        }
        
    except Exception as e:
        # 获取错误消息，只使用异常消息本身，不包含类型名称
        error_msg = str(e) if str(e) else f"{type(e).__name__}"
        logger.error(f"[任务ID: {task_id}] ========== 文档 {document_id} 处理失败 ==========")
        logger.error(f"[任务ID: {task_id}] 错误信息: {type(e).__name__}: {error_msg}", exc_info=True)
        
        # 更新文档状态为失败
        if document:
            try:
                document.status = DOC_STATUS_FAILED
                document.error_message = error_msg
                db.commit()
                logger.debug(f"[任务ID: {task_id}] 文档状态已更新为失败")
            except Exception as db_err:
                logger.error(f"[任务ID: {task_id}] 更新文档状态失败: {db_err}", exc_info=True)
        
        # 更新任务状态为失败
        try:
            current_task.update_state(
                state="FAILURE",
                meta={"error": error_msg, "document_id": document_id}
            )
        except Exception as state_err:
            logger.error(f"[任务ID: {task_id}] 更新任务状态失败: {state_err}", exc_info=True)
        
        # 不抛出异常，避免 Celery 序列化异常时的问题
        # 即使配置了 ignore_result=True，Celery 仍然会尝试处理异常，可能导致序列化问题
        # 通过返回失败结果和更新状态，让调用方知道任务失败
        # 注意：由于 ignore_result=True，返回值不会被存储，但任务状态会更新为 FAILURE
        return {
            "status": "failed",
            "message": "文档处理失败",
            "document_id": document_id,
            "error": error_msg
        }
    finally:
        try:
            db.close()
            logger.debug(f"[任务ID: {task_id}] 数据库连接已关闭")
        except Exception as e:
            logger.warning(f"[任务ID: {task_id}] 关闭数据库连接时出错: {e}")

@celery_app.task(bind=True, ignore_result=True)
def reprocess_document_task(self, document_id: int):
    """重新向量化文档 - 根据文档修改功能设计实现"""
    db = SessionLocal()
    
    try:
        logger.info(f"开始重新向量化文档 {document_id}")
        
        # 获取文档
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"文档 {document_id} 不存在")
            raise Exception(f"文档 {document_id} 不存在")
        
        logger.info(f"找到文档 {document_id}: {document.original_filename}")
        
        # 更新文档状态为向量化中
        document.status = DOC_STATUS_VECTORIZING
        document.processing_progress = 50.0
        db.commit()
        
        # 获取所有块（不重新解析文件），按 chunk_index 排序
        db_chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index).all()
        
        logger.info(f"文档 {document_id} 共有 {len(db_chunks)} 个块需要重新向量化")
        
        # 向量化处理：从 MinIO 流式读取文本（避免内存占用）
        def _stream_chunk_texts_from_minio(doc_id: int):
            try:
                minio = MinioStorageService()
                files = minio.list_files("documents/")
                needle = f"/{doc_id}/parsed/chunks/chunks.jsonl.gz"
                target = None
                for fobj in files:
                    if fobj.get("object_name", "").endswith(needle):
                        target = fobj["object_name"]
                        break
                if not target:
                    logger.warning(f"重新向量化：未找到 MinIO 分块归档，文档ID={doc_id}")
                    return
                import gzip, json
                response = minio.client.get_object(minio.bucket_name, target)
                try:
                    with gzip.GzipFile(fileobj=response, mode='rb') as gz:
                        for line in gz:
                            try:
                                item = json.loads(line)
                                yield item.get("content", "")
                            except Exception:
                                yield ""
                finally:
                    try:
                        response.close(); response.release_conn()
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"重新向量化：从 MinIO 流式读取分块失败: {e}", exc_info=True)
                return

        vector_service = VectorService(db)
        opensearch_service = OpenSearchService()
        store_text = getattr(settings, 'STORE_CHUNK_TEXT_IN_DB', False)
        text_iter = _stream_chunk_texts_from_minio(document_id) if not store_text else None
        success_count = 0
        error_count = 0
        
        for i, chunk in enumerate(db_chunks):
            # ✅ 跳过图片分块：图片分块不进行文本向量化，图片向量化已在图片处理阶段完成
            if getattr(chunk, 'chunk_type', '').lower() == 'image':
                logger.debug(f"分块 {chunk.id} 是图片类型，跳过重新向量化（图片向量化已在图片处理阶段完成）")
                continue
            
            # 获取文本：优先从 MinIO 流式读取，否则从 DB
            if store_text:
                chunk_text = chunk.content or ""
            else:
                try:
                    chunk_text = next(text_iter) if text_iter else ""
                except (StopIteration, TypeError):
                    chunk_text = ""
            # 跳过空内容分块
            if not (chunk_text or "").strip():
                logger.warning(f"分块 {chunk.id} 内容为空，跳过重新向量化")
                continue
            try:
                # 生成向量
                vector = vector_service.generate_embedding(chunk_text)
                
                # 构建索引文档
                import json as _json
                meta_raw = getattr(chunk, 'meta', getattr(chunk, 'metadata', {}))
                meta_text = meta_raw if isinstance(meta_raw, str) else _json.dumps(meta_raw, ensure_ascii=False)
                chunk_doc = {
                    "document_id": document_id,
                    "chunk_id": chunk.id,
                    "knowledge_base_id": document.knowledge_base_id,
                    "category_id": document.category_id if hasattr(document, 'category_id') else None,
                    "content": chunk_text,
                    "chunk_type": getattr(chunk, 'chunk_type', "text"),
                    "metadata": meta_text,
                    "content_vector": vector,
                    "version": getattr(chunk, 'version', 1),
                    "created_at": chunk.created_at.isoformat() if chunk.created_at else None
                }
                
                # 更新OpenSearch索引
                opensearch_service.index_document_chunk_sync(chunk_doc)
                logger.debug(f"分块 {chunk.id} 重新向量化完成")
                success_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"分块 {chunk.id} 重新向量化失败: {e}", exc_info=True)
                continue
        
        logger.info(f"文档 {document_id} 重新向量化完成: 成功={success_count}, 失败={error_count}, 总块数={len(db_chunks)}")
        
        # 更新文档状态为完成
        document.status = DOC_STATUS_COMPLETED
        document.processing_progress = 100.0
        db.commit()
        
        return {
            "status": "success",
            "message": "重新向量化完成",
            "chunks_count": len(db_chunks),
            "success_count": success_count,
            "error_count": error_count
        }
        
    except Exception as e:
        # 获取错误消息，只使用异常消息本身，不包含类型名称
        error_msg = str(e) if str(e) else f"{type(e).__name__}"
        logger.error(f"重新向量化文档 {document_id} 失败: {type(e).__name__}: {error_msg}", exc_info=True)
        
        # 更新文档状态为失败
        if document:
            try:
                document.status = DOC_STATUS_FAILED
                document.error_message = error_msg
                db.commit()
            except Exception as db_err:
                logger.error(f"更新文档状态失败: {db_err}", exc_info=True)
        
        # 不抛出异常，避免 Celery 序列化异常时的问题
        # 通过返回失败结果和更新状态，让调用方知道任务失败
        return {
            "status": "failed",
            "message": "重新向量化失败",
            "document_id": document_id,
            "error": error_msg
        }
    finally:
        db.close()

@celery_app.task
def delete_document_task(document_id: int):
    """删除文档任务"""
    db = SessionLocal()
    try:
        # 获取文档
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return {"status": "error", "message": "文档不存在"}
        
        # 删除相关数据
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        
        # 软删除文档
        document.is_deleted = True
        db.commit()
        
        return {"status": "success", "message": "文档删除完成"}
        
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
