# Plan 03-02 Summary: CrawlCoordinator Extraction

**Status:** ✅ Complete
**Completed:** 2026-04-15
**Commit:** 01f57528

## Objective

Extract CrawlCoordinator from NewsAnalyzer to own hotlist crawling, extra API crawling, RSS crawling, merge logic, and storage. Eliminate the `process_rss_data_by_mode_fn` callback from rss_crawler.py.

## Tasks Completed

### Task 1: Eliminate callback from rss_crawler.py ✅
- Removed `process_rss_data_by_mode_fn` callback parameter
- Added explicit `report_mode: str` and `rank_threshold: int` parameters
- Call `process_rss_data_by_mode()` directly instead of via callback
- New signature: `crawl_rss_data(ctx, storage_manager, proxy_url, report_mode, rank_threshold)`

### Task 2: Create CrawlCoordinator class ✅
- Created `trendradar/core/crawl_coordinator.py` (210 lines)
- `CrawlCoordinator.__init__(ctx, proxy_url)` initializes all dependencies
- `crawl_all()` orchestrates hotlist + RSS + extra APIs, returns frozen `CrawlOutput`
- Internalized extra API merge loop (Pitfall 1) before freezing output
- Zero callback parameters throughout

## Files Modified

- `trendradar/core/rss_crawler.py` - callback eliminated
- `trendradar/core/crawl_coordinator.py` - new file

## Verification

- ✅ CrawlCoordinator class is importable
- ✅ rss_crawler.py has no `process_rss_data_by_mode_fn` parameter
- ✅ Existing pipeline tests pass (7 passed)
- ✅ Extra API merge logic replicated exactly from __main__.py lines 624-641

## Coverage Impact

Coverage dropped to 5.14% due to 85 new uncovered statements in crawl_coordinator.py. This is expected since the class isn't wired into the main flow yet (happens in Plan 04).

## Next Steps

Plan 03-03: Extract AnalysisEngine and eliminate all remaining _fn callbacks from core/ modules.
