"""HTML 报告区块渲染函数"""

from datetime import datetime as dt

from trendradar.report.helpers import html_escape
from trendradar.utils.time import convert_time_for_display


def build_hotlist_view(stats: list[dict], view_mode: str) -> str:
    """构建热榜视图（关键词/平台）"""
    if not stats:
        return ""

    total_count = len(stats)
    view_news_count = sum(len(stat["titles"]) for stat in stats)
    tabs = []
    stats_html = ""

    for i, stat in enumerate(stats, 1):
        count = stat["count"]

        # 确定热度等级
        if count >= 10:
            count_class = "hot"
        elif count >= 5:
            count_class = "warm"
        else:
            count_class = ""

        escaped_word = html_escape(stat["word"])
        tabs.append({"word": escaped_word, "count": count})

        stats_html += f"""
                <div class="word-group" data-topic="{escaped_word}">
                    <div class="word-header">
                        <div class="word-info">
                            <div class="word-name">{escaped_word}</div>
                            <div class="word-count {count_class}">{count} 条</div>
                        </div>
                        <div class="word-index">{i}/{total_count}</div>
                    </div>"""

        # 处理每个词组下的新闻标题，给每条新闻标上序号
        for j, title_data in enumerate(stat["titles"], 1):
            is_new = title_data.get("is_new", False)
            new_class = "new" if is_new else ""
            source_name = html_escape(title_data.get("source_name", ""))
            matched_keyword = title_data.get("matched_keyword", "")
            html_escape(matched_keyword) if matched_keyword else escaped_word

            search_blob = f"{title_data.get('title', '')} {title_data.get('source_name', '')} {matched_keyword} {stat['word']}"
            search_attr = html_escape(search_blob.lower())

            stats_html += f"""
                    <div class="news-item {new_class}" data-search="{search_attr}">
                        <div class="news-number">{j}</div>
                        <div class="news-content">
                            <div class="news-header">"""

            if view_mode == "keyword":
                stats_html += f'<span class="source-name">{source_name}</span>'
            else:
                if matched_keyword:
                    stats_html += (
                        f'<span class="keyword-tag">[{html_escape(matched_keyword)}]</span>'
                    )
                else:
                    stats_html += f'<span class="keyword-tag">[{escaped_word}]</span>'

            # 处理排名显示
            ranks = title_data.get("ranks", [])
            if ranks:
                min_rank = min(ranks)
                max_rank = max(ranks)
                rank_threshold = title_data.get("rank_threshold", 10)

                # 确定排名等级
                if min_rank <= 3:
                    rank_class = "top"
                elif min_rank <= rank_threshold:
                    rank_class = "high"
                else:
                    rank_class = ""

                rank_text = str(min_rank) if min_rank == max_rank else f"{min_rank}-{max_rank}"

                stats_html += f'<span class="rank-num {rank_class}">{rank_text}</span>'

            # 处理时间显示
            time_display = title_data.get("time_display", "")
            if time_display:
                simplified_time = time_display.replace(" ~ ", "~").replace("[", "").replace("]", "")
                stats_html += f'<span class="time-info">{html_escape(simplified_time)}</span>'

            # 处理出现次数
            count_info = title_data.get("count", 1)
            if count_info > 1:
                stats_html += f'<span class="count-info">{count_info}次</span>'

            stats_html += """
                            </div>
                            <div class="news-title">"""

            # 处理标题和链接
            escaped_title = html_escape(title_data["title"])
            link_url = title_data.get("mobile_url") or title_data.get("url", "")

            if link_url:
                escaped_url = html_escape(link_url)
                stats_html += (
                    f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                )
            else:
                stats_html += escaped_title

            stats_html += """
                            </div>
                        </div>
                    </div>"""

        stats_html += """
                </div>"""

    tabs_html = ""
    if len(tabs) > 1:
        tabs_html = f"""
                <div class="topic-tabs" role="tablist" aria-label="主题切换">
                    <button class="topic-tab active" data-topic="all">
                        全部 <span class="topic-count">{view_news_count}</span>
                    </button>"""
        for tab in tabs:
            tabs_html += f"""
                    <button class="topic-tab" data-topic="{tab["word"]}">
                        {tab["word"]} <span class="topic-count">{tab["count"]}</span>
                    </button>"""
        tabs_html += """
                </div>"""

    return f"""
                <div class="hotlist-view" data-view="{view_mode}">
                    {tabs_html}{stats_html}
                </div>"""


