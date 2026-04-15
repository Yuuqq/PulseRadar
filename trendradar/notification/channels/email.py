"""Email (SMTP) notification channel."""

import smtplib
from collections.abc import Callable
from datetime import datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path

from trendradar.logging import get_logger

logger = get_logger(__name__)


# Well-known SMTP server configurations
SMTP_CONFIGS = {
    "gmail.com": {"server": "smtp.gmail.com", "port": 587, "encryption": "TLS"},
    "qq.com": {"server": "smtp.qq.com", "port": 465, "encryption": "SSL"},
    "outlook.com": {"server": "smtp-mail.outlook.com", "port": 587, "encryption": "TLS"},
    "hotmail.com": {"server": "smtp-mail.outlook.com", "port": 587, "encryption": "TLS"},
    "live.com": {"server": "smtp-mail.outlook.com", "port": 587, "encryption": "TLS"},
    "163.com": {"server": "smtp.163.com", "port": 465, "encryption": "SSL"},
    "126.com": {"server": "smtp.126.com", "port": 465, "encryption": "SSL"},
    "sina.com": {"server": "smtp.sina.com", "port": 465, "encryption": "SSL"},
    "sohu.com": {"server": "smtp.sohu.com", "port": 465, "encryption": "SSL"},
    "189.cn": {"server": "smtp.189.cn", "port": 465, "encryption": "SSL"},
    "aliyun.com": {"server": "smtp.aliyun.com", "port": 587, "encryption": "TLS"},
    "yandex.com": {"server": "smtp.yandex.com", "port": 587, "encryption": "TLS"},
    "icloud.com": {"server": "smtp.mail.me.com", "port": 587, "encryption": "TLS"},
}


def send_to_email(
    from_email: str,
    password: str,
    to_email: str,
    report_type: str,
    html_file_path: str,
    custom_smtp_server: str | None = None,
    custom_smtp_port: int | None = None,
    *,
    get_time_func: Callable | None = None,
) -> bool:
    """Send an HTML report via SMTP email.

    Signature and behaviour are identical to the original in ``senders.py``.
    """
    try:
        if not html_file_path or not Path(html_file_path).exists():
            logger.error(
                "HTML\u6587\u4ef6\u4e0d\u5b58\u5728\u6216\u672a\u63d0\u4f9b",
                channel="email",
                html_file_path=html_file_path,
            )
            return False

        logger.info("\u4f7f\u7528HTML\u6587\u4ef6", channel="email", html_file_path=html_file_path)
        with open(html_file_path, encoding="utf-8") as f:
            html_content = f.read()

        domain = from_email.split("@")[-1].lower()

        if custom_smtp_server and custom_smtp_port:
            smtp_server = custom_smtp_server
            smtp_port = int(custom_smtp_port)
            if smtp_port == 465:
                use_tls = False
            elif smtp_port == 587:
                use_tls = True
            else:
                use_tls = True
        elif domain in SMTP_CONFIGS:
            config = SMTP_CONFIGS[domain]
            smtp_server = config["server"]
            smtp_port = config["port"]
            use_tls = config["encryption"] == "TLS"
        else:
            logger.warning(
                "\u672a\u8bc6\u522b\u7684\u90ae\u7bb1\u670d\u52a1\u5546\uff0c\u4f7f\u7528\u901a\u7528 SMTP \u914d\u7f6e",
                channel="email",
                domain=domain,
            )
            smtp_server = f"smtp.{domain}"
            smtp_port = 587
            use_tls = True

        msg = MIMEMultipart("alternative")
        sender_name = "TrendRadar"
        msg["From"] = formataddr((sender_name, from_email))

        recipients = [addr.strip() for addr in to_email.split(",")]
        if len(recipients) == 1:
            msg["To"] = recipients[0]
        else:
            msg["To"] = ", ".join(recipients)

        now = get_time_func() if get_time_func else datetime.now()
        time_str = now.strftime("%m月%d日 %H:%M")
        subject = f"TrendRadar 热点分析报告 - {report_type} - {time_str}"
        msg["Subject"] = Header(subject, "utf-8")

        msg["MIME-Version"] = "1.0"
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()

        text_content = f"""
TrendRadar \u70ed\u70b9\u5206\u6790\u62a5\u544a
========================
\u62a5\u544a\u7c7b\u578b\uff1a{report_type}
\u751f\u6210\u65f6\u95f4\uff1a{now.strftime("%Y-%m-%d %H:%M:%S")}

\u8bf7\u4f7f\u7528\u652f\u6301HTML\u7684\u90ae\u4ef6\u5ba2\u6237\u7aef\u67e5\u770b\u5b8c\u6574\u62a5\u544a\u5185\u5bb9\u3002
        """
        text_part = MIMEText(text_content, "plain", "utf-8")
        msg.attach(text_part)

        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        logger.info(
            "\u6b63\u5728\u53d1\u9001\u90ae\u4ef6",
            channel="email",
            to=to_email,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            from_email=from_email,
        )

        try:
            if use_tls:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                server.set_debuglevel(0)
                server.ehlo()
                server.starttls()
                server.ehlo()
            else:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
                server.set_debuglevel(0)
                server.ehlo()

            server.login(from_email, password)
            server.send_message(msg)
            server.quit()

            logger.info(
                "\u90ae\u4ef6\u53d1\u9001\u6210\u529f",
                channel="email",
                report_type=report_type,
                to=to_email,
            )
            return True

        except smtplib.SMTPServerDisconnected:
            logger.error(
                "\u90ae\u4ef6\u53d1\u9001\u5931\u8d25\uff1a\u670d\u52a1\u5668\u610f\u5916\u65ad\u5f00\u8fde\u63a5",
                channel="email",
            )
            return False

    except smtplib.SMTPAuthenticationError as e:
        logger.error(
            "\u90ae\u4ef6\u53d1\u9001\u5931\u8d25\uff1a\u8ba4\u8bc1\u9519\u8bef",
            channel="email",
            error=str(e),
        )
        return False
    except smtplib.SMTPRecipientsRefused as e:
        logger.error(
            "\u90ae\u4ef6\u53d1\u9001\u5931\u8d25\uff1a\u6536\u4ef6\u4eba\u5730\u5740\u88ab\u62d2\u7edd",
            channel="email",
            error=str(e),
        )
        return False
    except smtplib.SMTPSenderRefused as e:
        logger.error(
            "\u90ae\u4ef6\u53d1\u9001\u5931\u8d25\uff1a\u53d1\u4ef6\u4eba\u5730\u5740\u88ab\u62d2\u7edd",
            channel="email",
            error=str(e),
        )
        return False
    except smtplib.SMTPDataError as e:
        logger.error(
            "\u90ae\u4ef6\u53d1\u9001\u5931\u8d25\uff1a\u90ae\u4ef6\u6570\u636e\u9519\u8bef",
            channel="email",
            error=str(e),
        )
        return False
    except smtplib.SMTPConnectError as e:
        logger.error(
            "\u90ae\u4ef6\u53d1\u9001\u5931\u8d25\uff1a\u65e0\u6cd5\u8fde\u63a5\u5230 SMTP \u670d\u52a1\u5668",
            channel="email",
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            error=str(e),
        )
        return False
    except Exception as e:
        logger.error(
            "\u90ae\u4ef6\u53d1\u9001\u5931\u8d25",
            channel="email",
            report_type=report_type,
            error=str(e),
        )
        import traceback

        traceback.print_exc()
        return False
