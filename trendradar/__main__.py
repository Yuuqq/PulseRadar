# coding=utf-8
"""
TrendRadar 主程序

热点新闻聚合与分析工具
支持: python -m trendradar
"""

import argparse
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from trendradar.context import AppContext
from trendradar import __version__
from trendradar.core import load_config
from trendradar.logging import get_logger
from trendradar.core.pipeline import prepare_standalone_data, run_analysis_pipeline
from trendradar.core.mode_strategy import (
    process_rss_data_by_mode,
    execute_mode_strategy,
    convert_rss_items_to_list,
)
from trendradar.core.notification_service import (
    has_notification_configured,
    send_notification_if_needed,
)
from trendradar.core.ai_service import prepare_ai_analysis_data, run_ai_analysis
from trendradar.core.rss_crawler import crawl_rss_data
from trendradar.core.version_check import (
    check_all_versions,
    fetch_remote_version as _fetch_remote_version,
    parse_version as _parse_version,
)
from trendradar.crawler import DataFetcher
from trendradar.storage import convert_crawl_results_to_news_data, convert_news_data_to_results
from trendradar.utils.time import DEFAULT_TIMEZONE
from trendradar.ai import AIAnalysisResult
from trendradar.core.trend import TrendAnalyzer, TrendReport

logger = get_logger(__name__)


