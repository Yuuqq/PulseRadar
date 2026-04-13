# Phase 1: Dependency Hygiene - Research

**Researched:** 2026-04-13
**Domain:** Python dependency management (pyproject.toml, requirements.txt, optional extras, Docker)
**Confidence:** HIGH

## Summary

Phase 1 addresses three concrete dependency problems: (1) requirements.txt is missing structlog and pydantic versus pyproject.toml, (2) tenacity is exact-pinned at 8.5.0 while every other dependency uses ranges, and (3) boto3 is a mandatory install despite only being needed for S3 storage. All three fixes modify pyproject.toml, requirements.txt, and Dockerfiles. A unit test verifies the boto3 error UX.

The key research finding is that **tenacity is not actually imported or used anywhere in the project source code** (neither `trendradar/` nor `mcp_server/`). The circuit breaker in `trendradar/crawler/middleware/circuit_breaker.py` is a fully custom implementation using `time.monotonic` -- it does NOT use tenacity. This means the 8-to-9 upgrade has **zero code risk**. The only breaking change in tenacity 9.0.0 (statistics attribute location) is irrelevant since no code references tenacity at all.

The boto3 optional-extra work has clear integration points: `trendradar/storage/remote.py` already has a `HAS_BOTO3` try/except guard (lines 20-29), `trendradar/storage/manager.py` already uses lazy import for RemoteStorageBackend (line 133), and `trendradar/storage/__init__.py` already wraps RemoteStorageBackend in a try/except (lines 25-30). The planner's job is to wire a fail-fast startup check and update the Dockerfiles.

**Primary recommendation:** Execute the three changes in order: (1) pyproject.toml edits first (boto3 to optional, tenacity range, verify structlog/pydantic present), (2) regenerate requirements.txt via `uv pip compile`, (3) update Dockerfiles, (4) add fail-fast boto3 check with bilingual error, (5) write unit test, (6) update CHANGELOG + README.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Error must surface at startup / config load, not on first S3 operation. Fail fast when config.yaml declares a remote backend (or backend_type=auto resolves to remote based on env) but boto3 is unavailable.
- **D-02:** Error message is directive and includes the install command -- e.g., `S3 storage is configured but boto3 is not installed. Install with: pip install trendradar[s3]`. No env-var fallback hint.
- **D-03:** Error text is bilingual (Chinese + English) to match the project's existing docstring/log style. Both languages in a single message.
- **D-04:** A unit test verifies the error message. The test monkey-patches `boto3` (and/or `HAS_BOTO3`) to simulate the missing-dependency state and asserts the expected directive text. This locks the UX contract.
- **D-05:** requirements.txt becomes auto-generated from pyproject.toml via `pip-compile` (or `uv pip compile`). A header comment at the top of the file marks it as generated and names the regen command. Manual edits are explicitly discouraged.
- **D-06:** The generated file is a loose mirror of pyproject.toml ranges -- not a strict hash-pinned lock file. Same version ranges as pyproject.toml, just flattened with transitive deps. Preserves current Docker / GitHub Actions behavior where `pip install -r requirements.txt` picks the latest compatible versions.
- **D-07:** The generator tool (pip-compile or uv) is not added as a dev dependency. Developers install it ad-hoc. The regen command is documented in CONTRIBUTING.md and/or README.md.
- **D-08:** Enforcement is trust-based in Phase 1. No CI drift check added now (deferred to Phase 4).
- **D-09:** Both Docker images (docker/Dockerfile and docker/Dockerfile.mcp) explicitly install the [s3] extra so S3 is always available inside containers.
- **D-10:** Docker install command keeps using requirements.txt and adds boto3 separately -- pattern `pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir 'boto3>=1.35.0,<2.0.0'` (or equivalent). Do not switch to `pip install -e .[s3]`.
- **D-11:** The MCP Dockerfile also installs boto3 for consistency across images.
- **D-12:** A prominent CHANGELOG entry documents the boto3 change.

