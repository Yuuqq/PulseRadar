"""韩小韩热榜 API 爬虫插件"""

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

_VVHAN_SINGLE_BASE = "https://api.vvhan.com/api/hotlist/{platform}"
_VVHAN_ALL_URL = "https://api.vvhan.com/api/hotlist/all"


@CrawlerRegistry.register
class VvhanPlugin(CrawlerPlugin):
    """韩小韩热榜插件（支持单平台和全平台聚合）"""

    source_type = "vvhan"

    def __init__(self) -> None:
        self._session = requests.Session()

    @property
    def rate_limit(self) -> float:
        return 1.0

    def _get(self, url: str, params: dict | None = None) -> dict:
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
            logger.error("[VvhanPlugin] 请求失败", url=url, error=str(exc))
            raise

    def _fetch_single(self, platform: str) -> list[FetchedItem]:
        url = _VVHAN_SINGLE_BASE.format(platform=platform)
        data = self._get(url)
        if not data or not data.get("success"):
            return []
        items = []
        for idx, item in enumerate(data.get("data", []), 1):
            title = item.get("title", "").strip()
            if not title:
                continue
            items.append(
                FetchedItem(
                    title=title,
                    url=item.get("url", ""),
                    rank=idx,
                )
            )
        return items

    def _fetch_all(self) -> dict[str, list[FetchedItem]]:
        data = self._get(_VVHAN_ALL_URL)
        if not data or not data.get("success"):
            return {}
        result: dict[str, list[FetchedItem]] = {}
        for platform, raw_items in data.get("data", {}).items():
            platform_list = []
            for idx, item in enumerate(raw_items, 1):
                title = item.get("title", "").strip()
                if not title:
                    continue
                platform_list.append(
                    FetchedItem(
                        title=title,
                        url=item.get("url", ""),
                        rank=idx,
                    )
                )
            if platform_list:
                result[platform] = platform_list
        return result

    def fetch(self, source_config: dict) -> CrawlResult:
        source_id = source_config.get("id", "vvhan")
        source_name = source_config.get("name", "韩小韩热榜")
        platform = source_config.get("platform", "")
        fetched_at = datetime.now()

        try:
            if platform == "all":
                platform_map = self._fetch_all()
                # Flatten all platforms into one CrawlResult; prefix title with
                # platform name so consumers can distinguish origin.
                all_items: list[FetchedItem] = []
                rank_offset = 0
                for pname, pitems in platform_map.items():
                    for fi in pitems:
                        all_items.append(
                            FetchedItem(
                                title=f"[{pname}] {fi.title}",
                                url=fi.url,
                                rank=rank_offset + fi.rank,
                            )
                        )
                    rank_offset += len(pitems)
                if not all_items:
                    return CrawlResult(
                        source_id=source_id,
                        source_name=source_name,
                        items=(),
                        fetched_at=fetched_at,
                        errors=("[VvhanPlugin] 全平台聚合返回空数据",),
                    )
                logger.info("[VvhanPlugin] 全平台聚合成功", count=len(all_items))
                return CrawlResult(
                    source_id=source_id,
                    source_name=source_name,
                    items=tuple(all_items),
                    fetched_at=fetched_at,
                )
            else:
                items = self._fetch_single(platform)
                if not items:
                    return CrawlResult(
                        source_id=source_id,
                        source_name=source_name,
                        items=(),
                        fetched_at=fetched_at,
                        errors=(f"[VvhanPlugin] 平台 {platform!r} 返回空数据",),
                    )
                logger.info("[VvhanPlugin] 单平台获取成功", platform=platform, count=len(items))
                return CrawlResult(
                    source_id=source_id,
                    source_name=source_name,
                    items=tuple(items),
                    fetched_at=fetched_at,
                )
        except Exception as exc:
            error_msg = f"[VvhanPlugin] 获取失败: {exc}"
            logger.error(error_msg, platform=platform)
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
            logger.debug("[VvhanPlugin] 关闭 session 失败", exc_info=True)
