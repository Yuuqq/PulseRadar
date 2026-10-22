"""
TrendRadarConfig.to_legacy_dict 与 loader.load_config 之间的契约测试

目的：把 Pydantic 模型作为配置 schema 的唯一权威来源（task 5）。
本测试在一个完整 YAML 上执行两条加载路径，并断言它们产生 *键集合相同* 的扁平字典。
对于已知的字段默认值漂移，使用 KNOWN_DRIFT 白名单显式记录在
`.planning/codebase/CONCERNS.md`，避免静默回归。
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from trendradar.core.loader import load_config
from trendradar.models.config import TrendRadarConfig

# 完整覆盖所有顶层节点的 fixture YAML
FIXTURE_YAML = textwrap.dedent(
    """
    app:
      show_version_update: false
      timezone: "America/New_York"

    advanced:
      version_check_url: "https://example.com/v"
      configs_version_check_url: "https://example.com/cv"
      mcp_version_check_url: "https://example.com/m"
      debug: true
      batch_send_interval: 2.5
      feishu_message_separator: "==="
      max_accounts_per_channel: 5
      crawler:
        api_url: "https://crawler.example.com"
        default_proxy: "http://proxy.local:8080"
        request_interval: 500
        use_proxy: true
      rss:
        proxy_url: "http://rssproxy.local:8081"
        request_interval: 1500
        timeout: 20
        use_proxy: true
      batch_size:
        default: 5000
        dingtalk: 25000
        feishu: 35000
        bark: 4500
        slack: 4500
      weight:
        rank: 0.5
        frequency: 0.3
        hotness: 0.2

    report:
      mode: "incremental"
      display_mode: "platform"
      rank_threshold: 7
      sort_by_position_first: true
      max_news_per_keyword: 12
      max_keywords: 8

    notification:
      enabled: false
      channels:
        feishu: { webhook_url: "https://feishu.example/hook" }
        dingtalk: { webhook_url: "https://dingtalk.example/hook" }
        wework: { webhook_url: "https://wework.example/hook", msg_type: "text" }
        telegram: { bot_token: "tg_token", chat_id: "tg_chat" }
        email:
          smtp_server: "smtp.example.com"
          smtp_port: "587"
          from: "noreply@example.com"
          password: "pwd"
          to: "user@example.com"
        bark: { url: "https://bark.example/key" }
        ntfy: { server_url: "https://ntfy.example", topic: "trendradar", token: "ntfy_tok" }
        slack: { webhook_url: "https://slack.example/hook" }
        generic_webhook:
          webhook_url: "https://hook.example/x"
          payload_template: '{"text":"hi"}'
      push_window:
        enabled: true
        start: "09:00"
        end: "21:00"
        once_per_day: false

    platforms:
      enabled: true
      sources:
        - { id: "p1", name: "Platform 1" }
        - { id: "p2", name: "Platform 2" }

    rss:
      enabled: true
      feeds:
        - { id: "f1", name: "Feed 1", url: "https://feed1", enabled: true }
      freshness_filter:
        enabled: true
        max_age_days: 5

    ai:
      model: "openai/gpt-4"
      api_key: "sk-test"
      api_base: "https://api.example.com"
      timeout: 90
      temperature: 0.7
      max_tokens: 4096
      num_retries: 3
      fallback_models: ["gpt-3.5"]

    ai_analysis:
      enabled: true
      language: "English"
      mode: "incremental"
      max_news_for_analysis: 80
      include_rss: true
      include_rank_timeline: false
      analysis_window:
        enabled: true
        start: "10:00"
        end: "20:00"
        once_per_day: true

    ai_translation:
      enabled: true
      language: "Spanish"

    display:
      region_order: ["hotlist", "rss", "new_items", "standalone", "ai_analysis"]
      regions:
        hotlist: true
        rss: true
        new_items: false
        standalone: true
        ai_analysis: true
      standalone:
        platforms: ["p1"]
        rss_feeds: ["f1"]
        max_items: 15

    storage:
      backend: "local"
      formats: { sqlite: true, txt: true, html: false }
      local: { data_dir: "data", retention_days: 14 }
      remote:
        endpoint_url: "https://s3.example"
        bucket_name: "bucket"
        access_key_id: "ak"
        secret_access_key: "sk"
        region: "us-east-1"
        retention_days: 30
      pull: { enabled: true, days: 14 }

    extra_apis:
      enabled: true
      sources:
        - { id: "ex1", name: "Extra 1", type: "vvhan", enabled: true }
    """
)


# Pydantic 与 loader 之间已知的默认值/字段差异（不要静默吞掉）
# 这些差异已记录在 .planning/codebase/CONCERNS.md，由后续会话评审是否对齐。
KNOWN_DRIFT_KEYS: set[str] = set()


def _isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """清除会影响 loader 与 Pydantic 加载结果的所有相关环境变量。"""
    for key in [
        "TIMEZONE",
        "DEBUG",
        "CRAWLER_API_URL",
        "MAX_ACCOUNTS_PER_CHANNEL",
        "SORT_BY_POSITION_FIRST",
        "MAX_NEWS_PER_KEYWORD",
        "MAX_KEYWORDS",
        "PUSH_WINDOW_ENABLED",
        "PUSH_WINDOW_START",
        "PUSH_WINDOW_END",
        "PUSH_WINDOW_ONCE_PER_DAY",
        "AI_MODEL",
        "AI_API_KEY",
        "AI_API_BASE",
        "AI_TIMEOUT",
        "AI_ANALYSIS_ENABLED",
        "AI_ANALYSIS_WINDOW_ENABLED",
        "AI_ANALYSIS_WINDOW_START",
        "AI_ANALYSIS_WINDOW_END",
        "AI_ANALYSIS_WINDOW_ONCE_PER_DAY",
        "AI_TRANSLATION_ENABLED",
        "AI_TRANSLATION_LANGUAGE",
        "STORAGE_BACKEND",
        "STORAGE_HTML_ENABLED",
        "STORAGE_TXT_ENABLED",
        "LOCAL_RETENTION_DAYS",
        "REMOTE_RETENTION_DAYS",
        "PULL_ENABLED",
        "PULL_DAYS",
        "S3_ENDPOINT_URL",
        "S3_BUCKET_NAME",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
        "S3_REGION",
        "FEISHU_WEBHOOK_URL",
        "DINGTALK_WEBHOOK_URL",
        "WEWORK_WEBHOOK_URL",
        "WEWORK_MSG_TYPE",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "EMAIL_FROM",
        "EMAIL_PASSWORD",
        "EMAIL_TO",
        "EMAIL_SMTP_SERVER",
        "EMAIL_SMTP_PORT",
        "NTFY_SERVER_URL",
        "NTFY_TOPIC",
        "NTFY_TOKEN",
        "BARK_URL",
        "SLACK_WEBHOOK_URL",
        "GENERIC_WEBHOOK_URL",
        "GENERIC_WEBHOOK_TEMPLATE",
        "CONFIG_PATH",
    ]:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def fixture_yaml(tmp_path: Path) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(FIXTURE_YAML, encoding="utf-8")
    return p


def test_to_legacy_dict_top_level_keys_match_loader(
    fixture_yaml: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pydantic 与 loader 路径必须产生相同的 *顶层键集合*。"""
    _isolated_env(monkeypatch)

    legacy = load_config(str(fixture_yaml))
    pyd = TrendRadarConfig.from_yaml(fixture_yaml).to_legacy_dict()

    only_loader = set(legacy.keys()) - set(pyd.keys()) - KNOWN_DRIFT_KEYS
    only_pyd = set(pyd.keys()) - set(legacy.keys()) - KNOWN_DRIFT_KEYS

    assert not only_loader, f"loader 多出的键: {only_loader}"
    assert not only_pyd, f"Pydantic 多出的键: {only_pyd}"


