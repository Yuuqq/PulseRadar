"""东方财富 7x24 快讯爬虫插件"""

import json
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

_URL_TEMPLATE = (
    "https://newsapi.eastmoney.com/kuaixun/v1/getlist_{channel}_ajaxResult_{page_size}_{page}_.html"
)


@CrawlerRegistry.register
class EastMoneyPlugin(CrawlerPlugin):
    """东方财富 7x24 快讯插件"""

    source_type = "eastmoney"

    def __init__(self) -> None:
        self._session = requests.Session()

    @property
    def rate_limit(self) -> float:
        return 1.0

    def _get_text(self, url: str) -> str | None:
        try:
            resp = self._session.get(url, headers=DEFAULT_HEADERS, timeout=15)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            logger.error("[EastMoneyPlugin] 请求失败", url=url, error=str(exc))
            return None

    def _parse_response(self, content: str) -> list[FetchedItem]:
        raw = content.strip()
        # Strip JS variable assignment wrapper: `var xxx = {...};`
        if raw.startswith("var"):
            if "=" in raw:
                raw = raw.split("=", 1)[1].strip()
            raw = raw.rstrip(";")

        try:
            data = json.loads(raw)
        except Exception as exc:
            logger.error("[EastMoneyPlugin] JSON 解析失败", error=str(exc))
            return []

        if str(data.get("rc")) != "1":
            logger.warning("[EastMoneyPlugin] 响应状态非预期", rc=data.get("rc"))
            return []

        items: list[FetchedItem] = []
        for idx, item in enumerate(data.get("LivesList", []), 1):
            title = str(item.get("title") or item.get("simtitle") or "").strip()
            if not title:
                continue
            url = item.get("url_w") or item.get("url_unique") or item.get("url_m") or ""
            items.append(FetchedItem(title=title, url=url, rank=idx))

        return items

    def fetch(self, source_config: dict) -> CrawlResult:
        source_id = source_config.get("id", "eastmoney")
        source_name = source_config.get("name", "东方财富快讯")
        channel = str(source_config.get("channel", "102"))
        page_size = int(source_config.get("page_size", 50) or 50)
        page = int(source_config.get("page", 1) or 1)
        fetched_at = datetime.now()

        url = _URL_TEMPLATE.format(channel=channel, page_size=page_size, page=page)

        try:
            content = self._get_text(url)
            if not content:
                return CrawlResult(
                    source_id=source_id,
                    source_name=source_name,
                    items=(),
                    fetched_at=fetched_at,
                    errors=("[EastMoneyPlugin] 响应为空",),
                )

            items = self._parse_response(content)
            if not items:
                return CrawlResult(
                    source_id=source_id,
                    source_name=source_name,
                    items=(),
                    fetched_at=fetched_at,
                    errors=("[EastMoneyPlugin] 解析后无有效条目",),
                )

            logger.info("[EastMoneyPlugin] 获取成功", count=len(items))
            return CrawlResult(
                source_id=source_id,
                source_name=source_name,
                items=tuple(items),
                fetched_at=fetched_at,
            )

        except Exception as exc:
            error_msg = f"[EastMoneyPlugin] 获取失败: {exc}"
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
            logger.debug("[EastMoneyPlugin] 关闭 session 失败", exc_info=True)
