# Phase 1: Dependency Hygiene - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the broken install path so a fresh clone installs correctly from requirements.txt, and make the dependency manifest honestly reflect what the project needs. Three concrete changes:
1. Sync `requirements.txt` with `pyproject.toml` (add missing `structlog` + `pydantic`)
2. Unpin `tenacity` (exact `==8.5.0` → range `>=9.0,<10`)
3. Move `boto3` from core dependencies to an optional `[s3]` extra, with a clear startup error if S3 is configured without it

All CLI, config.yaml, Docker, and public imports used by MCP server + Web UI must keep working identically.

</domain>

<decisions>
## Implementation Decisions

### Missing boto3 error UX
- **D-01:** Error must surface **at startup / config load**, not on first S3 operation. Fail fast when `config.yaml` declares a remote backend (or `backend_type=auto` resolves to remote based on env) but `boto3` is unavailable.
- **D-02:** Error message is **directive and includes the install command** — e.g., `S3 storage is configured but boto3 is not installed. Install with: pip install trendradar[s3]`. No env-var fallback hint.
- **D-03:** Error text is **bilingual (Chinese + English)** to match the project's existing docstring/log style. Both languages in a single message.
- **D-04:** A **unit test** verifies the error message. The test monkey-patches `boto3` (and/or `HAS_BOTO3`) to simulate the missing-dependency state and asserts the expected directive text. This locks the UX contract.

### requirements.txt strategy
- **D-05:** `requirements.txt` becomes **auto-generated from `pyproject.toml`** via `pip-compile` (or `uv pip compile`). A header comment at the top of the file marks it as generated and names the regen command. Manual edits are explicitly discouraged.
- **D-06:** The generated file is a **loose mirror** of `pyproject.toml` ranges — not a strict hash-pinned lock file. Same version ranges as `pyproject.toml`, just flattened with transitive deps. Preserves current Docker / GitHub Actions behavior where `pip install -r requirements.txt` picks the latest compatible versions.
- **D-07:** The generator tool (`pip-compile` or `uv`) is **not added as a dev dependency**. Developers install it ad-hoc (`pip install uv` or `pip install pip-tools`). The regen command is documented in `CONTRIBUTING.md` and/or `README.md` (planner picks location). Keeps the dev dependency footprint minimal.
- **D-08:** Enforcement is **trust-based in Phase 1**. No CI drift check added now. Phase 4 (Quality Gates) can add a pre-commit/CI check to verify `requirements.txt` matches `pyproject.toml` if needed. Scope stays tight.

### Docker image handling
- **D-09:** Both Docker images (`docker/Dockerfile` and `docker/Dockerfile.mcp`) **explicitly install the `[s3]` extra** so S3 is always available inside containers. Remote storage is a common Docker deployment pattern; preserving that behavior is a hard compat requirement.
- **D-10:** Docker install command **keeps using `requirements.txt`** and adds boto3 separately — pattern `pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir 'boto3>=1.35.0,<2.0.0'` (or equivalent via a `docker-requirements.txt` overlay). Do **not** switch to `pip install -e .[s3]` — that would change layer caching and requires copying the source tree before install. The planner picks the exact syntax but must keep `requirements.txt` as the primary install source.
- **D-11:** The **MCP Dockerfile** (`docker/Dockerfile.mcp`) also installs boto3 even though the MCP server primarily reads local SQLite — consistency across images avoids two different image shapes and predictable behavior if MCP ever touches remote storage.
- **D-12:** A **prominent CHANGELOG entry** documents the boto3 change. Phrased as a notice to users who install from git: `boto3 is now optional; install with pip install trendradar[s3] for S3 storage`. README install instructions also updated.

