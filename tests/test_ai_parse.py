# coding=utf-8

from __future__ import annotations


def test_ai_analyzer_parse_response_json_code_block():
    # Avoid running AIAnalyzer.__init__ (it loads prompt files). _parse_response is pure.
    from trendradar.ai.analyzer import AIAnalyzer

    analyzer = AIAnalyzer.__new__(AIAnalyzer)
    resp = """Here is result:

```json
{
  "core_trends": "A",
  "sentiment_controversy": "B",
  "signals": "C",
  "rss_insights": "D",
  "outlook_strategy": "E"
}
```
"""

    parsed = analyzer._parse_response(resp)
    assert parsed.success is True
    assert parsed.core_trends == "A"
    assert parsed.outlook_strategy == "E"

