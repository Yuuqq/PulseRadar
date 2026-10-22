"""频率词加载与匹配模块的单元测试 (trendradar.core.frequency)。"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from trendradar.core.frequency import (
    _parse_word,
    _word_matches,
    load_frequency_words,
    matches_word_groups,
)


# ---------- _parse_word ----------


def test_parse_plain_word() -> None:
    parsed = _parse_word("北京")
    assert parsed == {
        "word": "北京",
        "is_regex": False,
        "pattern": None,
        "display_name": None,
    }


def test_parse_word_with_display_name() -> None:
    parsed = _parse_word("京东 => 京东集团")
    assert parsed["word"] == "京东"
    assert parsed["display_name"] == "京东集团"
    assert parsed["is_regex"] is False


def test_parse_regex_word() -> None:
    parsed = _parse_word("/京东|刘强东/i")
    assert parsed["is_regex"] is True
    assert parsed["pattern"] is not None
    assert parsed["pattern"].search("京东618")
    assert parsed["pattern"].search("刘强东事件")


def test_parse_regex_with_display_name() -> None:
    parsed = _parse_word("/京东|刘强东/ => 京东")
    assert parsed["is_regex"] is True
    assert parsed["display_name"] == "京东"


def test_parse_invalid_regex_falls_back_to_plain() -> None:
    parsed = _parse_word("/[unclosed/")
    # 无效正则会回退为普通字符串
    assert parsed["is_regex"] is False
    assert "[unclosed" in parsed["word"]


def test_parse_word_empty_display_name_arrow() -> None:
    """=> 后无内容不应被识别为 display_name。"""
    parsed = _parse_word("hello =>")
    assert parsed["word"] == "hello"
    assert parsed["display_name"] is None


# ---------- _word_matches ----------


def test_word_matches_legacy_string() -> None:
    assert _word_matches("北京", "今日北京天气") is True
    assert _word_matches("上海", "今日北京天气") is False


def test_word_matches_dict_substring() -> None:
    word_cfg = {"word": "京东", "is_regex": False, "pattern": None}
    assert _word_matches(word_cfg, "京东618大促") is True
    assert _word_matches(word_cfg, "苹果发布会") is False


def test_word_matches_dict_regex() -> None:
    parsed = _parse_word("/(\\d+)折/")
    assert _word_matches(parsed, "京东5折促销") is True
    assert _word_matches(parsed, "京东无折扣") is False


# ---------- load_frequency_words ----------


def _write_freq(tmp_path: Path, content: str) -> str:
    p = tmp_path / "frequency.txt"
    p.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    return str(p)


def test_load_simple_groups(tmp_path: Path) -> None:
    path = _write_freq(
        tmp_path,
        """
        京东
        刘强东

        小米
        雷军
        """,
    )
    groups, filters, globals_ = load_frequency_words(path)
    assert len(groups) == 2
    assert globals_ == []
    assert filters == []
    keys = {g["group_key"] for g in groups}
    assert "京东 刘强东" in keys
    assert "小米 雷军" in keys


def test_load_required_words(tmp_path: Path) -> None:
    path = _write_freq(
        tmp_path,
        """
        +Apple
        +Watch
        """,
    )
    groups, _, _ = load_frequency_words(path)
    assert len(groups) == 1
    assert len(groups[0]["required"]) == 2
    assert groups[0]["normal"] == []


def test_load_filter_words(tmp_path: Path) -> None:
    path = _write_freq(
        tmp_path,
        """
        华为
        !广告
        !推广
        """,
    )
    groups, filters, _ = load_frequency_words(path)
    assert len(groups) == 1
    assert len(filters) == 2
    assert any(f["word"] == "广告" for f in filters)


def test_load_max_count(tmp_path: Path) -> None:
    path = _write_freq(
        tmp_path,
        """
        高考
        @5
        """,
    )
    groups, _, _ = load_frequency_words(path)
    assert groups[0]["max_count"] == 5


def test_load_invalid_max_count_ignored(tmp_path: Path) -> None:
    path = _write_freq(
        tmp_path,
        """
        高考
        @abc
        @-3
        """,
    )
    groups, _, _ = load_frequency_words(path)
    assert groups[0]["max_count"] == 0


def test_load_global_filter_section(tmp_path: Path) -> None:
    path = _write_freq(
        tmp_path,
        """
        [GLOBAL_FILTER]
        广告
        推广

        [WORD_GROUPS]
        华为
        """,
    )
    groups, _, globals_ = load_frequency_words(path)
    assert "广告" in globals_ and "推广" in globals_
    assert len(groups) == 1


def test_load_group_alias(tmp_path: Path) -> None:
    path = _write_freq(
        tmp_path,
        """
        [科技公司]
        苹果
        华为
        """,
    )
    groups, _, _ = load_frequency_words(path)
    assert groups[0]["display_name"] == "科技公司"


def test_load_skips_comments_and_blank_lines(tmp_path: Path) -> None:
    path = _write_freq(
        tmp_path,
        """
        # 这是注释
        正常词

        # 另一组的注释
        另一词
        """,
    )
    groups, _, _ = load_frequency_words(path)
    assert len(groups) == 2


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_frequency_words(str(tmp_path / "nope.txt"))


def test_load_global_filter_ignores_special_prefixes(tmp_path: Path) -> None:
    """全局过滤区不支持 +/!/@ 语法，应被跳过。"""
    path = _write_freq(
        tmp_path,
        """
        [GLOBAL_FILTER]
        广告
        !忽略我
        +也忽略
        @123

        [WORD_GROUPS]
        测试
        """,
    )
    _, _, globals_ = load_frequency_words(path)
    assert globals_ == ["广告"]


def test_load_display_name_with_aliases(tmp_path: Path) -> None:
    path = _write_freq(
        tmp_path,
        """
        京东 => 京东集团
        阿里
        """,
    )
    groups, _, _ = load_frequency_words(path)
    assert groups[0]["display_name"] == "京东集团 / 阿里"


# ---------- matches_word_groups ----------


def test_matches_global_filter_takes_priority() -> None:
    groups = [{"required": [], "normal": [_parse_word("华为")], "group_key": "华为"}]
    assert matches_word_groups("华为新品", groups, [], None) is True
    assert matches_word_groups("华为广告", groups, [], ["广告"]) is False


def test_matches_filter_word() -> None:
    groups = [{"required": [], "normal": [_parse_word("苹果")], "group_key": "苹果"}]
    filters = [_parse_word("广告")]
    assert matches_word_groups("苹果发布会", groups, filters) is True
    assert matches_word_groups("苹果广告", groups, filters) is False


def test_matches_required_words_logic() -> None:
    groups = [
        {
            "required": [_parse_word("Apple"), _parse_word("Watch")],
            "normal": [],
            "group_key": "Apple Watch",
        }
    ]
    assert matches_word_groups("Apple Watch released", groups, []) is True
    assert matches_word_groups("Apple iPhone released", groups, []) is False


def test_matches_normal_any_logic() -> None:
    groups = [
        {
            "required": [],
            "normal": [_parse_word("北京"), _parse_word("上海")],
            "group_key": "北京 上海",
        }
    ]
    assert matches_word_groups("今日北京", groups, []) is True
    assert matches_word_groups("今日广州", groups, []) is False


def test_matches_empty_word_groups_returns_true() -> None:
    assert matches_word_groups("任何标题", [], []) is True


def test_matches_non_string_title() -> None:
    groups = [{"required": [], "normal": [_parse_word("test")], "group_key": "test"}]
    # 防御性类型转换
    assert matches_word_groups(None, groups, []) is False  # type: ignore[arg-type]
    assert matches_word_groups(123, groups, []) is False  # type: ignore[arg-type]
