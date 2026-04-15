"""
Domain data models for TrendRadar.

Frozen dataclasses (immutable) and enums for core domain concepts.
NewsItem, NewsData, RSSItem, RSSData are re-exported from storage.base
to avoid duplication — use this module as the canonical import point.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# Re-export existing storage models so callers only need one import location.
from trendradar.storage.base import NewsData, NewsItem, RSSData, RSSItem

__all__ = [
    "AnalysisResult",
    "CrawlResult",
    "JobStage",
    "JobStatus",
    "NewsData",
    # Re-exported from storage.base
    "NewsItem",
    # New domain models defined below
    "PlatformSource",
    "RSSData",
    "RSSItem",
    "ReportType",
]


@dataclass(frozen=True, slots=True)
class PlatformSource:
    """A crawl source/platform definition."""

    id: str
    name: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class CrawlResult:
    """Result produced by a single crawl run against one source."""

    source_id: str
    platform: str
    items: tuple[NewsItem, ...]
    fetched_at: datetime
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Output of an AI analysis pass."""

    content: str
    model: str
    tokens_used: int
    duration_seconds: float
    mode: str


class JobStatus(str, Enum):
    """Lifecycle status of a background job."""

    queued = "queued"
    running = "running"
    cancelling = "cancelling"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"


class JobStage(str, Enum):
    """Coarse-grained stage within a running job."""

    queued = "queued"
    starting = "starting"
    crawl = "crawl"
    rss = "rss"
    ai = "ai"
    report = "report"
    notify = "notify"
    finished = "finished"


class ReportType(str, Enum):
    """Identifies which kind of report was generated."""

    main = "main"
    rss = "rss"
    ai_analysis = "ai_analysis"
