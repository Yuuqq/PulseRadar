"""
模式策略执行与 RSS 数据按模式处理

从 NewsAnalyzer 中提取的纯函数，接受显式参数而非 self。
"""

import contextlib
import webbrowser
from pathlib import Path

from trendradar.context import AppContext
from trendradar.core.ai_service import (
    _load_analysis_data,
    _prepare_current_title_info,
    run_ai_analysis,
)
from trendradar.core.notification_service import send_notification_if_needed
from trendradar.core.pipeline import prepare_standalone_data, run_analysis_pipeline
from trendradar.logging import get_logger
from trendradar.utils.time import DEFAULT_TIMEZONE, calculate_days_old, is_within_days

logger = get_logger(__name__)


def convert_rss_items_to_list(
    ctx: AppContext,
    items_dict: dict,
    id_to_name: dict,
) -> list[dict]:
    """
    将 RSS 条目字典转换为列表格式，并应用新鲜度过滤

    Args:
        ctx: 应用上下文
        items_dict: feed_id -> [RSSItem] 的字典
        id_to_name: feed_id 到名称映射

    Returns:
        过滤后的 RSS 条目列表
    """
    rss_items = []
    filtered_count = 0
    filtered_details = []

    rss_config = ctx.rss_config
    freshness_config = rss_config.get("FRESHNESS_FILTER", {})
    freshness_enabled = freshness_config.get("ENABLED", True)
    default_max_age_days = freshness_config.get("MAX_AGE_DAYS", 3)
    timezone = ctx.config.get("TIMEZONE", DEFAULT_TIMEZONE)
    debug_mode = ctx.config.get("DEBUG", False)

    feed_max_age_map = {}
    for feed_cfg in ctx.rss_feeds:
        feed_id = feed_cfg.get("id", "")
        max_age = feed_cfg.get("max_age_days")
        if max_age is not None:
            with contextlib.suppress(ValueError, TypeError):
                feed_max_age_map[feed_id] = int(max_age)

    for feed_id, items in items_dict.items():
        max_days = feed_max_age_map.get(feed_id)
        if max_days is None:
            max_days = default_max_age_days

        for item in items:
            if freshness_enabled and max_days > 0:
                if item.published_at and not is_within_days(item.published_at, max_days, timezone):
                    filtered_count += 1
                    if debug_mode:
                        days_old = calculate_days_old(item.published_at, timezone)
                        feed_name = id_to_name.get(feed_id, feed_id)
                        filtered_details.append(
                            {
                                "title": item.title[:50] + "..."
                                if len(item.title) > 50
                                else item.title,
                                "feed": feed_name,
                                "days_old": days_old,
                                "max_days": max_days,
                            }
                        )
                    continue

            rss_items.append(
                {
                    "title": item.title,
                    "feed_id": feed_id,
                    "feed_name": id_to_name.get(feed_id, feed_id),
                    "url": item.url,
                    "published_at": item.published_at,
                    "summary": item.summary,
                    "author": item.author,
                }
            )

    if filtered_count > 0:
        logger.info("RSS 新鲜度过滤：跳过旧文章", skipped=filtered_count)
        if debug_mode and filtered_details:
            logger.debug(
                "RSS 被过滤的文章详情",
                count=len(filtered_details),
                details=[
                    {
                        "title": d["title"],
                        "feed": d["feed"],
                        "days_old": f"{d['days_old']:.1f}" if d["days_old"] else "未知",
                        "max_days": d["max_days"],
                    }
                    for d in filtered_details[:10]
                ],
            )
            if len(filtered_details) > 10:
                logger.debug("RSS 过滤详情截断", remaining=len(filtered_details) - 10)

    return rss_items


