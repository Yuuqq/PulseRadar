"""
通知调度器模块

提供统一的通知分发接口。
支持所有通知渠道的多账号配置，使用 `;` 分隔多个账号。

使用示例:
    dispatcher = NotificationDispatcher(config, get_time_func, split_content_func)
    results = dispatcher.dispatch_all(report_data, report_type, ...)
"""

from __future__ import annotations

import concurrent.futures
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from trendradar.core.config import (
    get_account_at_index,
    limit_accounts,
    parse_multi_account_config,
    validate_paired_configs,
)
from trendradar.logging import get_logger

from .renderer import (
    render_rss_dingtalk_content,
    render_rss_feishu_content,
    render_rss_markdown_content,
)
from .senders import (
    send_to_bark,
    send_to_dingtalk,
    send_to_email,
    send_to_feishu,
    send_to_generic_webhook,
    send_to_ntfy,
    send_to_slack,
    send_to_telegram,
    send_to_wework,
)

logger = get_logger(__name__)

if TYPE_CHECKING:
    from trendradar.ai import AIAnalysisResult, AITranslator

# ---------------------------------------------------------------------------
# Channel dispatch table for *dispatch_all*
#
# Each entry maps a simple single-URL webhook channel. Channels with paired
# configs (telegram, ntfy, generic_webhook) are handled separately.
# ---------------------------------------------------------------------------
_SIMPLE_CHANNELS = [
    {
        "name": "feishu", "display_name": "飞书",
        "config_keys": ["FEISHU_WEBHOOK_URL"], "config_key": "FEISHU_WEBHOOK_URL",
        "send_func": send_to_feishu, "url_param": "webhook_url",
        "batch_size_key": "FEISHU_BATCH_SIZE", "batch_size_default": 29000,
        "extra_config": {}, "pass_get_time": True,
    },
    {
        "name": "dingtalk", "display_name": "钉钉",
        "config_keys": ["DINGTALK_WEBHOOK_URL"], "config_key": "DINGTALK_WEBHOOK_URL",
        "send_func": send_to_dingtalk, "url_param": "webhook_url",
        "batch_size_key": "DINGTALK_BATCH_SIZE", "batch_size_default": 20000,
        "extra_config": {}, "pass_get_time": False,
    },
    {
        "name": "wework", "display_name": "企业微信",
        "config_keys": ["WEWORK_WEBHOOK_URL"], "config_key": "WEWORK_WEBHOOK_URL",
        "send_func": send_to_wework, "url_param": "webhook_url",
        "batch_size_key": "MESSAGE_BATCH_SIZE", "batch_size_default": 4000,
        "extra_config": {"msg_type": ("WEWORK_MSG_TYPE", "markdown")},
        "pass_get_time": False,
    },
    {
        "name": "bark", "display_name": "Bark",
        "config_keys": ["BARK_URL"], "config_key": "BARK_URL",
        "send_func": send_to_bark, "url_param": "bark_url",
        "batch_size_key": "BARK_BATCH_SIZE", "batch_size_default": 3600,
        "extra_config": {}, "pass_get_time": False,
    },
    {
        "name": "slack", "display_name": "Slack",
        "config_keys": ["SLACK_WEBHOOK_URL"], "config_key": "SLACK_WEBHOOK_URL",
        "send_func": send_to_slack, "url_param": "webhook_url",
        "batch_size_key": "SLACK_BATCH_SIZE", "batch_size_default": 4000,
        "extra_config": {}, "pass_get_time": False,
    },
]

# ---------------------------------------------------------------------------
# RSS payload builders (stateless functions)
# ---------------------------------------------------------------------------

def _rss_feishu_payload(batch_content: str, batch_idx: int, total: int) -> dict:
    suffix = f"({batch_idx + 1}/{total})" if total > 1 else ""
    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"\U0001f4f0 RSS \u8ba2\u9605\u66f4\u65b0 {suffix}"},
                "template": "green",
            },
            "elements": [{"tag": "markdown", "content": batch_content}],
        },
    }

def _rss_dingtalk_payload(batch_content: str, batch_idx: int, total: int) -> dict:
    suffix = f"({batch_idx + 1}/{total})" if total > 1 else ""
    return {"msgtype": "markdown", "markdown": {"title": f"\U0001f4f0 RSS \u8ba2\u9605\u66f4\u65b0 {suffix}", "text": batch_content}}

