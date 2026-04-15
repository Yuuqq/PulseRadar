"""
Convenience re-export hub for all TrendRadar domain models.

Import from here instead of reaching into sub-modules directly.
"""

from trendradar.models.config import TrendRadarConfig
from trendradar.models.news import (
    AnalysisResult,
    CrawlResult,
    JobStage,
    JobStatus,
    NewsData,
    NewsItem,
    PlatformSource,
    ReportType,
    RSSData,
    RSSItem,
)

__all__ = [
    "AnalysisResult",
    "CrawlResult",
    "JobStage",
    "JobStatus",
    "NewsData",
    "NewsItem",
    "PlatformSource",
    "RSSData",
    "RSSItem",
    "ReportType",
    "TrendRadarConfig",
]
