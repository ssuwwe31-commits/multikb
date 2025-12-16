from typing import Any, Dict, List, Optional
import datetime
import gzip
import json
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.logging import logger
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.services.minio_storage_service import MinioStorageService


class QueryService:
    """
    查询聚合服务：对命中的 chunk 做上下文聚合（父子+邻接窗口），并返回表格/图片上下文。
    仅依赖 DB 的 chunks 表（content/meta）与 element_index 相关元信息。
    """

    def __init__(self, db: Session):
        self.db = db

    def get_context_for_hit(
        self,
        document_id: int,
        hit_chunk_id: int,
        neighbor_pre: int = 1,
        neighbor_next: int = 1,
        parent_group_max_chars: int = 1500,
        total_context_max_chars: int = 2500,
        max_tables: int = 2,
        max_images: int = 2,
    ) -> Dict[str, Any]:
        chunk: Optional[DocumentChunk] = self.db.query(DocumentChunk).filter(
            DocumentChunk.id == hit_chunk_id,
            DocumentChunk.document_id == document_id,
            DocumentChunk.is_deleted == False,
        ).first()
        if not chunk:
            return {"error": "chunk_not_found"}

        def load_textual_content(document_id: int, chunk_index: Optional[int]) -> str:
            if chunk_index is None:
                return ""
            try:
                doc = self.db.query(Document).filter(Document.id == document_id).first()
                if not doc:
                    return ""
                created_at: datetime.datetime = getattr(doc, "created_at", None) or datetime.datetime.utcnow()
                year = created_at.strftime("%Y")
                month = created_at.strftime("%m")
                object_name = f"documents/{year}/{month}/{document_id}/parsed/chunks/chunks.jsonl.gz"
                minio = MinioStorageService()
                obj = minio.client.get_object(minio.bucket_name, object_name)
                try:
                    with gzip.GzipFile(fileobj=obj, mode="rb") as gz:
                        for line in gz:
                            try:
                                record = json.loads(line.decode("utf-8"))
                            except Exception:
                                continue
                            idx = record.get("index")
                            if idx is None:
                                idx = record.get("chunk_index")
                            if idx is None:
                                continue
                            if int(idx) == int(chunk_index):
                                return record.get("content") or ""
                finally:
                    try:
                        obj.close()
                        obj.release_conn()
                    except Exception:
                        pass
            except Exception as err:
                logger.debug(f"[ContextPreview] MinIO 归档读取失败 doc={document_id}, chunk_index={chunk_index}: {err}")
            return ""

        # 取同文档全部块（按 chunk_index）
        all_chunks: List[DocumentChunk] = self.db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id,
            DocumentChunk.is_deleted == False,
        ).order_by(DocumentChunk.chunk_index).all()

        # 解析 meta
        import json
        def load_meta(raw):
            if not raw:
                return {}
            if isinstance(raw, dict):
                return raw
            try:
                return json.loads(raw)
            except Exception:
                return {}

        hit_meta = load_meta(chunk.meta)
        section_id = hit_meta.get('section_id')
        parent_chunk_id = hit_meta.get('parent_chunk_id')

        # 父子聚合
        siblings: List[Dict[str, Any]] = []
        if parent_chunk_id is not None:
            for c in all_chunks:
                cm = load_meta(c.meta)
                if cm.get('parent_chunk_id') == parent_chunk_id:
                    content_value = c.content or ""
                    if not content_value:
                        content_value = load_textual_content(document_id, c.chunk_index)
                    siblings.append({
                        'chunk_id': c.id,
                        'chunk_index': c.chunk_index,
                        'content': content_value,
                        'chunk_type': getattr(c, 'chunk_type', 'text'),
                    })
            siblings.sort(key=lambda x: x.get('chunk_index', 0))

        # 邻接窗口
        neighbors_prev: List[Dict[str, Any]] = []
        neighbors_next_list: List[Dict[str, Any]] = []
        hit_pos = next((i for i, c in enumerate(all_chunks) if c.id == hit_chunk_id), -1)
        if hit_pos >= 0:
            i = hit_pos - 1
            cnt = 0
            while i >= 0 and cnt < neighbor_pre:
                cm = load_meta(all_chunks[i].meta)
                if section_id is None or cm.get('section_id') == section_id:
                    content_value = all_chunks[i].content or ""
                    if not content_value:
                        content_value = load_textual_content(document_id, all_chunks[i].chunk_index)
                    neighbors_prev.append({
                        'chunk_id': all_chunks[i].id,
                        'chunk_index': all_chunks[i].chunk_index,
                        'content': content_value,
                        'chunk_type': getattr(all_chunks[i], 'chunk_type', 'text'),
                    })
                    cnt += 1
                i -= 1
            neighbors_prev.reverse()
            j = hit_pos + 1
            cnt = 0
            while j < len(all_chunks) and cnt < neighbor_next:
                cm = load_meta(all_chunks[j].meta)
                if section_id is None or cm.get('section_id') == section_id:
                    content_value = all_chunks[j].content or ""
                    if not content_value:
                        content_value = load_textual_content(document_id, all_chunks[j].chunk_index)
                    neighbors_next_list.append({
                        'chunk_id': all_chunks[j].id,
                        'chunk_index': all_chunks[j].chunk_index,
                        'content': content_value,
                        'chunk_type': getattr(all_chunks[j], 'chunk_type', 'text'),
                    })
                    cnt += 1
                j += 1

        minio_for_context: Optional[MinioStorageService] = None

        def _get_minio_client() -> MinioStorageService:
            nonlocal minio_for_context
            if minio_for_context is None:
                minio_for_context = MinioStorageService()
            return minio_for_context

        # 为邻接块补充预览：如果是表格或图片，没有文本 content 就做摘要
        def _enrich_neighbors_for_preview(items: List[Dict[str, Any]]):
            try:
                from sqlalchemy import text as _sql
                from app.core.logging import logger as _lg
                for it in items:
                    if (it.get('content') or '').strip():
                        continue
                    cobj = next((c for c in all_chunks if c.id == it.get('chunk_id')), None)
                    if not cobj:
                        continue
                    archive_text = load_textual_content(document_id, getattr(cobj, 'chunk_index', None))
                    if archive_text.strip():
                        it['content'] = archive_text
                        continue
                    cm = load_meta(getattr(cobj, 'meta', None))
                    ctype_raw = it.get('chunk_type')
                    ctype = (ctype_raw or '').lower() or 'text'
                    # 表格预览：取第一行或 headers 组成一行简短文本
                    is_table = (ctype == 'table') or bool(cm.get('table_group_uid') or cm.get('table_id'))
                    if is_table:
                        table_uid = cm.get('table_id')
                        table_group_uid = cm.get('table_group_uid')
                        row_text = ""
                        try:
                            if table_uid:
                                r = self.db.execute(_sql(
                                    "SELECT headers_json, cells_json FROM document_tables WHERE document_id=:doc AND table_uid=:uid LIMIT 1"
                                ), {"doc": document_id, "uid": table_uid}).fetchone()
                                if r:
                                    import json as _json
                                    h, cells = r
                                    headers = []
                                    try:
                                        headers = _json.loads(h) if isinstance(h, str) else (h or [])
                                    except Exception:
                                        headers = []
                                    rows = []
                                    try:
                                        rows = _json.loads(cells) if isinstance(cells, str) else (cells or [])
                                    except Exception:
                                        rows = []
                                    if rows:
                                        row_text = " | ".join([str(x) for x in rows[0]])
                                    elif headers:
                                        row_text = " | ".join([str(x) for x in headers])
                            elif table_group_uid:
                                r = self.db.execute(_sql(
                                    "SELECT cells_json FROM document_tables WHERE document_id=:doc AND table_group_uid=:gid ORDER BY part_index ASC LIMIT 1"
                                ), {"doc": document_id, "gid": table_group_uid}).fetchone()
                                if r:
                                    import json as _json
                                    cells = r[0]
                                    rows = []
                                    try:
                                        rows = _json.loads(cells) if isinstance(cells, str) else (cells or [])
                                    except Exception:
                                        rows = []
                                    if rows:
                                        row_text = " | ".join([str(x) for x in rows[0]])
                        except Exception:
                            row_text = ""
                        it['content'] = row_text or "[表格]"
                    else:
                        # 图片预览
                        is_image = (ctype == 'image') or bool(cm.get('image_path') or cm.get('image_id'))
                        if is_image:
                            image_id = cm.get('image_id')
                            image_path = cm.get('image_path')
                            image_url = None
                            if image_path:
                                try:
                                    minio_client = _get_minio_client()
                                    image_url = minio_client.client.presigned_get_object(
                                        minio_client.bucket_name,
                                        image_path,
                                        expires=datetime.timedelta(hours=1)
                                    )
                                except Exception:
                                    image_url = f"/{image_path}"
                            desc = cm.get('description') or cm.get('ocr_text') or ""
                            it['image_id'] = image_id
                            it['image_path'] = image_path
                            it['image_url'] = image_url
                            it['description'] = desc
                            it['content'] = desc or "[图片]"
                            continue
                        if not is_image:
                            # 文本空块：多级回填策略（同section&同页 -> 同页 -> 全局最近）
                            if ctype == 'text':
                                try:
                                    cur_idx = getattr(cobj, 'chunk_index', None)
                                    cur_section = cm.get('section_id')
                                    cur_page = cm.get('page_number')
                                    def _ok_text_any(c):
                                        return bool((getattr(c, 'content', None) or '').strip())
                                    def _meta(c):
                                        return load_meta(getattr(c, 'meta', None))
                                    # 1) 同section & 同页
                                    cands = [c for c in all_chunks if _ok_text_any(c) and _meta(c).get('section_id') == cur_section and _meta(c).get('page_number') == cur_page]
                                    # 2) 同页
                                    if not cands:
                                        cands = [c for c in all_chunks if _ok_text_any(c) and _meta(c).get('page_number') == cur_page]
                                    # 3) 全局最近 (local)
                                    if not cands:
                                        cands = [c for c in all_chunks if _ok_text_any(c)]
                                    # 4) Global DB fallback if still no cands
                                    if not cands:
                                        try:
                                            from app.models.document import Document
                                            from sqlalchemy import func, and_
                                            doc = self.db.query(Document).filter(Document.id == document_id).first()
                                            kb_id = getattr(doc, 'knowledge_base_id', None) if doc else None
                                            if kb_id is not None:
                                                global_cands = self.db.query(DocumentChunk).join(
                                                    Document, DocumentChunk.document_id == Document.id
                                                ).filter(
                                                    and_(
                                                        Document.knowledge_base_id == kb_id,
                                                        DocumentChunk.chunk_type == 'text',
                                                        DocumentChunk.is_deleted == False,
                                                        Document.is_deleted == False
                                                    )
                                                ).order_by(
                                                    func.abs(DocumentChunk.chunk_index - (cur_idx or 0))
                                                ).limit(1).all()
                                                if not global_cands:
                                                    _lg.warning(f"[ContextPreview] KB={kb_id} has no text chunks for neighbor chunk={it.get('chunk_id')}")
                                                else:
                                                    pick = global_cands[0]
                                                    preview = load_textual_content(pick.document_id, pick.chunk_index)[:60]
                                                    if preview.strip():
                                                        it['content'] = preview
                                                        _lg.info(f"[ContextPreview] global fallback: chunk={pick.id} => '{preview[:40]}'")
                                                        continue
                                                    _lg.warning(f"[ContextPreview] loaded empty content from MinIO for chunk={pick.id}")
                                        except Exception as e:
                                            _lg.warning(f"[ContextPreview] global fallback error chunk={it.get('chunk_id')}: {e}")
                                    # Ultimate fallback if no content after all
                                    if not it.get('content'):
                                        it['content'] = "[空文本块 - 无可用回填]"
                                        _lg.warning(f"[ContextPreview] ultimate fallback for chunk={it.get('chunk_id')} - no text available")
                                    if cands and cur_idx is not None and not it.get('content'):
                                        cands.sort(key=lambda x: abs((getattr(x, 'chunk_index', 0) or 0) - cur_idx))
                                        pick = cands[0]
                                        preview = (pick.content or '')[:60]
                                        it['content'] = preview
                                        continue
                                except Exception as e:
                                    _lg.warning(f"[ContextPreview] text fallback error chunk={it.get('chunk_id')}: {e}")
                                if ctype != 'text':
                                    # 其它类型：兜底占位，避免空白
                                    if ctype_raw:
                                        it['content'] = f"[{ctype_raw or '非文本'}]"
                                        continue
                                    continue
            except Exception:
                pass

        _enrich_neighbors_for_preview(neighbors_prev)
        _enrich_neighbors_for_preview(neighbors_next_list)

        # 组装 merged_text（父子优先）并做总长度限制
        merged_parts: List[str] = []
        if siblings:
            total = 0
            for s in siblings:
                txt = s.get('content') or ""
                if not txt:
                    txt = load_textual_content(document_id, s.get('chunk_index'))
                if not txt:
                    continue
                if total + len(txt) > parent_group_max_chars:
                    break
                merged_parts.append(txt)
                total += len(txt)
        else:
            prev_texts = []
            for x in neighbors_prev:
                txt = x.get('content') or ""
                if not txt:
                    txt = load_textual_content(document_id, x.get('chunk_index'))
                if txt:
                    prev_texts.append(txt)
            next_texts = []
            for x in neighbors_next_list:
                txt = x.get('content') or ""
                if not txt:
                    txt = load_textual_content(document_id, x.get('chunk_index'))
                if txt:
                    next_texts.append(txt)
            anchor_content = chunk.content or ""
            if not anchor_content:
                anchor_content = load_textual_content(document_id, getattr(chunk, 'chunk_index', None))
            merged_parts.extend([*prev_texts, anchor_content, *next_texts])
        merged_text = "\n".join([p for p in merged_parts if p])
        if len(merged_text) > total_context_max_chars:
            merged_text = merged_text[:total_context_max_chars]

        # 附带邻接中的表格/图片（数量限制）
        def pick_nontext_limited(items: List[Dict[str, Any]], mt: int, mi: int):
            tables: List[Dict[str, Any]] = []
            images: List[Dict[str, Any]] = []
            for it in items:
                ctype = (it.get('chunk_type') or '').lower()
                if ctype == 'table' and len(tables) < mt:
                    tables.append({
                        'chunk_id': it['chunk_id'],
                        'chunk_index': it.get('chunk_index'),
                        'snippet': it.get('content'),
                    })
                elif ctype == 'image' and len(images) < mi:
                    images.append({
                        'chunk_id': it['chunk_id'],
                        'chunk_index': it.get('chunk_index'),
                        'image_id': it.get('image_id'),
                        'image_path': it.get('image_path'),
                        'image_url': it.get('image_url'),
                        'description': it.get('description') or it.get('content') or "",
                        'document_id': document_id,
                    })
            return tables, images

        t_prev, i_prev = pick_nontext_limited(neighbors_prev, max_tables, max_images)
        t_next, i_next = pick_nontext_limited(neighbors_next_list, max_tables - len(t_prev), max_images - len(i_prev))

        # 如果命中表块，补充整表 JSON（支持分片聚合）
        tables_payload: List[Dict[str, Any]] = []
        if getattr(chunk, 'chunk_type', 'text') == 'table':
            import json
            hit_table_meta = hit_meta
            table_uid = hit_table_meta.get('table_id')
            table_group_uid = hit_table_meta.get('table_group_uid')
            try:
                if table_group_uid:
                    sql = text(
                        "SELECT table_uid, headers_json, cells_json, part_index FROM document_tables "
                        "WHERE document_id=:document_id AND table_group_uid=:table_group_uid ORDER BY part_index ASC"
                    )
                    rows = self.db.execute(sql, {"document_id": document_id, "table_group_uid": table_group_uid}).fetchall()
                    headers = None
                    cells: List[List[str]] = []
                    for r in rows:
                        _, h, c, _ = r
                        try:
                            if headers is None and h:
                                headers = json.loads(h) if isinstance(h, str) else h
                        except Exception:
                            headers = headers or {}
                        try:
                            part_cells = json.loads(c) if isinstance(c, str) else (c or [])
                        except Exception:
                            part_cells = []
                        if isinstance(part_cells, list):
                            cells.extend([[str(x) if x is not None else "" for x in row] if isinstance(row, list) else [str(row)] for row in part_cells])
                    tables_payload.append({
                        'table_id': table_group_uid,
                        'json': {'headers': headers or {}, 'cells': cells},
                    })
                elif table_uid:
                    sql = text(
                        "SELECT headers_json, cells_json FROM document_tables WHERE document_id=:document_id AND table_uid=:table_uid LIMIT 1"
                    )
                    r = self.db.execute(sql, {"document_id": document_id, "table_uid": table_uid}).fetchone()
                    if r:
                        h, c = r
                        try:
                            headers = json.loads(h) if isinstance(h, str) else (h or {})
                        except Exception:
                            headers = {}
                        try:
                            cells = json.loads(c) if isinstance(c, str) else (c or [])
                        except Exception:
                            cells = []
                        tables_payload.append({'table_id': table_uid, 'json': {'headers': headers, 'cells': cells}})
            except Exception as e:
                logger.warning(f"QueryService: 聚合表格失败: {e}")

        # 如果合并文本最终为空且命中的是表格，尝试用表格内容生成一段可读摘要
        hit_type = getattr(chunk, 'chunk_type', 'text')
        if (not merged_text.strip()) and hit_type == 'table':
            try:
                # 优先用上文生成的 tables_payload；否则从邻接表格中取第一张
                table_source = None
                if tables_payload:
                    table_source = tables_payload[0].get('json')
                else:
                    for it in (t_prev + t_next):
                        # 读取该表格第一行
                        pass
                if table_source:
                    headers = table_source.get('headers') or []
                    cells = table_source.get('cells') or []
                    lines = []
                    if headers:
                        lines.append(" | ".join([str(x) for x in headers]))
                    if cells:
                        for r in cells[:3]:  # 取前3行即可
                            lines.append(" | ".join([str(x) for x in r]))
                    merged_text = "\n".join(lines)[:total_context_max_chars]
            except Exception:
                pass

        result: Dict[str, Any] = {
            'hit': {
                'chunk_id': chunk.id,
                'type': getattr(chunk, 'chunk_type', 'text'),
                'score': None,  # 预留：排序融合权重
            },
            'context': {
                'parent': None if parent_chunk_id is None else {'parent_chunk_id': parent_chunk_id},
                'siblings': siblings,
                'neighbors': {
                    'prev': neighbors_prev,
                    'next': neighbors_next_list,
                },
                'tables': tables_payload or (t_prev + t_next),
                'images': i_prev + i_next,
            },
            'display': {
                'merged_text': merged_text,
                'render_hint': 'text' if getattr(chunk, 'chunk_type', 'text') == 'text' else 'mixed',
            }
        }
        return result
