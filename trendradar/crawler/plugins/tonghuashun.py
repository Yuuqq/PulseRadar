"""同花顺资讯（财经头条）爬虫插件"""
import html
import re
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

_DEFAULT_URL = "https://news.10jqka.com.cn/clientinfo/finance.html"
_DEFAULT_ENCODING = "gbk"
_DEFAULT_MAX_ITEMS = 50


def _clean_text(raw: str) -> str:
    cleaned = re.sub(r"<[^>]+>", "", raw)
    return html.unescape(cleaned).strip()


@CrawlerRegistry.register
class TongHuaShunPlugin(CrawlerPlugin):
    """同花顺资讯爬虫插件（GBK HTML 抓取）"""

    source_type = "10jqka"

    def __init__(self) -> None:
        self._session = requests.Session()

    @property
    def rate_limit(self) -> float:
        return 1.0

    def _fetch_html(self, url: str, encoding: str) -> str | None:
        try:
            req_headers = {
                **DEFAULT_HEADERS,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://news.10jqka.com.cn/",
            }
            resp = self._session.get(url, headers=req_headers, timeout=15)
            resp.raise_for_status()
            if encoding:
                return resp.content.decode(encoding, errors="ignore")
            return resp.text
        except Exception as exc:
            logger.error("[TongHuaShunPlugin] 请求失败", url=url, error=str(exc))
            return None

    def _parse_html(self, text: str, max_items: int) -> list[FetchedItem]:
        items: list[FetchedItem] = []
        blocks = text.split('<div class="article"')
        for block in blocks:
            if "article-time" not in block:
                continue
            url_match = re.search(r"openbrower\('([^']+)'", block, re.I)
            title_match = re.search(r"<strong>\s*<a[^>]*>(.*?)</a>", block, re.I | re.S)

            if not url_match or not title_match:
                continue

            article_url = url_match.group(1).strip()
            title = _clean_text(title_match.group(1))
            if not title:
                continue

            items.append(FetchedItem(
                title=title,
                url=article_url,
                rank=len(items) + 1,
            ))

            if max_items and len(items) >= max_items:
                break

        return items

    def fetch(self, source_config: dict) -> CrawlResult:
        source_id = source_config.get("id", "10jqka")
        source_name = source_config.get("name", "同花顺资讯")
        url = source_config.get("url", _DEFAULT_URL)
        max_items = int(source_config.get("max_items", _DEFAULT_MAX_ITEMS) or _DEFAULT_MAX_ITEMS)
        encoding = source_config.get("encoding", _DEFAULT_ENCODING)
        fetched_at = datetime.now()

        try:
            text = self._fetch_html(url, encoding)
            if not text:
                return CrawlResult(
                    source_id=source_id,
                    source_name=source_name,
                    items=(),
                    fetched_at=fetched_at,
                    errors=("[TongHuaShunPlugin] 响应为空",),
                )

            items = self._parse_html(text, max_items)
            if not items:
                return CrawlResult(
                    source_id=source_id,
                    source_name=source_name,
                    items=(),
                    fetched_at=fetched_at,
                    errors=("[TongHuaShunPlugin] 解析后无有效条目（页面结构可能已变更）",),
                )

            logger.info("[TongHuaShunPlugin] 获取成功", count=len(items))
            return CrawlResult(
                source_id=source_id,
                source_name=source_name,
                items=tuple(items),
                fetched_at=fetched_at,
            )

        except Exception as exc:
            error_msg = f"[TongHuaShunPlugin] 获取失败: {exc}"
            logger.error(error_msg, url=url)
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
            logger.debug("[TongHuaShunPlugin] 关闭 session 失败", exc_info=True)
