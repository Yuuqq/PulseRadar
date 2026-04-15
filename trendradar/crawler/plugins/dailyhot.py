"""DailyHot 热榜 API 爬虫插件"""

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

DAILYHOT_BASE = "https://api.codelife.cc/api/top/list"
DAILYHOT_IMSYY_BASE = "https://api-hot.imsyy.top"

DAILYHOT_DEFAULT_PLATFORMS = (
    "toutiao",
    "weibo",
    "zhihu",
    "baidu",
    "bilibili",
    "douyin",
)


def _normalize_items(raw_items: list[dict], platform: str) -> list[FetchedItem]:
    result = []
    for idx, item in enumerate(raw_items, 1):
        title = str(item.get("title") or item.get("name") or "").strip()
        if not title:
            continue
        url = item.get("url") or item.get("link") or ""
        rank = item.get("index") or item.get("rank") or idx
        result.append(FetchedItem(title=title, url=url, rank=int(rank)))
    return result


def _parse_payload(payload: dict | None, fallback_platform: str) -> dict[str, list[FetchedItem]]:
    if not payload or payload.get("code") != 200:
        return {}
    items_data = payload.get("data")
    if not items_data:
        return {}
    if isinstance(items_data, list):
        normalized = _normalize_items(items_data, fallback_platform)
        return {fallback_platform: normalized} if normalized else {}
    if isinstance(items_data, dict):
        out: dict[str, list[FetchedItem]] = {}
        for pname, raw in items_data.items():
            if isinstance(raw, list):
                normalized = _normalize_items(raw, pname)
                if normalized:
                    out[pname] = normalized
        return out
    return {}


@CrawlerRegistry.register
class DailyHotPlugin(CrawlerPlugin):
    """DailyHot 热榜插件（支持单平台和多平台聚合）

    多平台结果打包为一个 CrawlResult，每条 FetchedItem 的 title
    带有 "[platform]" 前缀，rank 在全局范围内连续递增。
    """

    source_type = "dailyhot"

    def __init__(self) -> None:
        self._session = requests.Session()

    @property
    def rate_limit(self) -> float:
        return 0.5  # 多平台拉取较慢，给足空间

    def _get_json(self, url: str, params: dict | None = None) -> dict | None:
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
            logger.error("[DailyHotPlugin] 请求失败", url=url, error=str(exc))
            return None

    def _fetch_platform(self, platform: str) -> dict[str, list[FetchedItem]]:
        params = {"lang": "zh", "id": platform, "size": 50}
        payload = self._get_json(DAILYHOT_BASE, params=params)
        return _parse_payload(payload, platform)

    def _fetch_all_platforms(self) -> dict[str, list[FetchedItem]]:
        # Try bulk endpoint first
        params = {"lang": "zh", "size": 50}
        payload = self._get_json(DAILYHOT_BASE, params=params)
        result = _parse_payload(payload, "dailyhot")

        if not result:
            # Fallback: iterate default platforms individually
            for platform in DAILYHOT_DEFAULT_PLATFORMS:
                platform_result = self._fetch_platform(platform)
                if platform_result:
                    result.update(platform_result)

        return result

    def fetch(self, source_config: dict) -> CrawlResult:
        source_id = source_config.get("id", "dailyhot")
        source_name = source_config.get("name", "DailyHot")
        platform = source_config.get("platform")  # None = all platforms
        fetched_at = datetime.now()

        try:
            if platform:
                platform_map = self._fetch_platform(str(platform))
            else:
                platform_map = self._fetch_all_platforms()

            if not platform_map:
                return CrawlResult(
                    source_id=source_id,
                    source_name=source_name,
                    items=(),
                    fetched_at=fetched_at,
                    errors=("[DailyHotPlugin] 所有平台均返回空数据",),
                )

            # Pack all platforms into a single CrawlResult with prefixed titles
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

            logger.info(
                "[DailyHotPlugin] 获取成功",
                platforms=list(platform_map.keys()),
                total=len(all_items),
            )
            return CrawlResult(
                source_id=source_id,
                source_name=source_name,
                items=tuple(all_items),
                fetched_at=fetched_at,
            )

        except Exception as exc:
            error_msg = f"[DailyHotPlugin] 获取失败: {exc}"
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
            logger.debug("[DailyHotPlugin] 关闭 session 失败", exc_info=True)
