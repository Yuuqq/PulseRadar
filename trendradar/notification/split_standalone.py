# coding=utf-8
"""
独立展示区消息分批处理子模块

包含独立展示区区块的批次构建函数，
以及热榜条目和 RSS 条目的格式化辅助函数。
"""

from typing import Dict, List

from trendradar.report.helpers import format_rank_display
from trendradar.utils.time import DEFAULT_TIMEZONE, format_iso_time_friendly, convert_time_for_display


def _process_standalone_section(
    standalone_data: Dict,
    format_type: str,
    feishu_separator: str,
    base_header: str,
    base_footer: str,
    max_bytes: int,
    current_batch: str,
    current_batch_has_content: bool,
    batches: List[str],
    timezone: str = DEFAULT_TIMEZONE,
    rank_threshold: int = 10,
    add_separator: bool = True,
) -> tuple:
    """处理独立展示区区块

    独立展示区显示指定平台的完整热榜或 RSS 源内容，不受关键词过滤影响。
    热榜按原始排名排序，RSS 按发布时间排序。

    Args:
        standalone_data: 独立展示数据，格式：
            {
                "platforms": [{"id": "zhihu", "name": "知乎热榜", "items": [...]}],
                "rss_feeds": [{"id": "hacker-news", "name": "Hacker News", "items": [...]}]
            }
        format_type: 格式类型
        feishu_separator: 飞书分隔符
        base_header: 基础头部
        base_footer: 基础尾部
        max_bytes: 最大字节数
        current_batch: 当前批次内容
        current_batch_has_content: 当前批次是否有内容
        batches: 已完成的批次列表
        timezone: 时区名称
        rank_threshold: 排名高亮阈值
        add_separator: 是否在区块前添加分割线（第一个区域时为 False）

    Returns:
        (current_batch, current_batch_has_content, batches) 元组
    """
    if not standalone_data:
        return current_batch, current_batch_has_content, batches

    platforms = standalone_data.get("platforms", [])
    rss_feeds = standalone_data.get("rss_feeds", [])

    if not platforms and not rss_feeds:
        return current_batch, current_batch_has_content, batches

    # 计算总条目数
    total_platform_items = sum(len(p.get("items", [])) for p in platforms)
    total_rss_items = sum(len(f.get("items", [])) for f in rss_feeds)
    total_items = total_platform_items + total_rss_items

    # 独立展示区标题（根据 add_separator 决定是否添加前置分割线）
    section_header = ""
    if add_separator and current_batch_has_content:
        # 需要添加分割线
        if format_type == "feishu":
            section_header = f"\n{feishu_separator}\n\n📋 **独立展示区** (共 {total_items} 条)\n\n"
        elif format_type == "dingtalk":
            section_header = f"\n---\n\n📋 **独立展示区** (共 {total_items} 条)\n\n"
        elif format_type in ("wework", "bark"):
            section_header = f"\n\n\n\n📋 **独立展示区** (共 {total_items} 条)\n\n"
        elif format_type == "telegram":
            section_header = f"\n\n📋 独立展示区 (共 {total_items} 条)\n\n"
        elif format_type == "slack":
            section_header = f"\n\n📋 *独立展示区* (共 {total_items} 条)\n\n"
        else:
            section_header = f"\n\n📋 **独立展示区** (共 {total_items} 条)\n\n"
    else:
        # 不需要分割线（第一个区域）
        if format_type == "feishu":
            section_header = f"📋 **独立展示区** (共 {total_items} 条)\n\n"
        elif format_type == "dingtalk":
            section_header = f"📋 **独立展示区** (共 {total_items} 条)\n\n"
        elif format_type == "telegram":
            section_header = f"📋 独立展示区 (共 {total_items} 条)\n\n"
        elif format_type == "slack":
            section_header = f"📋 *独立展示区* (共 {total_items} 条)\n\n"
        else:
            section_header = f"📋 **独立展示区** (共 {total_items} 条)\n\n"

    # 添加区块标题
    test_content = current_batch + section_header
    if len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8")) < max_bytes:
        current_batch = test_content
        current_batch_has_content = True
    else:
        if current_batch_has_content:
            batches.append(current_batch + base_footer)
        current_batch = base_header + section_header
        current_batch_has_content = True

    # 处理热榜平台
    for platform in platforms:
        platform_name = platform.get("name", platform.get("id", ""))
        items = platform.get("items", [])
        if not items:
            continue

        # 平台标题
        platform_header = ""
        if format_type in ("wework", "bark"):
            platform_header = f"**{platform_name}** ({len(items)} 条):\n\n"
        elif format_type == "telegram":
            platform_header = f"{platform_name} ({len(items)} 条):\n\n"
        elif format_type == "ntfy":
            platform_header = f"**{platform_name}** ({len(items)} 条):\n\n"
        elif format_type == "feishu":
            platform_header = f"**{platform_name}** ({len(items)} 条):\n\n"
        elif format_type == "dingtalk":
            platform_header = f"**{platform_name}** ({len(items)} 条):\n\n"
        elif format_type == "slack":
            platform_header = f"*{platform_name}* ({len(items)} 条):\n\n"

        # 构建第一条新闻
        first_item_line = ""
        if items:
            first_item_line = _format_standalone_platform_item(items[0], 1, format_type, rank_threshold)

        # 原子性检查
        platform_with_first = platform_header + first_item_line
        test_content = current_batch + platform_with_first

        if len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8")) >= max_bytes:
            if current_batch_has_content:
                batches.append(current_batch + base_footer)
            current_batch = base_header + section_header + platform_with_first
            current_batch_has_content = True
            start_index = 1
        else:
            current_batch = test_content
            current_batch_has_content = True
            start_index = 1

        # 处理剩余条目
        for j in range(start_index, len(items)):
            item_line = _format_standalone_platform_item(items[j], j + 1, format_type, rank_threshold)

            test_content = current_batch + item_line
            if len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8")) >= max_bytes:
                if current_batch_has_content:
                    batches.append(current_batch + base_footer)
                current_batch = base_header + section_header + platform_header + item_line
                current_batch_has_content = True
            else:
                current_batch = test_content
                current_batch_has_content = True

        current_batch += "\n"

    # 处理 RSS 源
    for feed in rss_feeds:
        feed_name = feed.get("name", feed.get("id", ""))
        items = feed.get("items", [])
        if not items:
            continue

        # RSS 源标题
        feed_header = ""
        if format_type in ("wework", "bark"):
            feed_header = f"**{feed_name}** ({len(items)} 条):\n\n"
        elif format_type == "telegram":
            feed_header = f"{feed_name} ({len(items)} 条):\n\n"
        elif format_type == "ntfy":
            feed_header = f"**{feed_name}** ({len(items)} 条):\n\n"
        elif format_type == "feishu":
            feed_header = f"**{feed_name}** ({len(items)} 条):\n\n"
        elif format_type == "dingtalk":
            feed_header = f"**{feed_name}** ({len(items)} 条):\n\n"
        elif format_type == "slack":
            feed_header = f"*{feed_name}* ({len(items)} 条):\n\n"

        # 构建第一条 RSS
        first_item_line = ""
        if items:
            first_item_line = _format_standalone_rss_item(items[0], 1, format_type, timezone)

        # 原子性检查
        feed_with_first = feed_header + first_item_line
        test_content = current_batch + feed_with_first

        if len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8")) >= max_bytes:
            if current_batch_has_content:
                batches.append(current_batch + base_footer)
            current_batch = base_header + section_header + feed_with_first
            current_batch_has_content = True
            start_index = 1
        else:
            current_batch = test_content
            current_batch_has_content = True
            start_index = 1

        # 处理剩余条目
        for j in range(start_index, len(items)):
            item_line = _format_standalone_rss_item(items[j], j + 1, format_type, timezone)

            test_content = current_batch + item_line
            if len(test_content.encode("utf-8")) + len(base_footer.encode("utf-8")) >= max_bytes:
                if current_batch_has_content:
                    batches.append(current_batch + base_footer)
                current_batch = base_header + section_header + feed_header + item_line
                current_batch_has_content = True
            else:
                current_batch = test_content
                current_batch_has_content = True

        current_batch += "\n"

    return current_batch, current_batch_has_content, batches