def render_rss_stats_html(stats: list[dict], title: str = "RSS 订阅更新") -> str:
    """渲染 RSS 统计区块 HTML

    Args:
        stats: RSS 分组统计列表，格式与热榜一致：
            [
                {
                    "word": "关键词",
                    "count": 5,
                    "titles": [
                        {
                            "title": "标题",
                            "source_name": "Feed 名称",
                            "time_display": "12-29 08:20",
                            "url": "...",
                            "is_new": True/False
                        }
                    ]
                }
            ]
        title: 区块标题

    Returns:
        渲染后的 HTML 字符串
    """
    if not stats:
        return ""

    # 计算总条目数
    total_count = sum(stat.get("count", 0) for stat in stats)
    if total_count == 0:
        return ""

    rss_html = f"""
                <div class="rss-section">
                    <div class="rss-section-header">
                        <div class="rss-section-title">{title}</div>
                        <div class="rss-section-count">{total_count} 条</div>
                    </div>"""

    # 按关键词分组渲染（与热榜格式一致）
    for stat in stats:
        keyword = stat.get("word", "")
        titles = stat.get("titles", [])
        if not titles:
            continue

        keyword_count = len(titles)

        rss_html += f"""
                    <div class="feed-group">
                        <div class="feed-header">
                            <div class="feed-name">{html_escape(keyword)}</div>
                            <div class="feed-count">{keyword_count} 条</div>
                        </div>"""

        for title_data in titles:
            item_title = title_data.get("title", "")
            url = title_data.get("url", "")
            time_display = title_data.get("time_display", "")
            source_name = title_data.get("source_name", "")
            is_new = title_data.get("is_new", False)

            rss_html += """
                        <div class="rss-item">
                            <div class="rss-meta">"""

            if time_display:
                rss_html += f'<span class="rss-time">{html_escape(time_display)}</span>'

            if source_name:
                rss_html += f'<span class="rss-author">{html_escape(source_name)}</span>'

            if is_new:
                rss_html += '<span class="rss-author" style="color: #dc2626;">NEW</span>'

            rss_html += """
                            </div>
                            <div class="rss-title">"""

            escaped_title = html_escape(item_title)
            if url:
                escaped_url = html_escape(url)
                rss_html += (
                    f'<a href="{escaped_url}" target="_blank" class="rss-link">{escaped_title}</a>'
                )
            else:
                rss_html += escaped_title

            rss_html += """
                            </div>
                        </div>"""

        rss_html += """
                    </div>"""

    rss_html += """
                </div>"""
    return rss_html


