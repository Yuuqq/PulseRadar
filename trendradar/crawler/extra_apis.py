"""
额外数据源并发抓取模块

使用 CrawlerPlugin 插件池替代旧的串行 ExtraAPIFetcher。
插件实现位于 trendradar/crawler/plugins/ 目录。
"""

from trendradar.logging import get_logger

logger = get_logger(__name__)


def crawl_extra_sources_concurrent(
    config: dict,
    max_workers: int = 8,
    timeout: float = 30.0,
) -> tuple[dict[str, list[dict]], list[str]]:
    """
    使用插件池并发获取额外数据源

    Args:
        config: extra_apis 配置段
        max_workers: 最大并发数
        timeout: 单源超时秒数

    Returns:
        (结果字典, 失败列表)
    """
    from trendradar.crawler.pool import CrawlerPool
    from trendradar.crawler.registry import CrawlerRegistry

    CrawlerRegistry.discover()

    sources = config.get("sources", [])
    tasks = []
    plugin_instances = []

    for source in sources:
        if not source.get("enabled", True):
            continue
        source_type = source.get("type", "")
        plugin_cls = CrawlerRegistry.get(source_type)
        if plugin_cls is None:
            logger.warning(
                "无插件可处理此数据源类型", source_type=source_type, source_id=source.get("id")
            )
            continue
        plugin = plugin_cls()
        plugin_instances.append(plugin)
        tasks.append((plugin, source))

    if not tasks:
        return {}, []

    pool = CrawlerPool(max_workers=max_workers, timeout=timeout)
    raw_results = pool.fetch_all(tasks)

    # 转换 CrawlResult → Dict[str, List[Dict]] 格式
    results: dict[str, list[dict]] = {}
    failed: list[str] = []

    for cr in raw_results:
        if cr.success:
            items_list = []
            for item in cr.items:
                items_list.append(
                    {
                        "title": item.title,
                        "url": item.url,
                        "mobile_url": item.mobile_url,
                        "rank": item.rank,
                    }
                )
            results[cr.source_id] = items_list
        else:
            failed.append(cr.source_id)

    # 清理插件资源
    for plugin in plugin_instances:
        plugin.close()

    return results, failed
