"""
历史查询模块 -- 关键词历史趋势搜索

提供跨日期的关键词搜索能力，支持：
- 按关键词搜索历史新闻标题
- 按平台统计分布
- 按日期统计时间线
"""

from collections import Counter
from dataclasses import dataclass, field

from trendradar.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class HistoryMatch:
    """单条历史匹配记录"""

    title: str
    platform: str
    rank: int
    crawl_time: str
    url: str = ""


@dataclass
class HistoryResult:
    """历史查询结果"""

    keyword: str
    matches: list[HistoryMatch] = field(default_factory=list)
    total_count: int = 0
    date_range: tuple[str, str] = ("", "")
    platform_distribution: dict[str, int] = field(default_factory=dict)
    timeline: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转换为 JSON 可序列化的字典"""
        return {
            "keyword": self.keyword,
            "total_count": self.total_count,
            "date_range": list(self.date_range),
            "platform_distribution": self.platform_distribution,
            "timeline": self.timeline,
            "matches": [
                {
                    "title": m.title,
                    "platform": m.platform,
                    "rank": m.rank,
                    "crawl_time": m.crawl_time,
                    "url": m.url,
                }
                for m in self.matches
            ],
        }


class HistorySearcher:
    """历史数据搜索器"""

    def __init__(self, storage_manager):
        self.storage_manager = storage_manager

    def search(self, keyword: str, days: int = 7, limit: int = 200) -> HistoryResult:
        """
        Search historical crawl data for a keyword.

        Args:
            keyword: 搜索关键词
            days: 回溯天数（最大 30）
            limit: 最大返回条数（最大 500）

        Returns:
            HistoryResult 包含匹配记录和统计信息
        """
        days = max(1, min(days, 30))
        limit = max(1, min(limit, 500))

        raw_hits = self.storage_manager.search_titles(keyword, days=days, limit=limit)

        if not raw_hits:
            return HistoryResult(keyword=keyword)

        matches: list[HistoryMatch] = []
        platform_counter: Counter = Counter()
        date_counter: Counter = Counter()
        dates_seen: list[str] = []

        for hit in raw_hits:
            platform_name = hit.get("platform_name", hit.get("platform_id", ""))
            date_str = hit.get("date", "")
            crawl_time = hit.get("last_crawl_time", "")

            matches.append(
                HistoryMatch(
                    title=hit.get("title", ""),
                    platform=platform_name,
                    rank=hit.get("rank", 0),
                    crawl_time=crawl_time,
                    url=hit.get("url", ""),
                )
            )

            platform_counter[platform_name] += 1

            if date_str:
                date_counter[date_str] += 1
                if date_str not in dates_seen:
                    dates_seen.append(date_str)

        # Build date range from actual dates found
        if dates_seen:
            sorted_dates = sorted(dates_seen)
            date_range = (sorted_dates[0], sorted_dates[-1])
        else:
            date_range = ("", "")

        # Build sorted timeline
        timeline = dict(sorted(date_counter.items()))

        logger.info(
            "历史搜索完成",
            keyword=keyword,
            matches=len(matches),
            days=days,
        )

        return HistoryResult(
            keyword=keyword,
            matches=matches,
            total_count=len(matches),
            date_range=date_range,
            platform_distribution=dict(platform_counter),
            timeline=timeline,
        )
