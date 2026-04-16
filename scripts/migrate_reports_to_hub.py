"""
一次性迁移脚本：将 output/html/ 下的历史报告迁移到 reports/ 目录，
构建 manifest.json 并生成 Hub 首页（index.html）。

用法:
    python scripts/migrate_reports_to_hub.py [--source output/html] [--dest reports]
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

# 让脚本能在项目根目录运行时找到 trendradar 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trendradar.report.hub import generate_hub_html
from trendradar.report.manifest import (
    add_report_entry,
    build_report_entry,
    load_manifest,
    save_manifest,
)


def extract_metadata_from_html(html_path: Path) -> dict:
    """从报告 HTML 中提取元数据（mode、title count 等）"""
    content = html_path.read_text(encoding="utf-8", errors="replace")

    # 提取模式 — 从 info-tag span
    mode = "daily"
    mode_match = re.search(r'class="info-tag"[^>]*>\s*(当前榜单|增量分析|全天汇总)', content)
    if mode_match:
        label_to_mode = {"当前榜单": "current", "增量分析": "incremental", "全天汇总": "daily"}
        mode = label_to_mode.get(mode_match.group(1), "daily")

    # 提取总新闻数 — 从 info-tag 中的 "共 N 条"
    total_titles = 0
    total_match = re.search(r"共\s*(\d+)\s*条", content)
    if total_match:
        total_titles = int(total_match.group(1))

    # 提取关键词数 — 从 info-tag 中的 "N 个关键词" 或 topic-tab 计数
    stats_count = 0
    stats_match = re.search(r"(\d+)\s*个关键词", content)
    if stats_match:
        stats_count = int(stats_match.group(1))
    else:
        stats_count = len(re.findall(r'class="topic-tab"', content))

    return {
        "mode": mode,
        "total_titles": total_titles,
        "stats_count": stats_count,
    }


def migrate(source_dir: Path, dest_dir: Path) -> None:
    """扫描 source_dir 下的 {date}/{time}.html，复制到 dest_dir 并构建 manifest"""
    if not source_dir.exists():
        print(f"源目录不存在: {source_dir}")
        return

    manifest = load_manifest(dest_dir / "manifest.json")
    count = 0

    for date_dir in sorted(source_dir.iterdir()):
        if not date_dir.is_dir():
            continue
        date_folder = date_dir.name
        # 跳过 latest 目录
        if date_folder == "latest":
            continue

        for html_file in sorted(date_dir.glob("*.html")):
            if html_file.name == "index.html":
                continue

            time_filename = html_file.stem  # e.g. "03-19"
            metadata = extract_metadata_from_html(html_file)

            # 复制到 dest
            dest_file = dest_dir / date_folder / html_file.name
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(html_file, dest_file)

            # 也写入 latest/{mode}.html
            latest_dir = dest_dir / "latest"
            latest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(html_file, latest_dir / f"{metadata['mode']}.html")

            # 添加到 manifest
            entry = build_report_entry(
                date_folder=date_folder,
                time_filename=time_filename,
                mode=metadata["mode"],
                total_titles=metadata["total_titles"],
                stats_count=metadata["stats_count"],
            )
            manifest = add_report_entry(manifest, entry)
            count += 1
            print(f"  迁移: {date_folder}/{html_file.name} ({metadata['mode']})")

    if count == 0:
        print("未找到可迁移的报告文件")
        return

    # 保存 manifest
    save_manifest(dest_dir / "manifest.json", manifest)
    print(f"\n已写入 manifest.json ({count} 份报告)")

    # 生成 Hub 页面
    hub_html = generate_hub_html(manifest)
    root_index = Path("index.html")
    with open(root_index, "w", encoding="utf-8") as f:
        f.write(hub_html)
    print(f"已生成 Hub 页面: {root_index}")


def main():
    parser = argparse.ArgumentParser(description="迁移历史报告到 GitHub Pages Hub")
    parser.add_argument("--source", default="output/html", help="源报告目录 (default: output/html)")
    parser.add_argument("--dest", default="reports", help="目标报告目录 (default: reports)")
    args = parser.parse_args()

    source = Path(args.source)
    dest = Path(args.dest)
    print(f"迁移: {source} → {dest}")
    migrate(source, dest)


if __name__ == "__main__":
    main()
