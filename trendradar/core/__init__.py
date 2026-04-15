"""
核心模块 - 配置管理和核心工具
"""

from trendradar.core.analyzer import (
    calculate_news_weight,
    count_rss_frequency,
    count_word_frequency,
    format_time_display,
)
from trendradar.core.config import (
    get_account_at_index,
    limit_accounts,
    parse_multi_account_config,
    validate_paired_configs,
)
from trendradar.core.data import (
    detect_latest_new_titles,
    detect_latest_new_titles_from_storage,
    read_all_today_titles,
    read_all_today_titles_from_storage,
    save_titles_to_file,
)
from trendradar.core.frequency import load_frequency_words, matches_word_groups
from trendradar.core.loader import load_config

__all__ = [
    # 统计分析
    "calculate_news_weight",
    "count_rss_frequency",
    "count_word_frequency",
    "detect_latest_new_titles",
    "detect_latest_new_titles_from_storage",
    "format_time_display",
    "get_account_at_index",
    "limit_accounts",
    "load_config",
    "load_frequency_words",
    "matches_word_groups",
    "parse_multi_account_config",
    "read_all_today_titles",
    "read_all_today_titles_from_storage",
    # 数据处理
    "save_titles_to_file",
    "validate_paired_configs",
]
