"""
TrendRadar 主程序

热点新闻聚合与分析工具
支持: python -m trendradar
"""

import argparse
import contextlib
import os

from trendradar import __version__
from trendradar.context import AppContext
from trendradar.core import load_config
from trendradar.core.analysis_engine import AnalysisEngine
from trendradar.core.crawl_coordinator import CrawlCoordinator
from trendradar.core.notification_service import has_notification_configured
from trendradar.core.version_check import check_all_versions
from trendradar.logging import get_logger
from trendradar.utils.time import DEFAULT_TIMEZONE

logger = get_logger(__name__)


# === 主分析器 ===
class NewsAnalyzer:
    """新闻分析器 — 薄门面，委托给 CrawlCoordinator 和 AnalysisEngine"""

    def __init__(self, config: dict | None = None, update_info: dict | None = None):
        """
        初始化新闻分析器

        Args:
            config: 配置字典（如果为 None 则加载默认配置）
            update_info: 版本更新信息（构造器参数，避免后构造变更）
        """
        # 使用传入的配置或加载新配置
        if config is None:
            logger.info("正在加载配置")
            config = load_config()
        logger.info(
            "配置加载完成",
            version=__version__,
            platforms=len(config["PLATFORMS"]),
            timezone=config.get("TIMEZONE", DEFAULT_TIMEZONE),
        )

        # 创建应用上下文
        self.ctx = AppContext(config)
        self.update_info = update_info

        # 代理设置（保留现有逻辑）
        self.proxy_url = None
        is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"
        if not is_github_actions and self.ctx.config["USE_PROXY"]:
            self.proxy_url = self.ctx.config["DEFAULT_PROXY"]

        # 存储初始化（保留现有逻辑）
        env_retention = os.environ.get("STORAGE_RETENTION_DAYS", "").strip()
        if env_retention:
            self.ctx.config["STORAGE"]["RETENTION_DAYS"] = int(env_retention)
        self.storage_manager = self.ctx.get_storage_manager()

        # 创建编排器
        self.crawl_coordinator = CrawlCoordinator(self.ctx, proxy_url=self.proxy_url)
        self.analysis_engine = AnalysisEngine(
            self.ctx, update_info=self.update_info, proxy_url=self.proxy_url
        )

    def run(self) -> None:
        """执行分析流程"""
        try:
            self._log_startup()
            crawl_output = self.crawl_coordinator.crawl_all()
            self.analysis_engine.analyze(crawl_output)
        except Exception as e:
            logger.error("分析流程执行出错", error=str(e))
            if self.ctx.config.get("DEBUG", False):
                raise
        finally:
            # 清理资源（包括过期数据清理和数据库连接关闭）
            self.ctx.cleanup()

    def _log_startup(self) -> None:
        """记录启动信息（时间、爬虫状态、通知状态、模式）"""
        now = self.ctx.get_time()
        logger.info("当前北京时间", time=now.strftime("%Y-%m-%d %H:%M:%S"))

        if not self.ctx.config["ENABLE_CRAWLER"]:
            logger.info("爬虫功能已禁用，程序退出", config="ENABLE_CRAWLER=False")
            return

        has_notification = has_notification_configured(self.ctx)
        if not self.ctx.config["ENABLE_NOTIFICATION"]:
            logger.info("通知功能已禁用，将只进行数据抓取", config="ENABLE_NOTIFICATION=False")
        elif not has_notification:
            logger.info("未配置任何通知渠道，将只进行数据抓取，不发送通知")
        else:
            logger.info("通知功能已启用，将发送通知")

        mode_strategy = self.analysis_engine._get_mode_strategy()
        logger.info(
            "运行模式",
            report_mode=self.ctx.config["REPORT_MODE"],
            description=mode_strategy["description"],
        )


def _ensure_utf8_output():
    """确保 Windows 终端使用 UTF-8 编码输出，避免 emoji 等字符导致 UnicodeEncodeError"""
    import sys

    if sys.platform == "win32":
        for stream_name in ("stdout", "stderr"):
            stream = getattr(sys, stream_name, None)
            if stream and hasattr(stream, "reconfigure"):
                with contextlib.suppress(Exception):
                    stream.reconfigure(encoding="utf-8", errors="replace")


def main():
    """主程序入口"""
    _ensure_utf8_output()

    # 初始化结构化日志（在解析参数之前，确保所有日志都被捕获）
    from trendradar.logging import configure_logging

    configure_logging(debug=os.environ.get("DEBUG", "").lower() in ("1", "true", "yes"))

    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="TrendRadar - 热点新闻聚合与分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
状态管理命令:
  --show-push-status     显示推送状态（窗口配置、今日是否已推送）
  --show-ai-status       显示 AI 分析状态
  --reset-push-state     重置今日推送状态（允许重新推送）
  --reset-ai-state       重置今日 AI 分析状态
  --force-push           忽略 once_per_day 限制，强制推送
  --force-ai             忽略 once_per_day 限制，强制 AI 分析

