"""
RSS 消息分批处理子模块

包含 RSS 统计区块、RSS 新增区块的批次构建函数，
以及单条 RSS 条目的格式化辅助函数。
"""


from trendradar.report.formatter import format_title_for_platform
from trendradar.utils.time import DEFAULT_TIMEZONE, format_iso_time_friendly


def _process_rss_stats_section(
    rss_stats: list,
    format_type: str,
    feishu_separator: str,
    base_header: str,
    base_footer: str,
    max_bytes: int,
    current_batch: str,
    current_batch_has_content: bool,
    batches: list[str],
    timezone: str = DEFAULT_TIMEZONE,
    add_separator: bool = True,
) -> tuple:
    """处理 RSS 统计区块（按关键词分组，与热榜统计格式一致）

    Args:
        rss_stats: RSS 关键词统计列表，格式与热榜 stats 一致：
            [{"word": "AI", "count": 5, "titles": [...]}]
        format_type: 格式类型
        feishu_separator: 飞书分隔符
        base_header: 基础头部
        base_footer: 基础尾部
        max_bytes: 最大字节数
        current_batch: 当前批次内容
        current_batch_has_content: 当前批次是否有内容
        batches: 已完成的批次列表
        timezone: 时区名称
        add_separator: 是否在区块前添加分割线（第一个区域时为 False）

    Returns:
        (current_batch, current_batch_has_content, batches) 元组
    """
    if not rss_stats:
        return current_batch, current_batch_has_content, batches

    # 计算总条目数
    total_items = sum(stat["count"] for stat in rss_stats)
    total_keywords = len(rss_stats)

    # RSS 统计区块标题（根据 add_separator 决定是否添加前置分割线）
    rss_header = ""
    if add_separator and current_batch_has_content:
        # 需要添加分割线
        if format_type == "feishu":
            rss_header = f"\n{feishu_separator}\n\n📰 **RSS 订阅统计** (共 {total_items} 条)\n\n"
        elif format_type == "dingtalk":
            rss_header = f"\n---\n\n📰 **RSS 订阅统计** (共 {total_items} 条)\n\n"
        elif format_type in ("wework", "bark"):
            rss_header = f"\n\n\n\n📰 **RSS 订阅统计** (共 {total_items} 条)\n\n"
        elif format_type == "telegram":
            rss_header = f"\n\n📰 RSS 订阅统计 (共 {total_items} 条)\n\n"
        elif format_type == "slack":
            rss_header = f"\n\n📰 *RSS 订阅统计* (共 {total_items} 条)\n\n"
        else:
            rss_header = f"\n\n📰 **RSS 订阅统计** (共 {total_items} 条)\n\n"
    else:
        # 不需要分割线（第一个区域）
        if format_type == "feishu" or format_type == "dingtalk":
            rss_header = f"📰 **RSS 订阅统计** (共 {total_items} 条)\n\n"
        elif format_type == "telegram":
            rss_header = f"📰 RSS 订阅统计 (共 {total_items} 条)\n\n"
        elif format_type == "slack":
            rss_header = f"📰 *RSS 订阅统计* (共 {total_items} 条)\n\n"
        else:
            rss_header = f"📰 **RSS 订阅统计** (共 {total_items} 条)\n\n"

    # 添加 RSS 标题
    test_content = current_batch + rss_header
    if len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8")) < max_bytes:
        current_batch = test_content
        current_batch_has_content = True
    else:
        if current_batch_has_content:
            batches.append(current_batch + base_footer)
        current_batch = base_header + rss_header
        current_batch_has_content = True

    # 逐个处理关键词组（与热榜一致）
    for i, stat in enumerate(rss_stats):
        word = stat["word"]
        count = stat["count"]
        sequence_display = f"[{i + 1}/{total_keywords}]"

        # 构建关键词标题（与热榜格式一致）
        word_header = ""
        if format_type in ("wework", "bark"):
            if count >= 10:
                word_header = f"🔥 {sequence_display} **{word}** : **{count}** 条\n\n"
            elif count >= 5:
                word_header = f"📈 {sequence_display} **{word}** : **{count}** 条\n\n"
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
                word_header = f"🔥 {sequence_display} **{word}** : **{count}** 条\n\n"
            elif count >= 5:
                word_header = f"📈 {sequence_display} **{word}** : **{count}** 条\n\n"
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
                word_header = f"🔥 {sequence_display} **{word}** : **{count}** 条\n\n"
            elif count >= 5:
                word_header = f"📈 {sequence_display} **{word}** : **{count}** 条\n\n"
            else:
                word_header = f"📌 {sequence_display} **{word}** : {count} 条\n\n"
        elif format_type == "slack":
            if count >= 10:
                word_header = f"🔥 {sequence_display} *{word}* : *{count}* 条\n\n"
            elif count >= 5:
                word_header = f"📈 {sequence_display} *{word}* : *{count}* 条\n\n"
            else:
                word_header = f"📌 {sequence_display} *{word}* : {count} 条\n\n"

        # 构建第一条新闻（使用 format_title_for_platform）
        first_news_line = ""
        if stat["titles"]:
            first_title_data = stat["titles"][0]
            if format_type in ("wework", "bark"):
                formatted_title = format_title_for_platform("wework", first_title_data, show_source=True)
            elif format_type == "telegram":
                formatted_title = format_title_for_platform("telegram", first_title_data, show_source=True)
            elif format_type == "ntfy":
                formatted_title = format_title_for_platform("ntfy", first_title_data, show_source=True)
            elif format_type == "feishu":
                formatted_title = format_title_for_platform("feishu", first_title_data, show_source=True)
            elif format_type == "dingtalk":
                formatted_title = format_title_for_platform("dingtalk", first_title_data, show_source=True)
            elif format_type == "slack":
                formatted_title = format_title_for_platform("slack", first_title_data, show_source=True)
            else:
                formatted_title = f"{first_title_data['title']}"

            first_news_line = f"  1. {formatted_title}\n"
            if len(stat["titles"]) > 1:
                first_news_line += "\n"

        # 原子性检查：关键词标题 + 第一条新闻必须一起处理
        word_with_first_news = word_header + first_news_line
        test_content = current_batch + word_with_first_news

        if len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8")) >= max_bytes:
            if current_batch_has_content:
                batches.append(current_batch + base_footer)
            current_batch = base_header + rss_header + word_with_first_news
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
                formatted_title = format_title_for_platform("wework", title_data, show_source=True)
            elif format_type == "telegram":
                formatted_title = format_title_for_platform("telegram", title_data, show_source=True)
            elif format_type == "ntfy":
                formatted_title = format_title_for_platform("ntfy", title_data, show_source=True)
            elif format_type == "feishu":
                formatted_title = format_title_for_platform("feishu", title_data, show_source=True)
            elif format_type == "dingtalk":
                formatted_title = format_title_for_platform("dingtalk", title_data, show_source=True)
            elif format_type == "slack":
                formatted_title = format_title_for_platform("slack", title_data, show_source=True)
            else:
                formatted_title = f"{title_data['title']}"

            news_line = f"  {j + 1}. {formatted_title}\n"
            if j < len(stat["titles"]) - 1:
                news_line += "\n"

            test_content = current_batch + news_line
            if len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8")) >= max_bytes:
                if current_batch_has_content:
                    batches.append(current_batch + base_footer)
                current_batch = base_header + rss_header + word_header + news_line
                current_batch_has_content = True
            else:
                current_batch = test_content
                current_batch_has_content = True

        # 关键词间分隔符
        if i < len(rss_stats) - 1:
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
            if len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8")) < max_bytes:
                current_batch = test_content

    return current_batch, current_batch_has_content, batches


