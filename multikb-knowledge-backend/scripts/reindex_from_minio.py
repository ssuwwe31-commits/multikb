"""
从 MinIO 的 chunks.jsonl.gz 回灌 OpenSearch 索引
用法（PowerShell）：
  .\venv\Scripts\python.exe scripts\reindex_from_minio.py --document-id 123
可选参数：--kb-id --category-id --alpha
注意：会调用 VectorService 重新生成向量（开销较大）。
"""

import argparse
import gzip
from io import BytesIO
from typing import List, Dict

from app.services.minio_storage_service import MinioStorageService
from app.services.vector_service import VectorService
from app.services.opensearch_service import OpenSearchService
from app.config.database import SessionLocal
from app.core.logging import logger


def load_chunks_from_minio(document_id: int) -> List[Dict]:
    minio = MinioStorageService()
    # 目录推断（与 upload_chunks 一致）
    # 为简化：遍历前缀 documents/**/<document_id>/parsed/chunks/ 找第一条 jsonl.gz
    prefix = f"documents/"
    files = minio.list_files(prefix)
    target = None
    needle = f"/{document_id}/parsed/chunks/chunks.jsonl.gz"
    for f in files:
        if f["object_name"].endswith(needle):
            target = f["object_name"]
            break
    if not target:
        raise RuntimeError("未找到 chunks.jsonl.gz")
    data = minio.download_file(target)
    chunks: List[Dict] = []
    with gzip.GzipFile(fileobj=BytesIO(data), mode='rb') as gz:
        for line in gz:
            try:
                import json
                chunks.append(json.loads(line))
            except Exception:
                continue
    return chunks


def main(document_id: int, kb_id: int | None, category_id: int | None):
    db = SessionLocal()
    try:
        chunks = load_chunks_from_minio(document_id)
        logger.info(f"加载分块 {len(chunks)} 条")
        vs = VectorService(db)
        osvc = OpenSearchService()
        docs = []
        for item in chunks:
            content = item.get("content", "")
            if not content:
                continue
            vec = vs.generate_embedding(content)
            docs.append({
                "document_id": document_id,
                "chunk_id": item.get("index"),
                "knowledge_base_id": kb_id,
                "category_id": category_id,
                "content": content,
                "chunk_type": "text",
                "metadata": {"reindex": True},
                "content_vector": vec,
            })
        # 批量索引（默认不立即 refresh，提高吞吐；需要可在外部调用刷新）
        osvc.bulk_index_document_chunks_sync(docs)
        logger.info("回灌完成")
    finally:
        db.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--document-id", type=int, required=True)
    ap.add_argument("--kb-id", type=int, default=None)
    ap.add_argument("--category-id", type=int, default=None)
    args = ap.parse_args()
    main(args.document_id, args.kb_id, args.category_id)
