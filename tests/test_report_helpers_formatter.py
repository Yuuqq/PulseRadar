"""trendradar.report.helpers 与 trendradar.report.formatter 的单元测试。"""

from __future__ import annotations

import pytest

from trendradar.report.formatter import format_title_for_platform
from trendradar.report.helpers import clean_title, format_rank_display, html_escape


# ---------- clean_title ----------


def test_clean_title_strips_newlines_and_collapses_whitespace() -> None:
    assert clean_title("hello\n  world\r\n!") == "hello world !"


def test_clean_title_trims_edges() -> None:
    assert clean_title("   foo  ") == "foo"


def test_clean_title_handles_non_string() -> None:
    assert clean_title(123) == "123"  # type: ignore[arg-type]


# ---------- html_escape ----------


def test_html_escape_replaces_special_chars() -> None:
    assert html_escape("<div class=\"x\">A&B'</div>") == (
        "&lt;div class=&quot;x&quot;&gt;A&amp;B&#x27;&lt;/div&gt;"
    )


def test_html_escape_amp_first_avoids_double_escape() -> None:
    """& 必须最先转义，否则会把 &lt; 变成 &amp;lt;。"""
    out = html_escape("a&b<c")
    assert "&amp;" in out
    assert "&amp;lt;" not in out


def test_html_escape_handles_non_string() -> None:
    assert html_escape(42) == "42"  # type: ignore[arg-type]


# ---------- format_rank_display ----------


def test_format_rank_display_empty_returns_empty() -> None:
    assert format_rank_display([], 5, "html") == ""


def test_format_rank_display_single_rank_highlight() -> None:
    out = format_rank_display([1], 5, "html")
    assert "<font color='red'><strong>" in out
    assert "[1]" in out


def test_format_rank_display_no_highlight_when_above_threshold() -> None:
    out = format_rank_display([10], 5, "html")
    assert "<strong>" not in out
    assert out.startswith("[10]")


def test_format_rank_display_range() -> None:
    out = format_rank_display([1, 5], 5, "html")
    assert "[1 - 5]" in out


@pytest.mark.parametrize(
    "platform,expected_substr",
    [
        ("feishu", "<font color='red'>**"),
        ("dingtalk", "**"),
        ("wework", "**"),
        ("telegram", "<b>"),
        ("slack", "*"),
        ("unknown", "**"),
    ],
)
def test_format_rank_display_platform_highlight_styles(
    platform: str, expected_substr: str
) -> None:
    out = format_rank_display([1], 5, platform)
    assert expected_substr in out


def test_format_rank_display_trend_arrow_rising() -> None:
    out = format_rank_display([5, 3], 10, "html")
    assert "🔺" in out


def test_format_rank_display_trend_arrow_falling() -> None:
    out = format_rank_display([3, 5], 10, "html")
    assert "🔻" in out


def test_format_rank_display_trend_arrow_flat() -> None:
    out = format_rank_display([3, 3], 10, "html")
    assert "➖" in out


def test_format_rank_display_no_arrow_for_single() -> None:
    out = format_rank_display([3], 10, "html")
    assert "🔺" not in out and "🔻" not in out and "➖" not in out


# ---------- format_title_for_platform ----------


def _data(**overrides) -> dict:
    base = {
        "title": "苹果发布新品",
        "source_name": "微博",
        "time_display": "10:30",
        "count": 1,
        "ranks": [1],
        "rank_threshold": 5,
        "url": "https://example.com/a",
        "mobile_url": "https://m.example.com/a",
        "is_new": False,
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    "platform", ["feishu", "dingtalk", "wework", "bark", "telegram", "ntfy", "slack", "html"]
)
def test_format_title_for_each_platform_returns_string(platform: str) -> None:
    out = format_title_for_platform(platform, _data())
    assert isinstance(out, str) and len(out) > 0


def test_format_title_html_escapes_dangerous_chars() -> None:
    out = format_title_for_platform("html", _data(title="<script>alert(1)</script>"))
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_format_title_telegram_uses_anchor_tag() -> None:
    out = format_title_for_platform("telegram", _data())
    assert '<a href="https://m.example.com/a">' in out


def test_format_title_slack_uses_pipe_link() -> None:
    out = format_title_for_platform("slack", _data())
    assert "<https://m.example.com/a|" in out


def test_format_title_prefers_mobile_url() -> None:
    """mobile_url 优先于 url。"""
    out = format_title_for_platform("feishu", _data())
    assert "https://m.example.com/a" in out
    assert "https://example.com/a" not in out


def test_format_title_falls_back_to_url_when_mobile_missing() -> None:
    out = format_title_for_platform("feishu", _data(mobile_url=""))
    assert "https://example.com/a" in out


def test_format_title_is_new_prefix() -> None:
    out = format_title_for_platform("feishu", _data(is_new=True))
    assert "🆕" in out


def test_format_title_html_is_new_wraps_in_div() -> None:
    out = format_title_for_platform("html", _data(is_new=True))
    assert "<div class='new-title'>" in out


def test_format_title_count_suffix_only_when_gt_one() -> None:
    one = format_title_for_platform("feishu", _data(count=1))
    many = format_title_for_platform("feishu", _data(count=3))
    assert "次" not in one
    assert "(3次)" in many


def test_format_title_show_keyword_mode() -> None:
    out = format_title_for_platform(
        "feishu", _data(matched_keyword="苹果"), show_source=False, show_keyword=True
    )
    assert "[苹果]" in out


def test_format_title_unknown_platform_returns_clean_title() -> None:
    out = format_title_for_platform("nonexistent", _data())
    assert out == "苹果发布新品"


def test_format_title_handles_no_link() -> None:
    out = format_title_for_platform("feishu", _data(url="", mobile_url=""))
    # 没有 url 时不应输出 markdown 链接语法
    assert "](" not in out
