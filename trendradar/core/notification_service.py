# coding=utf-8
"""
通知发送服务

从 NewsAnalyzer 中提取的通知派发逻辑，接受显式参数而非 self。
"""

from typing import Dict, List, Optional

from trendradar.context import AppContext
from trendradar.ai import AIAnalysisResult
from trendradar.core.ai_service import run_ai_analysis
from trendradar.logging import get_logger

logger = get_logger(__name__)


def has_notification_configured(ctx: AppContext) -> bool:
    """检查是否配置了任何通知渠道"""
    cfg = ctx.config
    return any(
        [
            cfg["FEISHU_WEBHOOK_URL"],
            cfg["DINGTALK_WEBHOOK_URL"],
            cfg["WEWORK_WEBHOOK_URL"],
            (cfg["TELEGRAM_BOT_TOKEN"] and cfg["TELEGRAM_CHAT_ID"]),
            (
                cfg["EMAIL_FROM"]
                and cfg["EMAIL_PASSWORD"]
                and cfg["EMAIL_TO"]
            ),
            (cfg["NTFY_SERVER_URL"] and cfg["NTFY_TOPIC"]),
            cfg["BARK_URL"],
            cfg["SLACK_WEBHOOK_URL"],
            cfg["GENERIC_WEBHOOK_URL"],
        ]
    )


def has_valid_content(
    report_mode: str,
    stats: List[Dict],
    new_titles: Optional[Dict] = None,
) -> bool:
    """检查是否有有效的新闻内容"""
    if report_mode == "incremental":
        return any(stat["count"] > 0 for stat in stats)
    elif report_mode == "current":
        return any(stat["count"] > 0 for stat in stats)
    else:
        has_matched_news = any(stat["count"] > 0 for stat in stats)
        has_new_news = bool(
            new_titles and any(len(titles) > 0 for titles in new_titles.values())
        )
        return has_matched_news or has_new_news


def send_notification_if_needed(
    ctx: AppContext,
    report_mode: str,
    update_info: Optional[Dict],
    proxy_url: Optional[str],
    mode_strategies: Optional[Dict],
    stats: List[Dict],
    report_type: str,
    mode: str,
    failed_ids: Optional[List] = None,
    new_titles: Optional[Dict] = None,
    id_to_name: Optional[Dict] = None,
    html_file_path: Optional[str] = None,
    rss_items: Optional[List[Dict]] = None,
    rss_new_items: Optional[List[Dict]] = None,
    standalone_data: Optional[Dict] = None,
    ai_result: Optional[AIAnalysisResult] = None,
    current_results: Optional[Dict] = None,
) -> bool:
    """
    统一的通知发送逻辑，包含所有判断条件，支持热榜+RSS合并推送+AI分析+独立展示区

    Args:
        ctx: 应用上下文
        report_mode: 报告模式
        update_info: 版本更新信息
        proxy_url: 代理 URL
        mode_strategies: 模式策略字典（用于日志）
        stats: 统计数据列表
        report_type: 报告类型字符串
        mode: 运行模式
        failed_ids: 失败的平台 ID 列表
        new_titles: 新增标题字典
        id_to_name: 平台 ID 到名称映射
        html_file_path: HTML 文件路径
        rss_items: RSS 统计条目
        rss_new_items: RSS 新增条目
        standalone_data: 独立展示区数据
        ai_result: 已完成的 AI 分析结果（避免重复分析）
        current_results: 当前抓取结果

    Returns:
        是否成功发送通知
    """
    has_notif = has_notification_configured(ctx)
    cfg = ctx.config

    has_news_content = has_valid_content(report_mode, stats, new_titles)
    has_rss_content = bool(rss_items and len(rss_items) > 0)
    has_any_content = has_news_content or has_rss_content

    news_count = sum(len(stat.get("titles", [])) for stat in stats) if stats else 0
    rss_count = sum(stat.get("count", 0) for stat in rss_items) if rss_items else 0

    if cfg["ENABLE_NOTIFICATION"] and has_notif and has_any_content:
        total_count = news_count + rss_count
        logger.info("准备发送推送", news_count=news_count, rss_count=rss_count, total=total_count)

        # 推送窗口控制
        if cfg["PUSH_WINDOW"]["ENABLED"]:
            push_manager = ctx.create_push_manager()
            time_range_start = cfg["PUSH_WINDOW"]["TIME_RANGE"]["START"]
            time_range_end = cfg["PUSH_WINDOW"]["TIME_RANGE"]["END"]

            if not push_manager.is_in_time_range(time_range_start, time_range_end):
                now = ctx.get_time()
                logger.info(
                    "推送窗口控制：跳过",
                    current_time=now.strftime('%H:%M'),
                    window=f"{time_range_start}-{time_range_end}",
                )
                return False

            if cfg["PUSH_WINDOW"]["ONCE_PER_DAY"]:
                if push_manager.has_pushed_today():
                    logger.info("推送窗口控制：今天已推送过，跳过")
                    return False
                else:
                    logger.info("推送窗口控制：今天首次推送")

        # AI 分析：优先使用传入的结果，避免重复分析
        if ai_result is None:
            ai_config = cfg.get("AI_ANALYSIS", {})
            if ai_config.get("ENABLED", False):
                ai_result = run_ai_analysis(
                    ctx=ctx,
                    stats=stats,
                    rss_items=rss_items,
                    mode=mode,
                    report_type=report_type,
                    id_to_name=id_to_name,
                    current_results=current_results,
                )

        report_data = ctx.prepare_report(stats, failed_ids, new_titles, id_to_name, mode)
        update_info_to_send = update_info if cfg["SHOW_VERSION_UPDATE"] else None

        dispatcher = ctx.create_notification_dispatcher()
        results = dispatcher.dispatch_all(
            report_data=report_data,
            report_type=report_type,
            update_info=update_info_to_send,
            proxy_url=proxy_url,
            mode=mode,
            html_file_path=html_file_path,
            rss_items=rss_items,
            rss_new_items=rss_new_items,
            ai_analysis=ai_result,
            standalone_data=standalone_data,
        )

        if not results:
            logger.warning("未配置任何通知渠道，跳过通知发送")
            return False

        if (
            cfg["PUSH_WINDOW"]["ENABLED"]
            and cfg["PUSH_WINDOW"]["ONCE_PER_DAY"]
            and any(results.values())
        ):
            push_manager = ctx.create_push_manager()
            push_manager.record_push(report_type)

        return True

    elif cfg["ENABLE_NOTIFICATION"] and not has_notif:
        logger.warning("通知功能已启用但未配置任何通知渠道，将跳过通知发送")
    elif not cfg["ENABLE_NOTIFICATION"]:
        logger.info("跳过通知：通知功能已禁用", report_type=report_type)
    elif cfg["ENABLE_NOTIFICATION"] and has_notif and not has_any_content:
        mode_name = mode_strategies.get(report_mode, {}).get('mode_name', report_mode) if mode_strategies else report_mode
        if report_mode == "incremental":
            if not has_rss_content:
                logger.info("跳过通知：增量模式下未检测到匹配的新闻和RSS")
            else:
                logger.info("跳过通知：增量模式下新闻未匹配到关键词")
        else:
            logger.info("跳过通知：未检测到匹配的新闻", mode=mode_name)

    return False
