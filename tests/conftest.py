# coding=utf-8

from __future__ import annotations

# Ensure `import trendradar` works even when pytest uses importlib import mode.
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Phase 2 shared fixture library (TEST-04)
# ---------------------------------------------------------------------------
from typing import Any, Dict

import pytest


@pytest.fixture
def mock_config(tmp_path) -> Dict[str, Any]:
    """Minimal-valid config dict matching trendradar load_config() UPPERCASE shape.

    Per D-18: function-scoped, returns a fresh dict each call. Individual tests
    override via dict.update() or by copy.deepcopy + mutate before passing in.
    """
    return {
        "TIMEZONE": "UTC",
        "RANK_THRESHOLD": 50,
        "WEIGHT_CONFIG": {},
        "PLATFORMS": [],
        "RSS": {"ENABLED": False, "FEEDS": []},
        "DISPLAY_MODE": "keyword",
        "DISPLAY": {
            "REGIONS": {"NEW_ITEMS": True, "STANDALONE": False, "RSS": False},
            "REGION_ORDER": ["hotlist"],
        },
        "REPORT_MODE": "daily",
        "REQUEST_INTERVAL": 1000,
        "STORAGE": {
            "BACKEND": "local",
            "FORMATS": {"TXT": False, "HTML": False},
            "LOCAL": {"DATA_DIR": str(tmp_path / "output"), "RETENTION_DAYS": 0},
            "REMOTE": {},
            "PULL": {"ENABLED": False, "DAYS": 0},
        },
        "AI": {
            "MODEL": "test/test",
            "API_KEY": "fake-key",
            "API_BASE": "",
            "TIMEOUT": 5,
            "MAX_TOKENS": 100,
        },
        "AI_ANALYSIS": {"ENABLED": False},
        "AI_TRANSLATION": {"ENABLED": False},
        "SHOW_VERSION_UPDATE": False,
        "MAX_NEWS_PER_KEYWORD": 0,
        "MAX_KEYWORDS": 0,
        "SORT_BY_POSITION_FIRST": False,
        "DEBUG": False,
        "FEISHU_MESSAGE_SEPARATOR": "---",
        "FEISHU_BATCH_SIZE": 29000,
        "DINGTALK_BATCH_SIZE": 20000,
        "MESSAGE_BATCH_SIZE": 4000,
    }


@pytest.fixture
def mock_app_context(mock_config):
    """Real AppContext with controlled config and tmp_path-backed SQLite storage.

    Per D-19: instantiates the REAL AppContext class -- tests exercise the real
    wiring; only external I/O (AI client, HTTP) is patched separately.
    """
    from trendradar.context import AppContext
    return AppContext(mock_config)
