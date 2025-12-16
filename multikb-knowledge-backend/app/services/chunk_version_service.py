"""
Chunk Version Service
根据文档修改功能设计实现块版本管理服务
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.chunk import DocumentChunk
from app.models.chunk_version import ChunkVersion
from app.schemas.chunk_version import ChunkVersionCreate, ChunkVersionUpdate, ChunkVersionResponse, ChunkVersionListResponse, ChunkRevertRequest, ChunkRevertResponse
from app.services.base import BaseService
from app.core.logging import logger
from app.core.exceptions import CustomException, ErrorCode

class ChunkVersionService(BaseService[ChunkVersion]):
    """块版本服务 - 严格按照文档修改功能设计实现"""
    
    def __init__(self, db: Session):
        super().__init__(db, ChunkVersion)
    
    def create_chunk_version(self, chunk_id: int, version_data: ChunkVersionCreate) -> ChunkVersionResponse:
        """创建块版本 - 根据设计文档实现"""
        try:
            logger.info(f"创建块版本: chunk_id={chunk_id}")
            
            # 验证块是否存在
            chunk = self.db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
            if not chunk:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"块 {chunk_id} 不存在"
                )
            
            # 获取当前最大版本号
            last_version = self.db.query(ChunkVersion).filter(
                ChunkVersion.chunk_id == chunk_id
            ).order_by(ChunkVersion.version_number.desc()).first()
            
            version_number = (last_version.version_number + 1) if last_version else 1
            
            # 创建版本记录（兼容 dict 或 Pydantic 对象）
            # ✅ 修复：统一使用 meta 属性，处理 metadata 字段
            def _get(obj, attr: str, default=None):
                try:
                    # 兼容 pydantic BaseModel / 对象 / 字典
                    if isinstance(obj, dict):
                        return obj.get(attr, default)
                    value = getattr(obj, attr)
                    return value if value is not None else default
                except Exception:
                    return default

            version_meta = _get(version_data, 'meta')
            if not version_meta:
                version_meta = _get(version_data, 'metadata', '{}')
            # ✅ 统一序列化为字符串，避免 Pydantic from_orm 校验失败
            try:
                if version_meta is None:
                    version_meta = '{}'
                elif not isinstance(version_meta, str):
                    import json as _json
                    version_meta = _json.dumps(version_meta, ensure_ascii=False)
            except Exception:
                version_meta = str(version_meta)

            content_value = _get(version_data, 'content', '')
            if content_value is None:
                content_value = ''
            else:
                content_value = str(content_value)
            modified_by_value = _get(version_data, 'modified_by', 'system')
            version_comment_value = _get(version_data, 'version_comment', '')

            version = ChunkVersion(
                chunk_id=chunk_id,
                version_number=version_number,
                content=content_value,
                meta=version_meta,  # ✅ 使用 meta 属性
                modified_by=modified_by_value,
                version_comment=version_comment_value,
                created_at=datetime.now()
            )
            
            self.db.add(version)
            self.db.commit()
            self.db.refresh(version)
            
            logger.info(f"块版本创建成功: chunk_id={chunk_id}, version={version_number}")
            return ChunkVersionResponse.from_orm(version)
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"创建块版本错误: {e}", exc_info=True)
            self.db.rollback()
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"创建块版本失败: {str(e)}"
            )
    
    def get_chunk_versions(self, chunk_id: int, skip: int = 0, limit: int = 100) -> ChunkVersionListResponse:
        """获取块版本列表 - 根据设计文档实现"""
        try:
            logger.info(f"获取块版本列表: chunk_id={chunk_id}")
            
            # 验证块是否存在
            chunk = self.db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
            if not chunk:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"块 {chunk_id} 不存在"
                )
            
            # 获取版本列表
            versions = self.db.query(ChunkVersion).filter(
                ChunkVersion.chunk_id == chunk_id
            ).order_by(ChunkVersion.version_number.desc()).offset(skip).limit(limit).all()
            
            total_versions = self.db.query(ChunkVersion).filter(
                ChunkVersion.chunk_id == chunk_id
            ).count()
            
            version_responses = [ChunkVersionResponse.from_orm(v) for v in versions]
            
            logger.info(f"获取块版本列表成功: chunk_id={chunk_id}, 版本数={len(version_responses)}")
            return ChunkVersionListResponse(
                chunk_id=chunk_id,
                total_versions=total_versions,
                versions=version_responses
            )
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"获取块版本列表错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"获取块版本列表失败: {str(e)}"
            )
    
    def get_chunk_version(self, chunk_id: int, version_number: int) -> Optional[ChunkVersionResponse]:
        """获取特定版本 - 根据设计文档实现"""
        try:
            logger.info(f"获取块版本: chunk_id={chunk_id}, version={version_number}")
            
            version = self.db.query(ChunkVersion).filter(
                ChunkVersion.chunk_id == chunk_id,
                ChunkVersion.version_number == version_number
            ).first()
            
            if not version:
                logger.warning(f"版本不存在: chunk_id={chunk_id}, version={version_number}")
                return None
            
            logger.info(f"获取块版本成功: chunk_id={chunk_id}, version={version_number}")
            return ChunkVersionResponse.from_orm(version)
            
        except Exception as e:
            logger.error(f"获取块版本错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"获取块版本失败: {str(e)}"
            )
    
    def revert_chunk_to_version(self, chunk_id: int, revert_request: ChunkRevertRequest) -> ChunkRevertResponse:
        """回退块到指定版本 - 根据设计文档实现"""
        try:
            logger.info(f"回退块版本: chunk_id={chunk_id}, target_version={revert_request.target_version}")
            
            # 验证块是否存在
            chunk = self.db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
            if not chunk:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"块 {chunk_id} 不存在"
                )
            
            # 验证目标版本是否存在
            target_version = self.db.query(ChunkVersion).filter(
                ChunkVersion.chunk_id == chunk_id,
                ChunkVersion.version_number == revert_request.target_version
            ).first()
            
            if not target_version:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"目标版本 {revert_request.target_version} 不存在"
                )
            
            # 保存当前版本
            current_version = chunk.version
            current_content = chunk.content
            # ✅ 修复：统一使用 meta 属性（ChunkVersion 模型有 meta 字段）
            current_metadata = chunk.meta if hasattr(chunk, 'meta') and chunk.meta else (getattr(chunk, 'metadata', None) or '{}')
            
            # 创建当前版本的版本记录
            current_version_record = ChunkVersion(
                chunk_id=chunk_id,
                version_number=current_version + 1,
                content=current_content,
                meta=current_metadata,  # ✅ 使用 meta 属性
                modified_by="system",
                version_comment=f"回退前的版本保存",
                created_at=datetime.now()
            )
            
            self.db.add(current_version_record)
            
            # ✅ 在回退前保存表格标识符（table_id/table_group_uid 不会因回退而改变）
            preserved_table_ids = {}
            try:
                if hasattr(chunk, 'meta') and chunk.meta:
                    current_meta_str = chunk.meta if isinstance(chunk.meta, str) else json.dumps(chunk.meta, ensure_ascii=False)
                    current_meta_dict = json.loads(current_meta_str) if isinstance(current_meta_str, str) else (current_meta_str if isinstance(current_meta_str, dict) else {})
                    preserved_table_ids['table_id'] = current_meta_dict.get('table_id') or current_meta_dict.get('table_uid')
                    preserved_table_ids['table_group_uid'] = current_meta_dict.get('table_group_uid')
            except Exception:
                pass
            
            # 恢复目标版本（先回退文本和 metadata）
            chunk.content = target_version.content
            # ✅ 修复：ChunkVersion 模型使用 meta 属性（映射到数据库的 metadata 列）
            target_meta = target_version.meta if target_version.meta else '{}'
            chunk.meta = target_meta  # ✅ DocumentChunk 也使用 meta 属性
            
            # ✅ 恢复表格标识符（如果目标版本 meta 中没有，使用保存的标识符）
            try:
                if preserved_table_ids.get('table_id') or preserved_table_ids.get('table_group_uid'):
                    target_meta_dict = json.loads(target_meta) if isinstance(target_meta, str) else (target_meta if isinstance(target_meta, dict) else {})
                    if not target_meta_dict.get('table_id') and preserved_table_ids.get('table_id'):
                        target_meta_dict['table_id'] = preserved_table_ids['table_id']
                    if not target_meta_dict.get('table_group_uid') and preserved_table_ids.get('table_group_uid'):
                        target_meta_dict['table_group_uid'] = preserved_table_ids['table_group_uid']
                    chunk.meta = json.dumps(target_meta_dict, ensure_ascii=False)
            except Exception:
                pass
            
            # ✅ 修复：更新版本号和版本ID，确保一致性
            chunk.version = revert_request.target_version
            chunk.chunk_version_id = target_version.id  # ✅ 指向目标版本的记录ID
            chunk.last_modified_at = datetime.now()
            chunk.modification_count += 1
            chunk.last_modified_by = "system"
            
            self.db.commit()
            
            # ✅ 修复：重新向量化并更新所有数据库（MySQL、OpenSearch、MinIO）
            try:
                # 1. 重新向量化
                from app.services.vector_service import VectorService
                from app.services.opensearch_service import OpenSearchService
                from app.services.minio_storage_service import MinioStorageService
                import json
                
                vector_service = VectorService(self.db)
                osvc = OpenSearchService()
                minio_service = MinioStorageService()
                
                # 生成新向量
                content_vector = vector_service.generate_embedding(chunk.content or "") if (chunk.content or "").strip() else []
                
                # 2. 解析 metadata
                chunk_meta_dict = {}
                try:
                    if hasattr(chunk, 'meta') and chunk.meta:
                        if isinstance(chunk.meta, str):
                            chunk_meta_dict = json.loads(chunk.meta)
                        else:
                            chunk_meta_dict = chunk.meta
                    elif hasattr(chunk, 'metadata') and chunk.metadata:
                        if isinstance(chunk.metadata, str):
                            chunk_meta_dict = json.loads(chunk.metadata)
                        else:
                            chunk_meta_dict = chunk.metadata
                except (json.JSONDecodeError, TypeError, AttributeError):
                    chunk_meta_dict = {}
                
                # 标记为已编辑（回退也是一种编辑）
                chunk_meta_dict["edited"] = True
                chunk_meta_dict["reverted"] = True  # 标记为回退
                
                # 3. 获取文档信息（用于 OpenSearch 索引）
                from app.models.document import Document
                document = self.db.query(Document).filter(
                    Document.id == chunk.document_id
                ).first()
                
                # 4. 更新 OpenSearch
                osvc.index_document_chunk_sync({
                    "document_id": chunk.document_id,
                    "knowledge_base_id": document.knowledge_base_id if document else None,
                    "category_id": document.category_id if document else None,
                    "chunk_id": chunk.id,
                    "content": chunk.content or "",
                    "chunk_type": chunk.chunk_type or 'text',
                    "metadata": chunk_meta_dict,
                    "created_at": chunk.created_at.isoformat() if chunk.created_at else None,
                    "content_vector": content_vector,
                })
                logger.info(f"✅ OpenSearch 更新成功: chunk_id={chunk_id}")
                
                # 5. 更新 MinIO
                try:
                    minio_service.update_chunk_content(
                        document_id=chunk.document_id,
                        chunk_index=chunk.chunk_index,
                        new_content=chunk.content or "",
                        chunk_meta=chunk_meta_dict
                    )
                    logger.info(f"✅ MinIO 更新成功: chunk_id={chunk_id}, chunk_index={chunk.chunk_index}")
                except Exception as minio_err:
                    logger.warning(f"⚠️ MinIO 更新失败（不影响回退流程）: {minio_err}", exc_info=True)
                
                # 6. 如为表格块，更新 document_tables（表格懒加载源数据）
                try:
                    if (chunk.chunk_type or '').lower() == 'table':
                        from sqlalchemy import text as _sql_text
                        table_meta = chunk_meta_dict if isinstance(chunk_meta_dict, dict) else {}
                        table_data = table_meta.get('table_data') if isinstance(table_meta, dict) else None
                        cells = table_data.get('cells') if isinstance(table_data, dict) else None
                        
                        # ✅ 如果 meta 中没有 cells，从 content 解析（制表符分隔）
                        if not isinstance(cells, list) or not cells:
                            content_text = chunk.content or ""
                            if content_text and '\t' in content_text:
                                lines = content_text.split('\n')
                                cells = []
                                for line in lines:
                                    if line.strip():
                                        cells.append([cell.strip() for cell in line.split('\t')])
                                if cells:
                                    logger.info(f"✅ 回退：从 content 解析表格数据，行数={len(cells)}")
                        
                        if isinstance(cells, list) and cells:
                            n_rows = len(cells)
                            n_cols = max((len(r) if isinstance(r, list) else 0) for r in cells) if n_rows > 0 else 0
                            cells_json = json.dumps(cells, ensure_ascii=False)
                            headers_json = None
                            if isinstance(table_data, dict) and isinstance(table_data.get('headers'), (list, dict)):
                                headers_json = json.dumps(table_data.get('headers'), ensure_ascii=False)
                            
                            # ✅ 从 chunk.meta 获取 table_id/table_group_uid（已在回退时恢复）
                            # 如果 table_meta 中没有，chunk.meta 中应该已经有了（因为上面已经恢复了）
                            table_uid = table_meta.get('table_id') or table_meta.get('table_uid')
                            table_group_uid = table_meta.get('table_group_uid')
                            
                            # 如果还是空，从 chunk.meta 读取（应该已经恢复了）
                            if not table_uid or not table_group_uid:
                                try:
                                    chunk_meta_for_ids = json.loads(chunk.meta) if isinstance(chunk.meta, str) else (chunk.meta if isinstance(chunk.meta, dict) else {})
                                    table_uid = table_uid or chunk_meta_for_ids.get('table_id') or chunk_meta_for_ids.get('table_uid')
                                    table_group_uid = table_group_uid or chunk_meta_for_ids.get('table_group_uid')
                                except Exception:
                                    pass

                            if table_group_uid:
                                # 将整表 cells 拆分写回各个分片
                                part_rows = self.db.execute(
                                    _sql_text("SELECT table_uid, part_index, row_range, n_rows FROM document_tables WHERE table_group_uid=:g ORDER BY part_index"),
                                    {"g": table_group_uid}
                                ).fetchall()
                                if part_rows:
                                    def parse_range(s):
                                        try:
                                            if s and isinstance(s, str) and '-' in s:
                                                a,b = s.split('-',1)
                                                return int(a), int(b)
                                        except Exception:
                                            pass
                                        return None
                                    total = len(cells)
                                    for (uid, pidx, rr, pnrows) in part_rows:
                                        rng = parse_range(rr)
                                        if rng:
                                            start, end = rng
                                            start = max(0, start)
                                            end = min(total-1, end)
                                            slice_rows = cells[start:end+1] if end>=start else []
                                        else:
                                            count = int(pnrows or 0)
                                            assigned = self.db.execute(_sql_text("SELECT SUM(n_rows) FROM document_tables WHERE table_group_uid=:g AND part_index<:i"), {"g": table_group_uid, "i": pidx}).scalar() or 0
                                            slice_rows = cells[assigned:assigned+count]

                                        c_json = json.dumps(slice_rows, ensure_ascii=False)
                                        params = {"c": c_json, "r": len(slice_rows), "n": n_cols, "u": uid}
                                        if headers_json is not None and pidx == 0:
                                            self.db.execute(_sql_text("UPDATE document_tables SET cells_json=:c, n_rows=:r, n_cols=:n, headers_json=:h WHERE table_uid=:u"), {**params, "h": headers_json})
                                        else:
                                            self.db.execute(_sql_text("UPDATE document_tables SET cells_json=:c, n_rows=:r, n_cols=:n WHERE table_uid=:u"), params)
                                    self.db.commit()
                                    logger.info(f"✅ 回退：表格组更新成功(按分片写回): group={table_group_uid}, rows={n_rows}, cols={n_cols}")
                            elif table_uid:
                                params = {"c": cells_json, "r": n_rows, "n": n_cols, "u": table_uid}
                                if headers_json is not None:
                                    self.db.execute(_sql_text("UPDATE document_tables SET cells_json=:c, n_rows=:r, n_cols=:n, headers_json=:h WHERE table_uid=:u"), {**params, "h": headers_json})
                                else:
                                    self.db.execute(_sql_text("UPDATE document_tables SET cells_json=:c, n_rows=:r, n_cols=:n WHERE table_uid=:u"), params)
                                self.db.commit()
                                logger.info(f"✅ 回退：表格更新成功: table_uid={table_uid}, rows={n_rows}, cols={n_cols}")
                            else:
                                logger.warning("⚠️ 回退：表格块缺少 table_id/table_group_uid，跳过 document_tables 更新")
                except Exception as tbl_err:
                    logger.warning(f"⚠️ 回退：更新 document_tables 失败（不影响回退流程）: {tbl_err}", exc_info=True)
                
                # 7. 更新文档版本
                try:
                    from sqlalchemy import func
                    from app.models.version import DocumentVersion
                    
                    if document:
                        max_ver = self.db.query(func.max(DocumentVersion.version_number)).filter(
                            DocumentVersion.document_id == chunk.document_id,
                            DocumentVersion.is_deleted == False
                        ).scalar() or 0
                        next_ver = int(max_ver) + 1
                        ver = DocumentVersion(
                            document_id=chunk.document_id,
                            version_number=next_ver,
                            version_type="revert",
                            description=f"回退分块 {chunk_id} 到版本 {revert_request.target_version}",
                            file_path=document.file_path or "",
                            file_size=document.file_size,
                            file_hash=document.file_hash,
                        )
                        self.db.add(ver)
                        self.db.commit()
                        logger.info(f"✅ 文档版本更新成功: doc_id={chunk.document_id}, version={next_ver}")
                except Exception as ver_err:
                    logger.warning(f"⚠️ 记录文档版本失败（不影响回退流程）: {ver_err}", exc_info=True)
                
                task_id = f"revert_task_{chunk_id}_{datetime.now().timestamp()}"
                
                logger.info(f"✅ 块版本回退完成（已更新所有数据库）: chunk_id={chunk_id}, from={current_version}, to={revert_request.target_version}")
                return ChunkRevertResponse(
                    chunk_id=chunk_id,
                    from_version=current_version,
                    to_version=revert_request.target_version,
                    task_id=task_id,
                    message="块版本回退成功，已重新向量化并更新所有数据库"
                )
                
            except Exception as vector_err:
                logger.error(f"❌ 重新向量化或更新数据库失败: {vector_err}", exc_info=True)
                # 即使向量化失败，版本回退已完成，返回成功但记录错误
                task_id = f"revert_task_{chunk_id}_{datetime.now().timestamp()}"
                return ChunkRevertResponse(
                    chunk_id=chunk_id,
                    from_version=current_version,
                    to_version=revert_request.target_version,
                    task_id=task_id,
                    message=f"块版本回退成功，但重新向量化失败: {str(vector_err)}"
                )
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"回退块版本错误: {e}", exc_info=True)
            self.db.rollback()
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"回退块版本失败: {str(e)}"
            )
    
    def revert_chunk_to_previous_version(self, chunk_id: int) -> ChunkRevertResponse:
        """回退到上一个版本 - 根据设计文档实现"""
        try:
            logger.info(f"回退到上一个版本: chunk_id={chunk_id}")
            
            # 验证块是否存在
            chunk = self.db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
            if not chunk:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"块 {chunk_id} 不存在"
                )
            
            # 获取上一个版本
            previous_version = self.db.query(ChunkVersion).filter(
                ChunkVersion.chunk_id == chunk_id,
                ChunkVersion.version_number < chunk.version
            ).order_by(ChunkVersion.version_number.desc()).first()
            
            if not previous_version:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"块 {chunk_id} 没有上一个版本可以回退"
                )
            
            # 执行回退
            revert_request = ChunkRevertRequest(
                target_version=previous_version.version_number,
                revert_comment="回退到上一个版本"
            )
            
            return self.revert_chunk_to_version(chunk_id, revert_request)
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"回退到上一个版本错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"回退到上一个版本失败: {str(e)}"
            )
