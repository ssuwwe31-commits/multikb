"""
Document TOC Service
文档目录服务
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.document_toc import DocumentTOC
from app.core.logging import logger
import PyPDF2
import io


class DocumentTOCService:
    """文档目录服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def extract_toc_from_pdf(self, document_id: int, file_path: str) -> List[DocumentTOC]:
        """从PDF提取目录"""
        try:
            from app.services.minio_storage_service import MinioStorageService
            minio = MinioStorageService()
            
            # 从MinIO下载PDF文件
            file_data = minio.client.get_object(minio.bucket_name, file_path)
            pdf_bytes = file_data.read()
            
            # 使用PyPDF2解析PDF
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            
            # 提取书签（目录）- 先收集所有书签项
            toc_data_list = []
            if pdf_reader.outline:
                self._collect_outline_items(pdf_reader.outline, toc_data_list, pdf_reader)
            
            # 构建层级关系（使用临时索引，类似 Word 的处理方式）
            if toc_data_list:
                # 构建 parent_index 关系
                level_stack = []  # [(level, index), ...]
                for i, data in enumerate(toc_data_list):
                    level = data['level']
                    
                    # 从栈中找到合适的父级（级别小于当前级别的最后一个）
                    parent_index = None
                    while level_stack and level_stack[-1][0] >= level:
                        level_stack.pop()
                    
                    if level_stack:
                        parent_index = level_stack[-1][1]
                    
                    # 更新 parent_index
                    toc_data_list[i]['parent_index'] = parent_index
                    
                    # 将当前项的索引加入栈
                    level_stack.append((level, i))
            
            # 保存到数据库
            if toc_data_list:
                # 先删除旧的目录
                self.db.query(DocumentTOC).filter(
                    DocumentTOC.document_id == document_id
                ).delete()
                
                # 创建所有目录项（先不设置 parent_id）
                toc_items = []
                for data in toc_data_list:
                    toc = DocumentTOC(
                        document_id=document_id,
                        level=data['level'],
                        title=data['title'],
                        page_number=data.get('page_number'),
                        position=data['position'],
                        parent_id=None,  # 稍后设置
                        element_index=None,
                        paragraph_index=None,
                        start_chunk_id=None
                    )
                    toc_items.append(toc)
                    self.db.add(toc)
                
                # 刷新以获取所有ID
                self.db.flush()
                
                # 现在设置 parent_id（使用实际的ID）
                for i, data in enumerate(toc_data_list):
                    if data.get('parent_index') is not None:
                        toc_items[i].parent_id = toc_items[data['parent_index']].id
                
                # 提交以保存目录项
                self.db.commit()
                logger.info(f"PDF目录提取成功，文档ID: {document_id}, 目录项数: {len(toc_items)}")
            else:
                # 如果没有目录项，也要删除旧目录
                self.db.query(DocumentTOC).filter(
                    DocumentTOC.document_id == document_id
                ).delete()
                self.db.commit()
                return []
            
            return toc_items
            
        except Exception as e:
            logger.error(f"提取PDF目录失败: {e}", exc_info=True)
            self.db.rollback()
            return []
    
    def _collect_outline_items(self, outline: Any, toc_data_list: List[Dict], pdf_reader: PyPDF2.PdfReader, level: int = 1):
        """递归收集PDF书签项"""
        try:
            for item in outline:
                if isinstance(item, list):
                    # 嵌套的书签，递归处理
                    self._collect_outline_items(item, toc_data_list, pdf_reader, level + 1)
                else:
                    # 单个书签项
                    title = item.title if hasattr(item, 'title') else str(item)
                    if not title or not title.strip():
                        continue
                    
                    # 尝试获取页码
                    page_num = None
                    try:
                        if hasattr(item, 'page') and item.page:
                            # PyPDF2 中，page 可能是页码索引或页面对象
                            if isinstance(item.page, int):
                                page_num = item.page + 1  # PyPDF2 页码从0开始
                            elif hasattr(item.page, 'get_object'):
                                # 通过页面对象查找页码
                                page_obj = item.page.get_object()
                                if hasattr(page_obj, 'indirect_reference'):
                                    for i, page in enumerate(pdf_reader.pages):
                                        if hasattr(page, 'indirect_reference') and page.indirect_reference == page_obj.indirect_reference:
                                            page_num = i + 1
                                            break
                    except Exception as e:
                        logger.debug(f"获取PDF书签页码失败: {e}")
                    
                    # 添加到列表
                    toc_data_list.append({
                        'level': level,
                        'title': title.strip()[:500],  # 限制长度
                        'page_number': page_num,
                        'position': len(toc_data_list)  # 使用当前列表长度作为位置
                    })
        except Exception as e:
            logger.warning(f"收集PDF书签项失败: {e}")
    
    async def get_document_toc(self, document_id: int) -> List[Dict[str, Any]]:
        """获取文档目录（树形结构）"""
        try:
            toc_items = self.db.query(DocumentTOC).filter(
                DocumentTOC.document_id == document_id,
                DocumentTOC.is_deleted == False
            ).order_by(DocumentTOC.position).all()
            
            # 构建树形结构
            toc_dict = {}
            root_items = []
            
            for item in toc_items:
                toc_dict[item.id] = {
                    "id": item.id,
                    "level": item.level,
                    "title": item.title,
                    "page_number": item.page_number,
                    "position": item.position,
                    "children": []
                }
            
            for item in toc_items:
                if item.parent_id is None:
                    root_items.append(toc_dict[item.id])
                else:
                    parent = toc_dict.get(item.parent_id)
                    if parent:
                        parent["children"].append(toc_dict[item.id])
            
            return root_items
            
        except Exception as e:
            logger.error(f"获取文档目录失败: {e}", exc_info=True)
            return []
    
    def _get_heading_level(self, style_name: str) -> Optional[int]:
        """从样式名称提取标题级别"""
        if not style_name:
            return None
        
        style_lower = style_name.lower()
        
        # 英文样式：Heading 1, Heading 2, ...
        if style_name.startswith('Heading '):
            try:
                level = int(style_name.replace('Heading ', '').strip())
                if 1 <= level <= 6:
                    return level
            except ValueError:
                pass
        
        # 中文样式：标题1, 标题2, ...
        if '标题' in style_name:
            # 提取数字
            import re
            match = re.search(r'标题\s*(\d+)', style_name)
            if match:
                try:
                    level = int(match.group(1))
                    if 1 <= level <= 6:
                        return level
                except ValueError:
                    pass
        
        # 其他可能的标题样式：Title, 标题, 等
        if 'title' in style_lower or style_lower == '标题':
            return 1
        
        return None
    
    async def extract_toc_from_docx(self, document_id: int, file_path: str) -> List[DocumentTOC]:
        """从Word文档提取目录（基于标题样式，支持中英文样式）"""
        try:
            from app.services.minio_storage_service import MinioStorageService
            from docx import Document
            import io
            
            minio = MinioStorageService()
            
            # 从MinIO下载文件
            file_data = minio.client.get_object(minio.bucket_name, file_path)
            docx_bytes = file_data.read()
            
            # 使用python-docx解析
            doc = Document(io.BytesIO(docx_bytes))
            
            # 先收集所有标题段落（记录段落索引，用于后续匹配）
            heading_paragraphs = []
            paragraph_index = 0
            for paragraph in doc.paragraphs:
                style_name = paragraph.style.name
                level = self._get_heading_level(style_name)
                
                if level is not None:
                    title = paragraph.text.strip()
                    if title:
                        heading_paragraphs.append({
                            'level': level,
                            'title': title[:500],
                            'position': len(heading_paragraphs),
                            'paragraph_index': paragraph_index  # 记录段落索引
                        })
                paragraph_index += 1
            
            # 构建层级关系（使用索引，稍后转换为ID）
            # 先为每个标题分配临时索引，构建 parent_index 关系
            toc_data_list = []
            level_stack = []  # [(level, index), ...]
            
            for para_data in heading_paragraphs:
                level = para_data['level']
                title = para_data['title']
                position = para_data['position']
                
                # 从栈中找到合适的父级（级别小于当前级别的最后一个）
                parent_index = None
                while level_stack and level_stack[-1][0] >= level:
                    level_stack.pop()
                
                if level_stack:
                    parent_index = level_stack[-1][1]
                
                # 存储数据（包括 parent_index 和段落索引，稍后转换为 parent_id）
                toc_data_list.append({
                    'level': level,
                    'title': title,
                    'position': position,
                    'parent_index': parent_index,
                    'paragraph_index': para_data.get('paragraph_index')  # 传递段落索引
                })
                
                # 将当前项的索引加入栈
                level_stack.append((level, len(toc_data_list) - 1))
            
            # 保存到数据库
            if toc_data_list:
                # 先删除旧的目录
                self.db.query(DocumentTOC).filter(
                    DocumentTOC.document_id == document_id
                ).delete()
                
                # 创建所有目录项（先不设置 parent_id）
                toc_items = []
                for data in toc_data_list:
                    toc = DocumentTOC(
                        document_id=document_id,
                        level=data['level'],
                        title=data['title'],
                        page_number=None,
                        position=data['position'],
                        parent_id=None,  # 稍后设置
                        paragraph_index=data.get('paragraph_index')  # 记录段落索引（仅用于记录，不用于关联）
                    )
                    toc_items.append(toc)
                    self.db.add(toc)
                
                # 刷新以获取所有ID
                self.db.flush()
                
                # 现在设置 parent_id（使用实际的ID）
                for i, data in enumerate(toc_data_list):
                    if data['parent_index'] is not None:
                        toc_items[i].parent_id = toc_items[data['parent_index']].id
                
                # 提交以保存目录项
                self.db.commit()
                logger.info(f"Word目录提取成功，文档ID: {document_id}, 目录项数: {len(toc_items)}")
            else:
                # 如果没有目录项，也要删除旧目录
                self.db.query(DocumentTOC).filter(
                    DocumentTOC.document_id == document_id
                ).delete()
                self.db.commit()
                return []
            
            return toc_items
            
        except Exception as e:
            logger.error(f"提取Word目录失败: {e}", exc_info=True)
            self.db.rollback()
            return []
    
    async def extract_toc_from_markdown(self, document_id: int, heading_structure: List[Dict[str, Any]]) -> List[DocumentTOC]:
        """从 Markdown 文档的标题结构提取目录"""
        try:
            # 删除旧目录
            self.db.query(DocumentTOC).filter(
                DocumentTOC.document_id == document_id
            ).delete()
            
            if not heading_structure:
                self.db.commit()
                return []
            
            # 构建层级关系
            toc_data_list = []
            level_stack = []  # [(level, index), ...]
            
            for heading in heading_structure:
                level = heading.get('level', 1)
                title = heading.get('text', '').strip()
                line = heading.get('line', 0)
                
                if not title:
                    continue
                
                # 从栈中找到合适的父级
                parent_index = None
                while level_stack and level_stack[-1][0] >= level:
                    level_stack.pop()
                
                if level_stack:
                    parent_index = level_stack[-1][1]
                
                toc_data_list.append({
                    'level': level,
                    'title': title[:500],
                    'position': len(toc_data_list),
                    'parent_index': parent_index,
                    'line': line,
                })
                
                level_stack.append((level, len(toc_data_list) - 1))
            
            # 转换为数据库记录
            toc_items = []
            id_map = {}  # 临时索引 -> 数据库ID映射
            
            for i, data in enumerate(toc_data_list):
                toc_item = DocumentTOC(
                    document_id=document_id,
                    level=data['level'],
                    title=data['title'],
                    position=data['position'],
                    element_index=data.get('line'),
                    page_number=None,  # MD 文件没有页码
                    parent_id=id_map.get(data['parent_index']) if data['parent_index'] is not None else None,
                )
                self.db.add(toc_item)
                self.db.flush()  # 获取ID
                # 使用列表索引作为键（与 parent_index 对应）
                id_map[i] = toc_item.id
                toc_items.append(toc_item)
            
            self.db.commit()
            logger.info(f"Markdown目录提取成功，共 {len(toc_items)} 个目录项")
            return toc_items
            
        except Exception as e:
            logger.error(f"提取Markdown目录失败: {e}", exc_info=True)
            self.db.rollback()
            return []
    
    async def extract_toc_from_html(self, document_id: int, heading_structure: List[Dict[str, Any]]) -> List[DocumentTOC]:
        """从 HTML 标题结构提取目录"""
        try:
            self.db.query(DocumentTOC).filter(
                DocumentTOC.document_id == document_id
            ).delete()
            
            if not heading_structure:
                self.db.commit()
                return []
            
            toc_items: List[DocumentTOC] = []
            id_map: Dict[int, int] = {}
            level_stack: List[Tuple[int, int]] = []
            
            for idx, heading in enumerate(heading_structure):
                level = int(heading.get('level', 1) or 1)
                title = (heading.get('title') or heading.get('text') or '').strip()
                if not title:
                    continue
                
                parent_idx = None
                while level_stack and level_stack[-1][0] >= level:
                    level_stack.pop()
                if level_stack:
                    parent_idx = level_stack[-1][1]
                
                toc_item = DocumentTOC(
                    document_id=document_id,
                    level=level,
                    title=title[:500],
                    position=len(toc_items),
                    parent_id=id_map.get(parent_idx) if parent_idx is not None else None,
                    page_number=None,
                    element_index=heading.get('position'),
                )
                self.db.add(toc_item)
                self.db.flush()
                id_map[len(toc_items)] = toc_item.id
                level_stack.append((level, len(toc_items)))
                toc_items.append(toc_item)
            
            self.db.commit()
            logger.info(f"HTML目录提取成功: 文档ID={document_id}, 目录项数={len(toc_items)}")
            return toc_items
        except Exception as e:
            logger.error(f"提取HTML目录失败: {e}", exc_info=True)
            self.db.rollback()
            return []
    
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
                # 注意：使用 element_index 存储幻灯片编号（因为 DocumentTOC 模型没有 slide_number 字段）
                toc_item = DocumentTOC(
                    document_id=document_id,
                    level=1,
                    title=title[:500],  # 限制长度
                    position=len(toc_items),
                    parent_id=None,  # PPTX 目录暂不支持层级关系
                    page_number=None,  # PPTX 无页码概念
                    element_index=slide_number,  # 使用 element_index 存储幻灯片编号
                )
                self.db.add(toc_item)
                toc_items.append(toc_item)
            
            # 批量保存
            if toc_items:
                self.db.commit()
                logger.info(f"PPTX目录提取成功: 文档ID={document_id}, 目录项数={len(toc_items)}")
            
            return toc_items
        except Exception as e:
            logger.error(f"PPTX目录提取失败: {e}", exc_info=True)
            self.db.rollback()
            return []
