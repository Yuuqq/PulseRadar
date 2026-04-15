"""GNews API 爬虫插件"""
import contextlib
from datetime import datetime, timezone

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

_API_URL = "https://gnews.io/api/v4/top-headlines"


@CrawlerRegistry.register
class GNewsPlugin(CrawlerPlugin):
    """GNews.io 国际新闻头条插件"""

    source_type = "gnews"

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    @property
    def rate_limit(self) -> float:
        return 0.5

    def fetch(self, source_config: dict) -> CrawlResult:
        source_id = source_config.get("id", "gnews")
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

        params: dict = {
            "apikey": api_key,
            "country": source_config.get("country", "us"),
            "category": source_config.get("category", "general"),
            "max": min(int(source_config.get("max_results", 50) or 50), 100),
            "lang": source_config.get("lang", "en"),
        }

        response = None
        try:
            response = self._session.get(_API_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            error_detail = str(exc)
            if response is not None:
                with contextlib.suppress(Exception):
                    error_detail = f"HTTP {response.status_code}: {response.text[:200]}"
            logger.error("[GNews] 请求失败", source_id=source_id, error=error_detail)
            return CrawlResult(
                source_id=source_id,
                source_name=source_name,
                items=(),
                fetched_at=fetched_at,
                errors=(error_detail,),
            )

        if not data or "articles" not in data:
            error_msg = data.get("errors", ["未知错误"])[0] if data else "响应为空"
            logger.warning("[GNews] 获取失败", source_id=source_id, error=error_msg)
            return CrawlResult(
                source_id=source_id,
                source_name=source_name,
                items=(),
                fetched_at=fetched_at,
                errors=(str(error_msg),),
            )

        fetched_items = []
        for idx, article in enumerate(data.get("articles", []), 1):
            title = article.get("title", "").strip()
            if not title:
                continue
            fetched_items.append(
                FetchedItem(
                    title=title,
                    url=article.get("url", ""),
                    rank=idx,
                )
            )

        logger.info("[GNews] 获取成功", source_id=source_id, count=len(fetched_items))
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
            logger.debug("[GNews] 关闭 session 失败", exc_info=True)
