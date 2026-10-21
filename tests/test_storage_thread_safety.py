"""Cross-thread behaviour of the SQLite storage backends.

sqlite3 connections are thread-affine; the web UI serves requests from many
threads against one shared backend instance.
"""

from __future__ import annotations

import threading

from trendradar.storage.local import LocalStorageBackend


def test_connection_cache_is_per_thread(tmp_path):
    backend = LocalStorageBackend(
        data_dir=str(tmp_path), enable_txt=False, enable_html=False, timezone="UTC"
    )
    main_conn = backend._get_connection()

    seen: list[object] = []

    def worker() -> None:
        seen.append(backend._get_connection())

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert len(seen) == 1
    assert seen[0] is not main_conn
    assert len(backend._db_connections) == 2


def test_reads_from_another_thread_are_not_swallowed(tmp_path):
    """A cross-thread ProgrammingError must not turn into a silent empty result."""
    backend = LocalStorageBackend(
        data_dir=str(tmp_path), enable_txt=False, enable_html=False, timezone="UTC"
    )
    backend._get_connection()

    result: list[list[str]] = []
    thread = threading.Thread(target=lambda: result.append(backend.get_crawl_times()))
    thread.start()
    thread.join()

    assert result == [[]]
    assert len(backend._db_connections) == 2


def test_cleanup_closes_every_thread_connection(tmp_path):
    backend = LocalStorageBackend(
        data_dir=str(tmp_path), enable_txt=False, enable_html=False, timezone="UTC"
    )
    backend._get_connection()

    thread = threading.Thread(target=backend._get_connection)
    thread.start()
    thread.join()
    assert len(backend._db_connections) == 2

    backend.cleanup()

    assert backend._db_connections == {}
