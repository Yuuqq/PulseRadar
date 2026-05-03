"""trendradar.core.analyzer 的单元测试。"""

from __future__ import annotations

from trendradar.core.analyzer import (
    calculate_news_weight,
    count_word_frequency,
    format_time_display,
)
from trendradar.core.frequency import _parse_word


WEIGHT = {"RANK_WEIGHT": 0.6, "FREQUENCY_WEIGHT": 0.3, "HOTNESS_WEIGHT": 0.1}


# ---------- calculate_news_weight ----------


def test_weight_zero_when_no_ranks() -> None:
    assert calculate_news_weight({"ranks": [], "count": 0}, 5, WEIGHT) == 0.0


def test_weight_high_rank_higher_score() -> None:
    high = calculate_news_weight({"ranks": [1, 1, 1], "count": 3}, 5, WEIGHT)
    low = calculate_news_weight({"ranks": [10, 10, 10], "count": 3}, 5, WEIGHT)
    assert high > low


def test_weight_handles_rank_clamp() -> None:
    """rank>10 时 score 应等同于 rank=10。"""
    a = calculate_news_weight({"ranks": [50], "count": 1}, 5, WEIGHT)
    b = calculate_news_weight({"ranks": [10], "count": 1}, 5, WEIGHT)
    assert a == b


def test_weight_frequency_capped_at_10() -> None:
    """count 超过 10 后频次权重不再增加。"""
    w10 = calculate_news_weight({"ranks": [5] * 10, "count": 10}, 5, WEIGHT)
    w20 = calculate_news_weight({"ranks": [5] * 20, "count": 20}, 5, WEIGHT)
    assert w20 == w10


def test_weight_uses_count_default_when_missing() -> None:
    res = calculate_news_weight({"ranks": [3, 3]}, 5, WEIGHT)
    assert res > 0


# ---------- format_time_display ----------


def test_format_time_display_empty_first() -> None:
    assert format_time_display("", "10-30", lambda x: x.replace("-", ":")) == ""


def test_format_time_display_same_time() -> None:
    out = format_time_display("10-30", "10-30", lambda x: x.replace("-", ":"))
    assert out == "10:30"


def test_format_time_display_range() -> None:
    out = format_time_display("10-30", "12-45", lambda x: x.replace("-", ":"))
    assert out == "[10:30 ~ 12:45]"


def test_format_time_display_empty_last() -> None:
    out = format_time_display("10-30", "", lambda x: x.replace("-", ":"))
    assert out == "10:30"


# ---------- count_word_frequency ----------


def _make_results() -> dict:
    return {
        "src1": {
            "苹果发布新品": {"ranks": [1], "url": "https://a.example", "mobileUrl": ""},
            "广告内容": {"ranks": [2], "url": "https://b.example", "mobileUrl": ""},
            "无关新闻": {"ranks": [5], "url": "https://c.example", "mobileUrl": ""},
        },
        "src2": {
            "华为新机发布": {"ranks": [1], "url": "https://d.example", "mobileUrl": ""},
        },
    }


def test_count_word_frequency_filters_and_groups() -> None:
    word_groups = [
        {
            "required": [],
            "normal": [_parse_word("苹果"), _parse_word("华为")],
            "group_key": "苹果 华为",
            "max_count": 0,
        }
    ]
    filters = [_parse_word("广告")]
    id_to_name = {"src1": "源1", "src2": "源2"}

    stats, total = count_word_frequency(
        _make_results(),
        word_groups,
        filters,
        id_to_name,
        mode="daily",
        weight_config=WEIGHT,
        quiet=True,
    )

    assert total == 4
    assert len(stats) == 1
    titles = stats[0]["titles"]
    titles_text = {t["title"] for t in titles}
    assert "苹果发布新品" in titles_text
    assert "华为新机发布" in titles_text
    assert "广告内容" not in titles_text  # 被过滤


def test_count_word_frequency_empty_word_groups_shows_all() -> None:
    stats, total = count_word_frequency(
        _make_results(),
        [],
        [],
        {"src1": "s1", "src2": "s2"},
        mode="daily",
        quiet=True,
    )
    assert total == 4
    assert stats[0]["word"] == "全部新闻"
    assert stats[0]["count"] == 4