### Claude's Discretion
- Exact Python syntax of the startup check (which module raises, where the check is wired into the existing `StorageManager.is_github_actions` / backend-resolution flow).
- Exact location of the error-raising code (likely `trendradar/storage/manager.py` or `trendradar/storage/__init__.py` at the point where `RemoteStorageBackend` is resolved — `remote.py` already has the `HAS_BOTO3` guard to build on).
- Whether the regen command lives in README, CONTRIBUTING.md, or both.
- Exact Docker install syntax (separate `pip install` line vs. `docker-requirements.txt` overlay vs. build-arg). Any approach is fine as long as `requirements.txt` stays the primary source and boto3 is always present in built images.
- Exact CHANGELOG wording and whether it goes in an existing CHANGELOG file or a release notes section of README.
- Whether the `HAS_BOTO3` name stays or is renamed.
- Whether `__init__.py`'s re-export of `RemoteStorageBackend` needs to become lazy (likely yes, to avoid import-time `boto3` requirement).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Research artifacts (project-local)
- `.planning/research/STACK.md` §"Unpin tenacity", §"Make boto3 Optional", §"Updated pyproject.toml Configuration" — authoritative target configuration including version ranges and the optional-extras block. Use this as the reference pyproject.toml shape, but only apply the Phase 1 subset (do NOT apply pytest-cov, ruff, mypy, etc. — those belong to later phases).
- `.planning/research/PITFALLS.md` §"Pitfall 11: tenacity 8-to-9 Migration Breaking Retry Logic" — documents the risk that tenacity 9.x changed default retry behavior. Planner/researcher must verify the current `trendradar/crawler/middleware/circuit_breaker.py` and any `@retry` decorators still behave identically under 9.x before the phase can be called done.
- `.planning/research/FEATURES.md` §tenacity version range row — restates the DEPS-02 rationale and the expected change.
- `.planning/codebase/CONCERNS.md` §"Pinned tenacity" — codebase-map note calling out the exact pin as a resolution-conflict risk.

### Project contract docs
- `.planning/REQUIREMENTS.md` §"Dependency Management" (DEPS-01, DEPS-02, DEPS-03) — the three requirements this phase must satisfy.
- `.planning/ROADMAP.md` §"Phase 1: Dependency Hygiene" — the four Success Criteria that define "done".
- `.planning/PROJECT.md` §"Constraints" — CLI, config.yaml, Docker, and public import compatibility constraints that apply to every edit in this phase.

### Code files the planner/researcher will touch
- `pyproject.toml` — add structlog/pydantic already present; unpin tenacity; move boto3 to `[project.optional-dependencies] s3`.
- `requirements.txt` — regenerate from pyproject.toml (loose mirror, no hashes), add generated-file header.
- `trendradar/storage/remote.py` — already has `HAS_BOTO3` try/except guard (lines 20–29). Starting point for the import-guard pattern; may stay mostly as-is.
- `trendradar/storage/manager.py` — `StorageManager` resolves backend at line 133 via lazy `from trendradar.storage.remote import RemoteStorageBackend`. This is the likely site for the fail-fast check.
- `trendradar/storage/__init__.py` — re-exports `RemoteStorageBackend` at line 26; may need to become lazy or wrap in a try/except so `import trendradar.storage` doesn't require boto3.
- `docker/Dockerfile` — lines 53–54 `COPY requirements.txt . && pip install -r requirements.txt`. Add boto3 install step.
- `docker/Dockerfile.mcp` — lines 6–7 `COPY requirements.txt . && pip install -r requirements.txt`. Add boto3 install step.
- `tests/` — new unit test for the missing-boto3 startup error (location TBD by planner, but should sit next to existing storage tests).

