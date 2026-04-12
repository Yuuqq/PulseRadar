# coding=utf-8
"""
数据获取器模块

负责从 NewsNow API 抓取新闻数据，支持：
- 单个平台数据获取
- 批量平台数据爬取
- 自动重试机制
- 代理支持
"""

import concurrent.futures
import json
import random
import time
from typing import Dict, List, Tuple, Optional, Union

import requests

from trendradar.logging import get_logger

logger = get_logger(__name__)


class DataFetcher:
    """数据获取器"""

    # 默认 API 地址
    DEFAULT_API_URL = "https://newsnow.busiyi.world/api/s"

    # 默认请求头
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        api_url: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ):
        """
        初始化数据获取器

        Args:
            proxy_url: 代理服务器 URL（可选）
            api_url: API 基础 URL（可选，默认使用 DEFAULT_API_URL）
            session: 可注入的 requests.Session（可选，用于复用连接或测试）
        """
        self.proxy_url = proxy_url
        self.api_url = api_url or self.DEFAULT_API_URL
        self.session = session or requests.Session()

    def close(self) -> None:
        """释放底层 HTTP 连接资源"""
        try:
            self.session.close()
        except Exception:
            logger.debug("关闭 session 失败", exc_info=True)

    def fetch_data(
        self,
        id_info: Union[str, Tuple[str, str]],
        max_retries: int = 2,
        min_retry_wait: int = 3,
        max_retry_wait: int = 5,
    ) -> Tuple[Optional[str], str, str]:
        """
        获取指定ID数据，支持重试

        Args:
            id_info: 平台ID 或 (平台ID, 别名) 元组
            max_retries: 最大重试次数
            min_retry_wait: 最小重试等待时间（秒）
            max_retry_wait: 最大重试等待时间（秒）

        Returns:
            (响应文本, 平台ID, 别名) 元组，失败时响应文本为 None
        """
        if isinstance(id_info, tuple):
            id_value, alias = id_info
        else:
            id_value = id_info
            alias = id_value

        url = f"{self.api_url}?id={id_value}&latest"

        proxies = None
        if self.proxy_url:
            proxies = {"http": self.proxy_url, "https": self.proxy_url}

        retries = 0
        while retries <= max_retries:
            try:
                response = self.session.get(
                    url,
                    proxies=proxies,
                    headers=self.DEFAULT_HEADERS,
                    timeout=10,
                )
                response.raise_for_status()

                data_text = response.text
                data_json = json.loads(data_text)

                status = data_json.get("status", "未知")
                if status not in ["success", "cache"]:
                    raise ValueError(f"响应状态异常: {status}")

                status_info = "最新数据" if status == "success" else "缓存数据"
                logger.info("获取成功", id_value=id_value, status_info=status_info)
                return data_text, id_value, alias

            except Exception as e:
                retries += 1
                if retries <= max_retries:
                    base_wait = random.uniform(min_retry_wait, max_retry_wait)
                    additional_wait = (retries - 1) * random.uniform(1, 2)
                    wait_time = base_wait + additional_wait
                    logger.warning("请求失败，准备重试", id_value=id_value, error=str(e), wait_time=round(wait_time, 2))
                    time.sleep(wait_time)
                else:
                    logger.error("请求失败", id_value=id_value, error=str(e))
                    return None, id_value, alias

        return None, id_value, alias

    def crawl_websites(
        self,
        ids_list: List[Union[str, Tuple[str, str]]],
        request_interval: int = 100,
    ) -> Tuple[Dict, Dict, List]:
        """
        爬取多个网站数据

        Args:
            ids_list: 平台ID列表，每个元素可以是字符串或 (平台ID, 别名) 元组
            request_interval: 请求间隔（毫秒）

        Returns:
            (结果字典, ID到名称的映射, 失败ID列表) 元组
        """
        results = {}
        id_to_name = {}
        failed_ids = []

        # Build id_to_name mapping before concurrent execution
        for id_info in ids_list:
            if isinstance(id_info, tuple):
                id_value, name = id_info
            else:
                id_value = id_info
                name = id_value
            id_to_name[id_value] = name

        if not ids_list:
            return results, id_to_name, failed_ids

        max_workers = min(len(ids_list), 10)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_id: Dict[concurrent.futures.Future, str] = {}
            for i, id_info in enumerate(ids_list):
                # Small stagger (20 ms) to avoid thundering herd against the API
                if i > 0:
                    time.sleep(0.02)
                future = executor.submit(self.fetch_data, id_info)
                id_val = id_info[0] if isinstance(id_info, tuple) else id_info
                future_to_id[future] = id_val

            for future in concurrent.futures.as_completed(future_to_id):
                id_value = future_to_id[future]
                try:
                    response, _, _ = future.result()
                    if response:
                        data = json.loads(response)
                        results[id_value] = {}
                        for index, item in enumerate(data.get("items", []), 1):
                            title = item.get("title")
                            # Skip invalid titles (None, float, blank string)
                            if title is None or isinstance(title, float) or not str(title).strip():
                                continue
                            title = str(title).strip()
                            url = item.get("url", "")
                            mobile_url = item.get("mobileUrl", "")
                            if title in results[id_value]:
                                results[id_value][title]["ranks"].append(index)
                            else:
                                results[id_value][title] = {
                                    "ranks": [index],
                                    "url": url,
                                    "mobileUrl": mobile_url,
                                }
                    else:
                        failed_ids.append(id_value)
                except json.JSONDecodeError:
                    logger.error("解析响应失败", id_value=id_value)
                    failed_ids.append(id_value)
                except Exception as e:
                    logger.error("处理数据出错", id_value=id_value, error=str(e))
                    failed_ids.append(id_value)

        logger.info("爬取完成", succeeded=list(results.keys()), failed=failed_ids)
        return results, id_to_name, failed_ids
