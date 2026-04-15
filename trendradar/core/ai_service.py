"""
AI 分析服务

从 NewsAnalyzer 中提取的 AI 分析相关逻辑，接受显式参数而非 self。
"""

from trendradar.ai import AIAnalysisResult, AIAnalyzer
from trendradar.context import AppContext
from trendradar.core.analyzer import convert_keyword_stats_to_platform_stats
from trendradar.logging import get_logger

logger = get_logger(__name__)


def _load_analysis_data(
    ctx: AppContext,
    quiet: bool = False,
) -> tuple[dict, dict, dict, dict, list, list, list] | None:
    """统一的数据加载和预处理，使用当前监控平台列表过滤历史数据"""
    try:
        # 获取当前配置的监控平台ID列表
        current_platform_ids = ctx.platform_ids
        if not quiet:
            logger.info("当前监控平台", platform_ids=current_platform_ids)

        all_results, id_to_name, title_info = ctx.read_today_titles(
            current_platform_ids, quiet=quiet
        )

        if not all_results:
            logger.info("没有找到当天的数据")
            return None

        total_titles = sum(len(titles) for titles in all_results.values())
        if not quiet:
            logger.info("读取标题完成", total=total_titles)

        new_titles = ctx.detect_new_titles(current_platform_ids, quiet=quiet)
        word_groups, filter_words, global_filters = ctx.load_frequency_words()

        return (
            all_results,
            id_to_name,
            title_info,
            new_titles,
            word_groups,
            filter_words,
            global_filters,
        )
    except Exception as e:
        logger.error("数据加载失败", error=str(e))
        return None


def _prepare_current_title_info(results: dict, time_info: str) -> dict:
    """从当前抓取结果构建标题信息"""
    title_info = {}
    for source_id, titles_data in results.items():
        title_info[source_id] = {}
        for title, title_data in titles_data.items():
            ranks = title_data.get("ranks", [])
            url = title_data.get("url", "")
            mobile_url = title_data.get("mobileUrl", "")

            title_info[source_id][title] = {
                "first_time": time_info,
                "last_time": time_info,
                "count": 1,
                "ranks": ranks,
                "url": url,
                "mobileUrl": mobile_url,
            }
    return title_info


def prepare_ai_analysis_data(
    ctx: AppContext,
    ai_mode: str,
    current_results: dict | None = None,
    current_id_to_name: dict | None = None,
) -> tuple[list[dict], dict | None]:
    """
    为 AI 分析准备指定模式的数据

    Args:
        ctx: 应用上下文
        ai_mode: AI 分析模式 (daily/current/incremental)
        current_results: 当前抓取的结果（用于 incremental 模式）
        current_id_to_name: 当前的平台映射（用于 incremental 模式）

    Returns:
        (stats, id_to_name) 元组
    """
    try:
        word_groups, filter_words, global_filters = ctx.load_frequency_words()

        if ai_mode == "incremental":
            if not current_results or not current_id_to_name:
                logger.error("incremental 模式需要当前抓取数据，但未提供")
                return [], None

            time_info = ctx.format_time()
            title_info = _prepare_current_title_info(current_results, time_info)
            new_titles = ctx.detect_new_titles(list(current_results.keys()))

            stats, _ = ctx.count_frequency(
                current_results,
                word_groups,
                filter_words,
                current_id_to_name,
                title_info,
                new_titles,
                mode="incremental",
                global_filters=global_filters,
                quiet=True,
            )

            if ctx.display_mode == "platform" and stats:
                stats = convert_keyword_stats_to_platform_stats(
                    stats,
                    ctx.weight_config,
                    ctx.rank_threshold,
                )

            return stats, current_id_to_name

        elif ai_mode in ["daily", "current"]:
            analysis_data = _load_analysis_data(ctx, quiet=True)
            if not analysis_data:
                logger.error("无法加载历史数据", ai_mode=ai_mode)
                return [], None

            (
                all_results,
                id_to_name,
                title_info,
                new_titles,
                _,
                _,
                _,
            ) = analysis_data

            stats, _ = ctx.count_frequency(
                all_results,
                word_groups,
                filter_words,
                id_to_name,
                title_info,
                new_titles,
                mode=ai_mode,
                global_filters=global_filters,
                quiet=True,
            )

            if ctx.display_mode == "platform" and stats:
                stats = convert_keyword_stats_to_platform_stats(
                    stats,
                    ctx.weight_config,
                    ctx.rank_threshold,
                )

            return stats, id_to_name

        else:
            logger.error("未知的 AI 模式", ai_mode=ai_mode)
            return [], None

    except Exception as e:
        logger.error("准备 AI 模式数据时出错", ai_mode=ai_mode, error=str(e))
        if ctx.config.get("DEBUG", False):
            import traceback

            traceback.print_exc()
        return [], None