def process_rss_data_by_mode(
    ctx: AppContext,
    storage_manager,
    report_mode: str,
    rank_threshold: int,
    rss_data,
) -> tuple[list[dict] | None, list[dict] | None, list[dict] | None]:
    """
    按报告模式处理 RSS 数据，返回与热榜相同格式的统计结构

    三种模式：
    - daily: 当日汇总，统计=当天所有条目，新增=本次新增条目
    - current: 当前榜单，统计=当前榜单条目，新增=本次新增条目
    - incremental: 增量模式，统计=新增条目，新增=无

    Args:
        ctx: 应用上下文
        storage_manager: 存储管理器
        report_mode: 报告模式
        rank_threshold: 排名阈值
        rss_data: 当前抓取的 RSSData 对象

    Returns:
        (rss_stats, rss_new_stats, raw_rss_items) 元组
    """
    from trendradar.core.analyzer import count_rss_frequency

    rss_display_enabled = ctx.config.get("DISPLAY", {}).get("REGIONS", {}).get("RSS", True)

    try:
        word_groups, filter_words, global_filters = ctx.load_frequency_words()
    except FileNotFoundError:
        word_groups, filter_words, global_filters = [], [], []

    timezone = ctx.timezone
    max_news_per_keyword = ctx.config.get("MAX_NEWS_PER_KEYWORD", 0)
    max_keywords = ctx.config.get("MAX_KEYWORDS", 0)
    sort_by_position_first = ctx.config.get("SORT_BY_POSITION_FIRST", False)

    rss_stats = None
    rss_new_stats = None
    raw_rss_items = None

    # 1. 首先获取原始条目（用于独立展示区，不受 display.regions.rss 影响）
    if report_mode == "incremental":
        new_items_dict = storage_manager.detect_new_rss_items(rss_data)
        if new_items_dict:
            raw_rss_items = convert_rss_items_to_list(ctx, new_items_dict, rss_data.id_to_name)
    elif report_mode == "current":
        latest_data = storage_manager.get_latest_rss_data(rss_data.date)
        if latest_data:
            raw_rss_items = convert_rss_items_to_list(
                ctx, latest_data.items, latest_data.id_to_name
            )
    else:  # daily
        all_data = storage_manager.get_rss_data(rss_data.date)
        if all_data:
            raw_rss_items = convert_rss_items_to_list(ctx, all_data.items, all_data.id_to_name)

    if not rss_display_enabled:
        return None, None, raw_rss_items

    # 2. 获取新增条目（用于统计）
    new_items_dict = storage_manager.detect_new_rss_items(rss_data)
    new_items_list = None
    if new_items_dict:
        new_items_list = convert_rss_items_to_list(ctx, new_items_dict, rss_data.id_to_name)
        if new_items_list:
            logger.info("RSS 检测到新增条目", count=len(new_items_list))

    # 3. 根据模式获取统计条目
    if report_mode == "incremental":
        if not new_items_list:
            logger.info("RSS 增量模式：没有新增条目")
            return None, None, raw_rss_items

        rss_stats, total = count_rss_frequency(
            rss_items=new_items_list,
            word_groups=word_groups,
            filter_words=filter_words,
            global_filters=global_filters,
            new_items=new_items_list,
            max_news_per_keyword=max_news_per_keyword,
            max_keywords=max_keywords,
            sort_by_position_first=sort_by_position_first,
            timezone=timezone,
            rank_threshold=rank_threshold,
            quiet=False,
        )
        if not rss_stats:
            logger.info("RSS 增量模式：关键词匹配后没有内容")
            return None, None, raw_rss_items

    elif report_mode == "current":
        if not raw_rss_items:
            logger.info("RSS 当前榜单模式：没有 RSS 数据")
            return None, None, None

        rss_stats, total = count_rss_frequency(
            rss_items=raw_rss_items,
            word_groups=word_groups,
            filter_words=filter_words,
            global_filters=global_filters,
            new_items=new_items_list,
            max_news_per_keyword=max_news_per_keyword,
            max_keywords=max_keywords,
            sort_by_position_first=sort_by_position_first,
            timezone=timezone,
            rank_threshold=rank_threshold,
            quiet=False,
        )
        if not rss_stats:
            logger.info("RSS 当前榜单模式：关键词匹配后没有内容")
            return None, None, raw_rss_items

        if new_items_list:
            rss_new_stats, _ = count_rss_frequency(
                rss_items=new_items_list,
                word_groups=word_groups,
                filter_words=filter_words,
                global_filters=global_filters,
                new_items=new_items_list,
                max_news_per_keyword=max_news_per_keyword,
                max_keywords=max_keywords,
                sort_by_position_first=sort_by_position_first,
                timezone=timezone,
                rank_threshold=rank_threshold,
                quiet=True,
            )

    else:
        # daily 模式
        if not raw_rss_items:
            logger.info("RSS 当日汇总模式：没有 RSS 数据")
            return None, None, None

        rss_stats, _total = count_rss_frequency(
            rss_items=raw_rss_items,
            word_groups=word_groups,
            filter_words=filter_words,
            global_filters=global_filters,
            new_items=new_items_list,
            max_news_per_keyword=max_news_per_keyword,
            max_keywords=max_keywords,
            sort_by_position_first=sort_by_position_first,
            timezone=timezone,
            rank_threshold=rank_threshold,
            quiet=False,
        )
        if not rss_stats:
            logger.info("RSS 当日汇总模式：关键词匹配后没有内容")
            return None, None, raw_rss_items

        if new_items_list:
            rss_new_stats, _ = count_rss_frequency(
                rss_items=new_items_list,
                word_groups=word_groups,
                filter_words=filter_words,
                global_filters=global_filters,
                new_items=new_items_list,
                max_news_per_keyword=max_news_per_keyword,
                max_keywords=max_keywords,
                sort_by_position_first=sort_by_position_first,
                timezone=timezone,
                rank_threshold=rank_threshold,
                quiet=True,
            )

    return rss_stats, rss_new_stats, raw_rss_items


