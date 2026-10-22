"""
Atom feeds 生成模块

为最近一期报告生成静态 Atom feeds：
- ``reports/feed.xml``           —— 全站最新（取所有 cluster head / 单条标题前 N 条）
- ``reports/feeds/<slug>.xml``   —— 按关键词订阅
- ``reports/feeds/index.json``   —— 关键词 ↔ slug ↔ url 映射，便于发现 / 订阅 UI 使用

设计：
- 仅消费 cluster head 与未聚合条目（与页面渲染口径一致）
- entry id 用 ``urn:pulseradar:<date>:<sha1[:16](source::title)>`` 保持稳定
- 使用 stdlib（hashlib / xml.sax.saxutils），无新依赖
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape

SITE_URL = "https://pulseradar.aisbest.eu.cc"
GLOBAL_LIMIT = 80
PER_KEYWORD_LIMIT = 30
_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _x(text: str) -> str:
    """XML 文本安全转义。"""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return _xml_escape(text, {'"': "&quot;", "'": "&apos;"})


def slugify(keyword: str) -> str:
    """生成 URL-safe slug；含非 ASCII 字符则回退为短哈希。"""
    if not keyword:
        return "untitled"
    if all(ord(c) < 128 for c in keyword):
        s = _SLUG_NON_ALNUM.sub("-", keyword.lower()).strip("-")
        if s:
            return s
    return "kw-" + hashlib.sha1(keyword.encode("utf-8")).hexdigest()[:10]


def _entry_id(title: str, source: str, date_part: str) -> str:
    h = hashlib.sha1(f"{source}::{title}".encode("utf-8")).hexdigest()[:16]
    return f"urn:pulseradar:{date_part}:{h}"


def _atom_entry(title_data: dict, updated_iso: str) -> str:
    title = title_data.get("title", "") or ""
    source = title_data.get("source_name", "") or ""
    url = title_data.get("mobile_url") or title_data.get("url") or SITE_URL
    eid = _entry_id(title, source, updated_iso[:10])

    summary_lines: list[str] = []
    if title_data.get("cluster_role") == "head":
        members = title_data.get("cluster_sources") or []
        if members:
            others = [m.get("source_name", "") for m in members if m.get("source_name")]
            if others:
                summary_lines.append("Also reported by: " + ", ".join(others))
    ranks = title_data.get("ranks") or []
    if ranks:
        summary_lines.append(f"Rank: {min(ranks)}")
    summary = "\n".join(summary_lines)

    return (
        "  <entry>\n"
        f"    <id>{_x(eid)}</id>\n"
        f"    <title>{_x(title)}</title>\n"
        f'    <link rel="alternate" type="text/html" href="{_x(url)}"/>\n'
        f"    <updated>{updated_iso}</updated>\n"
        f"    <author><name>{_x(source)}</name></author>\n"
        f"    <summary>{_x(summary)}</summary>\n"
        "  </entry>"
    )


def _build_feed(
    entries: list[str],
    *,
    title: str,
    self_link: str,
    alternate_link: str,
    updated_iso: str,
    subtitle: str = "",
) -> str:
    feed_id = "urn:pulseradar:feed:" + hashlib.sha1(self_link.encode("utf-8")).hexdigest()[:12]
    subtitle_xml = f"\n  <subtitle>{_x(subtitle)}</subtitle>" if subtitle else ""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        f"  <title>{_x(title)}</title>{subtitle_xml}\n"
        f'  <link rel="self" type="application/atom+xml" href="{_x(self_link)}"/>\n'
        f'  <link rel="alternate" type="text/html" href="{_x(alternate_link)}"/>\n'
        f"  <updated>{updated_iso}</updated>\n"
        f"  <id>{feed_id}</id>\n"
        "  <author><name>PulseRadar</name></author>\n"
        f"{chr(10).join(entries)}\n"
        "</feed>\n"
    )


def collect_visible_titles(stats: list[dict]) -> list[tuple[str, dict]]:
    """从 processed_stats 中收集可见条目（cluster head + 未聚合）。"""
    out: list[tuple[str, dict]] = []
    for stat in stats:
        kw = stat.get("word", "") or ""
        for title_data in stat.get("titles") or []:
            if title_data.get("cluster_role") == "hidden":
                continue
            out.append((kw, title_data))
    return out


def write_feeds(pages_dir: Path | str, stats: list[dict], now: datetime | None = None) -> dict:
    """生成全站 + 各关键词的 Atom feeds，并写入 index.json。

    返回值：``{slug: {keyword, count, url}}`` 映射，便于调用方做 logging。
    """
    pages_dir = Path(pages_dir)
    feeds_dir = pages_dir / "feeds"
    feeds_dir.mkdir(parents=True, exist_ok=True)

    now = now or datetime.now(timezone.utc)
    updated = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    pairs = collect_visible_titles(stats)

    # 全站
    global_entries = [_atom_entry(t, updated) for _, t in pairs[:GLOBAL_LIMIT]]
    global_xml = _build_feed(
        global_entries,
        title="PulseRadar — Latest",
        subtitle="Cross-source aggregated headlines",
        self_link=f"{SITE_URL}/reports/feed.xml",
        alternate_link=f"{SITE_URL}/",
        updated_iso=updated,
    )
    (pages_dir / "feed.xml").write_text(global_xml, encoding="utf-8")

    # 按关键词
    by_kw: dict[str, list[dict]] = {}
    for kw, t in pairs:
        by_kw.setdefault(kw, []).append(t)

    mapping: dict[str, dict] = {}
    used_slugs: set[str] = set()
    for kw, items in by_kw.items():
        slug = slugify(kw)
        # 同 slug 冲突保护（极少见）
        if slug in used_slugs:
            slug = slug + "-" + hashlib.sha1(kw.encode("utf-8")).hexdigest()[:6]
        used_slugs.add(slug)

        entries = [_atom_entry(t, updated) for t in items[:PER_KEYWORD_LIMIT]]
        xml = _build_feed(
            entries,
            title=f"PulseRadar — {kw}",
            subtitle=f"Subscribe to keyword: {kw}",
            self_link=f"{SITE_URL}/reports/feeds/{slug}.xml",
            alternate_link=f"{SITE_URL}/",
            updated_iso=updated,
        )
        (feeds_dir / f"{slug}.xml").write_text(xml, encoding="utf-8")
        mapping[slug] = {
            "keyword": kw,
            "count": len(items),
            "url": f"/reports/feeds/{slug}.xml",
        }

    # 发现用 index.json
    (feeds_dir / "index.json").write_text(
        json.dumps(
            {"updated": updated, "global": "/reports/feed.xml", "feeds": mapping},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return mapping
