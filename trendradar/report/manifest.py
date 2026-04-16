"""
报告清单（manifest）管理模块

提供 GitHub Pages 报告索引的 CRUD 操作：
- load_manifest: 读取 manifest.json
- save_manifest: 写入 manifest.json
- add_report_entry: 追加报告条目（不可变）
- build_report_entry: 构建单条报告元数据
"""

import json
from datetime import datetime, timezone
from pathlib import Path

MODE_LABELS: dict[str, str] = {
    "current": "当前榜单",
    "daily": "全天汇总",
    "incremental": "增量分析",
}


def load_manifest(path: Path) -> dict:
    """读取 manifest.json，文件缺失时返回空结构"""
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"version": 1, "generated_at": "", "reports": []}


def save_manifest(path: Path, data: dict) -> None:
    """写入 manifest.json（indent=2, ensure_ascii=False）"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_report_entry(manifest: dict, entry: dict) -> dict:
    """返回新 manifest，追加 entry 并按 path 去重（保留最新）"""
    existing = [r for r in manifest.get("reports", []) if r.get("path") != entry.get("path")]
    return {
        **manifest,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reports": [*existing, entry],
    }


def build_report_entry(
    date_folder: str,
    time_filename: str,
    mode: str,
    total_titles: int,
    stats_count: int,
    generated_at: str | None = None,
) -> dict:
    """构建单条报告元数据"""
    time_display = time_filename.replace("-", ":")
    return {
        "date": date_folder,
        "time": time_display,
        "mode": mode,
        "mode_label": MODE_LABELS.get(mode, mode),
        "total_titles": total_titles,
        "stats_count": stats_count,
        "path": f"reports/{date_folder}/{time_filename}.html",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
    }
