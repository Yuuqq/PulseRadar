from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_mcp_tools_instances():
    """Reset MCP server _tools_instances singleton between tests.

    mcp_server/server.py:_tools_instances is a module-level dict populated
    lazily by _get_tools(). Without reset, stale tool instances from one
    test leak into the next.

    Per Plan 02-04 D-11 and RESEARCH.md Open Question #2.
    """
    import mcp_server.server as srv

    srv._tools_instances.clear()
    yield
    srv._tools_instances.clear()
