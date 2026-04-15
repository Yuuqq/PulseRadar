from __future__ import annotations

import tempfile
from pathlib import Path


def _write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def test_load_config_reads_crawler_api_url_and_ai_extra_params(monkeypatch):
    # Import inside the test so monkeypatch env is applied before load_config reads it.
    from trendradar.core.loader import load_config

    monkeypatch.delenv("CRAWLER_API_URL", raising=False)
    monkeypatch.delenv("AI_API_BASE", raising=False)

    Path(".pytest_tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=".pytest_tmp") as tmp:
        config_path = _write_yaml(
            Path(tmp),
            """
app:
  timezone: "Asia/Shanghai"

platforms:
  enabled: true
  sources: []

advanced:
  crawler:
    api_url: "http://127.0.0.1:9999/api/s"

ai:
  model: "openai/gpt-4o-mini"
  api_key: "test-key"
  api_base: "http://127.0.0.1:8317/v1"
  extra_params:
    top_p: 0.5
""".lstrip(),
        )

        cfg = load_config(str(config_path))
        assert cfg["CRAWLER_API_URL"] == "http://127.0.0.1:9999/api/s"
        assert cfg["AI"]["EXTRA_PARAMS"] == {"top_p": 0.5}
        assert cfg["AI"]["API_BASE"] == "http://127.0.0.1:8317/v1"

        # Env var override should win over config file.
        monkeypatch.setenv("CRAWLER_API_URL", "http://127.0.0.1:1234/api/s")
        monkeypatch.setenv("AI_API_BASE", "http://127.0.0.1:9999/v1")
        cfg2 = load_config(str(config_path))
        assert cfg2["CRAWLER_API_URL"] == "http://127.0.0.1:1234/api/s"
        assert cfg2["AI"]["API_BASE"] == "http://127.0.0.1:9999/v1"


def test_load_config_allows_zero_int_env_values(monkeypatch):
    from trendradar.core.loader import load_config

    Path(".pytest_tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=".pytest_tmp") as tmp:
        config_path = _write_yaml(
            Path(tmp),
            """
app:
  timezone: "Asia/Shanghai"

platforms:
  enabled: true
  sources: []

report:
  max_news_per_keyword: 5
  max_keywords: 9

advanced:
  max_accounts_per_channel: 3

storage:
  local:
    retention_days: 2
  remote:
    retention_days: 4
  pull:
    days: 7
""".lstrip(),
        )

        monkeypatch.setenv("MAX_NEWS_PER_KEYWORD", "0")
        monkeypatch.setenv("MAX_KEYWORDS", "0")
        monkeypatch.setenv("MAX_ACCOUNTS_PER_CHANNEL", "0")
        monkeypatch.setenv("LOCAL_RETENTION_DAYS", "0")
        monkeypatch.setenv("REMOTE_RETENTION_DAYS", "0")
        monkeypatch.setenv("PULL_DAYS", "0")

        cfg = load_config(str(config_path))

        assert cfg["MAX_NEWS_PER_KEYWORD"] == 0
        assert cfg["MAX_KEYWORDS"] == 0
        assert cfg["MAX_ACCOUNTS_PER_CHANNEL"] == 0
        assert cfg["STORAGE"]["LOCAL"]["RETENTION_DAYS"] == 0
        assert cfg["STORAGE"]["REMOTE"]["RETENTION_DAYS"] == 0
        assert cfg["STORAGE"]["PULL"]["DAYS"] == 0


def test_load_config_handles_empty_yaml_file():
    from trendradar.core.loader import load_config

    Path(".pytest_tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=".pytest_tmp") as tmp:
        config_path = _write_yaml(Path(tmp), "")
        cfg = load_config(str(config_path))

        assert isinstance(cfg, dict)
        assert cfg["PLATFORMS"] == []
