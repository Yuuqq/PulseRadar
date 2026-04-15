"""
消息分批处理模块

提供消息内容分批拆分功能，确保消息大小不超过各平台限制
"""

from collections.abc import Callable
from datetime import datetime

from trendradar.notification.split_rss import (
    _process_rss_new_titles_section,
    _process_rss_stats_section,
)
from trendradar.notification.split_standalone import _process_standalone_section
from trendradar.report.formatter import format_title_for_platform
from trendradar.utils.time import DEFAULT_TIMEZONE

# 默认批次大小配置
DEFAULT_BATCH_SIZES = {
    "dingtalk": 20000,
    "feishu": 29000,
    "ntfy": 3800,
    "default": 4000,
}

# 默认区域顺序
DEFAULT_REGION_ORDER = ["hotlist", "rss", "new_items", "standalone", "ai_analysis"]


def split_content_into_batches(
    report_data: dict,
    format_type: str,
    update_info: dict | None = None,
    max_bytes: int | None = None,
    mode: str = "daily",
    batch_sizes: dict[str, int] | None = None,
    feishu_separator: str = "---",
    region_order: list[str] | None = None,
    get_time_func: Callable[[], datetime] | None = None,
    rss_items: list | None = None,
    rss_new_items: list | None = None,
    timezone: str = DEFAULT_TIMEZONE,
    display_mode: str = "keyword",
    ai_content: str | None = None,
    standalone_data: dict | None = None,
    rank_threshold: int = 10,
    ai_stats: dict | None = None,
    report_type: str = "热点分析报告",
    show_new_section: bool = True,
) -> list[str]:
    """分批处理消息内容，确保词组标题+至少第一条新闻的完整性（支持热榜+RSS合并+AI分析+独立展示区）

    热榜统计与RSS统计并列显示，热榜新增与RSS新增并列显示。
    region_order 控制各区域的显示顺序。
    AI分析内容根据 region_order 中的位置显示。
    独立展示区根据 region_order 中的位置显示。

    Args:
        report_data: 报告数据字典，包含 stats, new_titles, failed_ids, total_new_count
        format_type: 格式类型 (feishu, dingtalk, wework, telegram, ntfy, bark, slack)
        update_info: 版本更新信息（可选）
        max_bytes: 最大字节数（可选，如果不指定则使用默认配置）
        mode: 报告模式 (daily, incremental, current)
        batch_sizes: 批次大小配置字典（可选）
        feishu_separator: 飞书消息分隔符
        region_order: 区域显示顺序列表
        get_time_func: 获取当前时间的函数（可选）
        rss_items: RSS 统计条目列表（按源分组，用于合并推送）
        rss_new_items: RSS 新增条目列表（可选，用于新增区块）
        timezone: 时区名称（用于 RSS 时间格式化）
        display_mode: 显示模式 (keyword=按关键词分组, platform=按平台分组)
        ai_content: AI 分析内容（已渲染的字符串，可选）
        standalone_data: 独立展示区数据（可选），包含 platforms 和 rss_feeds 列表
        ai_stats: AI 分析统计数据（可选），包含 total_news, analyzed_news, max_news_limit 等

    Returns:
        分批后的消息内容列表
    """
    if region_order is None:
        region_order = DEFAULT_REGION_ORDER
    # 合并批次大小配置
    sizes = {**DEFAULT_BATCH_SIZES, **(batch_sizes or {})}

    if max_bytes is None:
        if format_type == "dingtalk":
            max_bytes = sizes.get("dingtalk", 20000)
        elif format_type == "feishu":
            max_bytes = sizes.get("feishu", 29000)
        elif format_type == "ntfy":
            max_bytes = sizes.get("ntfy", 3800)
        else:
            max_bytes = sizes.get("default", 4000)

    batches = []

    total_hotlist_count = sum(
        len(stat["titles"]) for stat in report_data["stats"] if stat["count"] > 0
    )
    total_titles = total_hotlist_count
    
    # 累加 RSS 条目数
    if rss_items:
        total_titles += sum(stat.get("count", 0) for stat in rss_items)

    now = get_time_func() if get_time_func else datetime.now()

    # 构建头部信息
    base_header = ""
    
    # 准备 AI 分析统计行（如果存在）
    ai_stats_line = ""
    if ai_stats and ai_stats.get("analyzed_news", 0) > 0:
        analyzed_news = ai_stats.get("analyzed_news", 0)
        total_news = ai_stats.get("total_news", 0)
        ai_mode = ai_stats.get("ai_mode", "")

        # 构建分析数显示：如果被截断则显示 "实际分析数/总可分析数"
        if total_news > analyzed_news:
            news_display = f"{analyzed_news}/{total_news}"
        else:
            news_display = str(analyzed_news)

        # 如果 AI 模式与推送模式不同，显示模式标识
        mode_suffix = ""
        if ai_mode and ai_mode != mode:
            mode_map = {
                "daily": "全天汇总",
                "current": "当前榜单",
                "incremental": "增量分析"
            }
            mode_label = mode_map.get(ai_mode, ai_mode)
            mode_suffix = f" ({mode_label})"

        if format_type in ("wework", "bark", "ntfy", "feishu", "dingtalk"):
            ai_stats_line = f"**AI 分析数：** {news_display}{mode_suffix}\n"
        elif format_type == "slack":
            ai_stats_line = f"*AI 分析数：* {news_display}{mode_suffix}\n"
        elif format_type == "telegram":
            ai_stats_line = f"AI 分析数： {news_display}{mode_suffix}\n"

    # 构建统一的头部（总是显示总新闻数、时间和类型）
    if format_type in ("wework", "bark"):
        base_header = f"**总新闻数：** {total_titles}\n"
        base_header += ai_stats_line
        base_header += f"**时间：** {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        base_header += f"**类型：** {report_type}\n\n"
    elif format_type == "telegram":
        base_header = f"总新闻数： {total_titles}\n"
        base_header += ai_stats_line
        base_header += f"时间： {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        base_header += f"类型： {report_type}\n\n"
    elif format_type == "ntfy":
        base_header = f"**总新闻数：** {total_titles}\n"
        base_header += ai_stats_line
        base_header += f"**时间：** {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        base_header += f"**类型：** {report_type}\n\n"
    elif format_type == "feishu" or format_type == "dingtalk":
        base_header = f"**总新闻数：** {total_titles}\n"
        base_header += ai_stats_line
        base_header += f"**时间：** {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        base_header += f"**类型：** {report_type}\n\n"
        base_header += "---\n\n"
    elif format_type == "slack":
        base_header = f"*总新闻数：* {total_titles}\n"
        base_header += ai_stats_line
        base_header += f"*时间：* {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        base_header += f"*类型：* {report_type}\n\n"

    base_footer = ""
    if format_type in ("wework", "bark"):
        base_footer = f"\n\n\n> 更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}"
        if update_info:
            base_footer += f"\n> TrendRadar 发现新版本 **{update_info['remote_version']}**，当前 **{update_info['current_version']}**"
    elif format_type == "telegram":
        base_footer = f"\n\n更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}"
        if update_info:
            base_footer += f"\nTrendRadar 发现新版本 {update_info['remote_version']}，当前 {update_info['current_version']}"
    elif format_type == "ntfy":
        base_footer = f"\n\n> 更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}"
        if update_info:
            base_footer += f"\n> TrendRadar 发现新版本 **{update_info['remote_version']}**，当前 **{update_info['current_version']}**"
    elif format_type == "feishu":
        base_footer = f"\n\n<font color='grey'>更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}</font>"
        if update_info:
            base_footer += f"\n<font color='grey'>TrendRadar 发现新版本 {update_info['remote_version']}，当前 {update_info['current_version']}</font>"
    elif format_type == "dingtalk":
        base_footer = f"\n\n> 更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}"
        if update_info:
            base_footer += f"\n> TrendRadar 发现新版本 **{update_info['remote_version']}**，当前 **{update_info['current_version']}**"
    elif format_type == "slack":
        base_footer = f"\n\n_更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}_"
        if update_info:
            base_footer += f"\n_TrendRadar 发现新版本 *{update_info['remote_version']}*，当前 *{update_info['current_version']}_"

    # 根据 display_mode 选择统计标题
    stats_title = "热点词汇统计" if display_mode == "keyword" else "热点新闻统计"
    stats_header = ""
    if report_data["stats"]:
        if format_type in ("wework", "bark"):
            stats_header = f"📊 **{stats_title}** (共 {total_hotlist_count} 条)\n\n"
        elif format_type == "telegram":
            stats_header = f"📊 {stats_title} (共 {total_hotlist_count} 条)\n\n"
        elif format_type == "ntfy" or format_type == "feishu" or format_type == "dingtalk":
            stats_header = f"📊 **{stats_title}** (共 {total_hotlist_count} 条)\n\n"
        elif format_type == "slack":
            stats_header = f"📊 *{stats_title}* (共 {total_hotlist_count} 条)\n\n"

    current_batch = base_header
    current_batch_has_content = False

    # 当没有热榜数据时的处理
    # 注意：如果有 ai_content，不应该返回"暂无匹配"消息，而应该继续处理 AI 内容
    if (
        not report_data["stats"]
        and not report_data["new_titles"]
        and not report_data["failed_ids"]
        and not ai_content  # 有 AI 内容时不返回"暂无匹配"
        and not rss_items  # 有 RSS 内容时也不返回
        and not standalone_data  # 有独立展示区数据时也不返回
    ):
        if mode == "incremental":
            mode_text = "增量模式下暂无新增匹配的热点词汇"
        elif mode == "current":
            mode_text = "当前榜单模式下暂无匹配的热点词汇"
        else:
            mode_text = "暂无匹配的热点词汇"
        simple_content = f"📭 {mode_text}\n\n"
        final_content = base_header + simple_content + base_footer
        batches.append(final_content)
        return batches

    # 定义处理热点词汇统计的函数
    def process_stats_section(current_batch, current_batch_has_content, batches, add_separator=True):
        """处理热点词汇统计"""
        if not report_data["stats"]:
            return current_batch, current_batch_has_content, batches

        total_count = len(report_data["stats"])

        # 根据 add_separator 决定是否添加前置分割线
        actual_stats_header = ""
        if add_separator and current_batch_has_content:
            # 需要添加分割线
            if format_type == "feishu":
                actual_stats_header = f"\n{feishu_separator}\n\n{stats_header}"
            elif format_type == "dingtalk":
                actual_stats_header = f"\n---\n\n{stats_header}"
            elif format_type in ("wework", "bark"):
                actual_stats_header = f"\n\n\n\n{stats_header}"
            else:
                actual_stats_header = f"\n\n{stats_header}"
        else:
            # 不需要分割线（第一个区域）
            actual_stats_header = stats_header

        # 添加统计标题
        test_content = current_batch + actual_stats_header
        if (
            len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
            < max_bytes
        ):
            current_batch = test_content
            current_batch_has_content = True
        else:
            if current_batch_has_content:
                batches.append(current_batch + base_footer)
            # 新批次开头不需要分割线，使用原始 stats_header
            current_batch = base_header + stats_header
            current_batch_has_content = True

        # 逐个处理词组（确保词组标题+第一条新闻的原子性）
        for i, stat in enumerate(report_data["stats"]):
            word = stat["word"]
            count = stat["count"]
            sequence_display = f"[{i + 1}/{total_count}]"

            # 构建词组标题
            word_header = ""
            if format_type in ("wework", "bark"):
                if count >= 10:
                    word_header = (
                        f"🔥 {sequence_display} **{word}** : **{count}** 条\n\n"
                    )
                elif count >= 5:
                    word_header = (
                        f"📈 {sequence_display} **{word}** : **{count}** 条\n\n"
                    )
                else:
                    word_header = f"📌 {sequence_display} **{word}** : {count} 条\n\n"
            elif format_type == "telegram":
                if count >= 10:
                    word_header = f"🔥 {sequence_display} {word} : {count} 条\n\n"
                elif count >= 5:
                    word_header = f"📈 {sequence_display} {word} : {count} 条\n\n"
                else:
                    word_header = f"📌 {sequence_display} {word} : {count} 条\n\n"
            elif format_type == "ntfy":
                if count >= 10:
                    word_header = (
                        f"🔥 {sequence_display} **{word}** : **{count}** 条\n\n"
                    )
                elif count >= 5:
                    word_header = (
                        f"📈 {sequence_display} **{word}** : **{count}** 条\n\n"
                    )
                else:
                    word_header = f"📌 {sequence_display} **{word}** : {count} 条\n\n"
            elif format_type == "feishu":
                if count >= 10:
                    word_header = f"🔥 <font color='grey'>{sequence_display}</font> **{word}** : <font color='red'>{count}</font> 条\n\n"
                elif count >= 5:
                    word_header = f"📈 <font color='grey'>{sequence_display}</font> **{word}** : <font color='orange'>{count}</font> 条\n\n"
                else:
                    word_header = f"📌 <font color='grey'>{sequence_display}</font> **{word}** : {count} 条\n\n"
            elif format_type == "dingtalk":
                if count >= 10:
                    word_header = (
                        f"🔥 {sequence_display} **{word}** : **{count}** 条\n\n"
                    )
                elif count >= 5:
                    word_header = (
                        f"📈 {sequence_display} **{word}** : **{count}** 条\n\n"
                    )
                else:
                    word_header = f"📌 {sequence_display} **{word}** : {count} 条\n\n"
            elif format_type == "slack":
                if count >= 10:
                    word_header = (
                        f"🔥 {sequence_display} *{word}* : *{count}* 条\n\n"
                    )
                elif count >= 5:
                    word_header = (
                        f"📈 {sequence_display} *{word}* : *{count}* 条\n\n"
                    )
                else:
                    word_header = f"📌 {sequence_display} *{word}* : {count} 条\n\n"

            # 构建第一条新闻
            # display_mode: keyword=显示来源, platform=显示关键词
            show_source = display_mode == "keyword"
            show_keyword = display_mode == "platform"
            first_news_line = ""
            if stat["titles"]:
                first_title_data = stat["titles"][0]
                if format_type in ("wework", "bark"):
                    formatted_title = format_title_for_platform(
                        "wework", first_title_data, show_source=show_source, show_keyword=show_keyword
                    )
                elif format_type == "telegram":
                    formatted_title = format_title_for_platform(
                        "telegram", first_title_data, show_source=show_source, show_keyword=show_keyword
                    )
                elif format_type == "ntfy":
                    formatted_title = format_title_for_platform(
                        "ntfy", first_title_data, show_source=show_source, show_keyword=show_keyword
                    )
                elif format_type == "feishu":
                    formatted_title = format_title_for_platform(
                        "feishu", first_title_data, show_source=show_source, show_keyword=show_keyword
                    )
                elif format_type == "dingtalk":
                    formatted_title = format_title_for_platform(
                        "dingtalk", first_title_data, show_source=show_source, show_keyword=show_keyword
                    )
                elif format_type == "slack":
                    formatted_title = format_title_for_platform(
                        "slack", first_title_data, show_source=show_source, show_keyword=show_keyword
                    )
                else:
                    formatted_title = f"{first_title_data['title']}"

                first_news_line = f"  1. {formatted_title}\n"
                if len(stat["titles"]) > 1:
                    first_news_line += "\n"

            # 原子性检查：词组标题+第一条新闻必须一起处理
            word_with_first_news = word_header + first_news_line
            test_content = current_batch + word_with_first_news

            if (
                len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                >= max_bytes
            ):
                # 当前批次容纳不下，开启新批次
                if current_batch_has_content:
                    batches.append(current_batch + base_footer)
                current_batch = base_header + stats_header + word_with_first_news
                current_batch_has_content = True
                start_index = 1
            else:
                current_batch = test_content
                current_batch_has_content = True
                start_index = 1

            # 处理剩余新闻条目
            for j in range(start_index, len(stat["titles"])):
                title_data = stat["titles"][j]
                if format_type in ("wework", "bark"):
                    formatted_title = format_title_for_platform(
                        "wework", title_data, show_source=show_source, show_keyword=show_keyword
                    )
                elif format_type == "telegram":
                    formatted_title = format_title_for_platform(
                        "telegram", title_data, show_source=show_source, show_keyword=show_keyword
                    )
                elif format_type == "ntfy":
                    formatted_title = format_title_for_platform(
                        "ntfy", title_data, show_source=show_source, show_keyword=show_keyword
                    )
                elif format_type == "feishu":
                    formatted_title = format_title_for_platform(
                        "feishu", title_data, show_source=show_source, show_keyword=show_keyword
                    )
                elif format_type == "dingtalk":
                    formatted_title = format_title_for_platform(
                        "dingtalk", title_data, show_source=show_source, show_keyword=show_keyword
                    )
                elif format_type == "slack":
                    formatted_title = format_title_for_platform(
                        "slack", title_data, show_source=show_source, show_keyword=show_keyword
                    )
                else:
                    formatted_title = f"{title_data['title']}"

                news_line = f"  {j + 1}. {formatted_title}\n"
                if j < len(stat["titles"]) - 1:
                    news_line += "\n"

                test_content = current_batch + news_line
                if (
                    len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                    >= max_bytes
                ):
                    if current_batch_has_content:
                        batches.append(current_batch + base_footer)
                    current_batch = base_header + stats_header + word_header + news_line
                    current_batch_has_content = True
                else:
                    current_batch = test_content
                    current_batch_has_content = True

            # 词组间分隔符
            if i < len(report_data["stats"]) - 1:
                separator = ""
                if format_type in ("wework", "bark"):
                    separator = "\n\n\n\n"
                elif format_type == "telegram" or format_type == "ntfy":
                    separator = "\n\n"
                elif format_type == "feishu":
                    separator = f"\n{feishu_separator}\n\n"
                elif format_type == "dingtalk":
                    separator = "\n---\n\n"
                elif format_type == "slack":
                    separator = "\n\n"

                test_content = current_batch + separator
                if (
                    len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                    < max_bytes
                ):
                    current_batch = test_content

        return current_batch, current_batch_has_content, batches

    # 定义处理新增新闻的函数
    def process_new_titles_section(current_batch, current_batch_has_content, batches, add_separator=True):
        """处理新增新闻"""
        if not show_new_section or not report_data["new_titles"]:
            return current_batch, current_batch_has_content, batches

        # 根据 add_separator 决定是否添加前置分割线
        new_header = ""
        if add_separator and current_batch_has_content:
            # 需要添加分割线
            if format_type in ("wework", "bark"):
                new_header = f"\n\n\n\n🆕 **本次新增热点新闻** (共 {report_data['total_new_count']} 条)\n\n"
            elif format_type == "telegram":
                new_header = (
                    f"\n\n🆕 本次新增热点新闻 (共 {report_data['total_new_count']} 条)\n\n"
                )
            elif format_type == "ntfy":
                new_header = f"\n\n🆕 **本次新增热点新闻** (共 {report_data['total_new_count']} 条)\n\n"
            elif format_type == "feishu":
                new_header = f"\n{feishu_separator}\n\n🆕 **本次新增热点新闻** (共 {report_data['total_new_count']} 条)\n\n"
            elif format_type == "dingtalk":
                new_header = f"\n---\n\n🆕 **本次新增热点新闻** (共 {report_data['total_new_count']} 条)\n\n"
            elif format_type == "slack":
                new_header = f"\n\n🆕 *本次新增热点新闻* (共 {report_data['total_new_count']} 条)\n\n"
        else:
            # 不需要分割线（第一个区域）
            if format_type in ("wework", "bark"):
                new_header = f"🆕 **本次新增热点新闻** (共 {report_data['total_new_count']} 条)\n\n"
            elif format_type == "telegram":
                new_header = f"🆕 本次新增热点新闻 (共 {report_data['total_new_count']} 条)\n\n"
            elif format_type == "ntfy" or format_type == "feishu" or format_type == "dingtalk":
                new_header = f"🆕 **本次新增热点新闻** (共 {report_data['total_new_count']} 条)\n\n"
            elif format_type == "slack":
                new_header = f"🆕 *本次新增热点新闻* (共 {report_data['total_new_count']} 条)\n\n"

        test_content = current_batch + new_header
        if (
            len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
            >= max_bytes
        ):
            if current_batch_has_content:
                batches.append(current_batch + base_footer)
            current_batch = base_header + new_header
            current_batch_has_content = True
        else:
            current_batch = test_content
            current_batch_has_content = True

        # 逐个处理新增新闻来源
        for source_data in report_data["new_titles"]:
            source_header = ""
            if format_type in ("wework", "bark"):
                source_header = f"**{source_data['source_name']}** ({len(source_data['titles'])} 条):\n\n"
            elif format_type == "telegram":
                source_header = f"{source_data['source_name']} ({len(source_data['titles'])} 条):\n\n"
            elif format_type == "ntfy" or format_type == "feishu" or format_type == "dingtalk":
                source_header = f"**{source_data['source_name']}** ({len(source_data['titles'])} 条):\n\n"
            elif format_type == "slack":
                source_header = f"*{source_data['source_name']}* ({len(source_data['titles'])} 条):\n\n"

            # 构建第一条新增新闻
            first_news_line = ""
            if source_data["titles"]:
                first_title_data = source_data["titles"][0]
                title_data_copy = first_title_data.copy()
                title_data_copy["is_new"] = False

                if format_type in ("wework", "bark"):
                    formatted_title = format_title_for_platform(
                        "wework", title_data_copy, show_source=False
                    )
                elif format_type == "telegram":
                    formatted_title = format_title_for_platform(
                        "telegram", title_data_copy, show_source=False
                    )
                elif format_type == "feishu":
                    formatted_title = format_title_for_platform(
                        "feishu", title_data_copy, show_source=False
                    )
                elif format_type == "dingtalk":
                    formatted_title = format_title_for_platform(
                        "dingtalk", title_data_copy, show_source=False
                    )
                elif format_type == "slack":
                    formatted_title = format_title_for_platform(
                        "slack", title_data_copy, show_source=False
                    )
                else:
                    formatted_title = f"{title_data_copy['title']}"

                first_news_line = f"  1. {formatted_title}\n"

            # 原子性检查：来源标题+第一条新闻
            source_with_first_news = source_header + first_news_line
            test_content = current_batch + source_with_first_news

            if (
                len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                >= max_bytes
            ):
                if current_batch_has_content:
                    batches.append(current_batch + base_footer)
                current_batch = base_header + new_header + source_with_first_news
                current_batch_has_content = True
                start_index = 1
            else:
                current_batch = test_content
                current_batch_has_content = True
                start_index = 1

            # 处理剩余新增新闻
            for j in range(start_index, len(source_data["titles"])):
                title_data = source_data["titles"][j]
                title_data_copy = title_data.copy()
                title_data_copy["is_new"] = False

                if format_type == "wework":
                    formatted_title = format_title_for_platform(
                        "wework", title_data_copy, show_source=False
                    )
                elif format_type == "telegram":
                    formatted_title = format_title_for_platform(
                        "telegram", title_data_copy, show_source=False
                    )
                elif format_type == "feishu":
                    formatted_title = format_title_for_platform(
                        "feishu", title_data_copy, show_source=False
                    )
                elif format_type == "dingtalk":
                    formatted_title = format_title_for_platform(
                        "dingtalk", title_data_copy, show_source=False
                    )
                elif format_type == "slack":
                    formatted_title = format_title_for_platform(
                        "slack", title_data_copy, show_source=False
                    )
                else:
                    formatted_title = f"{title_data_copy['title']}"

                news_line = f"  {j + 1}. {formatted_title}\n"

                test_content = current_batch + news_line
                if (
                    len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                    >= max_bytes
                ):
                    if current_batch_has_content:
                        batches.append(current_batch + base_footer)
                    current_batch = base_header + new_header + source_header + news_line
                    current_batch_has_content = True
                else:
                    current_batch = test_content
                    current_batch_has_content = True

            current_batch += "\n"

        return current_batch, current_batch_has_content, batches

    # 定义处理 AI 分析的函数
    def process_ai_section(current_batch, current_batch_has_content, batches, add_separator=True):
        """处理 AI 分析内容"""
        nonlocal ai_content
        if not ai_content:
            return current_batch, current_batch_has_content, batches

        # 根据 add_separator 决定是否添加前置分割线
        ai_separator = ""
        if add_separator and current_batch_has_content:
            # 需要添加分割线
            if format_type == "feishu":
                ai_separator = f"\n{feishu_separator}\n\n"
            elif format_type == "dingtalk":
                ai_separator = "\n---\n\n"
            elif format_type in ("wework", "bark"):
                ai_separator = "\n\n\n\n"
            elif format_type in ("telegram", "ntfy", "slack"):
                ai_separator = "\n\n"
        # 如果不需要分割线，ai_separator 保持为空字符串

        # 尝试将 AI 内容添加到当前批次
        test_content = current_batch + ai_separator + ai_content
        if (
            len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
            < max_bytes
        ):
            current_batch = test_content
            current_batch_has_content = True
        else:
            # 当前批次容纳不下，开启新批次
            if current_batch_has_content:
                batches.append(current_batch + base_footer)
            # AI 内容可能很长，需要考虑是否需要进一步分割
            ai_with_header = base_header + ai_content
            current_batch = ai_with_header
            current_batch_has_content = True

        return current_batch, current_batch_has_content, batches

    # 定义处理独立展示区的函数
    def process_standalone_section_wrapper(current_batch, current_batch_has_content, batches, add_separator=True):
        """处理独立展示区"""
        if not standalone_data:
            return current_batch, current_batch_has_content, batches
        return _process_standalone_section(
            standalone_data, format_type, feishu_separator, base_header, base_footer,
            max_bytes, current_batch, current_batch_has_content, batches, timezone,
            rank_threshold, add_separator
        )

    # 定义处理 RSS 统计的函数
    def process_rss_stats_wrapper(current_batch, current_batch_has_content, batches, add_separator=True):
        """处理 RSS 统计"""
        if not rss_items:
            return current_batch, current_batch_has_content, batches
        return _process_rss_stats_section(
            rss_items, format_type, feishu_separator, base_header, base_footer,
            max_bytes, current_batch, current_batch_has_content, batches, timezone,
            add_separator
        )

    # 定义处理 RSS 新增的函数
    def process_rss_new_wrapper(current_batch, current_batch_has_content, batches, add_separator=True):
        """处理 RSS 新增"""
        if not rss_new_items:
            return current_batch, current_batch_has_content, batches
        return _process_rss_new_titles_section(
            rss_new_items, format_type, feishu_separator, base_header, base_footer,
            max_bytes, current_batch, current_batch_has_content, batches, timezone,
            add_separator
        )

    # 按 region_order 顺序处理各区域
    # 记录是否已有区域内容（用于决定是否添加分割线）
    has_region_content = False

    for region in region_order:
        # 记录处理前的状态，用于判断该区域是否产生了内容
        batch_before = current_batch
        has_content_before = current_batch_has_content
        batches_len_before = len(batches)

        # 决定是否需要添加分割线（第一个有内容的区域不需要）
        add_separator = has_region_content

        if region == "hotlist":
            # 处理热榜统计
            current_batch, current_batch_has_content, batches = process_stats_section(
                current_batch, current_batch_has_content, batches, add_separator
            )
        elif region == "rss":
            # 处理 RSS 统计
            current_batch, current_batch_has_content, batches = process_rss_stats_wrapper(
                current_batch, current_batch_has_content, batches, add_separator
            )
        elif region == "new_items":
            # 处理热榜新增
            current_batch, current_batch_has_content, batches = process_new_titles_section(
                current_batch, current_batch_has_content, batches, add_separator
            )
            # 处理 RSS 新增（跟随 new_items，继承 add_separator 逻辑）
            # 如果热榜新增产生了内容，RSS 新增需要分割线
            new_batch_changed = (
                current_batch != batch_before or
                current_batch_has_content != has_content_before or
                len(batches) != batches_len_before
            )
            rss_new_separator = new_batch_changed or has_region_content
            current_batch, current_batch_has_content, batches = process_rss_new_wrapper(
                current_batch, current_batch_has_content, batches, rss_new_separator
            )
        elif region == "standalone":
            # 处理独立展示区
            current_batch, current_batch_has_content, batches = process_standalone_section_wrapper(
                current_batch, current_batch_has_content, batches, add_separator
            )
        elif region == "ai_analysis":
            # 处理 AI 分析
            current_batch, current_batch_has_content, batches = process_ai_section(
                current_batch, current_batch_has_content, batches, add_separator
            )

        # 检查该区域是否产生了内容
        region_produced_content = (
            current_batch != batch_before or
            current_batch_has_content != has_content_before or
            len(batches) != batches_len_before
        )
        if region_produced_content:
            has_region_content = True

    if report_data["failed_ids"]:
        failed_header = ""
        if format_type == "wework":
            failed_header = "\n\n\n\n⚠️ **数据获取失败的平台：**\n\n"
        elif format_type == "telegram":
            failed_header = "\n\n⚠️ 数据获取失败的平台：\n\n"
        elif format_type == "ntfy":
            failed_header = "\n\n⚠️ **数据获取失败的平台：**\n\n"
        elif format_type == "feishu":
            failed_header = f"\n{feishu_separator}\n\n⚠️ **数据获取失败的平台：**\n\n"
        elif format_type == "dingtalk":
            failed_header = "\n---\n\n⚠️ **数据获取失败的平台：**\n\n"

        test_content = current_batch + failed_header
        if (
            len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
            >= max_bytes
        ):
            if current_batch_has_content:
                batches.append(current_batch + base_footer)
            current_batch = base_header + failed_header
            current_batch_has_content = True
        else:
            current_batch = test_content
            current_batch_has_content = True

        for _i, id_value in enumerate(report_data["failed_ids"], 1):
            if format_type == "feishu":
                failed_line = f"  • <font color='red'>{id_value}</font>\n"
            elif format_type == "dingtalk":
                failed_line = f"  • **{id_value}**\n"
            else:
                failed_line = f"  • {id_value}\n"

            test_content = current_batch + failed_line
            if (
                len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8"))
                >= max_bytes
            ):
                if current_batch_has_content:
                    batches.append(current_batch + base_footer)
                current_batch = base_header + failed_header + failed_line
                current_batch_has_content = True
            else:
                current_batch = test_content
                current_batch_has_content = True

    # 完成最后批次
    if current_batch_has_content:
        batches.append(current_batch + base_footer)

    return batches