def _format_standalone_platform_item(item: Dict, index: int, format_type: str, rank_threshold: int = 10) -> str:
    """格式化独立展示区的热榜条目（复用热点词汇统计区样式）

    Args:
        item: 热榜条目，包含 title, url, rank, ranks, first_time, last_time, count
        index: 序号
        format_type: 格式类型
        rank_threshold: 排名高亮阈值

    Returns:
        格式化后的条目行字符串
    """
    title = item.get("title", "")
    url = item.get("url", "") or item.get("mobileUrl", "")
    ranks = item.get("ranks", [])
    rank = item.get("rank", 0)
    first_time = item.get("first_time", "")
    last_time = item.get("last_time", "")
    count = item.get("count", 1)

    # 使用 format_rank_display 格式化排名（复用热点词汇统计区逻辑）
    # 如果没有 ranks 列表，用单个 rank 构造
    if not ranks and rank > 0:
        ranks = [rank]
    rank_display = format_rank_display(ranks, rank_threshold, format_type) if ranks else ""

    # 构建时间显示（用 ~ 连接范围，与热点词汇统计区一致）
    # 将 HH-MM 格式转换为 HH:MM 格式
    time_display = ""
    if first_time and last_time and first_time != last_time:
        first_time_display = convert_time_for_display(first_time)
        last_time_display = convert_time_for_display(last_time)
        time_display = f"{first_time_display}~{last_time_display}"
    elif first_time:
        time_display = convert_time_for_display(first_time)

    # 构建次数显示（格式为 (N次)，与热点词汇统计区一致）
    count_display = f"({count}次)" if count > 1 else ""

    # 根据格式类型构建条目行（复用热点词汇统计区样式）
    if format_type == "feishu":
        if url:
            item_line = f"  {index}. [{title}]({url})"
        else:
            item_line = f"  {index}. {title}"
        if rank_display:
            item_line += f" {rank_display}"
        if time_display:
            item_line += f" <font color='grey'>- {time_display}</font>"
        if count_display:
            item_line += f" <font color='green'>{count_display}</font>"

    elif format_type == "dingtalk":
        if url:
            item_line = f"  {index}. [{title}]({url})"
        else:
            item_line = f"  {index}. {title}"
        if rank_display:
            item_line += f" {rank_display}"
        if time_display:
            item_line += f" - {time_display}"
        if count_display:
            item_line += f" {count_display}"

    elif format_type == "telegram":
        if url:
            item_line = f"  {index}. {title} ({url})"
        else:
            item_line = f"  {index}. {title}"
        if rank_display:
            item_line += f" {rank_display}"
        if time_display:
            item_line += f" - {time_display}"
        if count_display:
            item_line += f" {count_display}"

    elif format_type == "slack":
        if url:
            item_line = f"  {index}. <{url}|{title}>"
        else:
            item_line = f"  {index}. {title}"
        if rank_display:
            item_line += f" {rank_display}"
        if time_display:
            item_line += f" _{time_display}_"
        if count_display:
            item_line += f" {count_display}"

    else:
        # wework, bark, ntfy
        if url:
            item_line = f"  {index}. [{title}]({url})"
        else:
            item_line = f"  {index}. {title}"
        if rank_display:
            item_line += f" {rank_display}"
        if time_display:
            item_line += f" - {time_display}"
        if count_display:
            item_line += f" {count_display}"

    item_line += "\n"
    return item_line