@pytest.mark.parametrize(
    "key",
    [
        "VERSION_CHECK_URL",
        "TIMEZONE",
        "DEBUG",
        "REQUEST_INTERVAL",
        "USE_PROXY",
        "DEFAULT_PROXY",
        "CRAWLER_API_URL",
        "ENABLE_CRAWLER",
        "REPORT_MODE",
        "DISPLAY_MODE",
        "RANK_THRESHOLD",
        "SORT_BY_POSITION_FIRST",
        "MAX_NEWS_PER_KEYWORD",
        "MAX_KEYWORDS",
        "ENABLE_NOTIFICATION",
        "MESSAGE_BATCH_SIZE",
        "DINGTALK_BATCH_SIZE",
        "FEISHU_BATCH_SIZE",
        "BARK_BATCH_SIZE",
        "SLACK_BATCH_SIZE",
        "BATCH_SEND_INTERVAL",
        "FEISHU_MESSAGE_SEPARATOR",
        "MAX_ACCOUNTS_PER_CHANNEL",
        "FEISHU_WEBHOOK_URL",
        "TELEGRAM_BOT_TOKEN",
        "EMAIL_FROM",
        "BARK_URL",
        "SLACK_WEBHOOK_URL",
    ],
)
def test_to_legacy_dict_scalar_value_equivalence(
    fixture_yaml: Path, monkeypatch: pytest.MonkeyPatch, key: str
) -> None:
    """对显式在 fixture 中提供的字段，两条路径必须返回相同标量值。"""
    _isolated_env(monkeypatch)

    legacy = load_config(str(fixture_yaml))
    pyd = TrendRadarConfig.from_yaml(fixture_yaml).to_legacy_dict()

    assert pyd[key] == legacy[key], f"{key} 漂移: pyd={pyd[key]!r} legacy={legacy[key]!r}"


