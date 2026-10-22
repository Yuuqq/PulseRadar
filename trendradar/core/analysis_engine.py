"""
AnalysisEngine — 第二个编排器类

从 NewsAnalyzer 中提取的分析编排逻辑，拥有模式策略选择、分析流水线和 AI 分析。
"""

import os

from trendradar.context import AppContext
from trendradar.core.mode_strategies import (
    MODE_STRATEGIES,
    ModeStrategy,
    get_mode_strategy,
)
from trendradar.core.mode_strategy import execute_mode_strategy
from trendradar.core.types import AnalysisOutput, CrawlOutput
from trendradar.logging import get_logger

logger = get_logger(__name__)


def _detect_docker_environment() -> bool:
    """检测是否运行在 Docker 容器中"""
    # 检查 /.dockerenv 文件
    if os.path.exists("/.dockerenv"):
        return True

    # 检查 /proc/1/cgroup 中的 docker 标记
    try:
        with open("/proc/1/cgroup") as f:
            return "docker" in f.read()
    except (FileNotFoundError, PermissionError):
        pass

    # 检查环境变量
    return os.environ.get("DOCKER_CONTAINER") == "true"


class AnalysisEngine:
    """分析引擎 — 编排模式策略、分析流水线和 AI 分析"""

    # 模式策略表（单一权威来源在 trendradar.core.mode_strategies）
    # 保留类属性别名以维持向后兼容。
    MODE_STRATEGIES: dict[str, ModeStrategy] = MODE_STRATEGIES  # type: ignore[assignment]

    def __init__(
        self,
        ctx: AppContext,
        update_info: dict | None = None,
        proxy_url: str | None = None,
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

    def _get_mode_strategy(self) -> ModeStrategy:
        """获取当前报告模式的策略配置（未知模式回退到 daily）"""
        return get_mode_strategy(self.report_mode)

    def _should_open_browser(self) -> bool:
        """判断是否应该打开浏览器"""
        return not self.is_github_actions and not self.is_docker_container
