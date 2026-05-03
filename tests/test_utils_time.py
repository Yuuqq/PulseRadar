"""trendradar.utils.time 的单元测试。"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest
import pytz

from trendradar.utils.time import (
    DEFAULT_TIMEZONE,
    TimeWindowChecker,
    calculate_days_old,
    convert_time_for_display,
    format_date_folder,
    format_iso_time_friendly,
    format_time_filename,
    get_configured_time,
    get_current_time_display,
    is_within_days,
)


# ---------- 简单格式化函数 ----------


def test_get_configured_time_returns_aware_datetime() -> None:
    now = get_configured_time("Asia/Shanghai")
    assert now.tzinfo is not None
    assert "Shanghai" in str(now.tzinfo)


def test_get_configured_time_invalid_falls_back() -> None:
    now = get_configured_time("Mars/Olympus")
    assert now.tzinfo is not None  # 回退到默认时区


def test_format_date_folder_explicit_date() -> None:
    assert format_date_folder("2025-01-02") == "2025-01-02"


def test_format_date_folder_default_uses_now() -> None:
    out = format_date_folder()
    assert len(out) == 10 and out[4] == "-" and out[7] == "-"


def test_format_time_filename_uses_dash() -> None:
    out = format_time_filename()
    assert len(out) == 5 and out[2] == "-"


def test_get_current_time_display_uses_colon() -> None:
    out = get_current_time_display()
    assert len(out) == 5 and out[2] == ":"


# ---------- convert_time_for_display ----------


def test_convert_time_for_display_normal() -> None:
    assert convert_time_for_display("10-30") == "10:30"


def test_convert_time_for_display_passthrough_unknown() -> None:
    assert convert_time_for_display("abc") == "abc"
    assert convert_time_for_display("") == ""
    assert convert_time_for_display("12:34") == "12:34"


# ---------- format_iso_time_friendly ----------


def test_format_iso_time_friendly_with_z() -> None:
    out = format_iso_time_friendly("2025-12-29T00:20:00Z", timezone="UTC")
    assert out == "12-29 00:20"


def test_format_iso_time_friendly_with_offset() -> None:
    out = format_iso_time_friendly("2025-12-29T00:20:00+00:00", timezone="UTC")
    assert out == "12-29 00:20"


def test_format_iso_time_friendly_naive_assumed_utc() -> None:
    out = format_iso_time_friendly("2025-12-29T00:20:00", timezone="UTC")
    assert out == "12-29 00:20"


def test_format_iso_time_friendly_no_date() -> None:
    out = format_iso_time_friendly("2025-12-29T00:20:00Z", timezone="UTC", include_date=False)
    assert out == "00:20"


def test_format_iso_time_friendly_empty() -> None:
    assert format_iso_time_friendly("") == ""


def test_format_iso_time_friendly_invalid_returns_simplified() -> None:
    out = format_iso_time_friendly("garbage")
    assert out == "garbage"


def test_format_iso_time_friendly_unknown_timezone_falls_back() -> None:
    out = format_iso_time_friendly("2025-12-29T00:20:00Z", timezone="Mars/Olympus")
    assert "12-29" in out


def test_format_iso_time_friendly_timezone_conversion() -> None:
    """UTC 00:20 在 Asia/Shanghai (+08) 应为 08:20。"""
    out = format_iso_time_friendly("2025-12-29T00:20:00Z", timezone="Asia/Shanghai")
    assert out == "12-29 08:20"


# ---------- is_within_days ----------


def test_is_within_days_empty_or_disabled() -> None:
    assert is_within_days("", 3) is True
    assert is_within_days("2020-01-01T00:00:00Z", 0) is True
    assert is_within_days("2020-01-01T00:00:00Z", -1) is True


def test_is_within_days_recent_returns_true() -> None:
    now = datetime.now(pytz.UTC)
    iso = now.isoformat()
    assert is_within_days(iso, 3) is True


def test_is_within_days_old_returns_false() -> None:
    assert is_within_days("2000-01-01T00:00:00Z", 3) is False


def test_is_within_days_unparseable_returns_true() -> None:
    """无法解析时保留文章。"""
    assert is_within_days("not-a-date", 3) is True


# ---------- calculate_days_old ----------


def test_calculate_days_old_empty_returns_none() -> None:
    assert calculate_days_old("") is None


def test_calculate_days_old_unparseable_returns_none() -> None:
    assert calculate_days_old("garbage") is None


def test_calculate_days_old_old_date_positive() -> None:
    days = calculate_days_old("2000-01-01T00:00:00Z")
    assert days is not None and days > 1000


# ---------- TimeWindowChecker ----------


def _checker_at(time_str: str) -> TimeWindowChecker:
    """构造一个返回固定时间的 checker。"""
    fake_dt = datetime.strptime(time_str, "%H:%M").replace(
        tzinfo=pytz.timezone(DEFAULT_TIMEZONE)
    )
    return TimeWindowChecker(MagicMock(), get_time_func=lambda: fake_dt)


def test_window_normal_range_inside() -> None:
    c = _checker_at("12:00")
    assert c.is_in_time_range("09:00", "21:00") is True


def test_window_normal_range_outside() -> None:
    c = _checker_at("23:00")
    assert c.is_in_time_range("09:00", "21:00") is False


def test_window_overnight_range_late() -> None:
    c = _checker_at("23:30")
    assert c.is_in_time_range("22:00", "02:00") is True


def test_window_overnight_range_early() -> None:
    c = _checker_at("01:30")
    assert c.is_in_time_range("22:00", "02:00") is True


def test_window_overnight_range_outside() -> None:
    c = _checker_at("12:00")
    assert c.is_in_time_range("22:00", "02:00") is False


def test_window_normalize_invalid_format() -> None:
    c = _checker_at("12:00")
    assert c._normalize_time("bad-time") == "bad-time"
    assert c._normalize_time("25:00") == "25:00"


def test_window_normalize_pads_single_digit() -> None:
    c = _checker_at("12:00")
    assert c._normalize_time("9:5") == "09:05"


def test_check_window_disabled_passes() -> None:
    c = _checker_at("12:00")
    proceed, _ = c.check_window({"ENABLED": False})
    assert proceed is True


def test_check_window_outside_range_blocks() -> None:
    c = _checker_at("23:00")
    proceed, reason = c.check_window(
        {
            "ENABLED": True,
            "TIME_RANGE": {"START": "09:00", "END": "21:00"},
            "ONCE_PER_DAY": False,
        }
    )
    assert proceed is False
    assert "不在窗口" in reason


def test_check_window_inside_range_passes() -> None:
    c = _checker_at("12:00")
    proceed, reason = c.check_window(
        {
            "ENABLED": True,
            "TIME_RANGE": {"START": "09:00", "END": "21:00"},
            "ONCE_PER_DAY": False,
        }
    )
    assert proceed is True
    assert "在窗口" in reason


def test_check_window_once_per_day_blocked_when_executed() -> None:
    c = _checker_at("12:00")
    proceed, reason = c.check_window(
        {
            "ENABLED": True,
            "TIME_RANGE": {"START": "09:00", "END": "21:00"},
            "ONCE_PER_DAY": True,
        },
        check_once_per_day_func=lambda: True,
    )
    assert proceed is False
    assert "今天已执行过" in reason


def test_check_window_once_per_day_allowed_when_not_executed() -> None:
    c = _checker_at("12:00")
    proceed, _ = c.check_window(
        {
            "ENABLED": True,
            "TIME_RANGE": {"START": "09:00", "END": "21:00"},
            "ONCE_PER_DAY": True,
        },
        check_once_per_day_func=lambda: False,
    )
    assert proceed is True


def test_get_status_returns_full_dict() -> None:
    c = _checker_at("12:00")
    status = c.get_status(
        {
            "ENABLED": True,
            "TIME_RANGE": {"START": "09:00", "END": "21:00"},
            "ONCE_PER_DAY": True,
        },
        check_once_per_day_func=lambda: False,
    )
    assert status["enabled"] is True
    assert status["in_window"] is True
    assert status["executed_today"] is False
    assert status["window_start"] == "09:00"


def test_get_status_disabled() -> None:
    c = _checker_at("12:00")
    status = c.get_status({"ENABLED": False})
    assert status["enabled"] is False
    assert "in_window" not in status


# Avoid unused-import lint warnings
_ = pytest
