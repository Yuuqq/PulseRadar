"""Root conftest — loaded before tests/conftest.py.

Applies environment-level patches that must run before any library imports.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Workaround: WMI query hang on Windows
#
# platform.system() → platform._wmi_query() can hang indefinitely when the
# Windows WMI service is unresponsive.  aiohttp.helpers calls platform.system()
# at module level, blocking every import chain that touches aiohttp (including
# litellm → openai → httpx/aiohttp).  Raising OSError makes platform fall back
# to the safe sys.getwindowsversion() path (stdlib platform.py, _win32_ver).
# ---------------------------------------------------------------------------
import platform as _platform

if hasattr(_platform, "_wmi_query"):
    _platform._wmi_query = lambda *a, **k: (_ for _ in ()).throw(
        OSError("WMI disabled by test harness")
    )
