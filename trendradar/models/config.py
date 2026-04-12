# coding=utf-8
"""
TrendRadar Pydantic 配置模型

将 config.yaml 的所有顶层节点映射为强类型 BaseModel，实现：
- 零迁移成本：字段名和默认值与 YAML 完全对齐
- 环境变量覆盖：通过 model_validator 在构造后注入
- 向后兼容：to_dict() 以原始 dict 形式暴露给现有代码
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# 辅助函数：安全读取环境变量
# ---------------------------------------------------------------------------

def _env_str(key: str) -> Optional[str]:
    """返回非空字符串环境变量值，否则返回 None。"""
    val = os.environ.get(key, "").strip()
    return val if val else None


def _env_bool(key: str) -> Optional[bool]:
    """将环境变量解析为布尔值，未设置时返回 None。"""
    val = os.environ.get(key, "").strip().lower()
    if not val:
        return None
    return val in ("true", "1", "yes")


def _env_int(key: str) -> Optional[int]:
    """将环境变量解析为整数，未设置或解析失败时返回 None。"""
    val = os.environ.get(key, "").strip()
    if not val:
        return None
    try:
        return int(val)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# advanced 节
# ---------------------------------------------------------------------------

class CrawlerConfig(BaseModel):
    """爬虫子配置：代理、API 地址和请求间隔。"""

    model_config = ConfigDict(extra="allow")

    api_url: str = Field(default="", description="爬虫 API 端点，为空时直接抓取")
    default_proxy: str = Field(
        default="http://127.0.0.1:10801",
        description="默认 HTTP 代理地址",
    )
    request_interval: int = Field(
        default=2000, description="爬虫请求间隔（毫秒）"
    )
    use_proxy: bool = Field(default=False, description="是否启用代理")

    @model_validator(mode="after")
    def _apply_env(self) -> "CrawlerConfig":
        override = _env_str("CRAWLER_API_URL")
        if override is not None:
            self.api_url = override
        return self


class BatchSizeConfig(BaseModel):
    """各渠道消息分批大小（字节）。"""

    model_config = ConfigDict(extra="allow")

    bark: int = Field(default=4000)
    default: int = Field(default=4000)
    dingtalk: int = Field(default=20000)
    feishu: int = Field(default=30000)
    slack: int = Field(default=4000)


class RssAdvancedConfig(BaseModel):
    """RSS 高级参数（请求间隔、超时、代理）。"""

    model_config = ConfigDict(extra="allow")

    proxy_url: str = Field(default="", description="RSS 专属代理，为空时复用 crawler.default_proxy")
    request_interval: int = Field(default=1000, description="RSS 请求间隔（毫秒）")
    timeout: int = Field(default=15, description="RSS 请求超时（秒）")
    use_proxy: bool = Field(default=False, description="是否为 RSS 启用代理")


class WeightConfig(BaseModel):
    """热度评分权重，三项之和应为 1.0。"""

    model_config = ConfigDict(extra="allow")

    frequency: float = Field(default=0.3, description="词频权重")
    hotness: float = Field(default=0.1, description="平台热度权重")
    rank: float = Field(default=0.6, description="排名权重")


class AdvancedConfig(BaseModel):
    """高级配置节：批量发送、爬虫、RSS、权重等底层参数。"""

    model_config = ConfigDict(extra="allow")

    batch_send_interval: float = Field(
        default=3, description="批次间发送间隔（秒）"
    )
    batch_size: BatchSizeConfig = Field(default_factory=BatchSizeConfig)
    configs_version_check_url: str = Field(
        default="https://raw.githubusercontent.com/sansan0/TrendRadar/refs/heads/master/version_configs",
        description="配置版本检查 URL",
    )
    crawler: CrawlerConfig = Field(default_factory=CrawlerConfig)
    debug: bool = Field(default=False, description="调试模式开关")
    feishu_message_separator: str = Field(
        default="━━━━━━━━━━━━━━━━━━━",
        description="飞书消息分隔符",
    )
    max_accounts_per_channel: int = Field(
        default=3, description="每个渠道允许的最大账号数"
    )
    mcp_version_check_url: str = Field(
        default="https://raw.githubusercontent.com/sansan0/TrendRadar/refs/heads/master/version_mcp",
        description="MCP 版本检查 URL",
    )
    rss: RssAdvancedConfig = Field(default_factory=RssAdvancedConfig)
    version_check_url: str = Field(
        default="https://raw.githubusercontent.com/sansan0/TrendRadar/refs/heads/master/version",
        description="应用版本检查 URL",
    )
    weight: WeightConfig = Field(default_factory=WeightConfig)

    @model_validator(mode="after")
    def _apply_env(self) -> "AdvancedConfig":
        debug_env = _env_bool("DEBUG")
        if debug_env is not None:
            self.debug = debug_env
        max_acc_env = _env_int("MAX_ACCOUNTS_PER_CHANNEL")
        if max_acc_env is not None:
            self.max_accounts_per_channel = max_acc_env
        return self


# ---------------------------------------------------------------------------
# ai 节
# ---------------------------------------------------------------------------

class AiConfig(BaseModel):
    """AI 模型配置（LiteLLM 格式）。"""

    model_config = ConfigDict(extra="allow")

    model: str = Field(
        default="openai/gemini-3-pro-preview",
        description="LiteLLM 模型标识符，格式：provider/model-name",
    )
    api_key: str = Field(
        default="",
        description="AI 服务 API Key",
        json_schema_extra={"sensitive": True},
    )
    api_base: str = Field(default="", description="自定义 API Base URL")
    timeout: int = Field(default=120, description="请求超时（秒）")
    temperature: float = Field(default=1.0, description="生成温度")
    max_tokens: int = Field(default=5000, description="单次最大 token 数")
    num_retries: int = Field(default=1, description="失败重试次数")
    fallback_models: List[str] = Field(
        default_factory=list, description="备用模型列表"
    )

    @model_validator(mode="after")
    def _apply_env(self) -> "AiConfig":
        for attr, env_key in (
            ("model", "AI_MODEL"),
            ("api_key", "AI_API_KEY"),
            ("api_base", "AI_API_BASE"),
        ):
            override = _env_str(env_key)
            if override is not None:
                setattr(self, attr, override)
        timeout_env = _env_int("AI_TIMEOUT")
        if timeout_env is not None:
            self.timeout = timeout_env
        return self


# ---------------------------------------------------------------------------
# ai_analysis 节
# ---------------------------------------------------------------------------

class AnalysisWindowConfig(BaseModel):
    """AI 分析的可用时间窗口配置。"""

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=False, description="是否启用时间窗口限制")
    start: str = Field(default="09:00", description="窗口开始时间（HH:MM）")
    end: str = Field(default="22:00", description="窗口结束时间（HH:MM）")
    once_per_day: bool = Field(default=False, description="每天只触发一次")

    @model_validator(mode="after")
    def _apply_env(self) -> "AnalysisWindowConfig":
        enabled_env = _env_bool("AI_ANALYSIS_WINDOW_ENABLED")
        if enabled_env is not None:
            self.enabled = enabled_env
        start_env = _env_str("AI_ANALYSIS_WINDOW_START")
        if start_env is not None:
            self.start = start_env
        end_env = _env_str("AI_ANALYSIS_WINDOW_END")
        if end_env is not None:
            self.end = end_env
        once_env = _env_bool("AI_ANALYSIS_WINDOW_ONCE_PER_DAY")
        if once_env is not None:
            self.once_per_day = once_env
        return self


class AiAnalysisConfig(BaseModel):
    """AI 分析功能配置（运行模式、语言、触发条件等）。"""

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=True, description="是否启用 AI 分析")
    language: str = Field(default="Chinese", description="分析输出语言")
    mode: Literal["follow_report", "daily", "incremental", "current"] = Field(
        default="follow_report",
        description="分析触发模式",
    )
    max_news_for_analysis: int = Field(
        default=60, description="每次分析最多处理的新闻条数"
    )
    include_rss: bool = Field(
        default=False, description="是否将 RSS 条目纳入分析"
    )
    include_rank_timeline: bool = Field(
        default=True, description="是否在分析中包含排名时间线"
    )
    prompt_file: str = Field(
        default="ai_analysis_prompt.txt", description="分析 Prompt 文件名"
    )
    analysis_window: AnalysisWindowConfig = Field(
        default_factory=AnalysisWindowConfig
    )

    @model_validator(mode="after")
    def _apply_env(self) -> "AiAnalysisConfig":
        enabled_env = _env_bool("AI_ANALYSIS_ENABLED")
        if enabled_env is not None:
            self.enabled = enabled_env
        return self


# ---------------------------------------------------------------------------
# ai_translation 节
# ---------------------------------------------------------------------------

class AiTranslationConfig(BaseModel):
    """AI 翻译功能配置。"""

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=True, description="是否启用 AI 翻译")
    language: str = Field(default="Chinese", description="翻译目标语言")
    prompt_file: str = Field(
        default="ai_translation_prompt.txt", description="翻译 Prompt 文件名"
    )

    @model_validator(mode="after")
    def _apply_env(self) -> "AiTranslationConfig":
        enabled_env = _env_bool("AI_TRANSLATION_ENABLED")
        if enabled_env is not None:
            self.enabled = enabled_env
        lang_env = _env_str("AI_TRANSLATION_LANGUAGE")
        if lang_env is not None:
            self.language = lang_env
        return self


# ---------------------------------------------------------------------------
# app 节
# ---------------------------------------------------------------------------

class AppConfig(BaseModel):
    """应用级别配置：时区、版本更新提示等。"""

    model_config = ConfigDict(extra="allow")

    show_version_update: bool = Field(
        default=True, description="是否显示版本更新通知"
    )
    timezone: str = Field(default="Asia/Shanghai", description="运行时时区")

    @model_validator(mode="after")
    def _apply_env(self) -> "AppConfig":
        tz_env = _env_str("TIMEZONE")
        if tz_env is not None:
            self.timezone = tz_env
        return self


# ---------------------------------------------------------------------------
# display 节
# ---------------------------------------------------------------------------

RegionName = Literal["new_items", "hotlist", "rss", "standalone", "ai_analysis"]


class RegionsConfig(BaseModel):
    """各显示区域的开关。"""

    model_config = ConfigDict(extra="allow")

    ai_analysis: bool = Field(default=True)
    hotlist: bool = Field(default=True)
    new_items: bool = Field(default=True)
    rss: bool = Field(default=True)
    standalone: bool = Field(default=False)


class StandaloneConfig(BaseModel):
    """独立展示区配置：独显的平台和 RSS 源。"""

    model_config = ConfigDict(extra="allow")

    max_items: int = Field(default=20, description="独立区最多展示条目数")
    platforms: List[str] = Field(
        default_factory=list, description="独立展示的平台 ID 列表"
    )
    rss_feeds: List[str] = Field(
        default_factory=list, description="独立展示的 RSS Feed ID 列表"
    )


class DisplayConfig(BaseModel):
    """推送内容布局配置：区域顺序与开关。"""

    model_config = ConfigDict(extra="allow")

    region_order: List[RegionName] = Field(
        default_factory=lambda: ["new_items", "hotlist", "rss", "standalone", "ai_analysis"],
        description="区域展示顺序",
    )
    regions: RegionsConfig = Field(default_factory=RegionsConfig)
    standalone: StandaloneConfig = Field(default_factory=StandaloneConfig)


# ---------------------------------------------------------------------------
# extra_apis 节
# ---------------------------------------------------------------------------

class ExtraApiSource(BaseModel):
    """单个额外 API 数据源条目。字段因 type 不同而有差异，用 extra=allow 兼容。"""

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="数据源唯一标识符")
    name: str = Field(description="数据源显示名称")
    type: str = Field(description="数据源类型，如 vvhan/dailyhot/newsapi 等")
    enabled: bool = Field(default=True, description="是否启用该数据源")


class ExtraApisConfig(BaseModel):
    """额外 API 数据源汇总配置。"""

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=True, description="是否启用额外 API 数据源")
    sources: List[ExtraApiSource] = Field(
        default_factory=list, description="数据源配置列表"
    )


# ---------------------------------------------------------------------------
# notification 节
# ---------------------------------------------------------------------------

class TelegramChannelConfig(BaseModel):
    """Telegram 推送渠道配置。"""

    model_config = ConfigDict(extra="allow")

    bot_token: str = Field(
        default="",
        description="Telegram Bot Token",
        json_schema_extra={"sensitive": True},
    )
    chat_id: str = Field(default="", description="目标会话 ID")


class WeworkChannelConfig(BaseModel):
    """企业微信推送渠道配置。"""

    model_config = ConfigDict(extra="allow")

    webhook_url: str = Field(
        default="",
        description="企业微信 Webhook URL",
        json_schema_extra={"sensitive": True},
    )
    msg_type: str = Field(default="markdown", description="消息格式类型")


class DingtalkChannelConfig(BaseModel):
    """钉钉推送渠道配置。"""

    model_config = ConfigDict(extra="allow")

    webhook_url: str = Field(
        default="",
        description="钉钉 Webhook URL",
        json_schema_extra={"sensitive": True},
    )


class FeishuChannelConfig(BaseModel):
    """飞书推送渠道配置。"""

    model_config = ConfigDict(extra="allow")

    webhook_url: str = Field(
        default="",
        description="飞书 Webhook URL",
        json_schema_extra={"sensitive": True},
    )


class SlackChannelConfig(BaseModel):
    """Slack 推送渠道配置。"""

    model_config = ConfigDict(extra="allow")

    webhook_url: str = Field(
        default="",
        description="Slack Webhook URL",
        json_schema_extra={"sensitive": True},
    )


class EmailChannelConfig(BaseModel):
    """电子邮件推送渠道配置。"""

    model_config = ConfigDict(extra="allow")

    smtp_server: str = Field(default="", description="SMTP 服务器地址")
    smtp_port: str = Field(default="", description="SMTP 端口号")
    from_: str = Field(
        default="",
        alias="from",
        description="发件人地址",
        json_schema_extra={"sensitive": True},
    )
    password: str = Field(
        default="",
        description="发件人密码",
        json_schema_extra={"sensitive": True},
    )
    to: str = Field(default="", description="收件人地址")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class BarkChannelConfig(BaseModel):
    """Bark 推送渠道配置。"""

    model_config = ConfigDict(extra="allow")

    url: str = Field(
        default="",
        description="Bark 推送 URL（含 Device Key）",
        json_schema_extra={"sensitive": True},
    )


class NtfyChannelConfig(BaseModel):
    """ntfy 推送渠道配置。"""

    model_config = ConfigDict(extra="allow")

    server_url: str = Field(default="https://ntfy.sh", description="ntfy 服务器地址")
    topic: str = Field(default="", description="ntfy 话题名")
    token: str = Field(
        default="",
        description="ntfy 认证 Token",
        json_schema_extra={"sensitive": True},
    )


class GenericWebhookChannelConfig(BaseModel):
    """通用 Webhook 推送渠道配置。"""

    model_config = ConfigDict(extra="allow")

    webhook_url: str = Field(
        default="",
        description="通用 Webhook URL",
        json_schema_extra={"sensitive": True},
    )
    payload_template: str = Field(
        default="", description="Webhook 请求体模板（JSON 字符串）"
    )


class NotificationChannelsConfig(BaseModel):
    """所有通知渠道的配置集合。"""

    model_config = ConfigDict(extra="allow")

    telegram: TelegramChannelConfig = Field(default_factory=TelegramChannelConfig)
    wework: WeworkChannelConfig = Field(default_factory=WeworkChannelConfig)
    dingtalk: DingtalkChannelConfig = Field(default_factory=DingtalkChannelConfig)
    feishu: FeishuChannelConfig = Field(default_factory=FeishuChannelConfig)
    slack: SlackChannelConfig = Field(default_factory=SlackChannelConfig)
    email: EmailChannelConfig = Field(default_factory=EmailChannelConfig)
    bark: BarkChannelConfig = Field(default_factory=BarkChannelConfig)
    ntfy: NtfyChannelConfig = Field(default_factory=NtfyChannelConfig)
    generic_webhook: GenericWebhookChannelConfig = Field(
        default_factory=GenericWebhookChannelConfig
    )


class PushWindowConfig(BaseModel):
    """推送时间窗口限制配置。"""

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=False, description="是否启用推送时间窗口")
    start: str = Field(default="20:00", description="窗口开始时间（HH:MM）")
    end: str = Field(default="22:00", description="窗口结束时间（HH:MM）")
    once_per_day: bool = Field(default=True, description="每天只推送一次")

    @model_validator(mode="after")
    def _apply_env(self) -> "PushWindowConfig":
        enabled_env = _env_bool("PUSH_WINDOW_ENABLED")
        if enabled_env is not None:
            self.enabled = enabled_env
        start_env = _env_str("PUSH_WINDOW_START")
        if start_env is not None:
            self.start = start_env
        end_env = _env_str("PUSH_WINDOW_END")
        if end_env is not None:
            self.end = end_env
        once_env = _env_bool("PUSH_WINDOW_ONCE_PER_DAY")
        if once_env is not None:
            self.once_per_day = once_env
        return self


class NotificationConfig(BaseModel):
    """通知总配置：渠道列表和推送窗口。"""

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=True, description="是否启用通知推送")
    channels: NotificationChannelsConfig = Field(
        default_factory=NotificationChannelsConfig
    )
    push_window: PushWindowConfig = Field(default_factory=PushWindowConfig)


# ---------------------------------------------------------------------------
# platforms 节
# ---------------------------------------------------------------------------

class PlatformSource(BaseModel):
    """单个平台数据源条目。"""

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="平台唯一标识符")
    name: str = Field(description="平台显示名称")


class PlatformsConfig(BaseModel):
    """平台爬取配置。"""

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=True, description="是否启用平台数据源")
    sources: List[PlatformSource] = Field(
        default_factory=list, description="已配置的平台列表"
    )


# ---------------------------------------------------------------------------
# report 节
# ---------------------------------------------------------------------------

class ReportConfig(BaseModel):
    """报告生成配置：模式、阈值和展示限制。"""

    model_config = ConfigDict(extra="allow")

    display_mode: Literal["keyword", "platform"] = Field(
        default="keyword", description="报告展示模式"
    )
    max_keywords: int = Field(
        default=0, description="报告最多展示关键词数（0 表示不限）"
    )
    max_news_per_keyword: int = Field(
        default=0, description="每个关键词最多展示新闻条数（0 表示不限）"
    )
    mode: Literal["current", "daily", "incremental"] = Field(
        default="current", description="报告数据范围模式"
    )
    rank_threshold: int = Field(
        default=5, description="进入报告的排名阈值（≤ 该值才纳入）"
    )
    sort_by_position_first: bool = Field(
        default=False, description="是否优先按平台位置排序"
    )

    @model_validator(mode="after")
    def _apply_env(self) -> "ReportConfig":
        sort_env = _env_bool("SORT_BY_POSITION_FIRST")
        if sort_env is not None:
            self.sort_by_position_first = sort_env
        max_news_env = _env_int("MAX_NEWS_PER_KEYWORD")
        if max_news_env is not None:
            self.max_news_per_keyword = max_news_env
        max_kw_env = _env_int("MAX_KEYWORDS")
        if max_kw_env is not None:
            self.max_keywords = max_kw_env
        return self


# ---------------------------------------------------------------------------
# rss 节
# ---------------------------------------------------------------------------

class RssFeedEntry(BaseModel):
    """单个 RSS Feed 条目。"""

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Feed 唯一标识符")
    name: str = Field(description="Feed 显示名称")
    url: str = Field(description="Feed 订阅地址")
    enabled: bool = Field(default=True, description="是否启用该 Feed")


class FreshnessFilterConfig(BaseModel):
    """RSS 条目新鲜度过滤配置。"""

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=True, description="是否启用新鲜度过滤")
    max_age_days: int = Field(
        default=3, description="超过该天数的条目将被过滤（0 表示不限）"
    )


class RssConfig(BaseModel):
    """RSS 数据源总配置。"""

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=True, description="是否启用 RSS 数据源")
    feeds: List[RssFeedEntry] = Field(
        default_factory=list, description="已配置的 RSS Feed 列表"
    )
    freshness_filter: FreshnessFilterConfig = Field(
        default_factory=FreshnessFilterConfig
    )


# ---------------------------------------------------------------------------
# storage 节
# ---------------------------------------------------------------------------

class StorageFormatsConfig(BaseModel):
    """存储文件格式开关。"""

    model_config = ConfigDict(extra="allow")

    html: bool = Field(default=True, description="是否生成 HTML 报告")
    sqlite: bool = Field(default=True, description="是否写入 SQLite 数据库")
    txt: bool = Field(default=False, description="是否生成纯文本报告")

    @model_validator(mode="after")
    def _apply_env(self) -> "StorageFormatsConfig":
        html_env = _env_bool("STORAGE_HTML_ENABLED")
        if html_env is not None:
            self.html = html_env
        txt_env = _env_bool("STORAGE_TXT_ENABLED")
        if txt_env is not None:
            self.txt = txt_env
        return self


class LocalStorageConfig(BaseModel):
    """本地存储参数。"""

    model_config = ConfigDict(extra="allow")

    data_dir: str = Field(default="output", description="本地数据目录")
    retention_days: int = Field(
        default=0, description="本地数据保留天数（0 表示永久保留）"
    )

    @model_validator(mode="after")
    def _apply_env(self) -> "LocalStorageConfig":
        ret_env = _env_int("LOCAL_RETENTION_DAYS")
        if ret_env is not None:
            self.retention_days = ret_env
        return self


class RemoteStorageConfig(BaseModel):
    """S3 兼容远端存储参数。"""

    model_config = ConfigDict(extra="allow")

    access_key_id: str = Field(
        default="",
        description="S3 Access Key ID",
        json_schema_extra={"sensitive": True},
    )
    bucket_name: str = Field(default="", description="S3 存储桶名称")
    endpoint_url: str = Field(default="", description="S3 兼容端点 URL")
    region: str = Field(default="", description="S3 区域")
    retention_days: int = Field(
        default=0, description="远端数据保留天数（0 表示永久保留）"
    )
    secret_access_key: str = Field(
        default="",
        description="S3 Secret Access Key",
        json_schema_extra={"sensitive": True},
    )

    @model_validator(mode="after")
    def _apply_env(self) -> "RemoteStorageConfig":
        mapping = {
            "endpoint_url": "S3_ENDPOINT_URL",
            "bucket_name": "S3_BUCKET_NAME",
            "access_key_id": "S3_ACCESS_KEY_ID",
            "secret_access_key": "S3_SECRET_ACCESS_KEY",
            "region": "S3_REGION",
        }
        for attr, env_key in mapping.items():
            val = _env_str(env_key)
            if val is not None:
                setattr(self, attr, val)
        ret_env = _env_int("REMOTE_RETENTION_DAYS")
        if ret_env is not None:
            self.retention_days = ret_env
        return self


class PullConfig(BaseModel):
    """远端数据拉取配置。"""

    model_config = ConfigDict(extra="allow")

    days: int = Field(default=7, description="拉取最近几天的数据")
    enabled: bool = Field(default=False, description="是否启用远端数据拉取")

    @model_validator(mode="after")
    def _apply_env(self) -> "PullConfig":
        enabled_env = _env_bool("PULL_ENABLED")
        if enabled_env is not None:
            self.enabled = enabled_env
        days_env = _env_int("PULL_DAYS")
        if days_env is not None:
            self.days = days_env
        return self


class StorageConfig(BaseModel):
    """存储总配置：后端选择、格式、本地/远端参数。"""

    model_config = ConfigDict(extra="allow")

    backend: Literal["auto", "local", "remote"] = Field(
        default="auto",
        description="存储后端选择：auto 根据远端配置自动判断",
    )
    formats: StorageFormatsConfig = Field(default_factory=StorageFormatsConfig)
    local: LocalStorageConfig = Field(default_factory=LocalStorageConfig)
    pull: PullConfig = Field(default_factory=PullConfig)
    remote: RemoteStorageConfig = Field(default_factory=RemoteStorageConfig)

    @model_validator(mode="after")
    def _apply_env(self) -> "StorageConfig":
        backend_env = _env_str("STORAGE_BACKEND")
        if backend_env is not None:
            self.backend = backend_env  # type: ignore[assignment]
        return self


# ---------------------------------------------------------------------------
# 根配置模型
# ---------------------------------------------------------------------------

class TrendRadarConfig(BaseModel):
    """
    TrendRadar 全局配置根模型。

    映射 config.yaml 所有顶层节点，字段默认值与 YAML 完全一致，
    支持通过环境变量覆盖关键参数。
    """

    model_config = ConfigDict(extra="allow")

    advanced: AdvancedConfig = Field(default_factory=AdvancedConfig)
    ai: AiConfig = Field(default_factory=AiConfig)
    ai_analysis: AiAnalysisConfig = Field(default_factory=AiAnalysisConfig)
    ai_translation: AiTranslationConfig = Field(default_factory=AiTranslationConfig)
    app: AppConfig = Field(default_factory=AppConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    extra_apis: ExtraApisConfig = Field(default_factory=ExtraApisConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
    platforms: PlatformsConfig = Field(default_factory=PlatformsConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    rss: RssConfig = Field(default_factory=RssConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    # ------------------------------------------------------------------
    # 工厂方法
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: "str | Path") -> "TrendRadarConfig":
        """
        从 YAML 文件加载配置并验证。

        Args:
            path: config.yaml 文件路径

        Returns:
            经过验证的 TrendRadarConfig 实例

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: YAML 格式错误或字段验证失败
        """
        import yaml  # 仅在调用时导入，避免模块级强依赖

        path = Path(path) if not isinstance(path, Path) else path
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在：{path}")

        with path.open("r", encoding="utf-8") as fh:
            raw: Dict[str, Any] = yaml.safe_load(fh) or {}

        return cls.model_validate(raw)

    # ------------------------------------------------------------------
    # 向后兼容
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        将配置序列化为普通 dict，供现有依赖 dict 接口的代码使用。

        Returns:
            嵌套字典，键与 YAML 原始结构对齐
        """
        return self.model_dump(by_alias=True)