def test_count_word_frequency_global_filter_priority() -> None:
    word_groups = [
        {
            "required": [],
            "normal": [_parse_word("苹果")],
            "group_key": "苹果",
            "max_count": 0,
        }
    ]
    stats, _ = count_word_frequency(
        {"src1": {"苹果发布新品": {"ranks": [1], "url": "", "mobileUrl": ""}}},
        word_groups,
        [],
        {"src1": "s1"},
        mode="daily",
        global_filters=["发布"],
        quiet=True,
    )
    assert sum(s["count"] for s in stats) == 0


def test_count_word_frequency_max_news_per_keyword_limit() -> None:
    word_groups = [
        {
            "required": [],
            "normal": [_parse_word("新闻")],
            "group_key": "新闻",
            "max_count": 0,
        }
    ]
    results = {
        "s1": {
            f"新闻 {i}": {"ranks": [i + 1], "url": "", "mobileUrl": ""} for i in range(10)
        }
    }
    stats, _ = count_word_frequency(
        results,
        word_groups,
        [],
        {"s1": "s1"},
        mode="daily",
        max_news_per_keyword=3,
        weight_config=WEIGHT,
        quiet=True,
    )
    assert len(stats[0]["titles"]) == 3


def test_count_word_frequency_max_keywords_limit() -> None:
    word_groups = [
        {
            "required": [],
            "normal": [_parse_word(w)],
            "group_key": w,
            "max_count": 0,
        }
        for w in ("aa", "bb", "cc", "dd")
    ]
    results = {
        "s1": {
            f"{w} 标题 {i}": {"ranks": [1], "url": "", "mobileUrl": ""}
            for w in ("aa", "bb", "cc", "dd")
            for i in range(2)
        }
    }
    stats, _ = count_word_frequency(
        results,
        word_groups,
        [],
        {"s1": "s1"},
        mode="daily",
        max_keywords=2,
        weight_config=WEIGHT,
        quiet=True,
    )
    assert len(stats) == 2


def test_count_word_frequency_incremental_first_today_marks_all_new() -> None:
    word_groups = [
        {"required": [], "normal": [_parse_word("苹果")], "group_key": "苹果", "max_count": 0}
    ]
    stats, _ = count_word_frequency(
        {"s1": {"苹果发布": {"ranks": [1], "url": "", "mobileUrl": ""}}},
        word_groups,
        [],
        {"s1": "s1"},
        mode="incremental",
        is_first_crawl_func=lambda: True,
        weight_config=WEIGHT,
        quiet=True,
    )
    assert all(t["is_new"] for t in stats[0]["titles"])


def test_count_word_frequency_incremental_non_first_uses_new_titles_only() -> None:
    word_groups = [
        {"required": [], "normal": [_parse_word("苹果")], "group_key": "苹果", "max_count": 0}
    ]
    stats, _ = count_word_frequency(
        {"s1": {"苹果旧闻": {"ranks": [3], "url": "", "mobileUrl": ""}}},
        word_groups,
        [],
        {"s1": "s1"},
        new_titles={"s1": {"苹果新闻": {"ranks": [1], "url": "", "mobileUrl": ""}}},
        mode="incremental",
        is_first_crawl_func=lambda: False,
        weight_config=WEIGHT,
        quiet=True,
    )
    titles = {t["title"] for t in stats[0]["titles"]}
    assert "苹果新闻" in titles
    assert "苹果旧闻" not in titles


def test_count_word_frequency_sort_by_position_first() -> None:
    word_groups = [
        {"required": [], "normal": [_parse_word("a")], "group_key": "a", "max_count": 0},
        {"required": [], "normal": [_parse_word("b")], "group_key": "b", "max_count": 0},
    ]
    # b 数量更多，但 a 在前 — 按位置排序时 a 应排第一
    results = {
        "s1": {
            "a 1": {"ranks": [1], "url": "", "mobileUrl": ""},
            "b 1": {"ranks": [1], "url": "", "mobileUrl": ""},
            "b 2": {"ranks": [1], "url": "", "mobileUrl": ""},
            "b 3": {"ranks": [1], "url": "", "mobileUrl": ""},
        }
    }
    stats, _ = count_word_frequency(
        results,
        word_groups,
        [],
        {"s1": "s1"},
        mode="daily",
        sort_by_position_first=True,
        weight_config=WEIGHT,
        quiet=True,
    )
    assert stats[0]["word"] == "a"

    stats2, _ = count_word_frequency(
        results,
        word_groups,
        [],
        {"s1": "s1"},
        mode="daily",
        sort_by_position_first=False,
        weight_config=WEIGHT,
        quiet=True,
    )
    assert stats2[0]["word"] == "b"  # 按数量优先时 b 在前