def _rss_wework_payload(batch_content: str, _idx: int, _total: int) -> dict:
    return {"msgtype": "markdown", "markdown": {"content": batch_content}}

def _rss_slack_payload(batch_content: str, _idx: int, _total: int) -> dict:
    return {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": batch_content}}]}

# RSS dispatch table for simple POST-JSON webhook channels
_RSS_WEBHOOK_CHANNELS = [
    {"name": "feishu", "config_key": "FEISHU_WEBHOOK_URL", "display_name": "飞书",
     "batch_size_key": "FEISHU_BATCH_SIZE", "batch_size_default": 29000,
     "renderer": render_rss_feishu_content, "payload_builder": _rss_feishu_payload},
    {"name": "dingtalk", "config_key": "DINGTALK_WEBHOOK_URL", "display_name": "钉钉",
     "batch_size_key": "DINGTALK_BATCH_SIZE", "batch_size_default": 20000,
     "renderer": render_rss_dingtalk_content, "payload_builder": _rss_dingtalk_payload},
    {"name": "wework", "config_key": "WEWORK_WEBHOOK_URL", "display_name": "企业微信",
     "batch_size_key": "MESSAGE_BATCH_SIZE", "batch_size_default": 4000,
     "renderer": render_rss_markdown_content, "payload_builder": _rss_wework_payload},
    {"name": "slack", "config_key": "SLACK_WEBHOOK_URL", "display_name": "Slack",
     "batch_size_key": "SLACK_BATCH_SIZE", "batch_size_default": 4000,
     "renderer": render_rss_markdown_content, "payload_builder": _rss_slack_payload},
]


class NotificationDispatcher:
    """统一的多账号通知调度器"""

    def __init__(
        self,
        config: dict[str, Any],
        get_time_func: Callable,
        split_content_func: Callable,
        translator: AITranslator | None = None,
    ):
        self.config = config
        self.get_time_func = get_time_func
        self.split_content_func = split_content_func
        self.max_accounts = config.get("MAX_ACCOUNTS_PER_CHANNEL", 3)
        self.translator = translator

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    def _translate_content(
        self,
        report_data: dict,
        rss_items: list[dict] | None = None,
        rss_new_items: list[dict] | None = None,
    ) -> tuple:
        """翻译推送内容（标题批量翻译后回填）"""
        if not self.translator or not self.translator.enabled:
            return report_data, rss_items, rss_new_items

        import copy
        logger.info("开始翻译内容", target_language=self.translator.target_language)

        report_data = copy.deepcopy(report_data)
        rss_items = copy.deepcopy(rss_items) if rss_items else None
        rss_new_items = copy.deepcopy(rss_new_items) if rss_new_items else None

        titles: list[str] = []
        locs: list[tuple] = []

        for si, stat in enumerate(report_data.get("stats", [])):
            for ti, td in enumerate(stat.get("titles", [])):
                titles.append(td.get("title", ""))
                locs.append(("stats", si, ti))

        for si, src in enumerate(report_data.get("new_titles", [])):
            for ti, td in enumerate(src.get("titles", [])):
                titles.append(td.get("title", ""))
                locs.append(("new_titles", si, ti))

        if rss_items:
            for ii, item in enumerate(rss_items):
                titles.append(item.get("title", ""))
                locs.append(("rss_items", ii, None))

        if rss_new_items:
            for ii, item in enumerate(rss_new_items):
                titles.append(item.get("title", ""))
                locs.append(("rss_new_items", ii, None))

        if not titles:
            logger.info("没有需要翻译的内容")
            return report_data, rss_items, rss_new_items

        logger.debug("标题待翻译", count=len(titles))
        result = self.translator.translate_batch(titles)

        if result.success_count == 0:
            logger.error("翻译失败", error=result.results[0].error if result.results else "未知错误")
            return report_data, rss_items, rss_new_items

        logger.info("翻译完成", success_count=result.success_count, total_count=result.total_count)

        for i, (loc_type, idx1, idx2) in enumerate(locs):
            if i < len(result.results) and result.results[i].success:
                t = result.results[i].translated_text
                if loc_type == "stats":
                    report_data["stats"][idx1]["titles"][idx2]["title"] = t
                elif loc_type == "new_titles":
                    report_data["new_titles"][idx1]["titles"][idx2]["title"] = t
                elif loc_type == "rss_items" and rss_items:
                    rss_items[idx1]["title"] = t
                elif loc_type == "rss_new_items" and rss_new_items:
                    rss_new_items[idx1]["title"] = t

        return report_data, rss_items, rss_new_items

    # ------------------------------------------------------------------
    # Display-region filtering
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_display_filter(ctx: dict) -> dict:
        """Return a new context dict with display-region suppression applied."""
        dr = ctx["display_regions"]
        out = dict(ctx)
        if not dr.get("HOTLIST", True):
            out["report_data"] = {"stats": [], "failed_ids": [], "new_titles": [], "id_to_name": {}}
        if not dr.get("RSS", True):
            out["rss_items"] = None
            out["rss_new_items"] = None
        if not dr.get("AI_ANALYSIS", True):
            out["ai_analysis"] = None
        if not dr.get("STANDALONE", False):
            out["standalone_data"] = None
        return out

    # ------------------------------------------------------------------
    # Main dispatch
    # ------------------------------------------------------------------

    def dispatch_all(
        self,
        report_data: dict,
        report_type: str,
        update_info: dict | None = None,
        proxy_url: str | None = None,
        mode: str = "daily",
        html_file_path: str | None = None,
        rss_items: list[dict] | None = None,
        rss_new_items: list[dict] | None = None,
        ai_analysis: AIAnalysisResult | None = None,
        standalone_data: dict | None = None,
    ) -> dict[str, bool]:
        """分发通知到所有已配置的渠道（支持热榜+RSS合并推送+AI分析+独立展示区）"""
        display_regions = self.config.get("DISPLAY", {}).get("REGIONS", {})
        report_data, rss_items, rss_new_items = self._translate_content(
            report_data, rss_items, rss_new_items,
        )

        # Pack common channel context once
        ctx = dict(
            report_data=report_data, report_type=report_type,
            update_info=update_info, proxy_url=proxy_url, mode=mode,
            rss_items=rss_items, rss_new_items=rss_new_items,
            ai_analysis=ai_analysis, display_regions=display_regions,
            standalone_data=standalone_data,
        )

        channel_tasks: list[tuple] = []

        # Table-driven simple webhook channels
        for ch in _SIMPLE_CHANNELS:
            if not all(self.config.get(k) for k in ch["config_keys"]):
                continue
            channel_tasks.append((
                ch["name"],
                lambda _ch=ch: self._dispatch_simple_channel(_ch, ctx),
            ))

        # Telegram (paired config)
        if self.config.get("TELEGRAM_BOT_TOKEN") and self.config.get("TELEGRAM_CHAT_ID"):
            channel_tasks.append(("telegram", lambda: self._dispatch_telegram(ctx)))

        # ntfy (triple config)
        if self.config.get("NTFY_SERVER_URL") and self.config.get("NTFY_TOPIC"):
            channel_tasks.append(("ntfy", lambda: self._dispatch_ntfy(ctx)))

        # generic webhook (paired url + template)
        if self.config.get("GENERIC_WEBHOOK_URL"):
            channel_tasks.append(("generic_webhook", lambda: self._dispatch_generic_webhook(ctx)))

        # email (completely different path)
        if self.config.get("EMAIL_FROM") and self.config.get("EMAIL_PASSWORD") and self.config.get("EMAIL_TO"):
            _html, _rt = html_file_path, report_type
            channel_tasks.append(("email", lambda: self._send_email(_rt, _html)))

        return self._run_concurrent(channel_tasks, "推送") if channel_tasks else {}

    # ------------------------------------------------------------------
    # RSS-only dispatch
    # ------------------------------------------------------------------

    def dispatch_rss(
        self,
        rss_items: list[dict],
        feeds_info: dict[str, str] | None = None,
        proxy_url: str | None = None,
        html_file_path: str | None = None,
    ) -> dict[str, bool]:
        """分发 RSS 通知到所有已配置的渠道"""
        if not rss_items:
            logger.info("没有 RSS 内容，跳过通知")
            return {}

        channel_tasks: list[tuple] = []

        # Table-driven webhook channels (feishu, dingtalk, wework, slack)
        for ch in _RSS_WEBHOOK_CHANNELS:
            if not self.config.get(ch["config_key"]):
                continue
            channel_tasks.append((
                ch["name"],
                lambda _ch=ch: self._dispatch_rss_webhook(
                    rss_items, feeds_info, proxy_url, _ch,
                ),
            ))

        # Telegram (paired)
        if self.config.get("TELEGRAM_BOT_TOKEN") and self.config.get("TELEGRAM_CHAT_ID"):
            channel_tasks.append(("telegram", lambda: self._dispatch_rss_telegram(rss_items, feeds_info, proxy_url)))

        # ntfy (triple config)
        if self.config.get("NTFY_SERVER_URL") and self.config.get("NTFY_TOPIC"):
            channel_tasks.append(("ntfy", lambda: self._dispatch_rss_ntfy(rss_items, feeds_info, proxy_url)))

        # Bark (URL-encoded GET)
        if self.config.get("BARK_URL"):
            channel_tasks.append(("bark", lambda: self._dispatch_rss_bark(rss_items, feeds_info, proxy_url)))

        # Email
        if self.config.get("EMAIL_FROM") and self.config.get("EMAIL_PASSWORD") and self.config.get("EMAIL_TO"):
            _html = html_file_path
            channel_tasks.append(("email", lambda: self._send_email("RSS 订阅更新", _html)))

        return self._run_concurrent(channel_tasks, "RSS") if channel_tasks else {}

    # ------------------------------------------------------------------
    # Concurrent execution
    # ------------------------------------------------------------------

    def _run_concurrent(self, channel_tasks: list[tuple], label: str) -> dict[str, bool]:
        """Run (channel_name, callable) tasks concurrently and collect results."""
        results: dict[str, bool] = {}
        logger.info(f"开始并发推送 {label}", channels=[n for n, _ in channel_tasks])
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(channel_tasks)) as executor:
            fmap = {executor.submit(fn): name for name, fn in channel_tasks}
            for future in concurrent.futures.as_completed(fmap):
                ch = fmap[future]
                try:
                    results[ch] = future.result()
                except Exception as e:
                    logger.error("渠道发送异常", channel=ch, error=str(e))
                    results[ch] = False
        return results

    # ------------------------------------------------------------------
    # Multi-account sending
    # ------------------------------------------------------------------

    def _send_to_multi_accounts(
        self, channel_name: str, config_value: str,
        send_func: Callable[..., bool], **kwargs,
    ) -> bool:
        """通用多账号发送逻辑（任一账号成功即返回 True）"""
        accounts = parse_multi_account_config(config_value)
        if not accounts:
            return False
        accounts = limit_accounts(accounts, self.max_accounts, channel_name)

        active = [
            (f"账号{i+1}" if len(accounts) > 1 else "", acct)
            for i, acct in enumerate(accounts) if acct
        ]
        if not active:
            return False
        if len(active) == 1:
            label, acct = active[0]
            return send_func(acct, account_label=label, **kwargs)

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(active)) as executor:
            futures = {
                executor.submit(send_func, acct, account_label=label, **kwargs): label
                for label, acct in active
            }
            results = []
            for future in concurrent.futures.as_completed(futures):
                lbl = futures[future]
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.error("多账号发送异常", channel=channel_name, account_label=lbl, error=str(e))
                    results.append(False)
        return any(results) if results else False

    # ------------------------------------------------------------------
    # Simple webhook channel dispatch (table-driven)
    # ------------------------------------------------------------------

    def _dispatch_simple_channel(self, ch: dict, ctx: dict) -> bool:
        """Dispatch to a simple single-URL webhook channel."""
        c = self._apply_display_filter(ctx)

        extra = {}
        for kwarg, (cfg_key, default) in ch.get("extra_config", {}).items():
            extra[kwarg] = self.config.get(cfg_key, default)
        if ch.get("pass_get_time"):
            extra["get_time_func"] = self.get_time_func

        send_fn, url_param = ch["send_func"], ch["url_param"]

        return self._send_to_multi_accounts(
            channel_name=ch["display_name"],
            config_value=self.config[ch["config_key"]],
            send_func=lambda url, account_label: send_fn(
                **{url_param: url},
                report_data=c["report_data"], report_type=c["report_type"],
                update_info=c["update_info"], proxy_url=c["proxy_url"],
                mode=c["mode"], account_label=account_label,
                batch_size=self.config.get(ch["batch_size_key"], ch["batch_size_default"]),
                batch_interval=self.config.get("BATCH_SEND_INTERVAL", 1.0),
                split_content_func=self.split_content_func,
                rss_items=c["rss_items"], rss_new_items=c["rss_new_items"],
                ai_analysis=c["ai_analysis"], display_regions=c["display_regions"],
                standalone_data=c["standalone_data"], **extra,
            ),
        )

    # ------------------------------------------------------------------
    # Telegram (paired bot_token + chat_id)
    # ------------------------------------------------------------------

    def _dispatch_telegram(self, ctx: dict) -> bool:
        c = self._apply_display_filter(ctx)
        tokens = parse_multi_account_config(self.config["TELEGRAM_BOT_TOKEN"])
        chat_ids = parse_multi_account_config(self.config["TELEGRAM_CHAT_ID"])
        if not tokens or not chat_ids:
            return False

        valid, count = validate_paired_configs(
            {"bot_token": tokens, "chat_id": chat_ids}, "Telegram",
            required_keys=["bot_token", "chat_id"],
        )
        if not valid or count == 0:
            return False

        tokens = limit_accounts(tokens, self.max_accounts, "Telegram")
        chat_ids = chat_ids[:len(tokens)]

        kw = dict(
            report_data=c["report_data"], report_type=c["report_type"],
            update_info=c["update_info"], proxy_url=c["proxy_url"], mode=c["mode"],
            batch_size=self.config.get("MESSAGE_BATCH_SIZE", 4000),
            batch_interval=self.config.get("BATCH_SEND_INTERVAL", 1.0),
            split_content_func=self.split_content_func,
            rss_items=c["rss_items"], rss_new_items=c["rss_new_items"],
            ai_analysis=c["ai_analysis"], display_regions=c["display_regions"],
            standalone_data=c["standalone_data"],
        )
        results = []
        for i, (token, chat_id) in enumerate(zip(tokens, chat_ids, strict=False)):
            if token and chat_id:
                label = f"账号{i+1}" if len(tokens) > 1 else ""
                results.append(send_to_telegram(bot_token=token, chat_id=chat_id, account_label=label, **kw))
        return any(results) if results else False

    # ------------------------------------------------------------------
    # ntfy (server_url + topic + optional token)
    # ------------------------------------------------------------------

    def _dispatch_ntfy(self, ctx: dict) -> bool:
        c = self._apply_display_filter(ctx)
        server_url = self.config["NTFY_SERVER_URL"]
        topics = parse_multi_account_config(self.config["NTFY_TOPIC"])
        tokens = parse_multi_account_config(self.config.get("NTFY_TOKEN", ""))

        if not server_url or not topics:
            return False
        if tokens and len(tokens) != len(topics):
            logger.error(
                "ntfy 配置错误：topic 与 token 数量不一致，跳过推送",
                channel="ntfy", topic_count=len(topics), token_count=len(tokens),
            )
            return False

        topics = limit_accounts(topics, self.max_accounts, "ntfy")
        if tokens:
            tokens = tokens[:len(topics)]

        kw = dict(
            report_data=c["report_data"], report_type=c["report_type"],
            update_info=c["update_info"], proxy_url=c["proxy_url"], mode=c["mode"],
            batch_size=3800, split_content_func=self.split_content_func,
            rss_items=c["rss_items"], rss_new_items=c["rss_new_items"],
            ai_analysis=c["ai_analysis"], display_regions=c["display_regions"],
            standalone_data=c["standalone_data"],
        )
        results = []
        for i, topic in enumerate(topics):
            if topic:
                token = get_account_at_index(tokens, i, "") if tokens else ""
                label = f"账号{i+1}" if len(topics) > 1 else ""
                results.append(send_to_ntfy(server_url=server_url, topic=topic, token=token, account_label=label, **kw))
        return any(results) if results else False

    # ------------------------------------------------------------------
    # Generic webhook (paired url + template)
    # ------------------------------------------------------------------

    def _dispatch_generic_webhook(self, ctx: dict) -> bool:
        c = self._apply_display_filter(ctx)
        urls = parse_multi_account_config(self.config.get("GENERIC_WEBHOOK_URL", ""))
        templates = parse_multi_account_config(self.config.get("GENERIC_WEBHOOK_TEMPLATE", ""))
        if not urls:
            return False

        urls = limit_accounts(urls, self.max_accounts, "通用Webhook")

        kw = dict(
            report_data=c["report_data"], report_type=c["report_type"],
            update_info=c["update_info"], proxy_url=c["proxy_url"], mode=c["mode"],
            batch_size=self.config.get("MESSAGE_BATCH_SIZE", 4000),
            batch_interval=self.config.get("BATCH_SEND_INTERVAL", 1.0),
            split_content_func=self.split_content_func,
            rss_items=c["rss_items"], rss_new_items=c["rss_new_items"],
            ai_analysis=c["ai_analysis"], display_regions=c["display_regions"],
            standalone_data=c["standalone_data"],
        )
        results = []
        for i, url in enumerate(urls):
            if not url:
                continue
            template = ""
            if templates:
                template = templates[i] if i < len(templates) else (templates[0] if len(templates) == 1 else "")
            label = f"账号{i+1}" if len(urls) > 1 else ""
            results.append(send_to_generic_webhook(webhook_url=url, payload_template=template, account_label=label, **kw))
        return any(results) if results else False

    # ------------------------------------------------------------------
    # Email
    # ------------------------------------------------------------------

    def _send_email(self, report_type: str, html_file_path: str | None) -> bool:
        return send_to_email(
            from_email=self.config["EMAIL_FROM"],
            password=self.config["EMAIL_PASSWORD"],
            to_email=self.config["EMAIL_TO"],
            report_type=report_type, html_file_path=html_file_path,
            custom_smtp_server=self.config.get("EMAIL_SMTP_SERVER", ""),
            custom_smtp_port=self.config.get("EMAIL_SMTP_PORT", ""),
            get_time_func=self.get_time_func,
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _split_text_by_bytes(content: str, max_bytes: int) -> list[str]:
        """Split plain text into batches that respect UTF-8 byte limits."""
        if not content:
            return []
        if max_bytes <= 0:
            return [content]

        batches: list[str] = []
        current = ""

        for line in content.splitlines(keepends=True):
            candidate = current + line
            if len(candidate.encode("utf-8")) <= max_bytes:
                current = candidate
                continue
            if current:
                batches.append(current.rstrip("\n"))
                current = ""
            if len(line.encode("utf-8")) <= max_bytes:
                current = line
                continue
            remaining = line
            while remaining:
                chunk = remaining
                while chunk and len(chunk.encode("utf-8")) > max_bytes:
                    chunk = chunk[:-1]
                if not chunk:
                    break
                batches.append(chunk.rstrip("\n"))
                remaining = remaining[len(chunk):]

        if current:
            batches.append(current.rstrip("\n"))
        return batches

    # ------------------------------------------------------------------
    # RSS: webhook dispatch (table-driven for feishu, dingtalk, wework, slack)
    # ------------------------------------------------------------------

    def _dispatch_rss_webhook(
        self, rss_items: list[dict], feeds_info: dict[str, str] | None,
        proxy_url: str | None, ch: dict,
    ) -> bool:
        """Send RSS to a standard webhook channel (POST JSON payloads)."""
        import requests

        content = ch["renderer"](rss_items=rss_items, feeds_info=feeds_info, get_time_func=self.get_time_func)
        webhooks = parse_multi_account_config(self.config[ch["config_key"]])
        webhooks = limit_accounts(webhooks, self.max_accounts, ch["display_name"])

        results = []
        for i, webhook_url in enumerate(webhooks):
            if not webhook_url:
                continue
            label = f"账号{i+1}" if len(webhooks) > 1 else ""
            try:
                batches = self._split_text_by_bytes(content, self.config.get(ch["batch_size_key"], ch["batch_size_default"]))
                for bi, bc in enumerate(batches):
                    payload = ch["payload_builder"](bc, bi, len(batches))
                    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
                    requests.post(webhook_url, json=payload, proxies=proxies, timeout=30).raise_for_status()
                logger.info("RSS 通知发送成功", channel=ch["display_name"], account_label=label)
                results.append(True)
            except Exception as e:
                logger.error("RSS 通知发送失败", channel=ch["display_name"], account_label=label, error=str(e))
                results.append(False)
        return any(results) if results else False

    # ------------------------------------------------------------------
    # RSS: Telegram
    # ------------------------------------------------------------------

    def _dispatch_rss_telegram(
        self, rss_items: list[dict], feeds_info: dict[str, str] | None,
        proxy_url: str | None,
    ) -> bool:
        import requests
        content = render_rss_markdown_content(rss_items=rss_items, feeds_info=feeds_info, get_time_func=self.get_time_func)
        tokens = parse_multi_account_config(self.config["TELEGRAM_BOT_TOKEN"])
        chat_ids = parse_multi_account_config(self.config["TELEGRAM_CHAT_ID"])
        if not tokens or not chat_ids:
            return False

        results = []
        for i in range(min(len(tokens), len(chat_ids), self.max_accounts)):
            token, chat_id = tokens[i], chat_ids[i]
            if not token or not chat_id:
                continue
            label = f"账号{i+1}" if len(tokens) > 1 else ""
            try:
                for bc in self._split_text_by_bytes(content, self.config.get("MESSAGE_BATCH_SIZE", 4000)):
                    url = f"https://api.telegram.org/bot{token}/sendMessage"
                    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
                    requests.post(url, json={"chat_id": chat_id, "text": bc, "parse_mode": "Markdown"}, proxies=proxies, timeout=30).raise_for_status()
                logger.info("RSS 通知发送成功", channel="telegram", account_label=label)
                results.append(True)
            except Exception as e:
                logger.error("RSS 通知发送失败", channel="telegram", account_label=label, error=str(e))
                results.append(False)
        return any(results) if results else False

    # ------------------------------------------------------------------
    # RSS: ntfy
    # ------------------------------------------------------------------

    def _dispatch_rss_ntfy(
        self, rss_items: list[dict], feeds_info: dict[str, str] | None,
        proxy_url: str | None,
    ) -> bool:
        import requests
        content = render_rss_markdown_content(rss_items=rss_items, feeds_info=feeds_info, get_time_func=self.get_time_func)
        server_url = self.config["NTFY_SERVER_URL"]
        topics = parse_multi_account_config(self.config["NTFY_TOPIC"])
        tokens = parse_multi_account_config(self.config.get("NTFY_TOKEN", ""))
        if not server_url or not topics:
            return False

        topics = limit_accounts(topics, self.max_accounts, "ntfy")
        results = []
        for i, topic in enumerate(topics):
            if not topic:
                continue
            token = tokens[i] if tokens and i < len(tokens) else ""
            label = f"账号{i+1}" if len(topics) > 1 else ""
            try:
                for bc in self._split_text_by_bytes(content, 3800):
                    url = f"{server_url.rstrip('/')}/{topic}"
                    headers = {"Title": "RSS 订阅更新", "Markdown": "yes"}
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
                    requests.post(url, data=bc.encode("utf-8"), headers=headers, proxies=proxies, timeout=30).raise_for_status()
                logger.info("RSS 通知发送成功", channel="ntfy", account_label=label)
                results.append(True)
            except Exception as e:
                logger.error("RSS 通知发送失败", channel="ntfy", account_label=label, error=str(e))
                results.append(False)
        return any(results) if results else False

    # ------------------------------------------------------------------
    # RSS: Bark (URL-encoded GET)
    # ------------------------------------------------------------------

    def _dispatch_rss_bark(
        self, rss_items: list[dict], feeds_info: dict[str, str] | None,
        proxy_url: str | None,
    ) -> bool:
        import urllib.parse

        import requests
        content = render_rss_markdown_content(rss_items=rss_items, feeds_info=feeds_info, get_time_func=self.get_time_func)
        urls = parse_multi_account_config(self.config["BARK_URL"])
        urls = limit_accounts(urls, self.max_accounts, "Bark")

        results = []
        for i, bark_url in enumerate(urls):
            if not bark_url:
                continue
            label = f"账号{i+1}" if len(urls) > 1 else ""
            try:
                for bc in self._split_text_by_bytes(content, self.config.get("BARK_BATCH_SIZE", 3600)):
                    title = urllib.parse.quote("\U0001f4f0 RSS \u8ba2\u9605\u66f4\u65b0")
                    body = urllib.parse.quote(bc)
                    url = f"{bark_url.rstrip('/')}/{title}/{body}"
                    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
                    requests.get(url, proxies=proxies, timeout=30).raise_for_status()
                logger.info("RSS 通知发送成功", channel="bark", account_label=label)
                results.append(True)
            except Exception as e:
                logger.error("RSS 通知发送失败", channel="bark", account_label=label, error=str(e))
                results.append(False)
        return any(results) if results else False
