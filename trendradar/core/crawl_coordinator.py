"""
CrawlCoordinator - orchestrates all data fetching operations.

Extracted from NewsAnalyzer to own hotlist crawling, extra API crawling,
RSS crawling, merge logic, and storage. Returns frozen CrawlOutput.
"""

from trendradar.context import AppContext
from trendradar.core.types import CrawlOutput, RSSOutput
from trendradar.crawler import DataFetcher
from trendradar.logging import get_logger
from trendradar.storage import convert_crawl_results_to_news_data

logger = get_logger(__name__)


class CrawlCoordinator:
    """Orchestrates all crawling operations and returns frozen CrawlOutput."""

    def __init__(self, ctx: AppContext, proxy_url: str | None = None):
        """
        Initialize CrawlCoordinator.

        Args:
            ctx: Application context
            proxy_url: Optional proxy URL for HTTP requests
        """
        self.ctx = ctx
        self.proxy_url = proxy_url
        self.storage_manager = ctx.get_storage_manager()

        crawler_api_url = (ctx.config.get("CRAWLER_API_URL") or "").strip()
        self.data_fetcher = DataFetcher(
            proxy_url=proxy_url,
            api_url=crawler_api_url or None,
        )

        self.request_interval = ctx.config["REQUEST_INTERVAL"]
        self.report_mode = ctx.config["REPORT_MODE"]
        self.rank_threshold = ctx.rank_threshold

    def crawl_all(self) -> CrawlOutput:
        """
        Execute all crawling operations and return frozen output.

        Returns:
            CrawlOutput with merged hotlist + extra API + RSS results
        """
        # Crawl hotlist data
        results, id_to_name, failed_ids = self._crawl_hotlist()

        # Crawl RSS data
        rss_items, rss_new_items, raw_rss_items = self._crawl_rss()

        # Crawl extra API sources
        extra_results, extra_names, extra_failed = self._crawl_extra_apis()

        # Merge extra API results INTO results dict BEFORE freezing
        if extra_results:
            for source_id, items in extra_results.items():
                results[source_id] = {}
                for i, item in enumerate(items, 1):
                    title = item.get("title", "").strip()
                    if not title:
                        continue
                    rank = item.get("rank", i)
                    if title in results[source_id]:
                        results[source_id][title]["ranks"].append(rank)
                    else:
                        results[source_id][title] = {
                            "ranks": [rank],
                            "url": item.get("url", ""),
                            "mobileUrl": item.get("mobile_url", ""),
                        }
                id_to_name.update(extra_names)
                failed_ids.extend(extra_failed)

        # Return frozen output
        return CrawlOutput(
            results=results,
            id_to_name=id_to_name,
            failed_ids=tuple(failed_ids),
            rss=RSSOutput(
                stats_items=rss_items,
                new_items=rss_new_items,
                raw_items=raw_rss_items,
            ),
        )

    def _crawl_hotlist(self) -> tuple[dict, dict, list]:
        """
        Crawl hotlist platforms.

        Returns:
            (results, id_to_name, failed_ids) tuple
        """
        from pathlib import Path

        ids = []
        for platform in self.ctx.platforms:
            if "name" in platform:
                ids.append((platform["id"], platform["name"]))
            else:
                ids.append(platform["id"])

        logger.info("配置的监控平台", platforms=[p.get('name', p['id']) for p in self.ctx.platforms])
        logger.info("开始爬取数据", interval_ms=self.request_interval)
        Path("output").mkdir(parents=True, exist_ok=True)

        results, id_to_name, failed_ids = self.data_fetcher.crawl_websites(
            ids, self.request_interval
        )

        # Convert to NewsData format and save to storage backend
        crawl_time = self.ctx.format_time()
        crawl_date = self.ctx.format_date()
        news_data = convert_crawl_results_to_news_data(
            results, id_to_name, failed_ids, crawl_time, crawl_date
        )

        # Save to storage backend (SQLite)
        if self.storage_manager.save_news_data(news_data):
            logger.info("数据已保存到存储后端", backend=self.storage_manager.backend_name)

        # Save TXT snapshot (if enabled)
        txt_file = self.storage_manager.save_txt_snapshot(news_data)
        if txt_file:
            logger.info("TXT 快照已保存", file=str(txt_file))

        # Compatibility: also save to original TXT format (ensure backward compatibility)
        if self.ctx.config["STORAGE"]["FORMATS"]["TXT"]:
            title_file = self.ctx.save_titles(results, id_to_name, failed_ids)
            logger.info("标题已保存", file=str(title_file))

        return results, id_to_name, failed_ids

    def _crawl_rss(self) -> tuple[list[dict] | None, list[dict] | None, list[dict] | None]:
        """
        Crawl RSS feeds.

        Returns:
            (rss_items, rss_new_items, raw_rss_items) tuple
        """
        from trendradar.core.rss_crawler import crawl_rss_data

        return crawl_rss_data(
            ctx=self.ctx,
            storage_manager=self.storage_manager,
            proxy_url=self.proxy_url,
            report_mode=self.report_mode,
            rank_threshold=self.rank_threshold,
        )

    def _crawl_extra_apis(self) -> tuple[dict, dict, list]:
        """
        Crawl extra API data sources (concurrent mode).

        Returns:
            (results dict, ID-to-name mapping, failed IDs list) tuple
        """
        extra_apis_config = self.ctx.config.get("EXTRA_APIS", {})
        if not extra_apis_config.get("enabled", False):
            return {}, {}, []

        sources = extra_apis_config.get("sources", [])
        if not sources:
            logger.info("未配置额外 API 数据源")
            return {}, {}, []

        enabled_count = sum(1 for s in sources if s.get("enabled", True))
        if enabled_count == 0:
            logger.info("所有额外 API 数据源均已禁用")
            return {}, {}, []

        # Build id_to_name mapping from config so callers can display friendly names
        source_names: dict = {}
        for s in sources:
            if s.get("enabled", True):
                sid = s.get("id", "")
                source_names[sid] = s.get("name", sid)

        logger.info("开始抓取额外 API 数据源", total=len(sources), enabled=enabled_count)

        from trendradar.crawler.extra_apis import crawl_extra_sources_concurrent
        results, failed = crawl_extra_sources_concurrent(extra_apis_config)

        logger.info("额外 API 抓取完成", succeeded=len(results), failed=len(failed))
        if failed:
            logger.warning("失败的额外数据源", sources=failed)

        return results, source_names, failed
