# coding=utf-8
"""
RSS 数据抓取

从 NewsAnalyzer 中提取的 RSS 抓取逻辑，接受显式参数而非 self。
"""

from typing import Dict, List, Optional, Tuple

from trendradar.context import AppContext
from trendradar.logging import get_logger
from trendradar.utils.time import DEFAULT_TIMEZONE

logger = get_logger(__name__)


def crawl_rss_data(
    ctx: AppContext,
    storage_manager,
    proxy_url: Optional[str],
    process_rss_data_by_mode_fn,
) -> Tuple[Optional[List[Dict]], Optional[List[Dict]], Optional[List[Dict]]]:
    """
    执行 RSS 数据抓取

    Args:
        ctx: 应用上下文
        storage_manager: 存储管理器
        proxy_url: 代理 URL
        process_rss_data_by_mode_fn: 按模式处理 RSS 数据的函数

    Returns:
        (rss_items, rss_new_items, raw_rss_items) 元组：
        - rss_items: 统计条目列表（按模式处理，用于统计区块）
        - rss_new_items: 新增条目列表（用于新增区块）
        - raw_rss_items: 原始 RSS 条目列表（用于独立展示区）
        如果未启用或失败返回 (None, None, None)
    """
    if not ctx.rss_enabled:
        return None, None, None

    rss_feeds = ctx.rss_feeds
    if not rss_feeds:
        logger.warning("未配置任何 RSS 源")
        return None, None, None

    try:
        from trendradar.crawler.rss import RSSFetcher, RSSFeedConfig

        feeds = []
        for feed_config in rss_feeds:
            max_age_days_raw = feed_config.get("max_age_days")
            max_age_days = None
            if max_age_days_raw is not None:
                try:
                    max_age_days = int(max_age_days_raw)
                    if max_age_days < 0:
                        feed_id = feed_config.get("id", "unknown")
                        logger.warning(
                            "RSS feed 的 max_age_days 为负数，将使用全局默认值",
                            feed_id=feed_id,
                        )
                        max_age_days = None
                except (ValueError, TypeError):
                    feed_id = feed_config.get("id", "unknown")
                    logger.warning(
                        "RSS feed 的 max_age_days 格式错误",
                        feed_id=feed_id,
                        value=max_age_days_raw,
                    )
                    max_age_days = None

            feed = RSSFeedConfig(
                id=feed_config.get("id", ""),
                name=feed_config.get("name", ""),
                url=feed_config.get("url", ""),
                max_items=feed_config.get("max_items", 50),
                enabled=feed_config.get("enabled", True),
                max_age_days=max_age_days,
            )
            if feed.id and feed.url and feed.enabled:
                feeds.append(feed)

        if not feeds:
            logger.warning("没有启用的 RSS 源")
            return None, None, None

        rss_config = ctx.rss_config
        rss_proxy_url = rss_config.get("PROXY_URL", "") or proxy_url or ""
        timezone = ctx.config.get("TIMEZONE", DEFAULT_TIMEZONE)
        freshness_config = rss_config.get("FRESHNESS_FILTER", {})
        freshness_enabled = freshness_config.get("ENABLED", True)
        default_max_age_days = freshness_config.get("MAX_AGE_DAYS", 3)

        fetcher = RSSFetcher(
            feeds=feeds,
            request_interval=rss_config.get("REQUEST_INTERVAL", 2000),
            timeout=rss_config.get("TIMEOUT", 15),
            use_proxy=rss_config.get("USE_PROXY", False),
            proxy_url=rss_proxy_url,
            timezone=timezone,
            freshness_enabled=freshness_enabled,
            default_max_age_days=default_max_age_days,
        )

        rss_data = fetcher.fetch_all()

        if storage_manager.save_rss_data(rss_data):
            logger.info("RSS 数据已保存到存储后端")
            return process_rss_data_by_mode_fn(rss_data)
        else:
            logger.error("RSS 数据保存失败")
            return None, None, None

    except ImportError as e:
        logger.error("RSS 缺少依赖，请安装 feedparser", error=str(e))
        return None, None, None
    except Exception as e:
        logger.error("RSS 抓取失败", error=str(e))
        return None, None, None