def render_standalone_html(data: dict | None) -> str:
    """渲染独立展示区 HTML（复用热点词汇统计区样式）

    Args:
        data: 独立展示数据，格式：
            {
                "platforms": [
                    {
                        "id": "zhihu",
                        "name": "知乎热榜",
                        "items": [
                            {
                                "title": "标题",
                                "url": "链接",
                                "rank": 1,
                                "ranks": [1, 2, 1],
                                "first_time": "08:00",
                                "last_time": "12:30",
                                "count": 3,
                            }
                        ]
                    }
                ],
                "rss_feeds": [
                    {
                        "id": "hacker-news",
                        "name": "Hacker News",
                        "items": [
                            {
                                "title": "标题",
                                "url": "链接",
                                "published_at": "2025-01-07T08:00:00",
                                "author": "作者",
                            }
                        ]
                    }
                ]
            }

    Returns:
        渲染后的 HTML 字符串
    """
    if not data:
        return ""

    platforms = data.get("platforms", [])
    rss_feeds = data.get("rss_feeds", [])

    if not platforms and not rss_feeds:
        return ""

    # 计算总条目数
    total_platform_items = sum(len(p.get("items", [])) for p in platforms)
    total_rss_items = sum(len(f.get("items", [])) for f in rss_feeds)
    total_count = total_platform_items + total_rss_items

    if total_count == 0:
        return ""

    standalone_html = f"""
                <div class="standalone-section">
                    <div class="standalone-section-header">
                        <div class="standalone-section-title">独立展示区</div>
                        <div class="standalone-section-count">{total_count} 条</div>
                    </div>"""

    # 渲染热榜平台（复用 word-group 结构）
    for platform in platforms:
        platform_name = platform.get("name", platform.get("id", ""))
        items = platform.get("items", [])
        if not items:
            continue

        standalone_html += f"""
                    <div class="standalone-group">
                        <div class="standalone-header">
                            <div class="standalone-name">{html_escape(platform_name)}</div>
                            <div class="standalone-count">{len(items)} 条</div>
                        </div>"""

        # 渲染每个条目（复用 news-item 结构）
        for j, item in enumerate(items, 1):
            title = item.get("title", "")
            url = item.get("url", "") or item.get("mobileUrl", "")
            rank = item.get("rank", 0)
            ranks = item.get("ranks", [])
            first_time = item.get("first_time", "")
            last_time = item.get("last_time", "")
            count = item.get("count", 1)

            standalone_html += f"""
                        <div class="news-item">
                            <div class="news-number">{j}</div>
                            <div class="news-content">
                                <div class="news-header">"""

            # 排名显示（复用 rank-num 样式，无 # 前缀）
            if ranks:
                min_rank = min(ranks)
                max_rank = max(ranks)

                # 确定排名等级
                if min_rank <= 3:
                    rank_class = "top"
                elif min_rank <= 10:
                    rank_class = "high"
                else:
                    rank_class = ""

                rank_text = str(min_rank) if min_rank == max_rank else f"{min_rank}-{max_rank}"

                standalone_html += f'<span class="rank-num {rank_class}">{rank_text}</span>'
            elif rank > 0:
                if rank <= 3:
                    rank_class = "top"
                elif rank <= 10:
                    rank_class = "high"
                else:
                    rank_class = ""
                standalone_html += f'<span class="rank-num {rank_class}">{rank}</span>'

            # 时间显示（复用 time-info 样式，将 HH-MM 转换为 HH:MM）
            if first_time and last_time and first_time != last_time:
                first_time_display = convert_time_for_display(first_time)
                last_time_display = convert_time_for_display(last_time)
                standalone_html += f'<span class="time-info">{html_escape(first_time_display)}~{html_escape(last_time_display)}</span>'
            elif first_time:
                first_time_display = convert_time_for_display(first_time)
                standalone_html += (
                    f'<span class="time-info">{html_escape(first_time_display)}</span>'
                )

            # 出现次数（复用 count-info 样式）
            if count > 1:
                standalone_html += f'<span class="count-info">{count}次</span>'

            standalone_html += """
                                </div>
                                <div class="news-title">"""

            # 标题和链接（复用 news-link 样式）
            escaped_title = html_escape(title)
            if url:
                escaped_url = html_escape(url)
                standalone_html += (
                    f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                )
            else:
                standalone_html += escaped_title

            standalone_html += """
                                </div>
                            </div>
                        </div>"""

        standalone_html += """
                    </div>"""

    # 渲染 RSS 源（复用相同结构）
    for feed in rss_feeds:
        feed_name = feed.get("name", feed.get("id", ""))
        items = feed.get("items", [])
        if not items:
            continue

        standalone_html += f"""
                    <div class="standalone-group">
                        <div class="standalone-header">
                            <div class="standalone-name">{html_escape(feed_name)}</div>
                            <div class="standalone-count">{len(items)} 条</div>
                        </div>"""

        for j, item in enumerate(items, 1):
            title = item.get("title", "")
            url = item.get("url", "")
            published_at = item.get("published_at", "")
            author = item.get("author", "")

            standalone_html += f"""
                        <div class="news-item">
                            <div class="news-number">{j}</div>
                            <div class="news-content">
                                <div class="news-header">"""

            # 时间显示（格式化 ISO 时间）
            if published_at:
                try:
                    if "T" in published_at:
                        dt_obj = dt.fromisoformat(published_at.replace("Z", "+00:00"))
                        time_display = dt_obj.strftime("%m-%d %H:%M")
                    else:
                        time_display = published_at
                except (ValueError, TypeError):
                    time_display = published_at

                standalone_html += f'<span class="time-info">{html_escape(time_display)}</span>'

            # 作者显示
            if author:
                standalone_html += f'<span class="source-name">{html_escape(author)}</span>'

            standalone_html += """
                                </div>
                                <div class="news-title">"""

            escaped_title = html_escape(title)
            if url:
                escaped_url = html_escape(url)
                standalone_html += (
                    f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                )
            else:
                standalone_html += escaped_title

            standalone_html += """
                                </div>
                            </div>
                        </div>"""

        standalone_html += """
                    </div>"""

    standalone_html += """
                </div>"""
    return standalone_html


def add_section_divider(content: str) -> str:
    """为内容的外层 div 添加 section-divider 类"""
    if not content or 'class="' not in content:
        return content
    first_class_pos = content.find('class="')
    if first_class_pos != -1:
        insert_pos = first_class_pos + len('class="')
        return content[:insert_pos] + "section-divider " + content[insert_pos:]
    return content


def wrap_section(region: str, content: str) -> str:
    return f'<section class="report-section" data-section="{region}">{content}</section>'