def run_ai_analysis(
    ctx: AppContext,
    stats: list[dict],
    rss_items: list[dict] | None,
    mode: str,
    report_type: str,
    id_to_name: dict | None,
    current_results: dict | None = None,
) -> AIAnalysisResult | None:
    """
    执行 AI 分析

    Args:
        ctx: 应用上下文
        stats: 统计数据
        rss_items: RSS 统计条目
        mode: 报告模式
        report_type: 报告类型
        id_to_name: 平台 ID 到名称映射
        current_results: 当前抓取结果

    Returns:
        AI 分析结果，或 None（如果未启用或跳过）
    """
    analysis_config = ctx.config.get("AI_ANALYSIS", {})
    if not analysis_config.get("ENABLED", False):
        return None

    analysis_window = analysis_config.get("ANALYSIS_WINDOW", {})
    if analysis_window.get("ENABLED", False):
        push_manager = ctx.create_push_manager()
        time_range_start = analysis_window["TIME_RANGE"]["START"]
        time_range_end = analysis_window["TIME_RANGE"]["END"]

        if not push_manager.is_in_time_range(time_range_start, time_range_end):
            now = ctx.get_time()
            logger.info(
                "AI 分析窗口控制：跳过",
                current_time=now.strftime("%H:%M"),
                window=f"{time_range_start}-{time_range_end}",
            )
            return None

        if analysis_window.get("ONCE_PER_DAY", False):
            if push_manager.storage_backend.has_ai_analyzed_today():
                logger.info("AI 分析窗口控制：今天已分析过，跳过")
                return None
            else:
                logger.info("AI 分析窗口控制：今天首次分析")

    logger.info("正在进行 AI 分析")
    try:
        ai_config = ctx.config.get("AI", {})
        debug_mode = ctx.config.get("DEBUG", False)
        analyzer = AIAnalyzer(ai_config, analysis_config, ctx.get_time, debug=debug_mode)

        ai_mode_config = analysis_config.get("MODE", "follow_report")
        if ai_mode_config == "follow_report":
            ai_mode = mode
            ai_stats = stats
            ai_id_to_name = id_to_name
        elif ai_mode_config in ["daily", "current", "incremental"]:
            ai_mode = ai_mode_config
            if ai_mode != mode:
                logger.info("使用独立 AI 分析模式", ai_mode=ai_mode, push_mode=mode)
                logger.info("正在准备 AI 模式数据", ai_mode=ai_mode)

                ai_stats, ai_id_to_name = prepare_ai_analysis_data(
                    ctx, ai_mode, current_results, id_to_name
                )
                if not ai_stats:
                    logger.warning("无法准备 AI 模式数据，回退到推送模式数据", ai_mode=ai_mode)
                    ai_stats = stats
                    ai_id_to_name = id_to_name
                    ai_mode = mode
            else:
                ai_stats = stats
                ai_id_to_name = id_to_name
        else:
            logger.warning(
                "无效的 ai_analysis.mode 配置，使用推送模式",
                config_value=ai_mode_config,
                fallback_mode=mode,
            )
            ai_mode = mode
            ai_stats = stats
            ai_id_to_name = id_to_name

        platforms = list(ai_id_to_name.values()) if ai_id_to_name else []
        keywords = [s.get("word", "") for s in ai_stats if s.get("word")] if ai_stats else []

        if ai_mode != mode:
            ai_report_type = {
                "daily": "当日汇总",
                "current": "当前榜单",
                "incremental": "增量更新",
            }.get(ai_mode, report_type)
        else:
            ai_report_type = report_type

        result = analyzer.analyze(
            stats=ai_stats,
            rss_stats=rss_items,
            report_mode=ai_mode,
            report_type=ai_report_type,
            platforms=platforms,
            keywords=keywords,
        )

        if result.success:
            result.ai_mode = ai_mode
            if result.error:
                logger.info("AI 分析完成（有警告）", warning=result.error)
            else:
                logger.info("AI 分析完成")

            if analysis_window.get("ENABLED", False) and analysis_window.get("ONCE_PER_DAY", False):
                push_manager = ctx.create_push_manager()
                push_manager.storage_backend.record_ai_analysis(ai_mode)
        else:
            logger.error("AI 分析失败", error=result.error)

        return result

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        logger.error("AI 分析出错", error_type=error_type, error=error_msg, exc_info=True)
        return AIAnalysisResult(success=False, error=f"{error_type}: {error_msg}")
