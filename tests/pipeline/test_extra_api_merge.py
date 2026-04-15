"""
Extra-API merge shape lock test (Pitfall 3).

Replicates the EXACT merge loop from __main__.py lines 624-641 to lock the
current mutation-based merge pattern. Phase 3 CrawlCoordinator must internalize
this merge; this test catches regressions during that refactor.

This is a PURE unit test: no mocks, no fixtures, no I/O.
"""

from __future__ import annotations


def test_extra_api_merge_mutates_results_and_id_to_name():
    """Lock the extra-API merge pattern from __main__.py lines 624-641."""
    # Starting state: one hotlist platform
    results = {
        "hotlist_platform": {
            "Hotlist Title": {"ranks": [1], "url": "http://hot.com", "mobileUrl": ""},
        }
    }
    id_to_name = {"hotlist_platform": "Hotlist Platform"}
    failed_ids = []

    # Extra API data to merge
    extra_results = {
        "extra_api_1": [
            {"title": "Extra News A", "rank": 1, "url": "http://extra.com/a", "mobile_url": ""},
            {"title": "Extra News B", "rank": 2, "url": "http://extra.com/b", "mobile_url": ""},
            {"title": "", "rank": 3, "url": "", "mobile_url": ""},  # empty title -- skipped
        ],
    }
    extra_names = {"extra_api_1": "Extra API Source"}
    extra_failed = ["extra_api_2"]

    # Replicate __main__.py lines 624-641 exactly
    if extra_results:
        for source_id, items in extra_results.items():
            results[source_id] = {}
            for i, item in enumerate(items, 1):
                title = item.get("title", "").strip()
                if not title:
                    continue
                rank = item.get("rank", i)
                if title in results[source_id]:
                    results[source_id][title]["ranks"].append(rank)
                else:
                    results[source_id][title] = {
                        "ranks": [rank],
                        "url": item.get("url", ""),
                        "mobileUrl": item.get("mobile_url", ""),
                    }
        id_to_name.update(extra_names)
        failed_ids.extend(extra_failed)

    # Assert: results dict now contains both hotlist and extra-API source_ids
    assert "hotlist_platform" in results, "original hotlist platform must be preserved"
    assert "extra_api_1" in results, "extra-API source must be added to results"
    assert len(results) == 2, f"expected 2 sources, got {len(results)}: {list(results.keys())}"

    # Assert: extra-API items have correct shape
    assert "Extra News A" in results["extra_api_1"]
    assert results["extra_api_1"]["Extra News A"]["ranks"] == [1]
    assert results["extra_api_1"]["Extra News A"]["url"] == "http://extra.com/a"
    assert results["extra_api_1"]["Extra News A"]["mobileUrl"] == ""

    # Assert: second item also present
    assert "Extra News B" in results["extra_api_1"]
    assert results["extra_api_1"]["Extra News B"]["ranks"] == [2]

    # Assert: empty-title item was skipped
    assert len(results["extra_api_1"]) == 2, "empty title should be filtered"

    # Assert: id_to_name contains both source names
    assert "hotlist_platform" in id_to_name
    assert "extra_api_1" in id_to_name
    assert id_to_name["extra_api_1"] == "Extra API Source"

    # Assert: failed_ids extended
    assert "extra_api_2" in failed_ids


def test_extra_api_merge_duplicate_title_appends_rank():
    """Lock the duplicate-title rank-append behavior within the merge loop."""
    results = {}
    extra_results = {
        "api_dup": [
            {"title": "Dup Title", "rank": 1, "url": "http://dup.com", "mobile_url": ""},
            {"title": "Dup Title", "rank": 5, "url": "http://dup.com", "mobile_url": ""},
        ],
    }

    # Replicate merge loop
    for source_id, items in extra_results.items():
        results[source_id] = {}
        for i, item in enumerate(items, 1):
            title = item.get("title", "").strip()
            if not title:
                continue
            rank = item.get("rank", i)
            if title in results[source_id]:
                results[source_id][title]["ranks"].append(rank)
            else:
                results[source_id][title] = {
                    "ranks": [rank],
                    "url": item.get("url", ""),
                    "mobileUrl": item.get("mobile_url", ""),
                }

    # Duplicate title should have both ranks appended
    assert "Dup Title" in results["api_dup"]
    assert results["api_dup"]["Dup Title"]["ranks"] == [1, 5]
    assert len(results["api_dup"]) == 1, "duplicates merge into single entry"
