# coding=utf-8
"""爬虫插件基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True, slots=True)
class FetchedItem:
    """单条抓取结果"""
    title: str
    url: str = ""
    mobile_url: str = ""
    rank: int = 0


@dataclass(frozen=True, slots=True)
class CrawlResult:
    """单数据源抓取结果"""
    source_id: str
    source_name: str
    items: Tuple[FetchedItem, ...]
    fetched_at: datetime
    errors: Tuple[str, ...] = ()

    @property
    def success(self) -> bool:
        return len(self.errors) == 0 and len(self.items) > 0


class CrawlerPlugin(ABC):
    """
    爬虫插件基类

    所有数据源需实现此接口。插件通过 registry 自动发现注册。
    """

    @property
    @abstractmethod
    def source_type(self) -> str:
        """数据源类型标识 (如 'newsnow', 'dailyhot', 'newsapi')"""
        ...

    @property
    def rate_limit(self) -> float:
        """每秒最大请求数，子类可覆盖"""
        return 1.0

    @abstractmethod
    def fetch(self, source_config: Dict) -> CrawlResult:
        """
        获取数据

        Args:
            source_config: 数据源配置字典 (来自 config.yaml)

        Returns:
            CrawlResult 包含抓取到的条目或错误信息
        """
        ...

    def close(self) -> None:
        """释放资源，子类可覆盖"""
        pass