示例:
  python -m trendradar                    # 正常运行
  python -m trendradar --show-push-status # 查看推送状态
  python -m trendradar --reset-push-state # 重置推送状态后再运行
  python -m trendradar --force-push       # 强制推送（忽略今日已推送限制）
""",
    )
    parser.add_argument("--show-push-status", action="store_true", help="显示推送状态信息")
    parser.add_argument("--show-ai-status", action="store_true", help="显示 AI 分析状态信息")
    parser.add_argument("--reset-push-state", action="store_true", help="重置今日推送状态")
    parser.add_argument("--reset-ai-state", action="store_true", help="重置今日 AI 分析状态")
    parser.add_argument("--force-push", action="store_true", help="忽略 once_per_day 限制，强制推送")
    parser.add_argument("--force-ai", action="store_true", help="忽略 once_per_day 限制，强制 AI 分析")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config file (default: CONFIG_PATH or config/config.yaml)",
    )

    args = parser.parse_args()

    debug_mode = False
    try:
        # 先加载配置
        config = load_config(config_path=args.config)

        # 处理状态查看/重置命令
        if args.show_push_status or args.show_ai_status or args.reset_push_state or args.reset_ai_state:
            _handle_status_commands(config, args)
            return

        # 设置强制推送标志
        if args.force_push:
            config["_FORCE_PUSH"] = True
            logger.info("已启用强制推送模式，将忽略 once_per_day 限制")

        if args.force_ai:
            config["_FORCE_AI"] = True
            logger.info("已启用强制 AI 分析模式，将忽略 once_per_day 限制")

        version_url = config.get("VERSION_CHECK_URL", "")
        configs_version_url = config.get("CONFIGS_VERSION_CHECK_URL", "")

        # 统一版本检查（程序版本 + 配置文件版本，只请求一次远程）
        # 计算 update_info（在构造 NewsAnalyzer 之前）
        update_info = None
        if version_url:
            need_update, remote_version = check_all_versions(version_url, configs_version_url)
            is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"
            if is_github_actions and need_update and remote_version:
                update_info = {
                    "current_version": __version__,
                    "remote_version": remote_version,
                }

        # 复用已加载的配置，避免重复加载
        # 传递 update_info 作为构造器参数（D-08）
        analyzer = NewsAnalyzer(config=config, update_info=update_info)

        # 获取 debug 配置
        debug_mode = analyzer.ctx.config.get("DEBUG", False)
        analyzer.run()
    except FileNotFoundError as e:
        logger.error(
            "配置文件错误",
            error=str(e),
            hint="请确保 config/config.yaml 和 config/frequency_words.txt 存在",
        )
    except Exception as e:
        logger.error("程序运行错误", error=str(e))
        if debug_mode:
            raise


def _handle_status_commands(config: dict, args) -> None:
    """处理状态查看/重置命令"""
    from trendradar.context import AppContext

    ctx = AppContext(config)
    push_manager = ctx.create_push_manager()

    logger.info("TrendRadar 状态信息", version=__version__)

    # 显示推送状态
    if args.show_push_status:
        push_window_config = config.get("PUSH_WINDOW", {})
        status = push_manager.get_push_status(push_window_config)
        logger.info(
            "推送状态",
            current_time=status["current_time"],
            timezone=status["timezone"],
            current_date=status["current_date"],
            window_enabled=status["enabled"],
            window_start=status.get("window_start"),
            window_end=status.get("window_end"),
            in_window=status.get("in_window"),
            once_per_day=status.get("once_per_day"),
            executed_today=status.get("executed_today", False),
        )

    # 显示 AI 分析状态
    if args.show_ai_status:
        ai_window_config = config.get("AI_ANALYSIS", {}).get("ANALYSIS_WINDOW", {})
        status = push_manager.get_ai_analysis_status(ai_window_config)
        logger.info(
            "AI 分析状态",
            current_time=status["current_time"],
            timezone=status["timezone"],
            current_date=status["current_date"],
            window_enabled=status["enabled"],
            window_start=status.get("window_start"),
            window_end=status.get("window_end"),
            in_window=status.get("in_window"),
            once_per_day=status.get("once_per_day"),
            executed_today=status.get("executed_today", False),
        )

    # 重置推送状态
    if args.reset_push_state:
        logger.info("正在重置推送状态")
        if push_manager.reset_push_state():
            logger.info("推送状态已重置")
        else:
            logger.error("推送状态重置失败")

    # 重置 AI 分析状态
    if args.reset_ai_state:
        logger.info("正在重置 AI 分析状态")
        if push_manager.reset_ai_analysis_state():
            logger.info("AI 分析状态已重置")
        else:
            logger.error("AI 分析状态重置失败")

    logger.info("状态查询完成")

    # 清理资源
    ctx.cleanup()


if __name__ == "__main__":
    main()
