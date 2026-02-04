# coding=utf-8
"""
额外数据源 API 模块

支持多种免费/开放的新闻 API：
1. 国内热榜聚合 (VVHan, DailyHot)
2. 国际新闻 API (NewsAPI, GNews, MediaStack, TheNewsAPI)
"""

import json
import time
import random
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

import requests


class ExtraAPIFetcher:
    """额外 API 数据获取器"""

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ):
        """
        初始化额外 API 获取器

        Args:
            proxy_url: 代理服务器 URL（可选）
            session: 可注入的 requests.Session（可选）
        """
        self.proxy_url = proxy_url
        self.session = session or requests.Session()

    def close(self) -> None:
        """释放 HTTP 连接资源"""
        try:
            self.session.close()
        except Exception:
            pass

    def _get_proxies(self) -> Optional[Dict]:
        """获取代理配置"""
        if self.proxy_url:
            return {"http": self.proxy_url, "https": self.proxy_url}
        return None

    def _request(
        self,
        url: str,
        timeout: int = 15,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """
        发送 HTTP 请求

        Args:
            url: 请求 URL
            timeout: 超时时间（秒）
            headers: 额外请求头
            params: URL 参数

        Returns:
            JSON 响应或 None
        """
        try:
            req_headers = {**self.DEFAULT_HEADERS}
            if headers:
                req_headers.update(headers)

            response = self.session.get(
                url,
                headers=req_headers,
                params=params,
                proxies=self._get_proxies(),
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"请求失败 {url}: {e}")
            return None

    # =========================================================================
    # 国内热榜聚合 API
    # =========================================================================

    def fetch_vvhan_hotlist(self, source_type: str) -> List[Dict]:
        """
        获取韩小韩热榜 API 数据

        Args:
            source_type: 平台类型 (toutiao, weibo, zhihu, baidu, bilibili, douyin 等)

        Returns:
            新闻列表 [{"title": str, "url": str, "rank": int}, ...]
        """
        url = f"https://api.vvhan.com/api/hotlist/{source_type}"
        data = self._request(url)

        if not data or not data.get("success"):
            print(f"[VVHan] 获取 {source_type} 失败")
            return []

        items = []
        for idx, item in enumerate(data.get("data", []), 1):
            title = item.get("title", "").strip()
            if not title:
                continue
            items.append({
                "title": title,
                "url": item.get("url", ""),
                "rank": idx,
                "hot": item.get("hot", ""),
            })

        print(f"[VVHan] 获取 {source_type} 成功: {len(items)} 条")
        return items

    def fetch_vvhan_all(self) -> Dict[str, List[Dict]]:
        """
        获取韩小韩聚合热榜（所有平台）

        Returns:
            按平台分组的新闻字典
        """
        url = "https://api.vvhan.com/api/hotlist/all"
        data = self._request(url)

        if not data or not data.get("success"):
            print("[VVHan] 获取聚合热榜失败")
            return {}

        result = {}
        for platform, items in data.get("data", {}).items():
            platform_items = []
            for idx, item in enumerate(items, 1):
                title = item.get("title", "").strip()
                if not title:
                    continue
                platform_items.append({
                    "title": title,
                    "url": item.get("url", ""),
                    "rank": idx,
                    "hot": item.get("hot", ""),
                })
            if platform_items:
                result[platform] = platform_items

        print(f"[VVHan] 获取聚合热榜成功: {len(result)} 个平台")
        return result

    def fetch_dailyhot(self, source_id: Optional[str] = None) -> Dict[str, List[Dict]]:
        """
        获取 DailyHot API 数据

        Args:
            source_id: 指定平台 ID（可选，不指定则获取所有）

        Returns:
            按平台分组的新闻字典
        """
        if source_id:
            url = f"https://api.codelife.cc/api/top/list?lang=zh&id={source_id}"
        else:
            url = "https://api.codelife.cc/api/top/list?lang=zh"

        data = self._request(url)

        if not data or data.get("code") != 200:
            print(f"[DailyHot] 获取数据失败")
            return {}

        result = {}
        items_data = data.get("data", [])

        # 如果是单个平台
        if source_id and isinstance(items_data, list):
            platform_items = []
            for idx, item in enumerate(items_data, 1):
                title = item.get("title", "").strip()
                if not title:
                    continue
                platform_items.append({
                    "title": title,
                    "url": item.get("url", ""),
                    "rank": idx,
                    "hot": item.get("hot", ""),
                })
            result[source_id] = platform_items
        # 如果是多个平台
        elif isinstance(items_data, dict):
            for platform, items in items_data.items():
                platform_items = []
                for idx, item in enumerate(items, 1):
                    title = item.get("title", "").strip()
                    if not title:
                        continue
                    platform_items.append({
                        "title": title,
                        "url": item.get("url", ""),
                        "rank": idx,
                        "hot": item.get("hot", ""),
                    })
                if platform_items:
                    result[platform] = platform_items

        print(f"[DailyHot] 获取成功: {sum(len(v) for v in result.values())} 条")
        return result

    # =========================================================================
    # 国际新闻 API
    # =========================================================================

    def fetch_newsapi(
        self,
        api_key: str,
        country: str = "us",
        category: Optional[str] = None,
        page_size: int = 50,
    ) -> List[Dict]:
        """
        获取 NewsAPI.org 数据

        Args:
            api_key: API 密钥
            country: 国家代码 (us, gb, cn, jp 等)
            category: 分类 (business, technology, science 等)
            page_size: 返回数量（最大 100）

        Returns:
            新闻列表
        """
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            "apiKey": api_key,
            "country": country,
            "pageSize": min(page_size, 100),
        }
        if category:
            params["category"] = category

        data = self._request(url, params=params)

        if not data or data.get("status") != "ok":
            print(f"[NewsAPI] 获取失败: {data.get('message', '未知错误') if data else '请求失败'}")
            return []

        items = []
        for idx, article in enumerate(data.get("articles", []), 1):
            title = article.get("title", "").strip()
            if not title or title == "[Removed]":
                continue
            items.append({
                "title": title,
                "url": article.get("url", ""),
                "rank": idx,
                "source": article.get("source", {}).get("name", ""),
                "published_at": article.get("publishedAt", ""),
                "description": article.get("description", ""),
            })

        print(f"[NewsAPI] 获取成功: {len(items)} 条")
        return items

    def fetch_gnews(
        self,
        api_key: str,
        country: str = "us",
        category: str = "general",
        max_results: int = 50,
        lang: str = "en",
    ) -> List[Dict]:
        """
        获取 GNews API 数据

        Args:
            api_key: API 密钥
            country: 国家代码
            category: 分类 (general, world, nation, business, technology 等)
            max_results: 返回数量（最大 100）
            lang: 语言代码

        Returns:
            新闻列表
        """
        url = "https://gnews.io/api/v4/top-headlines"
        params = {
            "apikey": api_key,
            "country": country,
            "category": category,
            "max": min(max_results, 100),
            "lang": lang,
        }

        data = self._request(url, params=params)

        if not data or "articles" not in data:
            print(f"[GNews] 获取失败")
            return []

        items = []
        for idx, article in enumerate(data.get("articles", []), 1):
            title = article.get("title", "").strip()
            if not title:
                continue
            items.append({
                "title": title,
                "url": article.get("url", ""),
                "rank": idx,
                "source": article.get("source", {}).get("name", ""),
                "published_at": article.get("publishedAt", ""),
                "description": article.get("description", ""),
            })

        print(f"[GNews] 获取成功: {len(items)} 条")
        return items

    def fetch_mediastack(
        self,
        api_key: str,
        countries: str = "us",
        categories: Optional[str] = None,
        limit: int = 50,
        languages: str = "en",
    ) -> List[Dict]:
        """
        获取 MediaStack API 数据

        Args:
            api_key: API 密钥
            countries: 国家代码（逗号分隔）
            categories: 分类（逗号分隔，如 business,technology）
            limit: 返回数量（免费版最大 100）
            languages: 语言代码

        Returns:
            新闻列表
        """
        url = "http://api.mediastack.com/v1/news"
        params = {
            "access_key": api_key,
            "countries": countries,
            "limit": min(limit, 100),
            "languages": languages,
        }
        if categories:
            params["categories"] = categories

        data = self._request(url, params=params)

        if not data or "data" not in data:
            error = data.get("error", {}).get("message", "未知错误") if data else "请求失败"
            print(f"[MediaStack] 获取失败: {error}")
            return []

        items = []
        for idx, article in enumerate(data.get("data", []), 1):
            title = article.get("title", "").strip()
            if not title:
                continue
            items.append({
                "title": title,
                "url": article.get("url", ""),
                "rank": idx,
                "source": article.get("source", ""),
                "published_at": article.get("published_at", ""),
                "description": article.get("description", ""),
            })

        print(f"[MediaStack] 获取成功: {len(items)} 条")
        return items

    def fetch_thenewsapi(
        self,
        api_key: str,
        locale: str = "us",
        language: str = "en",
        limit: int = 50,
    ) -> List[Dict]:
        """
        获取 TheNewsAPI 数据

        Args:
            api_key: API 密钥
            locale: 地区代码
            language: 语言代码
            limit: 返回数量

        Returns:
            新闻列表
        """
        url = "https://api.thenewsapi.com/v1/news/top"
        params = {
            "api_token": api_key,
            "locale": locale,
            "language": language,
            "limit": min(limit, 50),
        }

        data = self._request(url, params=params)

        if not data or "data" not in data:
            print(f"[TheNewsAPI] 获取失败")
            return []

        items = []
        for idx, article in enumerate(data.get("data", []), 1):
            title = article.get("title", "").strip()
            if not title:
                continue
            items.append({
                "title": title,
                "url": article.get("url", ""),
                "rank": idx,
                "source": article.get("source", ""),
                "published_at": article.get("published_at", ""),
                "description": article.get("description", ""),
            })

        print(f"[TheNewsAPI] 获取成功: {len(items)} 条")
        return items

    # =========================================================================
    # 批量获取
    # =========================================================================

    def crawl_extra_sources(
        self,
        config: Dict,
        request_interval: int = 1000,
    ) -> Tuple[Dict[str, List[Dict]], List[str]]:
        """
        根据配置批量获取额外数据源

        Args:
            config: 额外数据源配置
            request_interval: 请求间隔（毫秒）

        Returns:
            (结果字典, 失败列表)
        """
        results = {}
        failed = []

        sources = config.get("sources", [])

        for source in sources:
            if not source.get("enabled", True):
                continue

            source_type = source.get("type", "")
            source_id = source.get("id", "")
            source_name = source.get("name", source_id)

            try:
                items = []

                # 国内热榜
                if source_type == "vvhan":
                    platform = source.get("platform", "")
                    if platform == "all":
                        all_data = self.fetch_vvhan_all()
                        for platform_name, platform_items in all_data.items():
                            results[f"vvhan-{platform_name}"] = platform_items
                        continue
                    else:
                        items = self.fetch_vvhan_hotlist(platform)

                elif source_type == "dailyhot":
                    platform = source.get("platform")
                    all_data = self.fetch_dailyhot(platform)
                    for platform_name, platform_items in all_data.items():
                        results[f"dailyhot-{platform_name}"] = platform_items
                    continue

                # 国际新闻
                elif source_type == "newsapi":
                    items = self.fetch_newsapi(
                        api_key=source.get("api_key", ""),
                        country=source.get("country", "us"),
                        category=source.get("category"),
                        page_size=source.get("page_size", 50),
                    )

                elif source_type == "gnews":
                    items = self.fetch_gnews(
                        api_key=source.get("api_key", ""),
                        country=source.get("country", "us"),
                        category=source.get("category", "general"),
                        max_results=source.get("max_results", 50),
                        lang=source.get("lang", "en"),
                    )

                elif source_type == "mediastack":
                    items = self.fetch_mediastack(
                        api_key=source.get("api_key", ""),
                        countries=source.get("countries", "us"),
                        categories=source.get("categories"),
                        limit=source.get("limit", 50),
                        languages=source.get("languages", "en"),
                    )

                elif source_type == "thenewsapi":
                    items = self.fetch_thenewsapi(
                        api_key=source.get("api_key", ""),
                        locale=source.get("locale", "us"),
                        language=source.get("language", "en"),
                        limit=source.get("limit", 50),
                    )

                else:
                    print(f"[ExtraAPI] 未知数据源类型: {source_type}")
                    failed.append(source_id)
                    continue

                if items:
                    results[source_id] = items
                else:
                    failed.append(source_id)

            except Exception as e:
                print(f"[ExtraAPI] 获取 {source_name} 失败: {e}")
                failed.append(source_id)

            # 请求间隔
            time.sleep(request_interval / 1000)

        return results, failed
