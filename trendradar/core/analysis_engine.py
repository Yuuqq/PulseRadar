# coding=utf-8
"""
AnalysisEngine — 第二个编排器类

从 NewsAnalyzer 中提取的分析编排逻辑，拥有模式策略选择、分析流水线和 AI 分析。
"""

import os
from typing import Dict, Optional

from trendradar.context import AppContext
from trendradar.core.types import CrawlOutput, AnalysisOutput
from trendradar.core.mode_strategy import execute_mode_strategy
from trendradar.logging import get_logger

logger = get_logger(__name__)


def _detect_docker_environment() -> bool:
    """检测是否运行在 Docker 容器中"""
    # 检查 /.dockerenv 文件
    if os.path.exists("/.dockerenv"):
        return True

    # 检查 /proc/1/cgroup 中的 docker 标记
    try:
        with open("/proc/1/cgroup", "r") as f:
            return "docker" in f.read()
    except (FileNotFoundError, PermissionError):
        pass

    # 检查环境变量
    return os.environ.get("DOCKER_CONTAINER") == "true"


class AnalysisEngine:
    """分析引擎 — 编排模式策略、分析流水线和 AI 分析"""

    # 模式策略定义（从 __main__.py 复制）
    MODE_STRATEGIES = {
        "incremental": {
            "mode_name": "增量模式",
            "description": "增量模式（只关注新增新闻，无新增时不推送）",
            "report_type": "增量分析",
            "should_send_notification": True,
        },
        "current": {
            "mode_name": "当前榜单模式",
            "description": "当前榜单模式（当前榜单匹配新闻 + 新增新闻区域 + 按时推送）",
            "report_type": "当前榜单",
            "should_send_notification": True,
        },
        "daily": {
            "mode_name": "全天汇总模式",
            "description": "全天汇总模式（所有匹配新闻 + 新增新闻区域 + 按时推送）",
            "report_type": "全天汇总",
            "should_send_notification": True,
        },
    }

    def __init__(
        self,
        ctx: AppContext,
        update_info: Optional[Dict] = None,
        proxy_url: Optional[str] = None,
    ):
        """
        初始化分析引擎

        Args:
            ctx: 应用上下文
            update_info: 版本更新信息
            proxy_url: 代理 URL
        """
        self.ctx = ctx
        self.storage_manager = ctx.get_storage_manager()
        self.update_info = update_info
        self.proxy_url = proxy_url
        self.report_mode = ctx.config["REPORT_MODE"]
        self.rank_threshold = ctx.rank_threshold
        self.is_docker_container = _detect_docker_environment()
        self.is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"

    def analyze(self, crawl_output: CrawlOutput) -> AnalysisOutput:
        """
        运行完整的分析流水线：模式策略 -> 分析 -> AI -> HTML

        Args:
            crawl_output: 爬取输出（来自 CrawlCoordinator）

        Returns:
            分析输出（stats, html_file_path, ai_result）
        """
        mode_strategy = self._get_mode_strategy()

        html_file = execute_mode_strategy(
            ctx=self.ctx,
            storage_manager=self.storage_manager,
            report_mode=self.report_mode,
            rank_threshold=self.rank_threshold,
            update_info=self.update_info,
            proxy_url=self.proxy_url,
            is_docker_container=self.is_docker_container,
            should_open_browser=self._should_open_browser(),
            mode_strategy=mode_strategy,
            mode_strategies=self.MODE_STRATEGIES,
            results=crawl_output.results,
            id_to_name=crawl_output.id_to_name,
            failed_ids=list(crawl_output.failed_ids),
            rss_items=crawl_output.rss.stats_items,
            rss_new_items=crawl_output.rss.new_items,
            raw_rss_items=crawl_output.rss.raw_items,
        )

        # Note: execute_mode_strategy currently handles notification internally.
        # AnalysisOutput captures the analysis results for the facade.
        # For now, return a minimal AnalysisOutput; the full return data
        # will be wired in Plan 04 when the facade is collapsed.
        return AnalysisOutput(stats=[], html_file_path=html_file, ai_result=None)

    def _get_mode_strategy(self) -> Dict:
        """获取当前报告模式的策略配置"""
        return self.MODE_STRATEGIES.get(self.report_mode, self.MODE_STRATEGIES["daily"])

    def _should_open_browser(self) -> bool:
        """判断是否应该打开浏览器"""
        return not self.is_github_actions and not self.is_docker_container