def execute_mode_strategy(
    ctx: AppContext,
    storage_manager,
    report_mode: str,
    rank_threshold: int,
    update_info: dict | None,
    proxy_url: str | None,
    is_docker_container: bool,
    should_open_browser: bool,
    mode_strategy: dict,
    mode_strategies: dict,
    results: dict,
    id_to_name: dict,
    failed_ids: list,
    rss_items: list[dict] | None = None,
    rss_new_items: list[dict] | None = None,
    raw_rss_items: list[dict] | None = None,
) -> str | None:
    """
    执行模式特定逻辑，支持热榜+RSS合并推送

    每次运行都生成 HTML 报告（时间戳快照 + latest/{mode}.html + index.html），
    根据模式发送通知。

    Args:
        ctx: 应用上下文
        storage_manager: 存储管理器
        report_mode: 报告模式
        rank_threshold: 排名阈值
        update_info: 版本更新信息
        proxy_url: 代理 URL
        is_docker_container: 是否运行在 Docker 容器中
        should_open_browser: 是否应该打开浏览器
        mode_strategy: 当前模式策略字典
        mode_strategies: 完整的模式策略字典（用于通知）
        results: 爬取结果
        id_to_name: 平台 ID 到名称映射
        failed_ids: 失败的平台 ID 列表
        rss_items: RSS 统计条目
        rss_new_items: RSS 新增条目
        raw_rss_items: 原始 RSS 条目

    Returns:
        生成的 HTML 文件路径，或 None
    """
    current_platform_ids = ctx.platform_ids

    new_titles = ctx.detect_new_titles(current_platform_ids)
    time_info = ctx.format_time()
    if ctx.config["STORAGE"]["FORMATS"]["TXT"]:
        ctx.save_titles(results, id_to_name, failed_ids)
    word_groups, filter_words, global_filters = ctx.load_frequency_words()

    html_file = None
    stats = []
    ai_result = None
    title_info = None

    if report_mode == "current":
        analysis_data = _load_analysis_data(ctx)
        if analysis_data:
            (
                all_results,
                historical_id_to_name,
                historical_title_info,
                historical_new_titles,
                _,
                _,
                _,
            ) = analysis_data

            logger.info("current 模式：使用过滤后的历史数据", platforms=list(all_results.keys()))

            standalone_data = prepare_standalone_data(
                ctx, all_results, historical_id_to_name, historical_title_info, raw_rss_items
            )

            # Run AI analysis before pipeline
            ai_result = (
                run_ai_analysis(
                    ctx=ctx,
                    stats=[],  # Will be computed in pipeline
                    rss_items=rss_items,
                    mode=report_mode,
                    report_type=mode_strategy["report_type"],
                    id_to_name=historical_id_to_name,
                    current_results=all_results,
                )
                if ctx.config.get("AI_ANALYSIS", {}).get("ENABLED", False)
                else None
            )

            stats, html_file, ai_result = run_analysis_pipeline(
                ctx=ctx,
                data_source=all_results,
                mode=report_mode,
                title_info=historical_title_info,
                new_titles=historical_new_titles,
                word_groups=word_groups,
                filter_words=filter_words,
                id_to_name=historical_id_to_name,
                report_mode=report_mode,
                update_info=update_info,
                report_type=mode_strategy["report_type"],
                ai_result=ai_result,
                failed_ids=failed_ids,
                global_filters=global_filters,
                rss_items=rss_items,
                rss_new_items=rss_new_items,
                standalone_data=standalone_data,
            )

            combined_id_to_name = {**historical_id_to_name, **id_to_name}
            new_titles = historical_new_titles
            id_to_name = combined_id_to_name
            title_info = historical_title_info
            results = all_results
        else:
            logger.error("严重错误：无法读取刚保存的数据文件")
            raise RuntimeError("数据一致性检查失败：保存后立即读取失败")

    elif report_mode == "daily":
        analysis_data = _load_analysis_data(ctx)
        if analysis_data:
            (
                all_results,
                historical_id_to_name,
                historical_title_info,
                historical_new_titles,
                _,
                _,
                _,
            ) = analysis_data

            standalone_data = prepare_standalone_data(
                ctx, all_results, historical_id_to_name, historical_title_info, raw_rss_items
            )

            # Run AI analysis before pipeline
            ai_result = (
                run_ai_analysis(
                    ctx=ctx,
                    stats=[],
                    rss_items=rss_items,
                    mode=report_mode,
                    report_type=mode_strategy["report_type"],
                    id_to_name=historical_id_to_name,
                    current_results=all_results,
                )
                if ctx.config.get("AI_ANALYSIS", {}).get("ENABLED", False)
                else None
            )

            stats, html_file, ai_result = run_analysis_pipeline(
                ctx=ctx,
                data_source=all_results,
                mode=report_mode,
                title_info=historical_title_info,
                new_titles=historical_new_titles,
                word_groups=word_groups,
                filter_words=filter_words,
                id_to_name=historical_id_to_name,
                report_mode=report_mode,
                update_info=update_info,
                report_type=mode_strategy["report_type"],
                ai_result=ai_result,
                failed_ids=failed_ids,
                global_filters=global_filters,
                rss_items=rss_items,
                rss_new_items=rss_new_items,
                standalone_data=standalone_data,
            )

            combined_id_to_name = {**historical_id_to_name, **id_to_name}
            new_titles = historical_new_titles
            id_to_name = combined_id_to_name
            title_info = historical_title_info
            results = all_results
        else:
            # 没有历史数据时使用当前数据
            title_info = _prepare_current_title_info(results, time_info)
            standalone_data = prepare_standalone_data(
                ctx, results, id_to_name, title_info, raw_rss_items
            )

            # Run AI analysis before pipeline
            ai_result = (
                run_ai_analysis(
                    ctx=ctx,
                    stats=[],
                    rss_items=rss_items,
                    mode=report_mode,
                    report_type=mode_strategy["report_type"],
                    id_to_name=id_to_name,
                    current_results=results,
                )
                if ctx.config.get("AI_ANALYSIS", {}).get("ENABLED", False)
                else None
            )

            stats, html_file, ai_result = run_analysis_pipeline(
                ctx=ctx,
                data_source=results,
                mode=report_mode,
                title_info=title_info,
                new_titles=new_titles,
                word_groups=word_groups,
                filter_words=filter_words,
                id_to_name=id_to_name,
                report_mode=report_mode,
                update_info=update_info,
                report_type=mode_strategy["report_type"],
                ai_result=ai_result,
                failed_ids=failed_ids,
                global_filters=global_filters,
                rss_items=rss_items,
                rss_new_items=rss_new_items,
                standalone_data=standalone_data,
            )

    else:
        # incremental 模式：只使用当前抓取的数据
        title_info = _prepare_current_title_info(results, time_info)
        standalone_data = prepare_standalone_data(
            ctx, results, id_to_name, title_info, raw_rss_items
        )

        # Run AI analysis before pipeline
        ai_result = (
            run_ai_analysis(
                ctx=ctx,
                stats=[],
                rss_items=rss_items,
                mode=report_mode,
                report_type=mode_strategy["report_type"],
                id_to_name=id_to_name,
                current_results=results,
            )
            if ctx.config.get("AI_ANALYSIS", {}).get("ENABLED", False)
            else None
        )

        stats, html_file, ai_result = run_analysis_pipeline(
            ctx=ctx,
            data_source=results,
            mode=report_mode,
            title_info=title_info,
            new_titles=new_titles,
            word_groups=word_groups,
            filter_words=filter_words,
            id_to_name=id_to_name,
            report_mode=report_mode,
            update_info=update_info,
            report_type=mode_strategy["report_type"],
            ai_result=ai_result,
            failed_ids=failed_ids,
            global_filters=global_filters,
            rss_items=rss_items,
            rss_new_items=rss_new_items,
            standalone_data=standalone_data,
        )

    if html_file:
        logger.info(
            "HTML 报告已生成", file=html_file, latest=f"output/html/latest/{report_mode}.html"
        )

    # 发送通知
    if mode_strategy["should_send_notification"]:
        standalone_data = prepare_standalone_data(
            ctx, results, id_to_name, title_info, raw_rss_items
        )
        send_notification_if_needed(
            ctx=ctx,
            report_mode=report_mode,
            update_info=update_info,
            proxy_url=proxy_url,
            mode_strategies=mode_strategies,
            stats=stats,
            report_type=mode_strategy["report_type"],
            mode=report_mode,
            failed_ids=failed_ids,
            new_titles=new_titles,
            id_to_name=id_to_name,
            html_file_path=html_file,
            rss_items=rss_items,
            rss_new_items=rss_new_items,
            standalone_data=standalone_data,
            ai_result=ai_result,
            current_results=results,
        )

    # 打开浏览器（仅在非容器环境）
    if should_open_browser and html_file:
        file_url = "file://" + str(Path(html_file).resolve())
        logger.info("正在打开 HTML 报告", url=file_url)
        webbrowser.open(file_url)
    elif is_docker_container and html_file:
        logger.info("HTML 报告已生成（Docker 环境）", file=html_file)

    return html_file
