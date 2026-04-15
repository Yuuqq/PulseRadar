# coding=utf-8
"""
分析流水线与独立展示区数据准备

从 NewsAnalyzer 中提取的纯函数，接受显式参数而非 self。
"""

from typing import Dict, List, Optional, Tuple

from trendradar.context import AppContext
from trendradar.logging import get_logger
from trendradar.core.analyzer import convert_keyword_stats_to_platform_stats

logger = get_logger(__name__)


def prepare_standalone_data(
    ctx: AppContext,
    results: Dict,
    id_to_name: Dict,
    title_info: Optional[Dict] = None,
    rss_items: Optional[List[Dict]] = None,
) -> Optional[Dict]:
    """
    从原始数据中提取独立展示区数据

    Args:
        ctx: 应用上下文
        results: 原始爬取结果 {platform_id: {title: title_data}}
        id_to_name: 平台 ID 到名称的映射
        title_info: 标题元信息（含排名历史、时间等）
        rss_items: RSS 条目列表

    Returns:
        独立展示数据字典，如果未启用返回 None
    """
    display_config = ctx.config.get("DISPLAY", {})
    regions = display_config.get("REGIONS", {})
    standalone_config = display_config.get("STANDALONE", {})

    if not regions.get("STANDALONE", False):
        return None

    platform_ids = standalone_config.get("PLATFORMS", [])
    rss_feed_ids = standalone_config.get("RSS_FEEDS", [])
    max_items = standalone_config.get("MAX_ITEMS", 20)

    if not platform_ids and not rss_feed_ids:
        return None

    standalone_data = {
        "platforms": [],
        "rss_feeds": [],
    }

    # 找出最新批次时间（类似 current 模式的过滤逻辑）
    latest_time = None
    if title_info:
        for source_titles in title_info.values():
            for title_data in source_titles.values():
                last_time = title_data.get("last_time", "")
                if last_time:
                    if latest_time is None or last_time > latest_time:
                        latest_time = last_time

    # 提取热榜平台数据
    for platform_id in platform_ids:
        if platform_id not in results:
            continue

        platform_name = id_to_name.get(platform_id, platform_id)
        platform_titles = results[platform_id]

        items = []
        for title, title_data in platform_titles.items():
            # 获取元信息（如果有 title_info）
            meta = {}
            if title_info and platform_id in title_info and title in title_info[platform_id]:
                meta = title_info[platform_id][title]

            # 只保留当前在榜的话题（last_time 等于最新时间）
            if latest_time and meta:
                if meta.get("last_time") != latest_time:
                    continue

            # 使用当前热榜的排名数据（title_data）进行排序
            current_ranks = title_data.get("ranks", [])
            current_rank = current_ranks[-1] if current_ranks else 0

            # 用于显示的排名范围：合并历史排名和当前排名
            historical_ranks = meta.get("ranks", []) if meta else []
            all_ranks = historical_ranks.copy()
            for rank in current_ranks:
                if rank not in all_ranks:
                    all_ranks.append(rank)
            display_ranks = all_ranks if all_ranks else current_ranks

            item = {
                "title": title,
                "url": title_data.get("url", ""),
                "mobileUrl": title_data.get("mobileUrl", ""),
                "rank": current_rank,
                "ranks": display_ranks,
                "first_time": meta.get("first_time", ""),
                "last_time": meta.get("last_time", ""),
                "count": meta.get("count", 1),
            }
            items.append(item)

        # 按当前排名排序
        items.sort(key=lambda x: x["rank"] if x["rank"] > 0 else 9999)

        # 限制条数
        if max_items > 0:
            items = items[:max_items]

        if items:
            standalone_data["platforms"].append({
                "id": platform_id,
                "name": platform_name,
                "items": items,
            })

    # 提取 RSS 数据
    if rss_items and rss_feed_ids:
        feed_items_map = {}
        for item in rss_items:
            feed_id = item.get("feed_id", "")
            if feed_id in rss_feed_ids:
                if feed_id not in feed_items_map:
                    feed_items_map[feed_id] = {
                        "name": item.get("feed_name", feed_id),
                        "items": [],
                    }
                feed_items_map[feed_id]["items"].append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "published_at": item.get("published_at", ""),
                    "author": item.get("author", ""),
                })

        for feed_id in rss_feed_ids:
            if feed_id in feed_items_map:
                feed_data = feed_items_map[feed_id]
                items = feed_data["items"]
                if max_items > 0:
                    items = items[:max_items]
                if items:
                    standalone_data["rss_feeds"].append({
                        "id": feed_id,
                        "name": feed_data["name"],
                        "items": items,
                    })

    if not standalone_data["platforms"] and not standalone_data["rss_feeds"]:
        return None

    return standalone_data


