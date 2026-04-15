"""华尔街见闻实时快讯爬虫插件"""

from datetime import datetime

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

_LIVES_URL = "https://api-prod.wallstreetcn.com/apiv1/content/lives"


@CrawlerRegistry.register
class WallStreetCNPlugin(CrawlerPlugin):
    """华尔街见闻实时快讯插件"""

    source_type = "wallstreetcn"

    def __init__(self) -> None:
        self._session = requests.Session()

    @property
    def rate_limit(self) -> float:
        return 1.0

    def _get_json(self, url: str, params: dict) -> dict | None:
        try:
            resp = self._session.get(
                url,
                headers=DEFAULT_HEADERS,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.error("[WallStreetCNPlugin] 请求失败", url=url, error=str(exc))
            return None

    def _parse_items(self, data: dict) -> list[FetchedItem]:
        items: list[FetchedItem] = []
        for idx, item in enumerate(data.get("data", {}).get("items", []), 1):
            title = item.get("title") or item.get("content_text") or ""
            title = str(title).replace("\n", " ").strip()
            if not title:
                continue
            live_id = item.get("id")
            url = f"https://wallstreetcn.com/live/{live_id}" if live_id else ""
            items.append(FetchedItem(title=title, url=url, rank=idx))
        return items

    def fetch(self, source_config: dict) -> CrawlResult:
        source_id = source_config.get("id", "wallstreetcn")
        source_name = source_config.get("name", "华尔街见闻")
        channel = source_config.get("channel", "global-channel")
        limit = int(source_config.get("limit", 50) or 50)
        fetched_at = datetime.now()

        params = {"channel": channel, "limit": max(1, min(limit, 100))}

        try:
            data = self._get_json(_LIVES_URL, params=params)
            if not data or data.get("code") != 20000:
                code = data.get("code") if data else "no_response"
                return CrawlResult(
                    source_id=source_id,
                    source_name=source_name,
                    items=(),
                    fetched_at=fetched_at,
                    errors=(f"[WallStreetCNPlugin] API 返回非预期状态码: {code}",),
                )

            items = self._parse_items(data)
            if not items:
                return CrawlResult(
                    source_id=source_id,
                    source_name=source_name,
                    items=(),
                    fetched_at=fetched_at,
                    errors=("[WallStreetCNPlugin] 解析后无有效条目",),
                )

            logger.info("[WallStreetCNPlugin] 获取成功", channel=channel, count=len(items))
            return CrawlResult(
                source_id=source_id,
                source_name=source_name,
                items=tuple(items),
                fetched_at=fetched_at,
            )

        except Exception as exc:
            error_msg = f"[WallStreetCNPlugin] 获取失败: {exc}"
            logger.error(error_msg, channel=channel)
            return CrawlResult(
                source_id=source_id,
                source_name=source_name,
                items=(),
                fetched_at=fetched_at,
                errors=(error_msg,),
            )

    def close(self) -> None:
        try:
            self._session.close()
        except Exception:
            logger.debug("[WallStreetCNPlugin] 关闭 session 失败", exc_info=True)
