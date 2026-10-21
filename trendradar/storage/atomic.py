"""原子写入工具。

报告、快照与数据文件在写入过程中被中断（进程被杀、磁盘写满、容器重启）时，
朴素的 ``open(path, "w")`` 会留下一个被截断的文件；下游的“文件存在即有效”
判断会把半个报告当成完整产物投递出去。

这里统一采用“同目录临时文件 + fsync + os.replace”：
读者要么看到旧文件，要么看到完整的新文件，不存在中间态。

Windows 上 ``os.replace`` 在目标被其他进程短暂持有句柄时会抛
``PermissionError``（WinError 5），属瞬时状态，用有限次退避重试吸收；
重试耗尽后仍抛出，避免把真实的权限问题伪装成成功。

本模块是跨项目共享模板的一份拷贝（同一实现在 newsbreakfast
``core/atomic_io.py``）。这些仓库彼此独立、没有共享依赖，所以选择复制
而非引入跨仓依赖；修改时请同步另一份。
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

PathLike = str | Path

_REPLACE_RETRY_DELAYS = (0.01, 0.02, 0.05, 0.1, 0.2)


def _replace_with_retry(source: Path, target: Path) -> None:
    last_error: OSError | None = None
    for delay in (0.0, *_REPLACE_RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        try:
            os.replace(source, target)
            return
        except PermissionError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error


def write_text_atomic(path: PathLike, text: str, *, encoding: str = "utf-8") -> Path:
    """Write `text` to `path` atomically and return the resolved path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_with_retry(Path(tmp_name), target)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return target


def write_lines_atomic(
    path: PathLike,
    write_body,
    *,
    encoding: str = "utf-8",
) -> Path:
    """Atomically write a file whose content is produced incrementally.

    `write_body` receives a writable text handle and writes into it. This keeps
    the streaming shape of the existing writers (news lists, generated HTML)
    while still publishing the file with a single rename.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as handle:
            write_body(handle)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_with_retry(Path(tmp_name), target)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return target