### Claude's Discretion
- Exact Python syntax of the startup check (which module raises, where the check is wired into the existing StorageManager backend-resolution flow).
- Exact location of the error-raising code (likely `trendradar/storage/manager.py` or `trendradar/storage/__init__.py`).
- Whether the regen command lives in README, CONTRIBUTING.md, or both.
- Exact Docker install syntax (separate pip install line vs. docker-requirements.txt overlay vs. build-arg).
- Exact CHANGELOG wording and whether it goes in an existing CHANGELOG file or a release notes section of README.
- Whether the `HAS_BOTO3` name stays or is renamed.
- Whether `__init__.py`'s re-export of `RemoteStorageBackend` needs to become lazy.

### Deferred Ideas (OUT OF SCOPE)
- CI drift check for requirements.txt vs pyproject.toml (Phase 4)
- Adding pip-tools / uv as a formal dev dependency
- Strict hash-pinned lock file
- pip-audit vulnerability scanning (v2 requirement)
- Splitting Docker images into core + -s3 variants
- MCP image dropping boto3 for size optimization
- Disabling S3 via env var as alternative to installing [s3]
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEPS-01 | requirements.txt contains exactly the runtime packages declared in pyproject.toml (no drift, no missing packages) | Current drift: requirements.txt is missing `structlog` and `pydantic`. Fix: regenerate via `uv pip compile pyproject.toml -o requirements.txt`. Auto-generation eliminates future drift. |
| DEPS-02 | tenacity version specifier is a range (`>=9.0,<10`) instead of exact pin | Current: `tenacity==8.5.0`. tenacity 9.1.4 is latest. **Zero code risk**: tenacity is not imported or used anywhere in the source. Breaking change (statistics attr) is irrelevant. |
| DEPS-03 | boto3 is an optional extra (`pip install trendradar[s3]`), with clear error if S3 is used without installation | Current: boto3 in core deps. Move to `[project.optional-dependencies] s3`. Existing `HAS_BOTO3` guard in remote.py + lazy import in manager.py provide the foundation. Add fail-fast startup check. |
</phase_requirements>

## Standard Stack

### Core (Phase 1 only -- tools used in this phase)

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| uv | 0.7.15+ | requirements.txt generation | Already installed on this machine. `uv pip compile` generates loose requirements from pyproject.toml. 10-100x faster than pip-compile. [VERIFIED: `uv --version` returned 0.7.15] |
| pip | bundled | Package installation | Standard Python package installer, already in use |
| pytest | >=8.0,<9 | Test runner for unit test | Already configured in pyproject.toml [VERIFIED: pyproject.toml] |

### Packages Modified (not installed as tools)

| Package | Current | Target | Change |
|---------|---------|--------|--------|
| tenacity | ==8.5.0 | >=9.0,<10 | Unpin; latest is 9.1.4 [VERIFIED: pip index] |
| boto3 | core dep >=1.35,<2 | optional extra `[s3]` | Move from `dependencies` to `[project.optional-dependencies]` |
| structlog | already in pyproject.toml | no change | Already present; missing from requirements.txt only |
| pydantic | already in pyproject.toml | no change | Already present; missing from requirements.txt only |

**Installation (Phase 1 scope):**
```bash
# Regenerate requirements.txt from pyproject.toml
uv pip compile pyproject.toml -o requirements.txt
```

## Architecture Patterns

### Pattern 1: Optional Dependency with Fail-Fast Check

**What:** Guard an optional dependency at the point where the backend is resolved, not at import time.

**When to use:** When a dependency (boto3) is needed only for a specific backend (remote/S3).

**Existing code to build on:**

```python
# trendradar/storage/remote.py:20-29 -- already exists
try:
    import boto3
    from botocore.config import Config as BotoConfig
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    boto3 = None
    BotoConfig = None
    ClientError = Exception
```
[VERIFIED: trendradar/storage/remote.py lines 20-29]

```python
# trendradar/storage/manager.py:130-148 -- already exists
def _create_remote_backend(self) -> Optional[StorageBackend]:
    try:
        from trendradar.storage.remote import RemoteStorageBackend
        return RemoteStorageBackend(...)
    except ImportError as e:
        logger.error("远程后端导入失败", error=str(e))
        logger.warning("请确保已安装 boto3: pip install boto3")
        return None
```
[VERIFIED: trendradar/storage/manager.py lines 130-148]

