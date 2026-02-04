# coding=utf-8

from __future__ import annotations

from datetime import datetime


def test_splitter_respects_max_bytes_and_keeps_first_title_with_header():
    from trendradar.notification.splitter import split_content_into_batches

    titles = [
        {
            "title": "TITLE1 " + ("x" * 220),
            "source_name": "src",
            "time_display": "12:00",
            "count": 1,
            "ranks": [1],
            "rank_threshold": 10,
            "url": "http://example.com/1",
            "mobile_url": "",
        },
        {
            "title": "TITLE2 " + ("y" * 220),
            "source_name": "src",
            "time_display": "12:01",
            "count": 1,
            "ranks": [2],
            "rank_threshold": 10,
            "url": "http://example.com/2",
            "mobile_url": "",
        },
    ]

    report_data = {
        "stats": [{"word": "KW", "count": len(titles), "titles": titles}],
        "new_titles": [],
        "failed_ids": [],
        "total_new_count": 0,
    }

    max_bytes = 550
    batches = split_content_into_batches(
        report_data=report_data,
        format_type="dingtalk",
        max_bytes=max_bytes,
        show_new_section=False,
        get_time_func=lambda: datetime(2026, 2, 4, 12, 0, 0),
    )

    assert len(batches) >= 2
    assert all(len(b.encode("utf-8")) <= max_bytes for b in batches)

    # Atomicity expectation: word header + first title should appear together in first batch.
    first_batch = batches[0]
    assert "KW" in first_batch
    assert "TITLE1" in first_batch

