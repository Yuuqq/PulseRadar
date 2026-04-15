"""
爬虫模块 - 数据抓取功能

提供:
- DataFetcher: NewsNow API 数据获取器（原有）
- CrawlerPool: 并发采集池（新增）
- CrawlerPlugin: 插件基类（新增）
- CrawlerRegistry: 插件注册表（新增）
"""

from trendradar.crawler.base import CrawlerPlugin, CrawlResult, FetchedItem
from trendradar.crawler.fetcher import DataFetcher
from trendradar.crawler.pool import CrawlerPool
from trendradar.crawler.registry import CrawlerRegistry

__all__ = [
    "CrawlResult",
    "CrawlerPlugin",
    "CrawlerPool",
    "CrawlerRegistry",
    "DataFetcher",
    "FetchedItem",
]
