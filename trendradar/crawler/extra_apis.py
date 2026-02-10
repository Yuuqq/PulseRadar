# coding=utf-8
"""
额外数据源 API 模块

支持多种免费/开放的新闻 API：
1. 国内热榜聚合 (VVHan, DailyHot)
2. 国际新闻 API (NewsAPI, GNews, MediaStack, TheNewsAPI)
"""

import html
import json
import time
import random
import re
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

    DAILYHOT_IMSYY_BASE = "https://api-hot.imsyy.top"
    DAILYHOT_BASE = "https://api.codelife.cc/api/top/list"
    DAILYHOT_DEFAULT_PLATFORMS = (
        "toutiao",
        "weibo",
        "zhihu",
        "baidu",
        "bilibili",
        "douyin",
    )

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
        self.last_error: Optional[str] = None

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
        response = None
        self.last_error = None
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
            error_detail = str(e)
            if response is not None:
                try:
                    error_detail = f"HTTP {response.status_code}: {response.text[:200]}"
                except Exception:
                    pass
            self.last_error = error_detail
            print(f"请求失败 {url}: {error_detail}")
            return None

    def _request_text(
        self,
        url: str,
        timeout: int = 15,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Optional[str]:
        """发送 HTTP 请求并返回文本响应"""
        response = None
        self.last_error = None
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
            return response.text
        except Exception as e:
            error_detail = str(e)
            if response is not None:
                try:
                    error_detail = f"HTTP {response.status_code}: {response.text[:200]}"
                except Exception:
                    pass
            self.last_error = error_detail
            print(f"请求失败 {url}: {error_detail}")
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
        def normalize_items(items: List[Dict], fallback_key: str) -> Dict[str, List[Dict]]:
            platform_items = []
            for idx, item in enumerate(items, 1):
                title = str(item.get("title") or item.get("name") or "").strip()
                if not title:
                    continue
                platform_items.append({
                    "title": title,
                    "url": item.get("url") or item.get("link") or "",
                    "rank": item.get("index") or item.get("rank") or idx,
                    "hot": item.get("hot") or item.get("hotValue") or item.get("value") or "",
                })
            return {fallback_key: platform_items} if platform_items else {}

        def parse_payload(payload: Optional[Dict], fallback_key: str) -> Dict[str, List[Dict]]:
            if not payload or payload.get("code") != 200:
                return {}
            items_data = payload.get("data")
            if not items_data:
                return {}
            if isinstance(items_data, list):
                return normalize_items(items_data, fallback_key)
            if isinstance(items_data, dict):
                result: Dict[str, List[Dict]] = {}
                for platform, items in items_data.items():
                    if isinstance(items, list):
                        normalized = normalize_items(items, platform)
                        if normalized:
                            result.update(normalized)
                return result
            return {}

        params = {"lang": "zh", "size": 50}
        if source_id:
            params["id"] = source_id
        payload = self._request(self.DAILYHOT_BASE, params=params)
        result = parse_payload(payload, source_id or "dailyhot")

        if not result and not source_id:
            for platform in self.DAILYHOT_DEFAULT_PLATFORMS:
                params = {"lang": "zh", "id": platform, "size": 50}
                payload = self._request(self.DAILYHOT_BASE, params=params)
                platform_result = parse_payload(payload, platform)
                if platform_result:
                    result.update(platform_result)

        if not result:
            print("[DailyHot] 获取数据失败")
            return {}

        print(f"[DailyHot] 获取成功: {sum(len(v) for v in result.values())} 条")
        return result

    def fetch_eastmoney_kuaixun(
        self,
        channel: str = "102",
        page_size: int = 50,
        page: int = 1,
    ) -> List[Dict]:
        """
        获取东方财富 7x24 快讯

        Args:
            channel: 频道 ID（默认 102）
            page_size: 单页数量
            page: 页码

        Returns:
            新闻列表
        """
        url = f"https://newsapi.eastmoney.com/kuaixun/v1/getlist_{channel}_ajaxResult_{page_size}_{page}_.html"
        content = self._request_text(url)

        if not content:
            print("[Eastmoney] 获取数据失败")
            return []

        raw = content.strip()
        if raw.startswith("var"):
            if "=" in raw:
                raw = raw.split("=", 1)[1].strip()
            raw = raw.rstrip(";")

        try:
            data = json.loads(raw)
        except Exception as e:
            self.last_error = str(e)
            print(f"[Eastmoney] 解析失败: {e}")
            return []

        if str(data.get("rc")) != "1":
            print("[Eastmoney] 获取数据失败")
            return []

        items = []
        for idx, item in enumerate(data.get("LivesList", []), 1):
            title = str(item.get("title") or item.get("simtitle") or "").strip()
            if not title:
                continue
            items.append({
                "title": title,
                "url": item.get("url_w") or item.get("url_unique") or item.get("url_m") or "",
                "rank": idx,
                "hot": item.get("sort") or item.get("newstype") or "",
                "published_at": item.get("showtime") or item.get("ordertime") or "",
            })

        print(f"[Eastmoney] 获取成功: {len(items)} 条")
        return items

    def fetch_wallstreetcn_live(
        self,
        channel: str = "global-channel",
        limit: int = 50,
    ) -> List[Dict]:
        """
        获取华尔街见闻实时快讯

        Args:
            channel: 频道 (global-channel/stock-channel/forex-channel 等)
            limit: 返回数量

        Returns:
            新闻列表
        """
        url = "https://api-prod.wallstreetcn.com/apiv1/content/lives"
        params = {"channel": channel, "limit": max(1, min(limit, 100))}

        data = self._request(url, params=params)
        if not data or data.get("code") != 20000:
            print("[Wallstreetcn] 获取失败")
            return []

        items = []
        for idx, item in enumerate(data.get("data", {}).get("items", []), 1):
            title = item.get("title") or item.get("content_text") or ""
            title = str(title).replace("\n", " ").strip()
            if not title:
                continue
            live_id = item.get("id")
            url = f"https://wallstreetcn.com/live/{live_id}" if live_id else ""
            items.append({
                "title": title,
                "url": url,
                "rank": idx,
                "hot": item.get("score") or "",
                "published_at": item.get("display_time") or "",
            })

        print(f"[Wallstreetcn] 获取成功: {len(items)} 条")
        return items

    def fetch_10jqka_finance_news(
        self,
        page_url: str = "https://news.10jqka.com.cn/clientinfo/finance.html",
        max_items: int = 50,
        encoding: str = "gbk",
    ) -> List[Dict]:
        """
        获取同花顺资讯（财经头条）

        Args:
            page_url: 资讯页 URL
            max_items: 最大条数
            encoding: 页面编码

        Returns:
            新闻列表
        """
        response = None
        self.last_error = None
        try:
            headers = {**self.DEFAULT_HEADERS}
            headers.update({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://news.10jqka.com.cn/",
            })
            response = self.session.get(
                page_url,
                headers=headers,
                proxies=self._get_proxies(),
                timeout=15,
            )
            response.raise_for_status()
            content = response.content
            if encoding:
                text = content.decode(encoding, errors="ignore")
            else:
                text = response.text
        except Exception as e:
            error_detail = str(e)
            if response is not None:
                try:
                    error_detail = f"HTTP {response.status_code}: {response.text[:200]}"
                except Exception:
                    pass
            self.last_error = error_detail
            print(f"[10jqka] 获取失败: {error_detail}")
            return []

        def clean_text(raw: str) -> str:
            cleaned = re.sub(r"<[^>]+>", "", raw)
            return html.unescape(cleaned).strip()

        items: List[Dict] = []
        blocks = text.split('<div class="article"')
        for block in blocks:
            if "article-time" not in block:
                continue
            time_match = re.search(r'article-time[^>]*>\s*([^<]+)', block, re.I)
            url_match = re.search(r"openbrower\('([^']+)'", block, re.I)
            title_match = re.search(r"<strong>\s*<a[^>]*>(.*?)</a>", block, re.I | re.S)

            if not url_match or not title_match:
                continue

            url = url_match.group(1).strip()
            title = clean_text(title_match.group(1))
            if not title:
                continue

            published_at = clean_text(time_match.group(1)) if time_match else ""

            items.append({
                "title": title,
                "url": url,
                "rank": len(items) + 1,
                "hot": "",
                "published_at": published_at,
            })

            if max_items and len(items) >= max_items:
                break

        print(f"[10jqka] 获取成功: {len(items)} 条")
        return items

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

                elif source_type == "eastmoney":
                    items = self.fetch_eastmoney_kuaixun(
                        channel=str(source.get("channel", "102")),
                        page_size=int(source.get("page_size", 50) or 50),
                        page=int(source.get("page", 1) or 1),
                    )

                elif source_type == "wallstreetcn":
                    items = self.fetch_wallstreetcn_live(
                        channel=source.get("channel", "global-channel"),
                        limit=int(source.get("limit", 50) or 50),
                    )

                elif source_type == "10jqka":
                    items = self.fetch_10jqka_finance_news(
                        page_url=source.get("url", "https://news.10jqka.com.cn/clientinfo/finance.html"),
                        max_items=int(source.get("max_items", 50) or 50),
                        encoding=source.get("encoding", "gbk"),
                    )

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
