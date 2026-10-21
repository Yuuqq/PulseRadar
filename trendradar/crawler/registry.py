"""插件自动发现与注册"""

import importlib
import pkgutil
import sys
from pathlib import Path

from trendradar.crawler.base import CrawlerPlugin
from trendradar.logging import get_logger

logger = get_logger(__name__)


class CrawlerRegistry:
    _plugins: dict[str, type[CrawlerPlugin]] = {}

    @classmethod
    def register(cls, plugin_class: type[CrawlerPlugin]) -> type[CrawlerPlugin]:
        """注册插件（可作为装饰器使用）"""
        instance = plugin_class()
        source_type = instance.source_type
        cls._plugins[source_type] = plugin_class
        logger.debug("注册爬虫插件", source_type=source_type, plugin=plugin_class.__name__)
        return plugin_class

    @classmethod
    def get(cls, source_type: str) -> type[CrawlerPlugin] | None:
        return cls._plugins.get(source_type)

    @classmethod
    def get_all(cls) -> dict[str, type[CrawlerPlugin]]:
        return dict(cls._plugins)

    @classmethod
    def discover(cls) -> None:
        """自动发现并导入 plugins 包下的所有模块"""
        plugins_dir = Path(__file__).parent / "plugins"
        if not plugins_dir.exists():
            return
        package_name = "trendradar.crawler.plugins"
        for _finder, name, _ispkg in pkgutil.iter_modules([str(plugins_dir)]):
            if name.startswith("_"):
                continue
            module_name = f"{package_name}.{name}"
            try:
                module = sys.modules.get(module_name)
                if module is None:
                    importlib.import_module(module_name)
                else:
                    # A cached module never re-runs its @register decorator, so
                    # re-scan it; otherwise discover() is empty on repeat calls.
                    cls._register_module_plugins(module)
            except Exception as e:
                logger.warning("加载插件失败", plugin=name, error=str(e))

    @classmethod
    def _register_module_plugins(cls, module) -> None:
        for attr_name in dir(module):
            candidate = getattr(module, attr_name, None)
            if (
                isinstance(candidate, type)
                and issubclass(candidate, CrawlerPlugin)
                and candidate is not CrawlerPlugin
                and getattr(candidate, "source_type", "")
            ):
                cls._plugins[candidate.source_type] = candidate
