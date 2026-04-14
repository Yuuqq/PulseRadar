# coding=utf-8
"""
Dead code lock test for _analyze_trends (Pitfall 8).

Verifies that _analyze_trends is called in NewsAnalyzer.run() but its result
(trend_report) is NOT passed to _execute_mode_strategy. This locks the current
dead code pattern so Phase 3 can decide whether to remove the dead call or
wire trend_report into the pipeline.

Uses static code inspection rather than full NewsAnalyzer.run() execution
(which would require extensive mocking beyond this plan's scope).
"""
from __future__ import annotations

import inspect


def test_analyze_trends_result_not_passed_to_execute_mode_strategy():
    """Lock Pitfall 8: _analyze_trends is called but trend_report is never used."""
    from trendradar.__main__ import NewsAnalyzer

    # Verify _analyze_trends exists as a method
    assert hasattr(NewsAnalyzer, "_analyze_trends"), (
        "NewsAnalyzer must have _analyze_trends method"
    )

    # Verify _execute_mode_strategy exists
    assert hasattr(NewsAnalyzer, "_execute_mode_strategy"), (
        "NewsAnalyzer must have _execute_mode_strategy method"
    )

    # Get _execute_mode_strategy parameters
    sig = inspect.signature(NewsAnalyzer._execute_mode_strategy)
    param_names = set(sig.parameters.keys())

    # Assert: trend_report is NOT a parameter of _execute_mode_strategy
    assert "trend_report" not in param_names, (
        f"_execute_mode_strategy should NOT accept trend_report "
        f"(Pitfall 8: dead code). Got params: {param_names}"
    )

    # Also verify in the source code of run() that trend_report is assigned
    # but not passed to _execute_mode_strategy
    run_source = inspect.getsource(NewsAnalyzer.run)
    assert "trend_report = self._analyze_trends(" in run_source, (
        "run() must call _analyze_trends and assign to trend_report"
    )
    assert "trend_report" not in inspect.getsource(
        NewsAnalyzer._execute_mode_strategy
    ), (
        "trend_report must not appear in _execute_mode_strategy source"
    )
