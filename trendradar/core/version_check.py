"""
版本检查工具

从 __main__.py 中提取的版本检查相关函数。
"""

import re
from pathlib import Path

import requests

from trendradar import __version__
from trendradar.logging import get_logger

logger = get_logger(__name__)


def parse_version(version_str: str) -> tuple[int, int, int]:
    """解析版本号字符串为元组"""
    try:
        parts = version_str.strip().split(".")
        if len(parts) >= 3:
            return int(parts[0]), int(parts[1]), int(parts[2])
        return 0, 0, 0
    except (ValueError, IndexError):
        return 0, 0, 0


def compare_version(local: str, remote: str) -> str:
    """比较版本号，返回状态文字"""
    local_tuple = parse_version(local)
    remote_tuple = parse_version(remote)

    if local_tuple < remote_tuple:
        return "需要更新"
    elif local_tuple > remote_tuple:
        return "超前版本"
    else:
        return "已是最新"


def fetch_remote_version(version_url: str, proxy_url: str | None = None) -> str | None:
    """获取远程版本号"""
    try:
        proxies = None
        if proxy_url:
            proxies = {"http": proxy_url, "https": proxy_url}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/plain, */*",
            "Cache-Control": "no-cache",
        }

        response = requests.get(version_url, proxies=proxies, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        logger.error("获取远程版本失败", error=str(e))
        return None


def parse_config_versions(content: str) -> dict[str, str]:
    """解析配置文件版本内容为字典"""
    versions = {}
    try:
        if not content:
            return versions
        for line in content.splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            name, version = line.split("=", 1)
            versions[name.strip()] = version.strip()
    except Exception as e:
        logger.error("解析配置版本失败", error=str(e))
    return versions


def check_all_versions(
    version_url: str,
    configs_version_url: str | None = None,
    proxy_url: str | None = None,
) -> tuple[bool, str | None]:
    """
    统一版本检查：程序版本 + 配置文件版本

    Args:
        version_url: 远程程序版本检查 URL
        configs_version_url: 远程配置文件版本检查 URL (返回格式: filename=version)
        proxy_url: 代理 URL

    Returns:
        (need_update, remote_version): 程序是否需要更新及远程版本号
    """
    remote_version = fetch_remote_version(version_url, proxy_url)

    remote_config_versions = {}
    if configs_version_url:
        content = fetch_remote_version(configs_version_url, proxy_url)
        if content:
            remote_config_versions = parse_config_versions(content)

    logger.info(
        "版本检查开始",
        remote_version=remote_version or "获取失败",
        config_files_count=len(remote_config_versions) if configs_version_url else None,
    )

    program_status = compare_version(__version__, remote_version) if remote_version else "(无法比较)"
    logger.info("主程序版本", version=__version__, status=program_status)

    config_files = [
        Path("config/config.yaml"),
        Path("config/frequency_words.txt"),
        Path("config/ai_analysis_prompt.txt"),
        Path("config/ai_translation_prompt.txt"),
    ]

    version_pattern = re.compile(r"Version:\s*(\d+\.\d+\.\d+)", re.IGNORECASE)

    for config_file in config_files:
        if not config_file.exists():
            logger.warning("配置文件不存在", file=config_file.name)
            continue

        try:
            with open(config_file, encoding="utf-8") as f:
                local_version = None
                for i, line in enumerate(f):
                    if i >= 20:
                        break
                    match = version_pattern.search(line)
                    if match:
                        local_version = match.group(1)
                        break

                target_remote_version = remote_config_versions.get(config_file.name)

                if local_version:
                    if target_remote_version:
                        status = compare_version(local_version, target_remote_version)
                        logger.info(
                            "配置文件版本",
                            file=config_file.name,
                            local_version=local_version,
                            status=status,
                        )
                    else:
                        logger.info(
                            "配置文件版本",
                            file=config_file.name,
                            local_version=local_version,
                            remote_version="未找到",
                        )
                else:
                    logger.warning("配置文件未找到版本号", file=config_file.name)
        except Exception as e:
            logger.error("配置文件读取失败", file=config_file.name, error=str(e))

    logger.info("版本检查完成")

    if remote_version:
        need_update = parse_version(__version__) < parse_version(remote_version)
        return need_update, remote_version if need_update else None
    return False, None
