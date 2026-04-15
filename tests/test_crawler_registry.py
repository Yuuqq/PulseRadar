from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clean_registry():
    """Ensure each test starts with a clean registry and restores state after."""
    from trendradar.crawler.registry import CrawlerRegistry

    saved = dict(CrawlerRegistry._plugins)
    CrawlerRegistry._plugins.clear()
    yield
    CrawlerRegistry._plugins.clear()
    CrawlerRegistry._plugins.update(saved)


def test_register_decorator_adds_plugin():
    from trendradar.crawler.base import CrawlerPlugin
    from trendradar.crawler.registry import CrawlerRegistry

    class FakePlugin(CrawlerPlugin):
        source_type = "fake_test"

        def fetch(self, source_config):
            pass

    CrawlerRegistry.register(FakePlugin)
    assert "fake_test" in CrawlerRegistry._plugins
    assert CrawlerRegistry._plugins["fake_test"] is FakePlugin


def test_get_returns_correct_plugin_class():
    from trendradar.crawler.base import CrawlerPlugin
    from trendradar.crawler.registry import CrawlerRegistry

    class AlphaPlugin(CrawlerPlugin):
        source_type = "alpha"

        def fetch(self, source_config):
            pass

    CrawlerRegistry.register(AlphaPlugin)
    assert CrawlerRegistry.get("alpha") is AlphaPlugin


def test_get_returns_none_for_unknown_type():
    from trendradar.crawler.registry import CrawlerRegistry

    assert CrawlerRegistry.get("nonexistent_xyz") is None


def test_get_all_returns_all_registered():
    from trendradar.crawler.base import CrawlerPlugin
    from trendradar.crawler.registry import CrawlerRegistry

    class PlugA(CrawlerPlugin):
        source_type = "plug_a"

        def fetch(self, source_config):
            pass

    class PlugB(CrawlerPlugin):
        source_type = "plug_b"

        def fetch(self, source_config):
            pass

    CrawlerRegistry.register(PlugA)
    CrawlerRegistry.register(PlugB)

    all_plugins = CrawlerRegistry.get_all()
    assert len(all_plugins) == 2
    assert "plug_a" in all_plugins
    assert "plug_b" in all_plugins


def test_discover_finds_all_builtin_plugins():
    """After discover(), all 9 built-in plugins are registered."""
    from trendradar.crawler.registry import CrawlerRegistry

    CrawlerRegistry.discover()
    all_plugins = CrawlerRegistry.get_all()

    # The project has 9 plugin files in plugins/
    assert (
        len(all_plugins) >= 9
    ), f"Expected >= 9 plugins, got {len(all_plugins)}: {list(all_plugins.keys())}"

    expected_types = {
        "dailyhot",
        "vvhan",
        "newsapi",
        "gnews",
        "mediastack",
        "eastmoney",
        "thenewsapi",
        "wallstreetcn",
        "10jqka",
    }
    registered_types = set(all_plugins.keys())
    assert expected_types.issubset(
        registered_types
    ), f"Missing plugins: {expected_types - registered_types}"


def test_register_overwrites_same_source_type():
    from trendradar.crawler.base import CrawlerPlugin
    from trendradar.crawler.registry import CrawlerRegistry

    class V1Plugin(CrawlerPlugin):
        source_type = "duptype"

        def fetch(self, source_config):
            pass

    class V2Plugin(CrawlerPlugin):
        source_type = "duptype"

        def fetch(self, source_config):
            pass

    CrawlerRegistry.register(V1Plugin)
    CrawlerRegistry.register(V2Plugin)
    assert CrawlerRegistry.get("duptype") is V2Plugin
