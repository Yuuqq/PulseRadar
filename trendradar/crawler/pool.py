"""并发采集池 — 基于 ThreadPoolExecutor"""
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from trendradar.crawler.base import CrawlerPlugin, CrawlResult
from trendradar.logging import get_logger

logger = get_logger(__name__)

class CrawlerPool:
    """
    并发采集池

    使用 ThreadPoolExecutor 并行调用多个 CrawlerPlugin，
    附带超时控制和错误隔离。
    """

    def __init__(self, max_workers: int = 10, timeout: float = 30.0):
        self.max_workers = max_workers
        self.timeout = timeout

    def fetch_all(
        self,
        tasks: Sequence[tuple],  # [(plugin_instance, source_config), ...]
    ) -> list[CrawlResult]:
        """
        并发执行所有采集任务

        Args:
            tasks: (CrawlerPlugin实例, source_config字典) 元组列表

        Returns:
            CrawlResult 列表（成功和失败都包含）
        """
        results: list[CrawlResult] = []

        if not tasks:
            return results

        logger.info("开始并发采集", total_tasks=len(tasks), max_workers=self.max_workers)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_config = {}
            for plugin, config in tasks:
                future = executor.submit(self._safe_fetch, plugin, config)
                source_id = config.get("id", "unknown")
                future_to_config[future] = (source_id, config)

            try:
                completed_futures = as_completed(future_to_config, timeout=self.timeout * 2)
                for future in completed_futures:
                    source_id, config = future_to_config[future]
                    try:
                        result = future.result(timeout=self.timeout)
                        results.append(result)
                    except Exception as e:
                        logger.error("采集任务异常", source_id=source_id, error=str(e))
                        results.append(CrawlResult(
                            source_id=source_id,
                            source_name=config.get("name", source_id),
                            items=(),
                            fetched_at=datetime.now(),
                            errors=(str(e),),
                        ))
            except TimeoutError:
                # Collect timed-out futures that never completed
                for future, (source_id, config) in future_to_config.items():
                    if not future.done():
                        logger.error("采集任务超时", source_id=source_id)
                        future.cancel()
                        results.append(CrawlResult(
                            source_id=source_id,
                            source_name=config.get("name", source_id),
                            items=(),
                            fetched_at=datetime.now(),
                            errors=("timeout",),
                        ))

        succeeded = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        logger.info("并发采集完成", succeeded=succeeded, failed=failed, total=len(results))

        return results

    @staticmethod
    def _safe_fetch(plugin: CrawlerPlugin, config: dict) -> CrawlResult:
        """安全包装单次采集，捕获所有异常"""
        source_id = config.get("id", "unknown")
        source_name = config.get("name", source_id)
        try:
            return plugin.fetch(config)
        except Exception as e:
            return CrawlResult(
                source_id=source_id,
                source_name=source_name,
                items=(),
                fetched_at=datetime.now(),
                errors=(str(e),),
            )
