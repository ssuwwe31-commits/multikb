"""
External Search Service
基于 SearxNG 的外部搜索兜底能力
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from app.config.settings import settings
from app.core.cache import cache_manager
from app.core.logging import logger


class ExternalSearchRateLimitError(Exception):
    """外部搜索触发限流"""


class ExternalSearchService:
    """封装 SearxNG 调用、缓存与限流控制"""

    CACHE_PREFIX = "external_search:cache:"
    RATE_PREFIX = "external_search:rate:"

    def __init__(self) -> None:
        self.enabled = bool(settings.SEARXNG_URL) and settings.EXTERNAL_SEARCH_ENABLED
        self._redis = cache_manager.redis_client

    async def search(
        self,
        question: str,
        context: Optional[str] = None,
        *,
        user_id: Optional[int] = None,
        limit: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        intent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行联网搜索"""
        if not self.enabled:
            raise RuntimeError("外部搜索未启用或 SEARXNG_URL 未配置")

        query = self._build_query(question, context, metadata)
        cache_key = self.CACHE_PREFIX + hashlib.sha1(query.encode("utf-8")).hexdigest()
        cached = await cache_manager.get(cache_key)
        if cached:
            cached["from_cache"] = True
            return cached

        await self._ensure_rate_limit(user_id)

        url = settings.SEARXNG_URL.rstrip("/") + "/search"
        params = {
            "q": query,
            "format": "json",
            "language": "zh-CN",
            "safesearch": 1,
        }
        categories = self._resolve_categories(intent)
        if categories:
            params["categories"] = categories

        logger.info("[外部搜索] query=%s user_id=%s", query, user_id)
        timeout = settings.EXTERNAL_SEARCH_TIMEOUT
        start_ts = datetime.utcnow()
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.debug("[外部搜索] 请求 SearxNG params=%s", params)
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        elapsed = (datetime.utcnow() - start_ts).total_seconds()
        results = self._normalize_results(payload, limit or settings.EXTERNAL_SEARCH_RESULT_LIMIT)
        result_payload = {
            "results": results,
            "from_cache": False,
            "query": query,
            "timestamp": datetime.utcnow().isoformat(),
            "latency": elapsed,
        }

        await cache_manager.set(cache_key, result_payload, settings.EXTERNAL_SEARCH_CACHE_TTL)
        return result_payload

    async def _ensure_rate_limit(self, user_id: Optional[int]) -> None:
        """简单的基于 Redis 的计数限流"""
        if not user_id:
            return
        key = self.RATE_PREFIX + str(user_id)
        pipe = self._redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, settings.EXTERNAL_SEARCH_RATE_LIMIT_WINDOW)
        count, _ = pipe.execute()
        if count == 1:
            self._redis.expire(key, settings.EXTERNAL_SEARCH_RATE_LIMIT_WINDOW)
        if count > settings.EXTERNAL_SEARCH_RATE_LIMIT_PER_USER:
            logger.warning("[外部搜索] 用户 %s 触发限流，count=%s", user_id, count)
            raise ExternalSearchRateLimitError("联网搜索过于频繁，请稍后再试")

    def _build_query(
        self,
        question: str,
        context: Optional[str],
        metadata: Optional[Dict[str, Any]],
    ) -> str:
        pieces: List[str] = [question.strip()]
        if metadata:
            kb_hits = metadata.get("knowledge_base_hits")
            top_score = metadata.get("top_score")
            if kb_hits is not None:
                pieces.append(f"命中数:{kb_hits}")
            if top_score is not None:
                pieces.append(f"得分:{top_score}")
        if context:
            trimmed = context.strip()
            if len(trimmed) > 400:
                trimmed = trimmed[:400]
            pieces.append(trimmed)
        return " ".join(pieces)

    def _resolve_categories(self, intent: Optional[str]) -> Optional[str]:
        if settings.EXTERNAL_SEARCH_CATEGORIES:
            return settings.EXTERNAL_SEARCH_CATEGORIES
        if intent == "news":
            logger.debug("[外部搜索] 依据意图选择 categories=news")
            return "news"
        if intent == "tech":
            logger.debug("[外部搜索] 依据意图选择 categories=it")
            return "it"
        return None
    def _normalize_results(self, payload: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        raw_results = payload.get("results", []) or []
        normalized: List[Dict[str, Any]] = []
        for item in raw_results:
            if len(normalized) >= limit:
                break
            url = item.get("url")
            if not url:
                continue
            normalized.append(
                {
                    "title": item.get("title") or url,
                    "url": url,
                    "snippet": item.get("content") or item.get("summary"),
                    "source": item.get("source") or self._extract_host(url),
                    "engines": item.get("engines"),
                }
            )
        return normalized

    @staticmethod
    def _extract_host(url: str) -> Optional[str]:
        try:
            from urllib.parse import urlparse

            return urlparse(url).netloc
        except Exception:
            return None
