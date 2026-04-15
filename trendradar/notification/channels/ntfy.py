"""ntfy notification channel."""

import contextlib
import time
from collections.abc import Callable
from typing import Any

import requests

from trendradar.logging import get_logger
from trendradar.notification.channels.base import (
    extract_ai_stats,
    prepare_batches,
    render_ai_content,
)

logger = get_logger(__name__)


def send_to_ntfy(
    server_url: str,
    topic: str,
    token: str | None,
    report_data: dict,
    report_type: str,
    update_info: dict | None = None,
    proxy_url: str | None = None,
    mode: str = "daily",
    account_label: str = "",
    *,
    batch_size: int = 3800,
    split_content_func: Callable | None = None,
    rss_items: list | None = None,
    rss_new_items: list | None = None,
    ai_analysis: Any = None,
    display_regions: dict | None = None,
    standalone_data: dict | None = None,
) -> bool:
    """Send report to ntfy (batch-aware, reversed order, rate-limit retry).

    Signature and behaviour are identical to the original in ``senders.py``.
    """
    log_prefix = f"ntfy{account_label}" if account_label else "ntfy"

    # Map Chinese report types to ASCII-safe HTTP header values
    report_type_en_map = {
        "\u5f53\u65e5\u6c47\u603b": "Daily Summary",
        "\u5f53\u524d\u699c\u5355\u6c47\u603b": "Current Ranking",
        "\u589e\u91cf\u66f4\u65b0": "Incremental Update",
        "\u5b9e\u65f6\u589e\u91cf": "Realtime Incremental",
        "\u5b9e\u65f6\u5f53\u524d\u699c\u5355": "Realtime Current Ranking",
    }
    report_type_en = report_type_en_map.get(report_type, "News Report")

    ntfy_headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Markdown": "yes",
        "Title": report_type_en,
        "Priority": "default",
        "Tags": "news",
    }
    if token:
        ntfy_headers["Authorization"] = f"Bearer {token}"

    base_url = server_url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"
    url = f"{base_url}/{topic}"

    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

    ai_content = render_ai_content(ai_analysis, "ntfy") or None
    ai_stats = extract_ai_stats(ai_analysis)

    batches = prepare_batches(
        report_data=report_data,
        format_type="ntfy",
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
    )

    total_batches = len(batches)
    logger.info(
        "\u6d88\u606f\u5206\u6279\u53d1\u9001",
        channel="ntfy",
        account_label=log_prefix,
        batches=total_batches,
        report_type=report_type,
    )

    # Reverse so that ntfy clients (newest-first) display in reading order
    reversed_batches = list(reversed(batches))
    logger.debug(
        "\u5c06\u6309\u53cd\u5411\u987a\u5e8f\u63a8\u9001\uff0c\u786e\u4fdd\u5ba2\u6237\u7aef\u663e\u793a\u987a\u5e8f\u6b63\u786e",
        channel="ntfy",
        account_label=log_prefix,
    )

    success_count = 0
    for idx, batch_content in enumerate(reversed_batches, 1):
        actual_batch_num = total_batches - idx + 1
        content_size = len(batch_content.encode("utf-8"))
        logger.debug(
            "\u53d1\u9001\u6279\u6b21",
            channel="ntfy",
            account_label=log_prefix,
            batch=actual_batch_num,
            total=total_batches,
            push_order=idx,
            size=content_size,
            report_type=report_type,
        )

        if content_size > 4096:
            logger.warning(
                "\u6279\u6b21\u6d88\u606f\u8fc7\u5927\uff0c\u53ef\u80fd\u88ab\u62d2\u7edd",
                channel="ntfy",
                account_label=log_prefix,
                batch=actual_batch_num,
                total=total_batches,
                size=content_size,
            )

        current_headers = ntfy_headers.copy()
        if total_batches > 1:
            current_headers["Title"] = f"{report_type_en} ({actual_batch_num}/{total_batches})"

        try:
            response = requests.post(
                url,
                headers=current_headers,
                data=batch_content.encode("utf-8"),
                proxies=proxies,
                timeout=30,
            )

            if response.status_code == 200:
                logger.info(
                    "\u6279\u6b21\u53d1\u9001\u6210\u529f",
                    channel="ntfy",
                    account_label=log_prefix,
                    batch=actual_batch_num,
                    total=total_batches,
                    report_type=report_type,
                )
                success_count += 1
                if idx < total_batches:
                    interval = 2 if "ntfy.sh" in server_url else 1
                    time.sleep(interval)
            elif response.status_code == 429:
                logger.warning(
                    "\u6279\u6b21\u901f\u7387\u9650\u5236\uff0c\u7b49\u5f85\u540e\u91cd\u8bd5",
                    channel="ntfy",
                    account_label=log_prefix,
                    batch=actual_batch_num,
                    total=total_batches,
                    report_type=report_type,
                )
                time.sleep(10)
                retry_response = requests.post(
                    url,
                    headers=current_headers,
                    data=batch_content.encode("utf-8"),
                    proxies=proxies,
                    timeout=30,
                )
                if retry_response.status_code == 200:
                    logger.info(
                        "\u6279\u6b21\u91cd\u8bd5\u6210\u529f",
                        channel="ntfy",
                        account_label=log_prefix,
                        batch=actual_batch_num,
                        total=total_batches,
                        report_type=report_type,
                    )
                    success_count += 1
                else:
                    logger.error(
                        "\u6279\u6b21\u91cd\u8bd5\u5931\u8d25",
                        channel="ntfy",
                        account_label=log_prefix,
                        batch=actual_batch_num,
                        total=total_batches,
                        status_code=retry_response.status_code,
                    )
            elif response.status_code == 413:
                logger.error(
                    "\u6279\u6b21\u6d88\u606f\u8fc7\u5927\u88ab\u62d2\u7edd",
                    channel="ntfy",
                    account_label=log_prefix,
                    batch=actual_batch_num,
                    total=total_batches,
                    report_type=report_type,
                    size=content_size,
                )
            else:
                logger.error(
                    "\u6279\u6b21\u53d1\u9001\u5931\u8d25",
                    channel="ntfy",
                    account_label=log_prefix,
                    batch=actual_batch_num,
                    total=total_batches,
                    report_type=report_type,
                    status_code=response.status_code,
                )
                with contextlib.suppress(Exception):
                    logger.debug(
                        "\u9519\u8bef\u8be6\u60c5", channel="ntfy", response_text=response.text
                    )

        except requests.exceptions.ConnectTimeout:
            logger.error(
                "\u6279\u6b21\u8fde\u63a5\u8d85\u65f6",
                channel="ntfy",
                account_label=log_prefix,
                batch=actual_batch_num,
                total=total_batches,
                report_type=report_type,
            )
        except requests.exceptions.ReadTimeout:
            logger.error(
                "\u6279\u6b21\u8bfb\u53d6\u8d85\u65f6",
                channel="ntfy",
                account_label=log_prefix,
                batch=actual_batch_num,
                total=total_batches,
                report_type=report_type,
            )
        except requests.exceptions.ConnectionError as e:
            logger.error(
                "\u6279\u6b21\u8fde\u63a5\u9519\u8bef",
                channel="ntfy",
                account_label=log_prefix,
                batch=actual_batch_num,
                total=total_batches,
                report_type=report_type,
                error=str(e),
            )
        except Exception as e:
            logger.error(
                "\u6279\u6b21\u53d1\u9001\u5f02\u5e38",
                channel="ntfy",
                account_label=log_prefix,
                batch=actual_batch_num,
                total=total_batches,
                report_type=report_type,
                error=str(e),
            )

    if success_count == total_batches:
        logger.info(
            "\u6240\u6709\u6279\u6b21\u53d1\u9001\u5b8c\u6210",
            channel="ntfy",
            account_label=log_prefix,
            batches=total_batches,
            report_type=report_type,
        )
    elif success_count > 0:
        logger.warning(
            "\u90e8\u5206\u53d1\u9001\u6210\u529f",
            channel="ntfy",
            account_label=log_prefix,
            success_count=success_count,
            total=total_batches,
            report_type=report_type,
        )
    else:
        logger.error(
            "\u53d1\u9001\u5b8c\u5168\u5931\u8d25",
            channel="ntfy",
            account_label=log_prefix,
            report_type=report_type,
        )
        return False

    return True