### External references (only if planner needs to verify)
- tenacity changelog: https://pypi.org/project/tenacity/ — planner MUST read the 8.x→9.x migration notes before declaring DEPS-02 done (per PITFALLS.md §11).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`HAS_BOTO3` import guard** in `trendradar/storage/remote.py:20-29` — already implements the try/except ImportError pattern with fallback sentinels. The Phase 1 error UX builds on this rather than replacing it. The guard itself can stay; we add a dedicated startup check that reads `HAS_BOTO3` (or re-does the import) and raises a directive error if the configured backend needs boto3.
- **`StorageManager.is_github_actions()` / backend resolution** in `trendradar/storage/manager.py` — central place where backend_type is resolved. Natural host for the fail-fast check before `RemoteStorageBackend` is constructed.
- **Existing `tenacity` retry callsites** — `.planning/codebase/CONVENTIONS.md` notes tenacity is "available but not heavily used in main code". Low blast radius for the 8→9 bump, but `trendradar/crawler/middleware/circuit_breaker.py` and any `@retry` decorators must be audited.
- **Lazy import pattern** — `manager.py:133` already uses `from trendradar.storage.remote import RemoteStorageBackend` inside a method, which is the pattern that avoids requiring boto3 at module-import time. `trendradar/storage/__init__.py:26` does NOT use lazy import and may need to be converted.

### Established Patterns
- **Bilingual Chinese/English strings** — project docstrings are primarily Chinese, some log messages mix both. Error message for missing boto3 should follow this — put the English install command verbatim (because it's a literal shell command) and add a Chinese explanation alongside.
- **Pydantic config models with env overrides** (`trendradar/models/config.py`) — config validation happens at load time; the boto3 check can hook into this phase or into `StorageManager.__init__`.
- **`# coding=utf-8` header** on most files — preserve this when editing.
- **`structlog` structured logging** — error should use `logger.error("message", key=value)` pattern, not raw prints. But since this is a fatal startup error, the message must also be visible on stderr so a user running `python -m trendradar` without configured logging still sees it.

### Integration Points
- **`trendradar/__main__.py:main()`** — CLI entry. The fail-fast check should run before any crawling is attempted, either inside `StorageManager` construction or right after config load in `main()`.
- **Docker entrypoint** — `docker/entrypoint.sh` runs `python -m trendradar` via supercronic. Error surfaces as a non-zero exit and a log line; no special handling needed.
- **MCP server** — `trendradar-mcp` entry only reads SQLite locally and does NOT construct a `RemoteStorageBackend` by default. MCP server should NOT hit the fail-fast check unless it's specifically configured for remote sync. Planner must verify this — a too-aggressive startup check could break MCP startup for users who don't use S3.
- **Web UI** — `python run_webui.py` / `trendradar/webui/app.py` — same concern as MCP. Check must only fire when remote backend is actually selected, not when any part of the storage module is imported.

</code_context>

<specifics>
## Specific Ideas

- Error message should literally say `pip install trendradar[s3]` — the exact command the user needs to copy-paste. No paraphrasing.
- Keep the `HAS_BOTO3` guard in `remote.py` (don't delete it just because there's now a startup check — defense in depth).
- "It should feel like the error message teaches the user how to fix it in one line" — directive, not diagnostic.

</specifics>

<deferred>
## Deferred Ideas

- **CI drift check for `requirements.txt` vs `pyproject.toml`** — defer to Phase 4 (Quality Gates). The pre-commit + CI infrastructure belongs in that phase; adding it now expands Phase 1 scope.
- **Adding `pip-tools` / `uv` as a formal dev dependency** — documented as ad-hoc install for now. If it becomes friction, revisit after Phase 4.
- **Strict hash-pinned lock file** — not for this milestone. Would change `pip install -r requirements.txt` UX and potentially break Docker/CI. Revisit if reproducible-build requirements emerge.
- **pip-audit vulnerability scanning** — already listed as v2 requirement in `REQUIREMENTS.md`.
- **Splitting Docker images into core + -s3 variants** — rejected. Both images include `[s3]` for consistency.
- **MCP image dropping boto3 for size optimization** — rejected. Consistency across images beats ~100MB savings for this milestone.
- **Disabling S3 via env var as an alternative to installing `[s3]`** — rejected for error message; not mentioned in the directive to keep it short and actionable.

</deferred>

---

*Phase: 01-dependency-hygiene*
*Context gathered: 2026-04-13*
