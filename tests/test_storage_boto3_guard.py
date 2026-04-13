# coding=utf-8
"""
测试 boto3 可选依赖的缺失检测

验证当 S3 存储已配置但 boto3 未安装时，StorageManager 会产生
包含安装指令的明确错误信息。
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from trendradar.storage.manager import StorageManager


def _block_boto3():
    """Remove boto3/botocore from sys.modules and return (saved, blocker)."""
    saved = {}
    modules_to_block = [
        "boto3", "botocore", "botocore.config",
        "botocore.exceptions", "botocore.session",
    ]

    for mod_name in list(sys.modules.keys()):
        if mod_name == "boto3" or mod_name.startswith("botocore"):
            saved[mod_name] = sys.modules.pop(mod_name)

    if "trendradar.storage.remote" in sys.modules:
        saved["trendradar.storage.remote"] = sys.modules.pop(
            "trendradar.storage.remote"
        )

    blocker = {name: None for name in modules_to_block}
    return saved, blocker


def _restore_modules(saved):
    """Restore previously saved modules."""
    for mod_name, mod in saved.items():
        sys.modules[mod_name] = mod


def _make_remote_manager():
    """Create a StorageManager configured for remote/S3 backend."""
    return StorageManager(
        backend_type="remote",
        remote_config={
            "bucket_name": "test-bucket",
            "access_key_id": "AKID_TEST",
            "secret_access_key": "SECRET_TEST",
            "endpoint_url": "https://s3.example.com",
        },
    )


def test_missing_boto3_raises_with_install_command():
    """配置 S3 存储但未安装 boto3 时，应抛出包含安装命令的 ImportError。"""
    saved, blocker = _block_boto3()

    try:
        with patch.dict("sys.modules", blocker):
            if "trendradar.storage.remote" in sys.modules:
                del sys.modules["trendradar.storage.remote"]

            sm = _make_remote_manager()
            with pytest.raises(ImportError, match=r"pip install trendradar\[s3\]"):
                sm.get_backend()
    finally:
        _restore_modules(saved)


def test_missing_boto3_error_is_bilingual():
    """错误信息应同时包含中文和英文说明。"""
    saved, blocker = _block_boto3()

    try:
        with patch.dict("sys.modules", blocker):
            if "trendradar.storage.remote" in sys.modules:
                del sys.modules["trendradar.storage.remote"]

            sm = _make_remote_manager()
            with pytest.raises(ImportError) as exc_info:
                sm.get_backend()

            msg = str(exc_info.value)
            # Chinese part
            assert "S3 远程存储已配置" in msg
            assert "未安装 boto3" in msg
            # English part
            assert "S3 storage is configured but boto3 is not installed" in msg
            # Directive command
            assert "pip install trendradar[s3]" in msg
    finally:
        _restore_modules(saved)


def test_local_backend_works_without_boto3():
    """未配置 S3 时，即使 boto3 未安装也不应报错。"""
    sm = StorageManager(
        backend_type="local",
        data_dir="output",
    )
    backend = sm.get_backend()
    assert backend is not None
    assert backend.backend_name == "local"
    sm.cleanup()
