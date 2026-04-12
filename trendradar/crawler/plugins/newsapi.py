# coding=utf-8
"""NewsAPI.org 爬虫插件"""
from datetime import datetime, timezone
from typing import Dict

import requests

from trendradar.crawler.base import CrawlerPlugin, CrawlResult, FetchedItem
from trendradar.crawler.registry import CrawlerRegistry
from trendradar.logging import get_logger

logger = get_logger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

_API_URL = "https://newsapi.org/v2/top-headlines"


@CrawlerRegistry.register
class NewsAPIPlugin(CrawlerPlugin):
    """NewsAPI.org 国际新闻头条插件"""

    source_type = "newsapi"

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    @property
    def rate_limit(self) -> float:
        return 0.5

    def fetch(self, source_config: Dict) -> CrawlResult:
        source_id = source_config.get("id", "newsapi")
        source_name = source_config.get("name", source_id)
        fetched_at = datetime.now(timezone.utc)

        api_key = source_config.get("api_key", "")
        if not api_key:
            return CrawlResult(
                source_id=source_id,
                source_name=source_name,
                items=(),
                fetched_at=fetched_at,
                errors=("api_key 未配置",),
            )

        params: Dict = {
            "apiKey": api_key,
            "country": source_config.get("country", "us"),
            "pageSize": min(int(source_config.get("page_size", 50) or 50), 100),
        }
        category = source_config.get("category")
        if category:
            params["category"] = category

        response = None
        try:
            response = self._session.get(_API_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            error_detail = str(exc)
            if response is not None:
                try:
                    error_detail = f"HTTP {response.status_code}: {response.text[:200]}"
                except Exception:
                    pass
            logger.error("[NewsAPI] 请求失败", source_id=source_id, error=error_detail)
            return CrawlResult(
                source_id=source_id,
                source_name=source_name,
                items=(),
                fetched_at=fetched_at,
                errors=(error_detail,),
            )

        if not data or data.get("status") != "ok":
            error_msg = data.get("message", "未知错误") if data else "响应为空"
            logger.warning("[NewsAPI] 获取失败", source_id=source_id, error=error_msg)
            return CrawlResult(
                source_id=source_id,
                source_name=source_name,
                items=(),
                fetched_at=fetched_at,
                errors=(error_msg,),
            )

        fetched_items = []
        for idx, article in enumerate(data.get("articles", []), 1):
            title = article.get("title", "").strip()
            if not title or title == "[Removed]":
                continue
            fetched_items.append(
                FetchedItem(
                    title=title,
                    url=article.get("url", ""),
                    rank=idx,
                )
            )

        logger.info("[NewsAPI] 获取成功", source_id=source_id, count=len(fetched_items))
        return CrawlResult(
            source_id=source_id,
            source_name=source_name,
            items=tuple(fetched_items),
            fetched_at=fetched_at,
        )

    def close(self) -> None:
        try:
            self._session.close()
        except Exception:
            logger.debug("[NewsAPI] 关闭 session 失败", exc_info=True)