def _process_rss_new_titles_section(
    rss_new_stats: list,
    format_type: str,
    feishu_separator: str,
    base_header: str,
    base_footer: str,
    max_bytes: int,
    current_batch: str,
    current_batch_has_content: bool,
    batches: list[str],
    timezone: str = DEFAULT_TIMEZONE,
    add_separator: bool = True,
) -> tuple:
    """处理 RSS 新增区块（按来源分组，与热榜新增格式一致）

    Args:
        rss_new_stats: RSS 新增关键词统计列表，格式与热榜 stats 一致：
            [{"word": "AI", "count": 5, "titles": [...]}]
        format_type: 格式类型
        feishu_separator: 飞书分隔符
        base_header: 基础头部
        base_footer: 基础尾部
        max_bytes: 最大字节数
        current_batch: 当前批次内容
        current_batch_has_content: 当前批次是否有内容
        batches: 已完成的批次列表
        timezone: 时区名称
        add_separator: 是否在区块前添加分割线（第一个区域时为 False）

    Returns:
        (current_batch, current_batch_has_content, batches) 元组
    """
    if not rss_new_stats:
        return current_batch, current_batch_has_content, batches

    # 从关键词分组中提取所有条目，重新按来源分组
    source_map = {}
    for stat in rss_new_stats:
        for title_data in stat.get("titles", []):
            source_name = title_data.get("source_name", "未知来源")
            if source_name not in source_map:
                source_map[source_name] = []
            source_map[source_name].append(title_data)

    if not source_map:
        return current_batch, current_batch_has_content, batches

    # 计算总条目数
    total_items = sum(len(titles) for titles in source_map.values())

    # RSS 新增区块标题（根据 add_separator 决定是否添加前置分割线）
    new_header = ""
    if add_separator and current_batch_has_content:
        # 需要添加分割线
        if format_type in ("wework", "bark"):
            new_header = f"\n\n\n\n🆕 **RSS 本次新增** (共 {total_items} 条)\n\n"
        elif format_type == "telegram":
            new_header = f"\n\n🆕 RSS 本次新增 (共 {total_items} 条)\n\n"
        elif format_type == "ntfy":
            new_header = f"\n\n🆕 **RSS 本次新增** (共 {total_items} 条)\n\n"
        elif format_type == "feishu":
            new_header = f"\n{feishu_separator}\n\n🆕 **RSS 本次新增** (共 {total_items} 条)\n\n"
        elif format_type == "dingtalk":
            new_header = f"\n---\n\n🆕 **RSS 本次新增** (共 {total_items} 条)\n\n"
        elif format_type == "slack":
            new_header = f"\n\n🆕 *RSS 本次新增* (共 {total_items} 条)\n\n"
    else:
        # 不需要分割线（第一个区域）
        if format_type in ("wework", "bark"):
            new_header = f"🆕 **RSS 本次新增** (共 {total_items} 条)\n\n"
        elif format_type == "telegram":
            new_header = f"🆕 RSS 本次新增 (共 {total_items} 条)\n\n"
        elif format_type == "ntfy" or format_type == "feishu" or format_type == "dingtalk":
            new_header = f"🆕 **RSS 本次新增** (共 {total_items} 条)\n\n"
        elif format_type == "slack":
            new_header = f"🆕 *RSS 本次新增* (共 {total_items} 条)\n\n"

    # 添加 RSS 新增标题
    test_content = current_batch + new_header
    if len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8")) >= max_bytes:
        if current_batch_has_content:
            batches.append(current_batch + base_footer)
        current_batch = base_header + new_header
        current_batch_has_content = True
    else:
        current_batch = test_content
        current_batch_has_content = True

    # 按来源分组显示（与热榜新增格式一致）
    source_list = list(source_map.items())
    for _i, (source_name, titles) in enumerate(source_list):
        count = len(titles)

        # 构建来源标题（与热榜新增格式一致）
        source_header = ""
        if format_type in ("wework", "bark"):
            source_header = f"**{source_name}** ({count} 条):\n\n"
        elif format_type == "telegram":
            source_header = f"{source_name} ({count} 条):\n\n"
        elif format_type == "ntfy" or format_type == "feishu" or format_type == "dingtalk":
            source_header = f"**{source_name}** ({count} 条):\n\n"
        elif format_type == "slack":
            source_header = f"*{source_name}* ({count} 条):\n\n"

        # 构建第一条新闻（不显示来源，禁用 new emoji）
        first_news_line = ""
        if titles:
            first_title_data = titles[0].copy()
            first_title_data["is_new"] = False
            if format_type in ("wework", "bark"):
                formatted_title = format_title_for_platform("wework", first_title_data, show_source=False)
            elif format_type == "telegram":
                formatted_title = format_title_for_platform("telegram", first_title_data, show_source=False)
            elif format_type == "ntfy":
                formatted_title = format_title_for_platform("ntfy", first_title_data, show_source=False)
            elif format_type == "feishu":
                formatted_title = format_title_for_platform("feishu", first_title_data, show_source=False)
            elif format_type == "dingtalk":
                formatted_title = format_title_for_platform("dingtalk", first_title_data, show_source=False)
            elif format_type == "slack":
                formatted_title = format_title_for_platform("slack", first_title_data, show_source=False)
            else:
                formatted_title = f"{first_title_data['title']}"

            first_news_line = f"  1. {formatted_title}\n"

        # 原子性检查：来源标题 + 第一条新闻必须一起处理
        source_with_first_news = source_header + first_news_line
        test_content = current_batch + source_with_first_news

        if len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8")) >= max_bytes:
            if current_batch_has_content:
                batches.append(current_batch + base_footer)
            current_batch = base_header + new_header + source_with_first_news
            current_batch_has_content = True
            start_index = 1
        else:
            current_batch = test_content
            current_batch_has_content = True
            start_index = 1

        # 处理剩余新闻条目（禁用 new emoji）
        for j in range(start_index, len(titles)):
            title_data = titles[j].copy()
            title_data["is_new"] = False
            if format_type in ("wework", "bark"):
                formatted_title = format_title_for_platform("wework", title_data, show_source=False)
            elif format_type == "telegram":
                formatted_title = format_title_for_platform("telegram", title_data, show_source=False)
            elif format_type == "ntfy":
                formatted_title = format_title_for_platform("ntfy", title_data, show_source=False)
            elif format_type == "feishu":
                formatted_title = format_title_for_platform("feishu", title_data, show_source=False)
            elif format_type == "dingtalk":
                formatted_title = format_title_for_platform("dingtalk", title_data, show_source=False)
            elif format_type == "slack":
                formatted_title = format_title_for_platform("slack", title_data, show_source=False)
            else:
                formatted_title = f"{title_data['title']}"

            news_line = f"  {j + 1}. {formatted_title}\n"

            test_content = current_batch + news_line
            if len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8")) >= max_bytes:
                if current_batch_has_content:
                    batches.append(current_batch + base_footer)
                current_batch = base_header + new_header + source_header + news_line
                current_batch_has_content = True
            else:
                current_batch = test_content
                current_batch_has_content = True

        # 来源间添加空行（与热榜新增格式一致）
        current_batch += "\n"

    return current_batch, current_batch_has_content, batches


def _format_rss_item_line(
    item: dict,
    index: int,
    format_type: str,
    timezone: str = DEFAULT_TIMEZONE,
) -> str:
    """格式化单条 RSS 条目

    Args:
        item: RSS 条目字典
        index: 序号
        format_type: 格式类型
        timezone: 时区名称

    Returns:
        格式化后的条目行字符串
    """
    title = item.get("title", "")
    url = item.get("url", "")
    published_at = item.get("published_at", "")

    # 使用友好时间格式
    if published_at:
        friendly_time = format_iso_time_friendly(published_at, timezone, include_date=True)
    else:
        friendly_time = ""

    # 构建条目行
    if format_type == "feishu":
        item_line = f"  {index}. [{title}]({url})" if url else f"  {index}. {title}"
        if friendly_time:
            item_line += f" <font color='grey'>- {friendly_time}</font>"
    elif format_type == "telegram":
        item_line = f"  {index}. {title} ({url})" if url else f"  {index}. {title}"
        if friendly_time:
            item_line += f" - {friendly_time}"
    else:
        item_line = f"  {index}. [{title}]({url})" if url else f"  {index}. {title}"
        if friendly_time:
            item_line += f" `{friendly_time}`"

    item_line += "\n"
    return item_line
