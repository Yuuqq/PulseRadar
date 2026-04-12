# coding=utf-8

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


def _write_yaml(tmp_dir: Path, content: str) -> Path:
    p = tmp_dir / "config.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def test_from_yaml_loads_minimal_config():
    from trendradar.models.config import TrendRadarConfig

    Path(".pytest_tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=".pytest_tmp") as tmp:
        config_path = _write_yaml(
            Path(tmp),
            """
app:
  timezone: "UTC"
platforms:
  enabled: true
  sources:
    - id: test_src
      name: Test Source
""".lstrip(),
        )
        cfg = TrendRadarConfig.from_yaml(config_path)
        assert cfg.app.timezone == "UTC"
        assert len(cfg.platforms.sources) == 1
        assert cfg.platforms.sources[0].id == "test_src"


def test_from_yaml_loads_actual_project_config():
    from trendradar.models.config import TrendRadarConfig

    project_config = Path("D:\\AI_empower\\TrendRadar\\config\\config.yaml")
    if not project_config.exists():
        pytest.skip("Project config.yaml not found")

    cfg = TrendRadarConfig.from_yaml(project_config)
    assert isinstance(cfg, TrendRadarConfig)
    assert cfg.app.timezone  # Should have a timezone value


def test_from_yaml_missing_file_raises_error():
    from trendradar.models.config import TrendRadarConfig

    with pytest.raises(FileNotFoundError):
        TrendRadarConfig.from_yaml("/nonexistent/path/config.yaml")


def test_from_yaml_empty_file_uses_defaults():
    from trendradar.models.config import TrendRadarConfig

    Path(".pytest_tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=".pytest_tmp") as tmp:
        config_path = _write_yaml(Path(tmp), "")
        cfg = TrendRadarConfig.from_yaml(config_path)
        # All defaults should be applied
        assert cfg.app.timezone == "Asia/Shanghai"
        assert cfg.report.mode == "current"
        assert cfg.storage.backend == "auto"


def test_env_var_overrides(monkeypatch):
    from trendradar.models.config import TrendRadarConfig

    monkeypatch.setenv("TIMEZONE", "America/New_York")
    monkeypatch.setenv("AI_API_KEY", "test-secret-key")
    monkeypatch.setenv("CRAWLER_API_URL", "http://my-crawler/api")

    Path(".pytest_tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=".pytest_tmp") as tmp:
        config_path = _write_yaml(
            Path(tmp),
            """
app:
  timezone: "Asia/Shanghai"
ai:
  api_key: "original-key"
advanced:
  crawler:
    api_url: "http://original/api"
""".lstrip(),
        )
        cfg = TrendRadarConfig.from_yaml(config_path)
        assert cfg.app.timezone == "America/New_York"
        assert cfg.ai.api_key == "test-secret-key"
        assert cfg.advanced.crawler.api_url == "http://my-crawler/api"


def test_to_dict_returns_dict_with_expected_keys():
    from trendradar.models.config import TrendRadarConfig

    cfg = TrendRadarConfig()
    d = cfg.to_dict()
    assert isinstance(d, dict)

    expected_keys = {
        "advanced", "ai", "ai_analysis", "ai_translation",
        "app", "display", "extra_apis", "notification",
        "platforms", "report", "rss", "storage",
    }
    assert expected_keys.issubset(set(d.keys())), (
        f"Missing keys: {expected_keys - set(d.keys())}"
    )


def test_to_dict_nested_values():
    from trendradar.models.config import TrendRadarConfig

    cfg = TrendRadarConfig()
    d = cfg.to_dict()

    # Check nested structure preserved
    assert "formats" in d["storage"]
    assert "html" in d["storage"]["formats"]
    assert d["storage"]["formats"]["html"] is True


def test_default_construction_without_yaml():
    from trendradar.models.config import TrendRadarConfig

    cfg = TrendRadarConfig()
    assert cfg.report.rank_threshold == 5
    assert cfg.advanced.max_accounts_per_channel == 3
    assert cfg.notification.enabled is True
    assert cfg.ai_analysis.enabled is True
