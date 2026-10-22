"""单元测试：trendradar.core.mode_strategies 单一权威表 + 类型化辅助。"""

from __future__ import annotations

import pytest

from trendradar.core.analysis_engine import AnalysisEngine
from trendradar.core.mode_strategies import (
    DEFAULT_REPORT_MODE,
    MODE_STRATEGIES,
    ModeStrategy,
    get_mode_strategy,
)


def test_mode_strategies_has_three_canonical_modes():
    assert set(MODE_STRATEGIES.keys()) == {"incremental", "current", "daily"}


def test_default_mode_is_daily():
    assert DEFAULT_REPORT_MODE == "daily"


@pytest.mark.parametrize("mode", ["incremental", "current", "daily"])
def test_each_mode_has_required_typeddict_fields(mode):
    strategy = MODE_STRATEGIES[mode]
    # 所有 ModeStrategy 字段必须存在且非空
    assert isinstance(strategy["mode_name"], str) and strategy["mode_name"]
    assert isinstance(strategy["description"], str) and strategy["description"]
    assert isinstance(strategy["report_type"], str) and strategy["report_type"]
    assert isinstance(strategy["should_send_notification"], bool)


def test_get_mode_strategy_known_mode_returns_exact_entry():
    assert get_mode_strategy("incremental") is MODE_STRATEGIES["incremental"]
    assert get_mode_strategy("current") is MODE_STRATEGIES["current"]
    assert get_mode_strategy("daily") is MODE_STRATEGIES["daily"]


def test_get_mode_strategy_unknown_falls_back_to_daily():
    fallback = get_mode_strategy("nonexistent_mode")
    assert fallback is MODE_STRATEGIES["daily"]
    assert fallback["report_type"] == "全天汇总"


def test_get_mode_strategy_empty_string_falls_back():
    assert get_mode_strategy("") is MODE_STRATEGIES[DEFAULT_REPORT_MODE]


def test_analysis_engine_class_attr_is_same_object():
    """AnalysisEngine.MODE_STRATEGIES 是模块级表的别名，不是独立副本。

    这是关键去重断言：旧实现在 AnalysisEngine 内复制了一份 dict 字面量，
    Task 6 把它收敛为单一权威来源后，二者必须 is 同一对象。
    """
    assert AnalysisEngine.MODE_STRATEGIES is MODE_STRATEGIES


def test_modestrategy_typeddict_keys_match_runtime_data():
    """TypedDict 注解的字段集合必须和实际数据 key 一致。"""
    declared = set(ModeStrategy.__annotations__.keys())
    for mode, strategy in MODE_STRATEGIES.items():
        assert set(strategy.keys()) == declared, f"{mode} 的 key 与 ModeStrategy 不一致"