**Recommended fail-fast location:** Inside `StorageManager._create_remote_backend()` or a new method called from `get_backend()`. When the resolved backend type is "remote" and boto3 is not installed, raise an `ImportError` with the bilingual directive message BEFORE attempting to construct `RemoteStorageBackend`. This keeps the check centralized in the manager and avoids affecting MCP/WebUI that only use local storage.

**Key constraint:** The check must ONLY fire when the backend actually resolves to "remote". It must NOT fire when:
- `trendradar.storage` is merely imported (MCP, WebUI do this)
- `backend_type="local"` or `backend_type="auto"` resolves to local
- No config references S3

### Pattern 2: Auto-Generated requirements.txt with Header

**What:** Generate requirements.txt from pyproject.toml with a machine-readable header comment.

```
# This file is auto-generated from pyproject.toml via:
#   uv pip compile pyproject.toml -o requirements.txt
# Do not edit manually. To regenerate:
#   pip install uv && uv pip compile pyproject.toml -o requirements.txt
<generated content>
```
[ASSUMED - header format is Claude's discretion per D-05]

### Pattern 3: Docker boto3 Installation

**What:** Add a separate pip install line in Dockerfiles for boto3.

**Current Dockerfile pattern (line 53-54):**
```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```
[VERIFIED: docker/Dockerfile lines 53-54]

**Target pattern (per D-10):**
```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir 'boto3>=1.35.0,<2.0.0'
```

### Anti-Patterns to Avoid
- **Eager boto3 check at module import time:** Do NOT check `HAS_BOTO3` in `trendradar/storage/__init__.py` top-level. This would break `from trendradar.storage import get_storage_manager` for users who don't use S3.
- **Switching Dockerfiles to `pip install -e .[s3]`:** Per D-10, this changes layer caching behavior and requires copying the source tree before install. Keep `requirements.txt` as the primary Docker install source.
- **Deleting requirements.txt entirely:** While STACK.md research recommended this as ideal, D-05 locked the decision to auto-generate it. Keep it as a generated artifact.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| requirements.txt sync | Manual copy of versions from pyproject.toml | `uv pip compile pyproject.toml -o requirements.txt` | Eliminates human error; auto-includes transitive deps; reproducible |
| Optional dependency error UX | Custom import hook or monkeypatch | Simple `if not HAS_BOTO3: raise ImportError(...)` in StorageManager | The existing guard + lazy import pattern already handles 90% of the work; just add the directive message |

## Common Pitfalls

### Pitfall 1: __init__.py Re-export Breaking Non-S3 Users

**What goes wrong:** `trendradar/storage/__init__.py` line 26 does `from trendradar.storage.remote import RemoteStorageBackend` inside a try/except. If boto3 is removed from core deps, this import fails silently (which is the correct behavior -- `HAS_REMOTE=False`). However, if anyone adds an unconditional `RemoteStorageBackend` reference at import time, it will be `None` and cause confusing errors later.

**Why it happens:** The try/except in `__init__.py` already handles this correctly. Risk is low but must be verified after the change.

**How to avoid:** After moving boto3 to optional, verify that `import trendradar.storage` succeeds without boto3 installed. The existing try/except on lines 25-30 already handles this. [VERIFIED: trendradar/storage/__init__.py lines 24-30]

**Warning signs:** `AttributeError: 'NoneType' object has no attribute ...` when using storage module.

### Pitfall 2: MCP/WebUI Startup Failure from Overly Aggressive Check

**What goes wrong:** The fail-fast check fires when ANY part of the storage module is imported, not just when remote backend is actually selected. This breaks MCP server and WebUI for users who don't use S3.

**Why it happens:** Putting the check in `__init__.py` or `StorageManager.__init__()` instead of in the backend resolution path.

**How to avoid:** Place the check inside `StorageManager._create_remote_backend()` or `StorageManager.get_backend()` only when `resolved_type == "remote"`. The MCP server's `storage_sync.py` also imports `RemoteStorageBackend` lazily (line 88) and already handles `ImportError` (line 103). [VERIFIED: mcp_server/tools/storage_sync.py lines 87-108]

**Warning signs:** MCP server or WebUI crashes on startup with "boto3 not installed" even though they only use local storage.

### Pitfall 3: uv pip compile Output Not Matching Expected Format

**What goes wrong:** `uv pip compile` may produce a format that differs from the current hand-maintained requirements.txt (e.g., including transitive deps, different comment style, different line ordering).

**Why it happens:** The generated file includes the full transitive dependency tree, not just direct deps. This is actually the correct behavior per D-06 ("flattened with transitive deps"), but the output may surprise reviewers.

**How to avoid:** Run `uv pip compile pyproject.toml -o requirements.txt --no-header` and add a custom header manually, OR use the default header. Verify that `pip install -r requirements.txt` in a clean venv produces the same installed packages as before.

### Pitfall 4: CHANGELOG Format Mismatch

**What goes wrong:** The existing CHANGELOG.md uses a specific date-based format with Chinese section headers. Adding a section in a different format breaks the document's consistency.

**How to avoid:** Follow the existing template at bottom of CHANGELOG.md. [VERIFIED: CHANGELOG.md lines 177-193]

## Code Examples

### Fail-Fast boto3 Check (Recommended Implementation)

```python
# In trendradar/storage/manager.py, modify _create_remote_backend() or get_backend()
# Source: based on existing pattern at remote.py:20-29 and manager.py:130-148

def _create_remote_backend(self) -> Optional[StorageBackend]:
    """创建远程存储后端"""
    try:
        from trendradar.storage.remote import RemoteStorageBackend, HAS_BOTO3
    except ImportError:
        HAS_BOTO3 = False

    if not HAS_BOTO3:
        raise ImportError(
            "S3 远程存储已配置，但未安装 boto3。\n"
            "S3 storage is configured but boto3 is not installed.\n"
            "Install with: pip install trendradar[s3]"
        )

    # ... existing RemoteStorageBackend construction ...
```

### Unit Test for Missing boto3 Error

```python
# tests/test_storage_boto3_guard.py
# Source: pattern from CONTEXT.md D-04

from unittest.mock import patch
import pytest

def test_missing_boto3_raises_with_install_command():
    """Verify that configuring S3 without boto3 produces a directive error."""
    with patch.dict("sys.modules", {"boto3": None, "botocore": None, "botocore.config": None, "botocore.exceptions": None}):
        # Force reimport to trigger the guard
        from trendradar.storage.manager import StorageManager
        sm = StorageManager(backend_type="remote", remote_config={
            "bucket_name": "test",
            "access_key_id": "test",
            "secret_access_key": "test",
            "endpoint_url": "https://test.example.com",
        })
        with pytest.raises(ImportError, match="pip install trendradar\\[s3\\]"):
            sm.get_backend()
```

### pyproject.toml Changes

```toml
# Move boto3 from dependencies to optional-dependencies
# Source: CONTEXT.md locked decisions + STACK.md reference config

[project]
dependencies = [
    "requests>=2.32.5,<3.0.0",
    "pytz>=2025.2,<2026.0",
    "PyYAML>=6.0.3,<7.0.0",
    "fastmcp>=2.14.0,<3.0.0",
    "websockets>=15.0.1,<16.0.0",
    "feedparser>=6.0.0,<7.0.0",
    "litellm>=1.57.0,<2.0.0",
    "tenacity>=9.0,<10",          # was ==8.5.0
    "flask>=3.0.0,<4.0.0",
    "mcp>=1.23.0,<2.0.0",
    "structlog>=24.0.0,<26.0.0",  # already present
    "pydantic>=2.0.0,<3.0.0",    # already present
    # boto3 removed from here
]

[project.optional-dependencies]
s3 = ["boto3>=1.35.0,<2.0.0"]
```

### Dockerfile Addition

```dockerfile
# docker/Dockerfile -- add boto3 after requirements.txt install
# Source: CONTEXT.md D-09, D-10

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir 'boto3>=1.35.0,<2.0.0'
```

## Tenacity 8-to-9 Migration Analysis

### Breaking Changes in 9.0.0

| Change | Impact on TrendRadar | Risk |
|--------|---------------------|------|
| `statistics` attribute moved from `func.retry.statistics` to `func.statistics` | **NONE** -- tenacity is not imported or used anywhere in source code | ZERO |
| `wait_random_exponential` now respects `min` argument | **NONE** -- tenacity is not imported or used anywhere in source code | ZERO |

[VERIFIED: `grep -r "import tenacity\|from tenacity\|@retry" trendradar/ mcp_server/` returned zero matches]
[CITED: https://github.com/jd/tenacity/releases/tag/9.0.0]

### Tenacity Usage Audit

The circuit breaker at `trendradar/crawler/middleware/circuit_breaker.py` is a **fully custom implementation** using `time.monotonic()` and `threading.Lock`. It does not use tenacity's retry decorators. [VERIFIED: circuit_breaker.py source, 69 lines total]

tenacity appears in `pyproject.toml` and `requirements.txt` as a declared dependency but is **never imported** by any module in the project. It is likely a vestigial dependency from an earlier version of the codebase, or it is pulled in transitively by another package (litellm uses tenacity internally). Either way, the version bump from 8.5.0 to >=9.0 has zero code impact.

**Conclusion:** The tenacity upgrade is a one-line change to pyproject.toml with no migration effort needed. It should be combined with the `uv pip compile` regeneration.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-maintained requirements.txt | Auto-generated via `uv pip compile` | 2024 (uv matured) | Eliminates drift between pyproject.toml and requirements.txt |
| Exact version pins for all deps | Range specifiers (>=X,<Y) for all except lock files | PEP 621 standard practice | Allows security patches, reduces resolver conflicts |
| All deps in core install | Optional extras for heavy/niche deps | PEP 621 `[project.optional-dependencies]` | Reduces install footprint (boto3+botocore is ~100MB) |

## Files to Modify

| File | Change | Rationale |
|------|--------|-----------|
| `pyproject.toml` | Remove boto3 from `dependencies`, add `[project.optional-dependencies] s3`, change tenacity to `>=9.0,<10` | DEPS-02, DEPS-03 |
| `requirements.txt` | Regenerate via `uv pip compile`, add header comment | DEPS-01, D-05, D-06 |
| `trendradar/storage/manager.py` | Add fail-fast check in `_create_remote_backend()` with bilingual error message | D-01, D-02, D-03 |
| `trendradar/storage/__init__.py` | Verify existing try/except still works (likely no change needed) | Safety check |
| `docker/Dockerfile` | Add `pip install --no-cache-dir 'boto3>=1.35.0,<2.0.0'` after requirements.txt install | D-09, D-10 |
| `docker/Dockerfile.mcp` | Same boto3 addition | D-11 |
| `tests/test_storage_boto3_guard.py` (new) | Unit test for missing-boto3 error message | D-04 |
| `CHANGELOG.md` | Add entry documenting boto3 optional change | D-12 |
| `README.md` or `README-EN.md` | Update install instructions to mention `[s3]` extra | D-12 |

## Assumptions Log

> List all claims tagged [ASSUMED] in this research.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Header comment format for generated requirements.txt | Pattern 2 | Low -- cosmetic only, any header works |
| A2 | `uv pip compile pyproject.toml -o requirements.txt` produces a loose (non-hashed) output by default | Pattern 2 | Medium -- if uv defaults to hashes, need `--no-hashes` flag; easily verified at execution time |

**If this table is empty:** Almost all claims were verified or cited. Only two minor assumptions remain.

## Open Questions

1. **uv pip compile exact invocation flags**
   - What we know: `uv pip compile` exists and generates requirements files. uv 0.7.15 is installed.
   - What's unclear: Whether the default output matches D-06 expectations (loose mirror, no hashes). May need `--no-header` to add custom header.
   - Recommendation: Test the command during execution; adjust flags if output doesn't match.

2. **Whether the README install section mentions pip install specifically**
   - What we know: README focuses on Docker deployment and GitHub Actions. No explicit `pip install -r requirements.txt` instructions found in the first 100 lines.
   - What's unclear: Whether there's a "local install" section deeper in the README that references requirements.txt.
   - Recommendation: Search full README for install instructions before deciding where to add the `[s3]` notice.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All code | Yes | 3.12.7 | -- |
| uv | requirements.txt generation (D-05) | Yes | 0.7.15 | pip-compile from pip-tools |
| pip | Package installation | Yes | bundled | -- |
| pytest | Unit test (D-04) | Yes | configured in pyproject.toml | -- |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Security Domain

> Phase 1 is purely dependency management. Security concerns are limited to dependency supply chain.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | -- |
| V3 Session Management | No | -- |
| V4 Access Control | No | -- |
| V5 Input Validation | No | -- |
| V6 Cryptography | No | -- |
| V14 Configuration | Yes | Version range specifiers prevent known-vulnerable exact versions; `uv pip compile` from pyproject.toml provides auditability |

### Known Threat Patterns for Dependency Management

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Dependency confusion (typosquatting) | Spoofing | Use exact package names from pyproject.toml; `uv pip compile` resolves from the same source |
| Stale pinned dependency with known CVE | Tampering | Range specifiers (`>=9.0,<10`) allow patch updates |
| Unnecessary dependency increasing attack surface | Elevation of Privilege | Making boto3 optional reduces installed package count for users who don't need S3 |

## Project Constraints (from CLAUDE.md)

- **CLI compatibility**: `python -m trendradar` and all CLI arguments must keep working
- **Config compatibility**: Existing `config/config.yaml` files must work without migration
- **Docker compatibility**: Docker images and docker-compose files must keep working
- **Import compatibility**: Public imports used by MCP server and Web UI must not break
- **Immutability preference**: Create new objects rather than mutate (CLAUDE.md coding-style)
- **Error handling**: Always handle errors comprehensively with structured logging
- **File size limit**: Keep files under 800 lines
- **Chinese docstrings**: Project uses Chinese language docstrings throughout
- **`# coding=utf-8` header**: Preserve on all existing files
- **Commit format**: `<type>: <description>` (feat, fix, refactor, docs, test, chore)

## Sources

### Primary (HIGH confidence)
- `pyproject.toml` -- current dependency declarations [VERIFIED: direct read]
- `requirements.txt` -- current state showing missing structlog + pydantic [VERIFIED: direct read]
- `trendradar/storage/remote.py` -- HAS_BOTO3 guard at lines 20-29 [VERIFIED: direct read]
- `trendradar/storage/manager.py` -- lazy import at line 133, _create_remote_backend at lines 130-151 [VERIFIED: direct read]
- `trendradar/storage/__init__.py` -- try/except RemoteStorageBackend at lines 24-30 [VERIFIED: direct read]
- `mcp_server/tools/storage_sync.py` -- lazy import + ImportError handling at lines 87-108 [VERIFIED: direct read]
- `docker/Dockerfile` -- requirements.txt install at lines 53-54 [VERIFIED: direct read]
- `docker/Dockerfile.mcp` -- requirements.txt install at lines 6-7 [VERIFIED: direct read]
- Codebase-wide grep for tenacity usage: zero matches in `trendradar/` and `mcp_server/` [VERIFIED: ripgrep search]
- `pip index versions tenacity` -- 9.1.4 is latest, 8.5.0 is installed [VERIFIED: pip index]
- `uv --version` -- 0.7.15 installed [VERIFIED: command output]

### Secondary (MEDIUM confidence)
- [Tenacity 9.0.0 release notes](https://github.com/jd/tenacity/releases/tag/9.0.0) -- breaking change is statistics attribute + wait_random_exponential min arg [CITED: GitHub release page]
- [Tenacity changelog](https://tenacity.readthedocs.io/en/latest/changelog.html) -- confirmed changelog exists [CITED: official docs]
- [Tenacity issue #486](https://github.com/jd/tenacity/issues/486) -- confirms 8.5.0 included the statistics breaking change that prompted the 9.0.0 major bump [CITED: GitHub issue]

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all tools verified as installed, versions confirmed
- Architecture: HIGH -- all code paths verified by direct source reading
- Pitfalls: HIGH -- each pitfall derived from reading the actual source files
- Tenacity migration: HIGH -- zero usage confirmed by exhaustive codebase search

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable domain; dependency versions move slowly)
