"""
Auto Tagging Service
自动标签/摘要服务 - 根据设计文档实现
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.ollama_service import OllamaService
from app.services.minio_storage_service import MinioStorageService
from app.config.settings import settings
from app.core.logging import logger
import json
import re
import gzip
from io import BytesIO
import datetime

class AutoTaggingService:
    """自动标签/摘要服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ollama_service = OllamaService(db)
    
    async def generate_tags_and_summary(
        self,
        document_id: int,
        max_content_length: int = 10000
    ) -> Optional[Dict[str, Any]]:
        """为文档生成标签和摘要"""
        try:
            document = self.db.query(Document).filter(
                Document.id == document_id,
                Document.is_deleted == False
            ).first()
            
            if not document:
                logger.error(f"文档不存在: {document_id}")
                return None
            
            # 收集所有chunk的文本内容
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id,
                DocumentChunk.is_deleted == False
            ).order_by(DocumentChunk.chunk_index).all()
            
            if not chunks:
                logger.warning(f"文档 {document_id} 没有分块数据")
                return None
            
            # 限制总长度
            text_content = ""
            store_text_in_db = getattr(settings, 'STORE_CHUNK_TEXT_IN_DB', False)
            
            if store_text_in_db:
                # 从数据库读取
                for chunk in chunks:
                    if chunk.content:
                        if len(text_content) + len(chunk.content) > max_content_length:
                            remaining = max_content_length - len(text_content)
                            text_content += chunk.content[:remaining]
                            break
                        text_content += chunk.content + "\n"
            else:
                # 从 MinIO 读取
                try:
                    minio = MinioStorageService()
                    # 构建 MinIO 路径：documents/YYYY/MM/document_id/parsed/chunks/chunks.jsonl.gz
                    created = getattr(document, 'created_at', None) or datetime.datetime.utcnow()
                    if isinstance(created, str):
                        # 如果是字符串，尝试解析
                        try:
                            created = datetime.datetime.fromisoformat(created.replace('Z', '+00:00'))
                        except:
                            created = datetime.datetime.utcnow()
                    year = created.strftime('%Y')
                    month = created.strftime('%m')
                    object_name = f"documents/{year}/{month}/{document_id}/parsed/chunks/chunks.jsonl.gz"
                    
                    # 尝试下载文件
                    try:
                        raw = minio.download_file(object_name)
                        with gzip.GzipFile(fileobj=BytesIO(raw), mode='rb') as gz:
                            for line in gz:
                                try:
                                    item = json.loads(line.decode('utf-8'))
                                    content = item.get('content', '')
                                    if content:
                                        if len(text_content) + len(content) > max_content_length:
                                            remaining = max_content_length - len(text_content)
                                            text_content += content[:remaining]
                                            break
                                        text_content += content + "\n"
                                except Exception as e:
                                    logger.debug(f"解析chunk JSON行失败: {e}")
                                    continue
                    except Exception as minio_err:
                        logger.warning(f"从MinIO读取chunk内容失败，尝试备用路径: {minio_err}")
                        # 备用方案：尝试从list_files查找
                        files = minio.list_files("documents/")
                        needle = f"/{document_id}/parsed/chunks/chunks.jsonl.gz"
                        target = None
                        for fobj in files:
                            if fobj.get("object_name", "").endswith(needle):
                                target = fobj["object_name"]
                                break
                        if target:
                            raw = minio.download_file(target)
                            with gzip.GzipFile(fileobj=BytesIO(raw), mode='rb') as gz:
                                for line in gz:
                                    try:
                                        item = json.loads(line.decode('utf-8'))
                                        content = item.get('content', '')
                                        if content:
                                            if len(text_content) + len(content) > max_content_length:
                                                remaining = max_content_length - len(text_content)
                                                text_content += content[:remaining]
                                                break
                                            text_content += content + "\n"
                                    except Exception:
                                        continue
                        else:
                            logger.warning(f"未找到MinIO中的chunk文件: {object_name}")
                except Exception as e:
                    logger.error(f"从MinIO读取chunk内容失败: {e}", exc_info=True)
            
            if not text_content.strip():
                logger.warning(f"文档 {document_id} 没有可用的文本内容")
                return None
            
            # 调用LLM生成标签和摘要
            prompt = f"""请为以下文档内容提取5个中文关键词，并生成2句摘要。

内容：
{text_content[:max_content_length]}

请以JSON格式返回，格式如下：
{{
    "keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"],
    "summary": "摘要文本（2句话）"
}}"""
            
            # 使用format="json"强制JSON输出
            response_text = await self.ollama_service.generate_text(
                prompt=prompt,
                format="json"
            )
            
            # 解析响应
            result = self._parse_llm_response(response_text)
            
            if result:
                # 更新文档metadata
                metadata = document.meta or {}
                if not isinstance(metadata, dict):
                    metadata = {}
                metadata["auto_keywords"] = result.get("keywords", [])
                metadata["auto_summary"] = result.get("summary", "")
                document.meta = metadata
                
                # 标记JSON列已修改（SQLAlchemy需要这个来检测JSON列的变更）
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(document, "meta")
                
                self.db.commit()
                # 刷新对象以确保更新生效
                self.db.refresh(document)
                
                # 验证更新是否成功
                updated_meta = document.meta or {}
                logger.info(f"文档 {document_id} 自动标签/摘要生成成功, keywords数量: {len(metadata.get('auto_keywords', []))}, summary长度: {len(metadata.get('auto_summary', ''))}")
                logger.info(f"文档 {document_id} 更新后验证 - 包含auto_keywords: {'auto_keywords' in updated_meta}, 包含auto_summary: {'auto_summary' in updated_meta}")
                logger.debug(f"文档 {document_id} metadata内容: {updated_meta}")
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"生成自动标签/摘要失败: document_id={document_id}, error={e}", exc_info=True)
            return None
    
    def _parse_llm_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """解析LLM响应"""
        try:
            # 尝试直接解析JSON
            if response_text.strip().startswith('{'):
                return json.loads(response_text)
            
            # 尝试提取JSON部分
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            # 如果无法解析，尝试从文本中提取
            keywords_match = re.search(r'关键词[：:]\s*([^\n]+)', response_text)
            summary_match = re.search(r'摘要[：:]\s*([^\n]+)', response_text)
            
            if keywords_match or summary_match:
                keywords = []
                if keywords_match:
                    keywords_str = keywords_match.group(1)
                    keywords = [k.strip() for k in keywords_str.split('、') if k.strip()][:5]
                
                summary = ""
                if summary_match:
                    summary = summary_match.group(1).strip()
                
                return {
                    "keywords": keywords,
                    "summary": summary
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"解析LLM响应失败: {e}, response_text={response_text[:200]}")
            return None
    
    async def regenerate_tags_and_summary(self, document_id: int) -> Optional[Dict[str, Any]]:
        """重新生成标签和摘要"""
        return await self.generate_tags_and_summary(document_id)