def _format_standalone_rss_item(
    item: Dict, index: int, format_type: str, timezone: str = "Asia/Shanghai"
) -> str:
    """格式化独立展示区的 RSS 条目

    Args:
        item: RSS 条目，包含 title, url, published_at, author
        index: 序号
        format_type: 格式类型
        timezone: 时区名称

    Returns:
        格式化后的条目行字符串
    """
    title = item.get("title", "")
    url = item.get("url", "")
    published_at = item.get("published_at", "")
    author = item.get("author", "")

    # 使用友好时间格式
    friendly_time = ""
    if published_at:
        friendly_time = format_iso_time_friendly(published_at, timezone, include_date=True)

    # 构建元信息
    meta_parts = []
    if friendly_time:
        meta_parts.append(friendly_time)
    if author:
        meta_parts.append(author)
    meta_str = ", ".join(meta_parts)

    # 根据格式类型构建条目行
    if format_type == "feishu":
        if url:
            item_line = f"  {index}. [{title}]({url})"
        else:
            item_line = f"  {index}. {title}"
        if meta_str:
            item_line += f" <font color='grey'>- {meta_str}</font>"
    elif format_type == "telegram":
        if url:
            item_line = f"  {index}. {title} ({url})"
        else:
            item_line = f"  {index}. {title}"
        if meta_str:
            item_line += f" - {meta_str}"
    elif format_type == "slack":
        if url:
            item_line = f"  {index}. <{url}|{title}>"
        else:
            item_line = f"  {index}. {title}"
        if meta_str:
            item_line += f" _{meta_str}_"
    else:
        # wework, bark, ntfy, dingtalk
        if url:
            item_line = f"  {index}. [{title}]({url})"
        else:
            item_line = f"  {index}. {title}"
        if meta_str:
            item_line += f" `{meta_str}`"

    item_line += "\n"
    return item_line
