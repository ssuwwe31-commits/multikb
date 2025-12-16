from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config.database import SessionLocal
from app.core.logging import logger
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/tables", tags=["tables"], dependencies=[Depends(get_current_user)])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TableResponse(BaseModel):
    data: Dict[str, Any]


@router.get("/{table_uid}", response_model=TableResponse)
def get_table(table_uid: str, db: Session = Depends(get_db)):
    try:
        logger.info(f"API请求: 获取表格 table_uid={table_uid}")
        sql = text("SELECT document_id, table_group_uid, element_index, n_rows, n_cols, headers_json, cells_json, spans_json, stats_json, part_index, part_count, row_range FROM document_tables WHERE table_uid=:table_uid")
        res = db.execute(sql, {"table_uid": table_uid}).fetchone()
        if not res:
            logger.warning(f"表格不存在: table_uid={table_uid}")
            raise HTTPException(status_code=404, detail="table_not_found")
        # headers/cells/spans/stats 作为JSON字符串返回，前端可直接解析
        keys = ["document_id","table_group_uid","element_index","n_rows","n_cols","headers_json","cells_json","spans_json","stats_json","part_index","part_count","row_range"]
        data = {k: v for k, v in zip(keys, res)}
        data["table_uid"] = table_uid
        logger.info(f"API响应: 获取表格成功 table_uid={table_uid}")
        return {"code": 0, "message": "ok", "data": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取表格API错误: table_uid={table_uid}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表格失败: {str(e)}"
        )


class TableGroupResponse(BaseModel):
    data: Dict[str, Any]


@router.get("/group/{table_group_uid}", response_model=TableGroupResponse)
def get_table_group(table_group_uid: str, db: Session = Depends(get_db)):
    try:
        logger.info(f"API请求: 获取表格组 table_group_uid={table_group_uid}")
        sql = text(
            "SELECT table_uid, document_id, element_index, n_rows, n_cols, headers_json, cells_json, spans_json, stats_json, part_index, part_count, row_range "
            "FROM document_tables WHERE table_group_uid=:table_group_uid ORDER BY part_index ASC"
        )
        rows = db.execute(sql, {"table_group_uid": table_group_uid}).fetchall()
        if not rows:
            logger.warning(f"表格组不存在: table_group_uid={table_group_uid}")
            raise HTTPException(status_code=404, detail="table_group_not_found")

        # 简单合并：
        # - headers: 取分片0
        # - cells: 纵向拼接
        # - spans/stats: 保留为数组（或后续服务层做更精细合并）
        def _json_load(v):
            if v is None:
                return None
            try:
                import json
                return json.loads(v) if isinstance(v, str) else v
            except Exception:
                return None

        headers = None
        cells: List[List[str]] = []
        spans_list: List[Any] = []
        stats_list: List[Any] = []
        document_id = None
        parts_meta: List[Dict[str, Any]] = []

        for r in rows:
            (table_uid, doc_id, element_index, n_rows, n_cols, headers_json, cells_json, spans_json, stats_json, part_index, part_count, row_range) = r
            document_id = document_id or doc_id
            if headers is None:
                headers = _json_load(headers_json) or {}
            part_cells = _json_load(cells_json) or []
            if isinstance(part_cells, list):
                cells.extend([[str(c) if c is not None else "" for c in row] if isinstance(row, list) else [str(row)] for row in part_cells])
            s1 = _json_load(spans_json)
            if s1 is not None:
                spans_list.append(s1)
            s2 = _json_load(stats_json)
            if s2 is not None:
                stats_list.append(s2)
            parts_meta.append({
                "table_uid": table_uid,
                "part_index": part_index,
                "row_range": row_range,
                "n_rows": n_rows,
                "n_cols": n_cols,
            })

        data = {
            "table_group_uid": table_group_uid,
            "document_id": document_id,
            "headers": headers,
            "cells": cells,
            "spans_list": spans_list,
            "stats_list": stats_list,
            "parts": parts_meta,
        }
        logger.info(f"API响应: 获取表格组成功 table_group_uid={table_group_uid}, parts={len(parts_meta)}, cells_rows={len(cells)}")
        return {"code": 0, "message": "ok", "data": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取表格组API错误: table_group_uid={table_group_uid}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表格组失败: {str(e)}"
        )