def run_analysis_pipeline(
    ctx: AppContext,
    data_source: Dict,
    mode: str,
    title_info: Dict,
    new_titles: Dict,
    word_groups: List[Dict],
    filter_words: List[str],
    id_to_name: Dict,
    report_mode: str,
    update_info: Optional[Dict],
    report_type: str,
    ai_result: object = None,
    failed_ids: Optional[List] = None,
    global_filters: Optional[List[str]] = None,
    quiet: bool = False,
    rss_items: Optional[List[Dict]] = None,
    rss_new_items: Optional[List[Dict]] = None,
    standalone_data: Optional[Dict] = None,
) -> Tuple[List[Dict], Optional[str], object]:
    """
    统一的分析流水线：数据处理 -> 统计计算 -> HTML生成

    Args:
        ctx: 应用上下文
        data_source: 数据源字典
        mode: 报告模式
        title_info: 标题元信息
        new_titles: 新增标题
        word_groups: 关键词分组
        filter_words: 过滤词列表
        id_to_name: 平台 ID 到名称映射
        report_mode: 当前报告模式字符串
        update_info: 版本更新信息
        report_type: 报告类型字符串
        ai_result: AI 分析结果（由调用者预先计算）
        failed_ids: 失败的平台 ID 列表
        global_filters: 全局过滤词列表
        quiet: 是否静默运行
        rss_items: RSS 统计条目
        rss_new_items: RSS 新增条目
        standalone_data: 独立展示区数据

    Returns:
        (stats, html_file, ai_result) 三元组
    """
    # 统计计算
    stats, total_titles = ctx.count_frequency(
        data_source,
        word_groups,
        filter_words,
        id_to_name,
        title_info,
        new_titles,
        mode=mode,
        global_filters=global_filters,
        quiet=quiet,
    )

    keyword_stats = stats
    alternate_stats = None
    alternate_display_mode = None

    # platform 模式转换数据结构
    if ctx.display_mode == "platform" and stats:
        stats = convert_keyword_stats_to_platform_stats(
            stats,
            ctx.weight_config,
            ctx.rank_threshold,
        )
        alternate_stats = keyword_stats
        alternate_display_mode = "keyword"
    elif stats:
        alternate_stats = convert_keyword_stats_to_platform_stats(
            stats,
            ctx.weight_config,
            ctx.rank_threshold,
        )
        alternate_display_mode = "platform"

    # ai_result is now passed in by caller (AnalysisEngine computes it)
    # The caller is responsible for running AI analysis before calling this function

    # HTML 生成
    html_file = None
    if ctx.config["STORAGE"]["FORMATS"]["HTML"]:
        html_file = ctx.generate_html(
            stats,
            total_titles,
            failed_ids=failed_ids,
            new_titles=new_titles,
            id_to_name=id_to_name,
            mode=mode,
            update_info=update_info if ctx.config["SHOW_VERSION_UPDATE"] else None,
            rss_items=rss_items,
            rss_new_items=rss_new_items,
            ai_analysis=ai_result,
            standalone_data=standalone_data,
            alternate_stats=alternate_stats,
            alternate_display_mode=alternate_display_mode,
        )

    return stats, html_file, ai_result