# === 主分析器 ===
class NewsAnalyzer:
    """新闻分析器"""

    # 模式策略定义
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

    def __init__(self, config: Optional[Dict] = None):
        # 使用传入的配置或加载新配置
        if config is None:
            logger.info("正在加载配置")
            config = load_config()
        logger.info("配置加载完成", version=__version__, platforms=len(config['PLATFORMS']), timezone=config.get('TIMEZONE', DEFAULT_TIMEZONE))

        # 创建应用上下文
        self.ctx = AppContext(config)

        self.request_interval = self.ctx.config["REQUEST_INTERVAL"]
        self.report_mode = self.ctx.config["REPORT_MODE"]
        self.rank_threshold = self.ctx.rank_threshold
        self.is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"
        self.is_docker_container = self._detect_docker_environment()
        self.update_info = None
        self.proxy_url = None
        self._setup_proxy()

        crawler_api_url = (self.ctx.config.get("CRAWLER_API_URL") or "").strip()
        self.data_fetcher = DataFetcher(
            proxy_url=self.proxy_url,
            api_url=crawler_api_url or None,
        )

        # 初始化存储管理器（使用 AppContext）
        self._init_storage_manager()
        # 注意：update_info 由 main() 函数设置，避免重复请求远程版本

    def _init_storage_manager(self) -> None:
        """初始化存储管理器（使用 AppContext）"""
        # 获取数据保留天数（支持环境变量覆盖）
        env_retention = os.environ.get("STORAGE_RETENTION_DAYS", "").strip()
        if env_retention:
            # 环境变量覆盖配置
            self.ctx.config["STORAGE"]["RETENTION_DAYS"] = int(env_retention)

        self.storage_manager = self.ctx.get_storage_manager()
        logger.info("存储后端初始化", backend=self.storage_manager.backend_name)

        retention_days = self.ctx.config.get("STORAGE", {}).get("RETENTION_DAYS", 0)
        if retention_days > 0:
            logger.info("数据保留天数", days=retention_days)

    def _detect_docker_environment(self) -> bool:
        """检测是否运行在 Docker 容器中"""
        try:
            if os.environ.get("DOCKER_CONTAINER") == "true":
                return True

            if os.path.exists("/.dockerenv"):
                return True

            return False
        except Exception:
            return False

    def _should_open_browser(self) -> bool:
        """判断是否应该打开浏览器"""
        return not self.is_github_actions and not self.is_docker_container

    def _setup_proxy(self) -> None:
        """设置代理配置"""
        if not self.is_github_actions and self.ctx.config["USE_PROXY"]:
            self.proxy_url = self.ctx.config["DEFAULT_PROXY"]
            logger.info("代理配置", env="本地", proxy=True)
        elif not self.is_github_actions and not self.ctx.config["USE_PROXY"]:
            logger.info("代理配置", env="本地", proxy=False)
        else:
            logger.info("代理配置", env="GitHub Actions", proxy=False)

    def _set_update_info_from_config(self) -> None:
        """从已缓存的远程版本设置更新信息（不再重复请求）"""
        try:
            version_url = self.ctx.config.get("VERSION_CHECK_URL", "")
            if not version_url:
                return

            remote_version = _fetch_remote_version(version_url, self.proxy_url)
            if remote_version:
                need_update = _parse_version(__version__) < _parse_version(remote_version)
                if need_update:
                    self.update_info = {
                        "current_version": __version__,
                        "remote_version": remote_version,
                    }
        except Exception as e:
            logger.error("版本检查出错", error=str(e))

    def _get_mode_strategy(self) -> Dict:
        """获取当前模式的策略配置"""
        return self.MODE_STRATEGIES.get(self.report_mode, self.MODE_STRATEGIES["daily"])

    def _has_notification_configured(self) -> bool:
        """检查是否配置了任何通知渠道"""
        return has_notification_configured(self.ctx)

    def _has_valid_content(
        self, stats: List[Dict], new_titles: Optional[Dict] = None
    ) -> bool:
        """检查是否有有效的新闻内容"""
        if self.report_mode == "incremental":
            # 增量模式：只要有匹配的新闻就推送
            # count_word_frequency 已经确保只处理新增的新闻（包括当天第一次爬取的情况）
            has_matched_news = any(stat["count"] > 0 for stat in stats)
            return has_matched_news
        elif self.report_mode == "current":
            # current模式：只要stats有内容就说明有匹配的新闻
            return any(stat["count"] > 0 for stat in stats)
        else:
            # 当日汇总模式下，检查是否有匹配的频率词新闻或新增新闻
            has_matched_news = any(stat["count"] > 0 for stat in stats)
            has_new_news = bool(
                new_titles and any(len(titles) > 0 for titles in new_titles.values())
            )
            return has_matched_news or has_new_news

    def _prepare_ai_analysis_data(
        self,
        ai_mode: str,
        current_results: Optional[Dict] = None,
        current_id_to_name: Optional[Dict] = None,
    ) -> Tuple[List[Dict], Optional[Dict]]:
        """为 AI 分析准备指定模式的数据"""
        return prepare_ai_analysis_data(
            ctx=self.ctx,
            ai_mode=ai_mode,
            prepare_current_title_info_fn=self._prepare_current_title_info,
            load_analysis_data_fn=self._load_analysis_data,
            current_results=current_results,
            current_id_to_name=current_id_to_name,
        )

    def _run_ai_analysis(
        self,
        stats: List[Dict],
        rss_items: Optional[List[Dict]],
        mode: str,
        report_type: str,
        id_to_name: Optional[Dict],
        current_results: Optional[Dict] = None,
    ) -> Optional[AIAnalysisResult]:
        """执行 AI 分析"""
        return run_ai_analysis(
            ctx=self.ctx,
            prepare_ai_data_fn=self._prepare_ai_analysis_data,
            stats=stats,
            rss_items=rss_items,
            mode=mode,
            report_type=report_type,
            id_to_name=id_to_name,
            current_results=current_results,
        )

    def _load_analysis_data(
        self,
        quiet: bool = False,
    ) -> Optional[Tuple[Dict, Dict, Dict, Dict, List, List]]:
        """统一的数据加载和预处理，使用当前监控平台列表过滤历史数据"""
        try:
            # 获取当前配置的监控平台ID列表
            current_platform_ids = self.ctx.platform_ids
            if not quiet:
                logger.info("当前监控平台", platform_ids=current_platform_ids)

            all_results, id_to_name, title_info = self.ctx.read_today_titles(
                current_platform_ids, quiet=quiet
            )

            if not all_results:
                logger.info("没有找到当天的数据")
                return None

            total_titles = sum(len(titles) for titles in all_results.values())
            if not quiet:
                logger.info("读取标题完成", total=total_titles)

            new_titles = self.ctx.detect_new_titles(current_platform_ids, quiet=quiet)
            word_groups, filter_words, global_filters = self.ctx.load_frequency_words()

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

    def _prepare_current_title_info(self, results: Dict, time_info: str) -> Dict:
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

    def _prepare_standalone_data(
        self,
        results: Dict,
        id_to_name: Dict,
        title_info: Optional[Dict] = None,
        rss_items: Optional[List[Dict]] = None,
    ) -> Optional[Dict]:
        """从原始数据中提取独立展示区数据"""
        return prepare_standalone_data(self.ctx, results, id_to_name, title_info, rss_items)

    def _run_analysis_pipeline(
        self,
        data_source: Dict,
        mode: str,
        title_info: Dict,
        new_titles: Dict,
        word_groups: List[Dict],
        filter_words: List[str],
        id_to_name: Dict,
        failed_ids: Optional[List] = None,
        global_filters: Optional[List[str]] = None,
        quiet: bool = False,
        rss_items: Optional[List[Dict]] = None,
        rss_new_items: Optional[List[Dict]] = None,
        standalone_data: Optional[Dict] = None,
    ) -> Tuple[List[Dict], Optional[str], Optional[AIAnalysisResult]]:
        """统一的分析流水线：数据处理 -> 统计计算 -> AI分析 -> HTML生成"""
        return run_analysis_pipeline(
            ctx=self.ctx,
            data_source=data_source,
            mode=mode,
            title_info=title_info,
            new_titles=new_titles,
            word_groups=word_groups,
            filter_words=filter_words,
            id_to_name=id_to_name,
            report_mode=self.report_mode,
            update_info=self.update_info,
            run_ai_analysis_fn=self._run_ai_analysis,
            get_mode_strategy_fn=self._get_mode_strategy,
            failed_ids=failed_ids,
            global_filters=global_filters,
            quiet=quiet,
            rss_items=rss_items,
            rss_new_items=rss_new_items,
            standalone_data=standalone_data,
        )

    def _send_notification_if_needed(
        self,
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
        """统一的通知发送逻辑，包含所有判断条件"""
        return send_notification_if_needed(
            ctx=self.ctx,
            report_mode=self.report_mode,
            update_info=self.update_info,
            proxy_url=self.proxy_url,
            get_mode_strategy_fn=self._get_mode_strategy,
            run_ai_analysis_fn=self._run_ai_analysis,
            stats=stats,
            report_type=report_type,
            mode=mode,
            failed_ids=failed_ids,
            new_titles=new_titles,
            id_to_name=id_to_name,
            html_file_path=html_file_path,
            rss_items=rss_items,
            rss_new_items=rss_new_items,
            standalone_data=standalone_data,
            ai_result=ai_result,
            current_results=current_results,
        )

    def _initialize_and_check_config(self) -> None:
        """通用初始化和配置检查"""
        now = self.ctx.get_time()
        logger.info("当前北京时间", time=now.strftime('%Y-%m-%d %H:%M:%S'))

        if not self.ctx.config["ENABLE_CRAWLER"]:
            logger.info("爬虫功能已禁用，程序退出", config="ENABLE_CRAWLER=False")
            return

        has_notification = self._has_notification_configured()
        if not self.ctx.config["ENABLE_NOTIFICATION"]:
            logger.info("通知功能已禁用，将只进行数据抓取", config="ENABLE_NOTIFICATION=False")
        elif not has_notification:
            logger.info("未配置任何通知渠道，将只进行数据抓取，不发送通知")
        else:
            logger.info("通知功能已启用，将发送通知")

        mode_strategy = self._get_mode_strategy()
        logger.info("运行模式", report_mode=self.report_mode, description=mode_strategy['description'])

    def _crawl_data(self) -> Tuple[Dict, Dict, List]:
        """执行数据爬取"""
        ids = []
        for platform in self.ctx.platforms:
            if "name" in platform:
                ids.append((platform["id"], platform["name"]))
            else:
                ids.append(platform["id"])

        logger.info("配置的监控平台", platforms=[p.get('name', p['id']) for p in self.ctx.platforms])
        logger.info("开始爬取数据", interval_ms=self.request_interval)
        Path("output").mkdir(parents=True, exist_ok=True)

        results, id_to_name, failed_ids = self.data_fetcher.crawl_websites(
            ids, self.request_interval
        )

        # 转换为 NewsData 格式并保存到存储后端
        crawl_time = self.ctx.format_time()
        crawl_date = self.ctx.format_date()
        news_data = convert_crawl_results_to_news_data(
            results, id_to_name, failed_ids, crawl_time, crawl_date
        )

        # 保存到存储后端（SQLite）
        if self.storage_manager.save_news_data(news_data):
            logger.info("数据已保存到存储后端", backend=self.storage_manager.backend_name)

        # 保存 TXT 快照（如果启用）
        txt_file = self.storage_manager.save_txt_snapshot(news_data)
        if txt_file:
            logger.info("TXT 快照已保存", file=str(txt_file))

        # 兼容：同时保存到原有 TXT 格式（确保向后兼容）
        if self.ctx.config["STORAGE"]["FORMATS"]["TXT"]:
            title_file = self.ctx.save_titles(results, id_to_name, failed_ids)
            logger.info("标题已保存", file=str(title_file))

        return results, id_to_name, failed_ids

    def _crawl_rss_data(self) -> Tuple[Optional[List[Dict]], Optional[List[Dict]], Optional[List[Dict]]]:
        """執行 RSS 数据抓取"""
        return crawl_rss_data(
            ctx=self.ctx,
            storage_manager=self.storage_manager,
            proxy_url=self.proxy_url,
            process_rss_data_by_mode_fn=self._process_rss_data_by_mode,
        )

    def _crawl_extra_apis(self) -> Tuple[Dict, Dict, List]:
        """
        执行额外 API 数据源抓取（并发模式）

        Returns:
            (结果字典, ID到名称映射, 失败ID列表) 三元组
        """
        extra_apis_config = self.ctx.config.get("EXTRA_APIS", {})
        if not extra_apis_config.get("enabled", False):
            return {}, {}, []

        sources = extra_apis_config.get("sources", [])
        if not sources:
            logger.info("未配置额外 API 数据源")
            return {}, {}, []

        enabled_count = sum(1 for s in sources if s.get("enabled", True))
        if enabled_count == 0:
            logger.info("所有额外 API 数据源均已禁用")
            return {}, {}, []

        # Build id_to_name mapping from config so callers can display friendly names
        source_names: Dict = {}
        for s in sources:
            if s.get("enabled", True):
                sid = s.get("id", "")
                source_names[sid] = s.get("name", sid)

        logger.info("开始抓取额外 API 数据源", total=len(sources), enabled=enabled_count)

        from trendradar.crawler.extra_apis import crawl_extra_sources_concurrent
        results, failed = crawl_extra_sources_concurrent(extra_apis_config)

        logger.info("额外 API 抓取完成", succeeded=len(results), failed=len(failed))
        if failed:
            logger.warning("失败的额外数据源", sources=failed)

        return results, source_names, failed

    def _process_rss_data_by_mode(self, rss_data) -> Tuple[Optional[List[Dict]], Optional[List[Dict]], Optional[List[Dict]]]:
        """按报告模式处理 RSS 数据，返回与热榜相同格式的统计结构"""
        return process_rss_data_by_mode(
            ctx=self.ctx,
            storage_manager=self.storage_manager,
            report_mode=self.report_mode,
            rank_threshold=self.rank_threshold,
            rss_data=rss_data,
        )

    def _convert_rss_items_to_list(self, items_dict: Dict, id_to_name: Dict) -> List[Dict]:
        """将 RSS 条目字典转换为列表格式，并应用新鲜度过滤（用于推送）"""
        return convert_rss_items_to_list(self.ctx, items_dict, id_to_name)

    def _filter_rss_by_keywords(self, rss_items: List[Dict]) -> List[Dict]:
        """使用 frequency_words.txt 过滤 RSS 条目"""
        try:
            word_groups, filter_words, global_filters = self.ctx.load_frequency_words()
            if word_groups or filter_words or global_filters:
                from trendradar.core.frequency import matches_word_groups
                filtered_items = []
                for item in rss_items:
                    title = item.get("title", "")
                    if matches_word_groups(title, word_groups, filter_words, global_filters):
                        filtered_items.append(item)

                original_count = len(rss_items)
                rss_items = filtered_items
                logger.info("RSS 关键词过滤", remaining=len(rss_items), total=original_count)

                if not rss_items:
                    logger.info("RSS 关键词过滤后没有匹配内容")
                    return []
        except FileNotFoundError:
            # frequency_words.txt 不存在时跳过过滤
            pass
        return rss_items

    def _generate_rss_html_report(self, rss_items: list, feeds_info: dict) -> str:
        """生成 RSS HTML 报告"""
        try:
            from trendradar.report.rss_html import render_rss_html_content
            from pathlib import Path

            html_content = render_rss_html_content(
                rss_items=rss_items,
                total_count=len(rss_items),
                feeds_info=feeds_info,
                get_time_func=self.ctx.get_time,
            )

            # 保存 HTML 文件（扁平化结构：output/html/日期/）
            date_folder = self.ctx.format_date()
            time_filename = self.ctx.format_time()
            output_dir = Path("output") / "html" / date_folder
            output_dir.mkdir(parents=True, exist_ok=True)

            file_path = output_dir / f"rss_{time_filename}.html"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.info("RSS HTML 报告已生成", file=str(file_path))
            return str(file_path)

        except Exception as e:
            logger.error("RSS 生成 HTML 报告失败", error=str(e))
            return None

    def _execute_mode_strategy(
        self, mode_strategy: Dict, results: Dict, id_to_name: Dict, failed_ids: List,
        rss_items: Optional[List[Dict]] = None,
        rss_new_items: Optional[List[Dict]] = None,
        raw_rss_items: Optional[List[Dict]] = None,
    ) -> Optional[str]:
        """执行模式特定逻辑，支持热榜+RSS合并推送"""
        return execute_mode_strategy(
            ctx=self.ctx,
            storage_manager=self.storage_manager,
            report_mode=self.report_mode,
            rank_threshold=self.rank_threshold,
            update_info=self.update_info,
            proxy_url=self.proxy_url,
            is_docker_container=self.is_docker_container,
            should_open_browser=self._should_open_browser(),
            mode_strategy=mode_strategy,
            results=results,
            id_to_name=id_to_name,
            failed_ids=failed_ids,
            load_analysis_data_fn=self._load_analysis_data,
            prepare_current_title_info_fn=self._prepare_current_title_info,
            run_analysis_pipeline_fn=self._run_analysis_pipeline,
            prepare_standalone_data_fn=self._prepare_standalone_data,
            send_notification_fn=self._send_notification_if_needed,
            rss_items=rss_items,
            rss_new_items=rss_new_items,
            raw_rss_items=raw_rss_items,
        )

    def _analyze_trends(self, results: Dict, id_to_name: Dict) -> Optional[TrendReport]:
        """Compare current crawl results with previous period for trend detection."""
        try:
            previous_data = self.storage_manager.get_previous_crawl_data()
            if previous_data is None:
                logger.info("无历史数据，跳过趋势分析")
                return None

            # Convert NewsData back to the results dict format that TrendAnalyzer expects
            previous_results, prev_id_to_name, _ = convert_news_data_to_results(previous_data)

            # Merge id_to_name maps so platform names are available for both periods
            merged_names = {**prev_id_to_name, **id_to_name}

            analyzer = TrendAnalyzer()
            report = analyzer.compare_periods(
                current_results=results,
                previous_results=previous_results,
                id_to_name=merged_names,
                current_period_label=self.ctx.format_time(),
                previous_period_label=previous_data.crawl_time,
            )

            logger.info(
                "趋势分析完成",
                new=len(report.new_trends),
                rising=len(report.rising_trends),
                falling=len(report.falling_trends),
                cross_platform=len(report.cross_platform),
            )
            return report
        except Exception as e:
            logger.warning("趋势分析失败", error=str(e))
            return None

    def run(self) -> None:
        """执行分析流程"""
        try:
            self._initialize_and_check_config()

            mode_strategy = self._get_mode_strategy()

            # 抓取热榜数据
            results, id_to_name, failed_ids = self._crawl_data()

            # 抓取 RSS 数据（如果启用），返回统计条目、新增条目和原始条目
            rss_items, rss_new_items, raw_rss_items = self._crawl_rss_data()

            # 抓取额外 API 数据源（如果启用），并发模式
            extra_results, extra_names, extra_failed = self._crawl_extra_apis()
            if extra_results:
                for source_id, items in extra_results.items():
                    results[source_id] = {}
                    for i, item in enumerate(items, 1):
                        title = item.get("title", "").strip()
                        if not title:
                            continue
                        rank = item.get("rank", i)
                        if title in results[source_id]:
                            results[source_id][title]["ranks"].append(rank)
                        else:
                            results[source_id][title] = {
                                "ranks": [rank],
                                "url": item.get("url", ""),
                                "mobileUrl": item.get("mobile_url", ""),
                            }
                id_to_name.update(extra_names)
                failed_ids.extend(extra_failed)

            # 趋势分析（对比当前抓取与上次抓取）
            trend_report = self._analyze_trends(results, id_to_name)

            # 执行模式策略，传递 RSS 数据用于合并推送
            self._execute_mode_strategy(
                mode_strategy, results, id_to_name, failed_ids,
                rss_items=rss_items, rss_new_items=rss_new_items,
                raw_rss_items=raw_rss_items
            )

        except Exception as e:
            logger.error("分析流程执行出错", error=str(e))
            if self.ctx.config.get("DEBUG", False):
                raise
        finally:
            # 清理资源（包括过期数据清理和数据库连接关闭）
            self.ctx.cleanup()


def _ensure_utf8_output():
    """确保 Windows 终端使用 UTF-8 编码输出，避免 emoji 等字符导致 UnicodeEncodeError"""
    import sys
    if sys.platform == "win32":
        for stream_name in ("stdout", "stderr"):
            stream = getattr(sys, stream_name, None)
            if stream and hasattr(stream, "reconfigure"):
                try:
                    stream.reconfigure(encoding="utf-8", errors="replace")
                except Exception:
                    pass


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

示例:
  python -m trendradar                    # 正常运行
  python -m trendradar --show-push-status # 查看推送状态
  python -m trendradar --reset-push-state # 重置推送状态后再运行
  python -m trendradar --force-push       # 强制推送（忽略今日已推送限制）
"""
    )
    parser.add_argument(
        "--show-push-status",
        action="store_true",
        help="显示推送状态信息"
    )
    parser.add_argument(
        "--show-ai-status",
        action="store_true",
        help="显示 AI 分析状态信息"
    )
    parser.add_argument(
        "--reset-push-state",
        action="store_true",
        help="重置今日推送状态"
    )
    parser.add_argument(
        "--reset-ai-state",
        action="store_true",
        help="重置今日 AI 分析状态"
    )
    parser.add_argument(
        "--force-push",
        action="store_true",
        help="忽略 once_per_day 限制，强制推送"
    )
    parser.add_argument(
        "--force-ai",
        action="store_true",
        help="忽略 once_per_day 限制，强制 AI 分析"
    )

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
        need_update = False
        remote_version = None
        if version_url:
            need_update, remote_version = check_all_versions(version_url, configs_version_url)

        # 复用已加载的配置，避免重复加载
        analyzer = NewsAnalyzer(config=config)

        # 设置更新信息（复用已获取的远程版本，不再重复请求）
        if analyzer.is_github_actions and need_update and remote_version:
            analyzer.update_info = {
                "current_version": __version__,
                "remote_version": remote_version,
            }

        # 获取 debug 配置
        debug_mode = analyzer.ctx.config.get("DEBUG", False)
        analyzer.run()
    except FileNotFoundError as e:
        logger.error("配置文件错误", error=str(e), hint="请确保 config/config.yaml 和 config/frequency_words.txt 存在")
    except Exception as e:
        logger.error("程序运行错误", error=str(e))
        if debug_mode:
            raise


def _handle_status_commands(config: Dict, args) -> None:
    """处理状态查看/重置命令"""
    from trendradar.context import AppContext

    ctx = AppContext(config)
    push_manager = ctx.create_push_manager()

    logger.info("TrendRadar 状态信息", version=__version__)

    # 显示推送状态
    if args.show_push_status:
        push_window_config = config.get("PUSH_WINDOW", {})
        status = push_manager.get_push_status(push_window_config)
        logger.info("推送状态", current_time=status['current_time'], timezone=status['timezone'], current_date=status['current_date'], window_enabled=status['enabled'], window_start=status.get('window_start'), window_end=status.get('window_end'), in_window=status.get('in_window'), once_per_day=status.get('once_per_day'), executed_today=status.get('executed_today', False))

    # 显示 AI 分析状态
    if args.show_ai_status:
        ai_window_config = config.get("AI_ANALYSIS", {}).get("ANALYSIS_WINDOW", {})
        status = push_manager.get_ai_analysis_status(ai_window_config)
        logger.info("AI 分析状态", current_time=status['current_time'], timezone=status['timezone'], current_date=status['current_date'], window_enabled=status['enabled'], window_start=status.get('window_start'), window_end=status.get('window_end'), in_window=status.get('in_window'), once_per_day=status.get('once_per_day'), executed_today=status.get('executed_today', False))

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
