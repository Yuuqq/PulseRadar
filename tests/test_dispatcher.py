from __future__ import annotations


def test_split_text_by_bytes_basic():
    from trendradar.notification.dispatcher import NotificationDispatcher

    batches = NotificationDispatcher._split_text_by_bytes("a\nb\nc", 3)
    assert all(len(chunk.encode("utf-8")) <= 3 for chunk in batches)
    assert "\n".join(batches) == "a\nb\nc"


def test_split_text_by_bytes_handles_long_line():
    from trendradar.notification.dispatcher import NotificationDispatcher

    content = "abcdef"
    batches = NotificationDispatcher._split_text_by_bytes(content, 2)
    assert batches == ["ab", "cd", "ef"]


def test_split_text_by_bytes_respects_utf8_boundary():
    from trendradar.notification.dispatcher import NotificationDispatcher

    content = "中中中"
    batches = NotificationDispatcher._split_text_by_bytes(content, len("中".encode()))
    assert batches == ["中", "中", "中"]
