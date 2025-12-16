"""
Log query service supporting ELK and Loki backends.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx

from app.core.logging import logger
from app.models.cluster_config import ClusterConfig
from app.core.cache import cache_manager
from app.config.settings import settings


class LogQueryService:
    """Service to query logs from configured logging system."""

    def __init__(self, cluster: ClusterConfig, runtime_config: Optional[Dict[str, Any]] = None):
        from app.core.exceptions import CustomException, ErrorCode
        
        runtime = runtime_config or {}
        log_endpoint = runtime.get("log_endpoint") or cluster.log_endpoint
        if not log_endpoint:
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"集群 '{cluster.name}' 未配置日志系统地址，请先在集群配置中添加日志系统端点"
            )
        self.cluster = cluster
        self.runtime = runtime
        self.log_endpoint = log_endpoint.rstrip("/")
        self.log_system = (runtime.get("log_system") or cluster.log_system or "custom").lower()
        self.auth_type = runtime.get("log_auth_type") or cluster.log_auth_type
        self.username = runtime.get("log_username") or cluster.log_username
        self.password = runtime.get("log_password") or cluster.log_password

    async def query_logs(
        self,
        query: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
        page: int = 1,
        page_size: Optional[int] = None,
        highlight: bool = False,
        include_stats: bool = False,
    ) -> Dict[str, Any]:
        page_size = page_size or limit or 100
        page = max(page, 1)
        cache_key = self._cache_key(query, start, end, page, page_size, highlight, include_stats)
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached

        system = self.log_system
        if system in ("elk", "elasticsearch"):
            data = await self._query_elasticsearch(query, start, end, page, page_size, highlight, include_stats)
        elif system == "loki":
            data = await self._query_loki(query, start, end, page, page_size, highlight, include_stats)
        else:
            raise ValueError(f"Unsupported log system: {system}")

        ttl = max(1, settings.OBSERVABILITY_LOG_CACHE_SECONDS)
        if ttl:
            await cache_manager.set(cache_key, data, ttl)
        return data

    async def _query_elasticsearch(
        self,
        query: str,
        start: Optional[datetime],
        end: Optional[datetime],
        page: int,
        page_size: int,
        highlight: bool,
        include_stats: bool,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "from": max(page - 1, 0) * page_size,
            "size": page_size,
            "query": {
                "bool": {
                    "must": [
                        {"query_string": {"query": query}},
                    ]
                }
            },
            "sort": [{"@timestamp": {"order": "desc"}}],
        }
        if start or end:
            range_filter: Dict[str, Any] = {"range": {"@timestamp": {}}}
            if start:
                range_filter["range"]["@timestamp"]["gte"] = start.isoformat()
            if end:
                range_filter["range"]["@timestamp"]["lte"] = end.isoformat()
            body["query"]["bool"].setdefault("filter", []).append(range_filter)

        if highlight:
            body["highlight"] = {
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"],
                "fields": {
                    "message": {"number_of_fragments": 0},
                    "log": {"number_of_fragments": 0},
                },
            }

        url = urljoin(self.log_endpoint + "/", "_search")
        headers = self._build_headers(self.auth_type, self.username, self.password)
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()

        hits = data.get("hits", {})
        total = None
        if isinstance(hits.get("total"), dict):
            total = hits["total"].get("value")
        elif isinstance(hits.get("total"), int):
            total = hits["total"]

        entries = []
        for hit in hits.get("hits", []):
            source = hit.get("_source", {})
            entry = {
                "timestamp": source.get("@timestamp"),
                "message": source.get("message") or source.get("log"),
                "severity": source.get("level") or source.get("severity") or source.get("log_level"),
                "raw": source,
            }
            highlight_fields = hit.get("highlight")
            if highlight_fields:
                entry["highlight"] = highlight_fields.get("message") or highlight_fields.get("log")
            entries.append(entry)

        result: Dict[str, Any] = {
            "results": entries,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
            },
            "raw": data,
        }

        if include_stats:
            level_counts: Dict[str, int] = {}
            for entry in entries:
                level = (entry.get("severity") or "unknown").lower()
                level_counts[level] = level_counts.get(level, 0) + 1
            result["stats"] = {"level_counts": level_counts}

        return result

    async def _query_loki(
        self,
        query: str,
        start: Optional[datetime],
        end: Optional[datetime],
        page: int,
        page_size: int,
        highlight: bool,
        include_stats: bool,
    ) -> Dict[str, Any]:
        fetch_limit = page_size * page
        params: Dict[str, Any] = {"query": query, "limit": fetch_limit}
        if start:
            params["start"] = int(start.timestamp() * 1e9)
        if end:
            params["end"] = int(end.timestamp() * 1e9)

        url = urljoin(self.log_endpoint + "/", "loki/api/v1/query_range")
        headers = self._build_headers(self.auth_type, self.username, self.password)

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        raw_results = data.get("data", {}).get("result", [])
        flat_entries: List[Dict[str, Any]] = []
        for result in raw_results:
            labels = result.get("stream", {})
            for ts, value in result.get("values", []):
                entry = {
                    "timestamp": datetime.utcfromtimestamp(int(ts) / 1e9).isoformat() + "Z",
                    "message": value,
                    "labels": labels,
                }
                flat_entries.append(entry)

        start_index = max(page - 1, 0) * page_size
        end_index = start_index + page_size
        paged_entries = flat_entries[start_index:end_index]

        if highlight:
            keyword = query.strip()
            if keyword:
                for entry in paged_entries:
                    message = entry.get("message") or ""
                    entry["highlight"] = message.replace(keyword, f"<mark>{keyword}</mark>")

        result: Dict[str, Any] = {
            "results": paged_entries,
            "pagination": {
                "total": len(flat_entries),
                "page": page,
                "page_size": page_size,
            },
            "raw": data,
        }

        if include_stats:
            level_counts: Dict[str, int] = {}
            for entry in paged_entries:
                level = entry.get("labels", {}).get("level") or "unknown"
                level_counts[level] = level_counts.get(level, 0) + 1
            result["stats"] = {"level_counts": level_counts}

        return result

    @staticmethod
    def _build_headers(auth_type: Optional[str], username: Optional[str], password: Optional[str]) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        auth = (auth_type or "none").lower()
        if auth == "basic" and username and password:
            import base64

            token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {token}"
        elif auth == "token" and password:
            headers["Authorization"] = f"Bearer {password}"
        return headers

    def _cache_key(
        self,
        query: str,
        start: Optional[datetime],
        end: Optional[datetime],
        page: int,
        page_size: int,
        highlight: bool,
        include_stats: bool,
    ) -> str:
        payload = {
            "cluster": self.cluster.id,
            "system": self.log_system,
            "query": query,
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "page": page,
            "page_size": page_size,
            "highlight": highlight,
            "stats": include_stats,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return f"obs:logs:{digest}"
