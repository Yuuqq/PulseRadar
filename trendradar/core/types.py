# coding=utf-8
"""
Stage boundary DTOs for the decomposed pipeline.

These frozen dataclasses are the ONLY data shapes that cross
between CrawlCoordinator, AnalysisEngine, and the notification layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True, slots=True)
class RSSOutput:
    """RSS crawl results carried within CrawlOutput (D-04)."""
    stats_items: Optional[List[Dict]] = None
    new_items: Optional[List[Dict]] = None
    raw_items: Optional[List[Dict]] = None


@dataclass(frozen=True, slots=True)
class CrawlOutput:
    """All crawl results merged into a single boundary object (D-01, D-02).

    CrawlCoordinator produces this after hotlist + extra APIs + RSS
    are all fetched, merged, and stored.
    """
    results: Dict
    id_to_name: Dict
    failed_ids: Tuple[str, ...] = ()
    rss: RSSOutput = field(default_factory=RSSOutput)


@dataclass(frozen=True, slots=True)
class AnalysisOutput:
    """Flat output mirroring current pipeline return shape (D-03).

    stats, html_file_path, ai_result -- same as the current
    run_analysis_pipeline() 3-tuple return.
    """
    stats: List[Dict]
    html_file_path: Optional[str] = None
    ai_result: object = None
