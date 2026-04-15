"""
趋势分析模块 -- 跨周期趋势检测与对比

Compare crawl results across two time periods to detect:
- New trending topics (appeared in current but not previous)
- Rising/falling/stable trends (rank movement)
- Cross-platform hot topics (appearing on 3+ platforms)
- Disappeared topics (dropped off between periods)
"""

from dataclasses import dataclass
from datetime import datetime

from trendradar.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TrendItem:
    """Single trend record with rank movement and platform coverage."""

    title: str
    current_rank: int
    previous_rank: int | None  # None = newly appeared
    rank_change: int  # positive = improved, negative = dropped
    platform_count: int
    platforms: tuple[str, ...]
    is_new: bool
    is_rising: bool
    heat_score: float


@dataclass
class TrendReport:
    """Cross-cycle trend comparison report."""

    generated_at: datetime
    current_period: str
    previous_period: str
    new_trends: list[TrendItem]
    rising_trends: list[TrendItem]
    falling_trends: list[TrendItem]
    stable_trends: list[TrendItem]
    disappeared: list[str]
    cross_platform: list[TrendItem]
    total_current: int
    total_previous: int


# Threshold for classifying a rank change as rising/falling vs stable.
_RANK_CHANGE_THRESHOLD = 2

# Minimum number of platforms for a topic to be considered cross-platform.
_CROSS_PLATFORM_MIN = 3


class TrendAnalyzer:
    """
    Stateless trend analyzer.

    Accepts raw crawl-result dicts (the same ``{platform_id: {title: data}}``
    format used throughout TrendRadar) and produces a ``TrendReport``.
    """

    def __init__(self, storage_manager=None):
        self.storage_manager = storage_manager

    def compare_periods(
        self,
        current_results: dict[str, dict],
        previous_results: dict[str, dict],
        id_to_name: dict[str, str] | None = None,
        current_period_label: str = "",
        previous_period_label: str = "",
    ) -> TrendReport:
        """
        Compare two crawl-result snapshots and produce a trend report.

        Args:
            current_results: ``{platform_id: {title: {"ranks": [...], "url": ...}}}``
            previous_results: same structure for the earlier period
            id_to_name: optional platform_id to display-name mapping
            current_period_label: human-readable label for the current period
            previous_period_label: human-readable label for the previous period

        Returns:
            A categorised ``TrendReport``.
        """
        id_to_name = id_to_name or {}

        current_topics = self._build_topic_index(current_results, id_to_name)
        previous_topics = self._build_topic_index(previous_results, id_to_name)

        new_trends: list[TrendItem] = []
        rising_trends: list[TrendItem] = []
        falling_trends: list[TrendItem] = []
        stable_trends: list[TrendItem] = []
        cross_platform: list[TrendItem] = []

        for title, (best_rank, platforms) in current_topics.items():
            platform_count = len(platforms)

            if title in previous_topics:
                prev_rank, _ = previous_topics[title]
                rank_change = prev_rank - best_rank  # positive = improved

                item = TrendItem(
                    title=title,
                    current_rank=best_rank,
                    previous_rank=prev_rank,
                    rank_change=rank_change,
                    platform_count=platform_count,
                    platforms=tuple(sorted(platforms)),
                    is_new=False,
                    is_rising=rank_change > 0,
                    heat_score=self._calculate_heat(best_rank, platform_count),
                )

                if rank_change > _RANK_CHANGE_THRESHOLD:
                    rising_trends.append(item)
                elif rank_change < -_RANK_CHANGE_THRESHOLD:
                    falling_trends.append(item)
                else:
                    stable_trends.append(item)
            else:
                item = TrendItem(
                    title=title,
                    current_rank=best_rank,
                    previous_rank=None,
                    rank_change=0,
                    platform_count=platform_count,
                    platforms=tuple(sorted(platforms)),
                    is_new=True,
                    is_rising=True,
                    heat_score=self._calculate_heat(best_rank, platform_count),
                )
                new_trends.append(item)

            if platform_count >= _CROSS_PLATFORM_MIN:
                cross_platform.append(item)

        disappeared = [title for title in previous_topics if title not in current_topics]

        # Sort each bucket by heat (highest first).
        new_trends.sort(key=lambda x: x.heat_score, reverse=True)
        rising_trends.sort(key=lambda x: x.heat_score, reverse=True)
        falling_trends.sort(key=lambda x: x.heat_score, reverse=True)
        stable_trends.sort(key=lambda x: x.heat_score, reverse=True)
        cross_platform.sort(key=lambda x: x.heat_score, reverse=True)

        now = datetime.now()
        report = TrendReport(
            generated_at=now,
            current_period=current_period_label or now.strftime("%Y-%m-%d %H:%M"),
            previous_period=previous_period_label,
            new_trends=new_trends,
            rising_trends=rising_trends,
            falling_trends=falling_trends,
            stable_trends=stable_trends,
            disappeared=disappeared,
            cross_platform=cross_platform,
            total_current=len(current_topics),
            total_previous=len(previous_topics),
        )

        logger.info(
            "趋势分析完成",
            new=len(new_trends),
            rising=len(rising_trends),
            falling=len(falling_trends),
            stable=len(stable_trends),
            disappeared=len(disappeared),
            cross_platform=len(cross_platform),
        )
        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_topic_index(
        results: dict[str, dict],
        id_to_name: dict[str, str],
    ) -> dict[str, tuple[int, list[str]]]:
        """
        Flatten crawl results into ``{title: (best_rank, [platform_names])}``.

        Each title keeps only its best (lowest) rank across all platforms
        where it appeared.
        """
        index: dict[str, tuple[int, list[str]]] = {}

        for platform_id, titles in results.items():
            platform_name = id_to_name.get(platform_id, platform_id)

            for title, data in titles.items():
                if isinstance(data, dict):
                    ranks = data.get("ranks", [])
                else:
                    # Legacy format: data is already a list of ranks.
                    ranks = data if isinstance(data, list) else []

                best_rank = min(ranks) if ranks else 999

                if title in index:
                    existing_rank, existing_platforms = index[title]
                    index[title] = (
                        min(existing_rank, best_rank),
                        [*existing_platforms, platform_name],
                    )
                else:
                    index[title] = (best_rank, [platform_name])

        return index

    @staticmethod
    def _calculate_heat(rank: int, platform_count: int) -> float:
        """
        Score a topic's heat.

        Lower rank and more platform appearances yield a higher score.
        - rank 1 on 1 platform  -> 98 + 15 = 113
        - rank 50 on 1 platform -> 0 + 15  = 15
        - rank 1 on 5 platforms -> 98 + 75 = 173
        """
        rank_score = max(0, 100 - rank * 2)
        platform_score = platform_count * 15
        return rank_score + platform_score
