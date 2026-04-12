# coding=utf-8
"""Generic webhook notification channel."""

import json
import time
from typing import Any, Callable, Dict, Optional

import requests

from trendradar.logging import get_logger
from trendradar.notification.channels.base import (
    extract_ai_stats,
    prepare_batches,
    render_ai_content,
)

logger = get_logger(__name__)


def send_to_generic_webhook(
    webhook_url: str,
    payload_template: Optional[str],
    report_data: Dict,
    report_type: str,
    update_info: Optional[Dict] = None,
    proxy_url: Optional[str] = None,
    mode: str = "daily",
    account_label: str = "",
    *,
    batch_size: int = 4000,
    batch_interval: float = 1.0,
    split_content_func: Optional[Callable] = None,
    rss_items: Optional[list] = None,
    rss_new_items: Optional[list] = None,
    ai_analysis: Any = None,
    display_regions: Optional[Dict] = None,
    standalone_data: Optional[Dict] = None,
) -> bool:
    """Send report to a generic webhook (batch-aware, custom JSON template).

    Signature and behaviour are identical to the original in ``senders.py``.
    """
    if split_content_func is None:
        raise ValueError("split_content_func is required")

    headers = {"Content-Type": "application/json"}
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
    log_prefix = f"\u901a\u7528Webhook{account_label}" if account_label else "\u901a\u7528Webhook"

    # Generic webhook renders AI analysis in markdown (wework format)
    ai_content = render_ai_content(ai_analysis, "wework") or None
    ai_stats = None
    if ai_analysis and getattr(ai_analysis, "success", False):
        ai_stats = {
            "total_news": getattr(ai_analysis, "total_news", 0),
            "analyzed_news": getattr(ai_analysis, "analyzed_news", 0),
            "max_news_limit": getattr(ai_analysis, "max_news_limit", 0),
            "hotlist_count": getattr(ai_analysis, "hotlist_count", 0),
            "rss_count": getattr(ai_analysis, "rss_count", 0),
        }

    batches = prepare_batches(
        report_data=report_data,
        format_type="wework",
        split_content_func=split_content_func,
        update_info=update_info,
        batch_size=batch_size,
        mode=mode,
        rss_items=rss_items,
        rss_new_items=rss_new_items,
        ai_content=ai_content,
        standalone_data=standalone_data,
        ai_stats=ai_stats,
        report_type=report_type,
        header_format_type="wework",
        template_overhead=200,
    )

    logger.info(
        "\u6d88\u606f\u5206\u6279\u53d1\u9001",
        channel="generic_webhook", account_label=log_prefix,
        batches=len(batches), report_type=report_type,
    )

    for i, batch_content in enumerate(batches, 1):
        content_size = len(batch_content.encode("utf-8"))
        logger.debug(
            "\u53d1\u9001\u6279\u6b21",
            channel="generic_webhook", account_label=log_prefix,
            batch=i, total=len(batches), size=content_size,
            report_type=report_type,
        )

        try:
            if payload_template:
                json_content = json.dumps(batch_content)[1:-1]
                json_title = json.dumps(report_type)[1:-1]
                payload_str = payload_template.replace("{content}", json_content).replace("{title}", json_title)
                try:
                    payload = json.loads(payload_str)
                except json.JSONDecodeError as e:
                    logger.error(
                        "JSON \u6a21\u677f\u89e3\u6790\u5931\u8d25",
                        channel="generic_webhook", account_label=log_prefix,
                        error=str(e),
                    )
                    payload = {"title": report_type, "content": batch_content}
            else:
                payload = {"title": report_type, "content": batch_content}

            response = requests.post(
                webhook_url, headers=headers, json=payload,
                proxies=proxies, timeout=30,
            )

            if 200 <= response.status_code < 300:
                logger.info(
                    "\u6279\u6b21\u53d1\u9001\u6210\u529f",
                    channel="generic_webhook", account_label=log_prefix,
                    batch=i, total=len(batches), report_type=report_type,
                )
                if i < len(batches):
                    time.sleep(batch_interval)
            else:
                logger.error(
                    "\u6279\u6b21\u53d1\u9001\u5931\u8d25",
                    channel="generic_webhook", account_label=log_prefix,
                    batch=i, total=len(batches),
                    report_type=report_type, status_code=response.status_code,
                    response_text=response.text,
                )
                return False
        except Exception as e:
            logger.error(
                "\u6279\u6b21\u53d1\u9001\u51fa\u9519",
                channel="generic_webhook", account_label=log_prefix,
                batch=i, total=len(batches),
                report_type=report_type, error=str(e),
            )
            return False

    logger.info(
        "\u6240\u6709\u6279\u6b21\u53d1\u9001\u5b8c\u6210",
        channel="generic_webhook", account_label=log_prefix,
        batches=len(batches), report_type=report_type,
    )
    return True
