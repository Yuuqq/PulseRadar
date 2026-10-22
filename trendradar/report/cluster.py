"""
跨源标题聚类模块

在同一关键词分组内，识别"同一事件被多家来源报道"的标题，
将它们合并成一个 cluster：
- head: 排名最靠前的代表条目，渲染时正常显示，并附 +N sources 徽章
- hidden: 同 cluster 内的其它条目，渲染时跳过（但其文本会进入 head 的搜索 blob）

算法：
- 标题归一化后取 char 3-gram 集合
- 仅在不同来源之间计算 Jaccard 相似度（同源不同标题视为不同事件）
- 阈值 0.55；并查集合并

数据契约：会在每个 title dict 上注入：
- cluster_role: "head" | "hidden"   （未聚合的不写）
- cluster_sources: list[{source_name, title, url}]   仅 head 才有
- cluster_count: int                                  仅 head 才有，含自身的去重源数
"""

from __future__ import annotations

import re

_NORMALIZE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[\W_]+", re.UNICODE)
DEFAULT_THRESHOLD = 0.55
NGRAM_N = 3


def _normalize(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    text = text.lower()
    text = _PUNCT_RE.sub("", text)
    text = _NORMALIZE_RE.sub("", text)
    return text


def _ngrams(text: str, n: int = NGRAM_N) -> set[str]:
    norm = _normalize(text)
    if not norm:
        return set()
    if len(norm) <= n:
        return {norm}
    return {norm[i : i + n] for i in range(len(norm) - n + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / len(a | b)


def cluster_titles(titles: list[dict], threshold: float = DEFAULT_THRESHOLD) -> list[dict]:
    """对一个关键词组内的标题列表做就地聚类标注。

    返回值就是原列表（已就地修改），便于链式调用。
    若 titles 长度 < 2，原样返回。
    """
    n = len(titles)
    if n < 2:
        return titles

    sigs = [_ngrams(t.get("title", "")) for t in titles]

    # 并查集
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(n):
        if not sigs[i]:
            continue
        for j in range(i + 1, n):
            if not sigs[j]:
                continue
            # 同源标题不合并：同一平台的两条不同标题通常就是两件事
            if titles[i].get("source_name") == titles[j].get("source_name"):
                continue
            if _jaccard(sigs[i], sigs[j]) >= threshold:
                union(i, j)

    groups: dict[int, list[int]] = {}
    for idx in range(n):
        groups.setdefault(find(idx), []).append(idx)

    for members in groups.values():
        if len(members) <= 1:
            continue
        # 至少要跨 2 家来源才算 cluster
        sources_in_group = {titles[m].get("source_name", "") for m in members}
        if len(sources_in_group) < 2:
            continue

        # 选 head：min rank 最小、标题最长（更完整）做 tiebreak
        def _head_key(idx: int) -> tuple[int, int]:
            t = titles[idx]
            ranks = t.get("ranks") or []
            min_r = min(ranks) if ranks else 9999
            return (min_r, -len(t.get("title") or ""))

        members.sort(key=_head_key)
        head_idx = members[0]
        head = titles[head_idx]
        head["cluster_role"] = "head"
        head["cluster_sources"] = []
        seen = {head.get("source_name", "")}

        for m_idx in members[1:]:
            m = titles[m_idx]
            m["cluster_role"] = "hidden"
            src = m.get("source_name", "")
            if src in seen:
                continue
            seen.add(src)
            head["cluster_sources"].append(
                {
                    "source_name": src,
                    "title": m.get("title", ""),
                    "url": m.get("mobile_url") or m.get("url", ""),
                }
            )

        head["cluster_count"] = len(seen)

    return titles


def cluster_stats(stats: list[dict], threshold: float = DEFAULT_THRESHOLD) -> list[dict]:
    """对 prepare_report_data 输出的 processed_stats 逐组聚类。"""
    for stat in stats:
        cluster_titles(stat.get("titles", []), threshold=threshold)
    return stats