@pytest.mark.parametrize(
    "key,sub",
    [
        ("PUSH_WINDOW", "ENABLED"),
        ("PUSH_WINDOW", "ONCE_PER_DAY"),
        ("WEIGHT_CONFIG", "RANK_WEIGHT"),
        ("WEIGHT_CONFIG", "FREQUENCY_WEIGHT"),
        ("WEIGHT_CONFIG", "HOTNESS_WEIGHT"),
        ("RSS", "ENABLED"),
        ("RSS", "TIMEOUT"),
        ("RSS", "PROXY_URL"),
        ("AI", "MODEL"),
        ("AI", "API_KEY"),
        ("AI", "TIMEOUT"),
        ("AI_ANALYSIS", "ENABLED"),
        ("AI_ANALYSIS", "MODE"),
        ("AI_ANALYSIS", "MAX_NEWS_FOR_ANALYSIS"),
        ("AI_TRANSLATION", "LANGUAGE"),
        ("STORAGE", "BACKEND"),
    ],
)
def test_to_legacy_dict_nested_value_equivalence(
    fixture_yaml: Path, monkeypatch: pytest.MonkeyPatch, key: str, sub: str
) -> None:
    """嵌套节点的关键字段也必须匹配。"""
    _isolated_env(monkeypatch)

    legacy = load_config(str(fixture_yaml))
    pyd = TrendRadarConfig.from_yaml(fixture_yaml).to_legacy_dict()

    assert pyd[key][sub] == legacy[key][sub], (
        f"{key}.{sub} 漂移: pyd={pyd[key][sub]!r} legacy={legacy[key][sub]!r}"
    )


def test_to_legacy_dict_webhook_env_override(
    fixture_yaml: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Webhook 环境变量覆盖必须在 Pydantic 路径中也生效。"""
    _isolated_env(monkeypatch)
    monkeypatch.setenv("FEISHU_WEBHOOK_URL", "https://env.feishu/override")
    monkeypatch.setenv("BARK_URL", "https://env.bark/override")

    pyd = TrendRadarConfig.from_yaml(fixture_yaml).to_legacy_dict()
    assert pyd["FEISHU_WEBHOOK_URL"] == "https://env.feishu/override"
    assert pyd["BARK_URL"] == "https://env.bark/override"


def test_to_legacy_dict_platforms_and_feeds_shape(
    fixture_yaml: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PLATFORMS 与 RSS.FEEDS 必须保持 list[dict] 形态以兼容下游消费者。"""
    _isolated_env(monkeypatch)
    pyd = TrendRadarConfig.from_yaml(fixture_yaml).to_legacy_dict()

    assert isinstance(pyd["PLATFORMS"], list)
    assert pyd["PLATFORMS"][0]["id"] == "p1"
    assert pyd["PLATFORMS"][0]["name"] == "Platform 1"

    assert isinstance(pyd["RSS"]["FEEDS"], list)
    assert pyd["RSS"]["FEEDS"][0]["id"] == "f1"
    assert pyd["RSS"]["FEEDS"][0]["url"] == "https://feed1"
