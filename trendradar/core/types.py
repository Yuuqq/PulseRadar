"""
Stage boundary DTOs for the decomposed pipeline.

These frozen dataclasses are the ONLY data shapes that cross
between CrawlCoordinator, AnalysisEngine, and the notification layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RSSOutput:
    """RSS crawl results carried within CrawlOutput (D-04)."""
    stats_items: list[dict] | None = None
    new_items: list[dict] | None = None
    raw_items: list[dict] | None = None


@dataclass(frozen=True, slots=True)
class CrawlOutput:
    """All crawl results merged into a single boundary object (D-01, D-02).

    CrawlCoordinator produces this after hotlist + extra APIs + RSS
    are all fetched, merged, and stored.
    """
    results: dict
    id_to_name: dict
    failed_ids: tuple[str, ...] = ()
    rss: RSSOutput = field(default_factory=RSSOutput)


@dataclass(frozen=True, slots=True)
class AnalysisOutput:
    """Flat output mirroring current pipeline return shape (D-03).

    stats, html_file_path, ai_result -- same as the current
    run_analysis_pipeline() 3-tuple return.
    """
    stats: list[dict]
    html_file_path: str | None = None
    ai_result: object = None
