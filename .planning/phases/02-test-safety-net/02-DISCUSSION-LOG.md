# Phase 2: Test Safety Net - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-13
**Phase:** 02-test-safety-net
**Areas discussed:** Coverage & dev deps, MCP testing strategy, Pipeline test boundaries, Fixture & test design

---

## Coverage & dev deps

### Question: What should coverage measure?

| Option | Description | Selected |
|--------|-------------|----------|
| trendradar + mcp_server | source = ["trendradar", "mcp_server"] in pyproject. Pitfall 15 warns against --cov=trendradar alone. MCP tests are a phase deliverable | ✓ |
| trendradar only | Keep MCP tests but don't count toward 80% gate | |
| trendradar + mcp_server with package-level thresholds | Global gate + per-package floors (needs .coveragerc) | |

**User's choice:** trendradar + mcp_server (Recommended)

### Question: How should the 80% gate be enforced locally?

| Option | Description | Selected |
|--------|-------------|----------|
| pyproject.toml addopts with --cov-fail-under=80 | Bare `pytest` runs coverage + gate. Branch coverage via [tool.coverage.run] branch=true | ✓ |
| Separate coverage command, pytest stays fast | `pytest` runs without coverage; documented `pytest --cov` for gated run | |
| Pyproject config + explicit target in README | Config in pyproject, README documents canonical invocation | |

**User's choice:** pyproject.toml addopts with --cov-fail-under=80 (Recommended)

### Question: Baseline coverage artifact for TEST-02?

| Option | Description | Selected |
|--------|-------------|----------|
| Commit coverage.xml + SUMMARY.md number | coverage.xml committed once at phase end; per-module table in SUMMARY.md; add to .gitignore after | ✓ |
| SUMMARY.md number only | No binary artifacts; per-package table only | |
| Committed .coverage file (SQLite) | Commit raw binary; most durable but bloaty | |

**User's choice:** Commit coverage.xml + SUMMARY.md number (Recommended)

### Question: How are pytest-cov and responses added?

| Option | Description | Selected |
|--------|-------------|----------|
| Declare in pyproject.toml [dependency-groups] dev + regenerate requirements-dev.txt | Follows Phase 1 canonical-source pattern; also add pytest-randomly | ✓ |
| Declare in pyproject only, leave requirements-dev.txt manual | Simpler but re-introduces drift | |
| Ad-hoc like Phase 1 pip-tools | Document in CONTRIBUTING as pip install command | |

**User's choice:** Declare in pyproject.toml [dependency-groups] dev + regenerate requirements-dev.txt (Recommended)

### Question: What should coverage EXCLUDE from measurement?

| Option | Description | Selected |
|--------|-------------|----------|
| tests/ + webui templates + __main__ guards | Standard exclusions; keep main() and trend_report IN scope | ✓ |
| Minimal exclusions — only obvious non-code | Only tests/ and templates | |
| Aggressive exclusions including known-dead code | Exclude trend_report and other dead paths | |

**User's choice:** tests/ + webui templates + __main__ guards (Recommended)

### Question: Add pytest-randomly to catch test-isolation bugs?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — add pytest-randomly as dev dep | Pitfall 12 singleton leak is real; randomly reordering surfaces it | ✓ |
| No — rely on autouse singleton reset fixture only | Offers no detection if a new test forgets the fixture | |
| Defer to v2/Phase 4 | Avoid piling on Phase 2 scope | |

**User's choice:** Yes — add pytest-randomly as dev dep (Recommended)

### Question: Where does the --cov-fail-under gate run in CI?

| Option | Description | Selected |
|--------|-------------|----------|
| Local only for Phase 2, CI gate added in Phase 4 | Keeps phase boundaries clean; Phase 1 D-08 deferred CI infra | ✓ |
| Add GitHub Actions step in Phase 2 too | Stronger teeth but stretches scope into Phase 4 territory | |
| Local pre-commit hook only | Middle ground; pre-commit infra itself is Phase 4 (QUAL-03) | |

**User's choice:** Local only for Phase 2, CI gate added in Phase 4 (Recommended)

### Question: How should new dev deps get propagated to requirements-dev.txt?

| Option | Description | Selected |
|--------|-------------|----------|
| Regenerate via uv pip compile | Consistent with Phase 1 pattern | ✓ |
| Hand-edit requirements-dev.txt | Simple but re-introduces drift | |
| Delete requirements-dev.txt, rely on pip install -e ".[dev]" | Pitfall 10 canonical-source recommendation; changes documented workflow | |

**User's choice:** Regenerate via uv pip compile (Recommended)

---

## MCP testing strategy

### Question: How should we structure MCP tests to cover 7 tool modules + 3 service modules?

| Option | Description | Selected |
|--------|-------------|----------|
| Handler-level testing with one smoke test through FastMCP | Test Python functions directly + ONE in-process FastMCP smoke test for wiring | ✓ |
| Full FastMCP in-process client for every test | Highest fidelity but STATE.md flagged this as research gap | |
| Pure function-level, skip FastMCP wiring tests entirely | Fastest but @mcp.tool registrations get zero coverage | |

**User's choice:** Handler-level testing with one smoke test through FastMCP (Recommended)

### Question: How should MCP tools mock their dependencies (storage, AI, cache)?

| Option | Description | Selected |
|--------|-------------|----------|
| Shared mock_app_context fixture + responses for HTTP | Matches TEST-04 fixture mandate; consistent with pipeline tests | ✓ |
| Per-tool ad-hoc mocks with unittest.mock.patch | Maximum flexibility but violates TEST-04 reuse goal | |
| Mock via dependency injection refactor first | Cleaner long-term but expands into Phase 3 decomposition | |

**User's choice:** Shared mock_app_context fixture + responses for HTTP (Recommended)

### Question: Async/sync handling for MCP tool tests?

| Option | Description | Selected |
|--------|-------------|----------|
| Claude's discretion — researcher determines based on FastMCP 2.0 spec | Planner inspects actual signatures; don't lock upfront | ✓ |
| Require pytest-asyncio as dev dep now | Adds dep before we know if we need it | |
| Only test sync tools, skip async ones | Whole modules might be untestable under this constraint | |

**User's choice:** Claude's discretion — researcher determines based on FastMCP 2.0 spec (Recommended)

---

## Pipeline test boundaries

### Question: Where do we draw the mock boundaries for the pipeline integration test?

| Option | Description | Selected |
|--------|-------------|----------|
| Mock HTTP + AI + notifications; real SQLite in tmp_path; assert on HTML and payloads | External I/O fully mocked; storage bugs matter. Covers Pitfall 3 + 7 | ✓ |
| Minimal — mock only HTTP, real SQLite, real AI/notifications | Breaks offline/deterministic requirement | |
| Maximum — in-memory SQLite + HTTP + AI + notifications; golden-file HTML | Overkill; golden files too brittle | |

**User's choice:** Mock HTTP + AI + notifications; real SQLite in tmp_path (Recommended)

### Question: How many pipeline integration test cases are required?

| Option | Description | Selected |
|--------|-------------|----------|
| One per mode + edge cases: 5 cases | Covers Pitfall 7 exhaustively (incremental+data, current+hist, current-no-hist RuntimeError, daily+hist, daily-no-hist fallback) | ✓ |
| One per mode — 3 cases | Misses the RuntimeError and fallback branches | |
| One monolithic end-to-end test | Root cause buried when it fails | |

**User's choice:** One per mode + key edge cases: 5 cases (Recommended)

### Question: Notification + extra-API merge assertions?

| Option | Description | Selected |
|--------|-------------|----------|
| Assert notification dispatcher CALLS + extra-API merged into results | Locks Pitfall 3 merge shape; records dispatcher sends | ✓ |
| Assert report HTML only, ignore notification internals | Lets Pitfall 3 escape detection | |
| Claude's discretion — planner picks assertion density | May under-test because assertions are tedious | |

**User's choice:** Assert notification dispatcher CALLS + extra-API merged into results (Recommended)

### Question: Handle Pitfall 8 (trend_report computed but unused)?

| Option | Description | Selected |
|--------|-------------|----------|
| Test current behavior (compute + ignore), flag for Phase 3 to resolve | Preserves no-behavior-change discipline; defers decision | ✓ |
| Remove the dead call in Phase 2 as scope cleanup | Expands Phase 2 into active refactoring | |
| Skip testing the trend computation path entirely | Silent hole in safety net | |

**User's choice:** Test current behavior (compute + ignore), flag for Phase 3 to resolve (Recommended)

---

## Fixture & test design

### Question: Shape of the TEST-04 fixtures?

| Option | Description | Selected |
|--------|-------------|----------|
| mock_config from Pydantic defaults + mock_app_context builds real AppContext + mock_http_response wraps responses.RequestsMock | Real code paths; only external I/O faked; function-scoped | ✓ |
| Raw dict fixtures, no AppContext construction | Each test duplicates boilerplate | |
| Session-scoped heavyweight fixtures with autouse singleton reset | Session scope hides mutation bugs | |

**User's choice:** mock_config from Pydantic model defaults + mock_app_context builds real AppContext with mocked storage/AI; mock_http_response wraps responses.RequestsMock (Recommended)

### Question: Crawler plugin test structure (9 plugins)?

| Option | Description | Selected |
|--------|-------------|----------|
| One file per plugin + shared helper for common assertions | Plugin-specific quirks explicit; error mode per file | ✓ |
| Single parametrized file for all 9 plugins | Buries plugin-specific quirks | |
| One file per plugin, happy path only | Hits coverage but misses error handling | |

**User's choice:** One file per plugin + shared helper for common assertions (Recommended)

### Question: Pitfall 12 (StorageManager singleton leak) handling?

| Option | Description | Selected |
|--------|-------------|----------|
| Autouse fixture in tests/conftest.py that resets _storage_manager before each test | Clean singleton per test; combined with pytest-randomly | ✓ |
| Explicit reset inside mock_app_context fixture only | Tests not consuming the fixture still leak | |
| Document the risk, no fixture — address in Phase 3 | pytest-randomly would surface real failures we'd have to triage | |

**User's choice:** Autouse fixture in tests/conftest.py that resets _storage_manager to None before each test (Recommended)

### Question: Test directory structure — flat vs nested?

| Option | Description | Selected |
|--------|-------------|----------|
| Nested by subsystem for NEW files; existing stays flat | tests/crawler/, tests/mcp/, tests/pipeline/; 16 existing files untouched | ✓ |
| Keep everything flat under tests/ | 35+ files at root; matches existing but unwieldy | |
| Full nested restructure including existing tests | Touches all 16 existing files; churn without functional value | |

**User's choice:** Nested by subsystem: tests/crawler/, tests/mcp/, tests/pipeline/, tests/ (legacy flat for existing) (Recommended)

---

## Claude's Discretion

Areas where user explicitly deferred to Claude / planner judgment:

- Exact `[tool.coverage.report]` exclude_lines patterns beyond the D-04 categories
- Exact file naming within `tests/mcp/tools/` vs `tests/mcp/services/`
- Exact assertion helper names in `tests/crawler/_helpers.py`
- Whether the one FastMCP smoke test lives in `tests/mcp/` root or `tests/mcp/tools/`
- `mock_app_context` attribute exposure (direct attributes vs AppContext accessors)
- Exact HTML substring assertions in the pipeline integration test
- Order of test commits during execution
- Whether to add `pytest-asyncio` or `anyio` — delegated to researcher (D-13)

## Deferred Ideas

- CI --cov-fail-under gate in GitHub Actions → Phase 4 (QUAL-03)
- Pre-commit coverage hook → Phase 4 (QUAL-03)
- Resolution of trend_report dead code (Pitfall 8) → Phase 3 AnalysisEngine extraction
- Resolution of extra-API in-place mutation (Pitfall 3) → Phase 3 CrawlCoordinator extraction
- Full error matrix per crawler plugin → v2
- Strict golden-file HTML diffing → v2
- Pydantic-model-validated test fixtures → revisit if test config errors become common
- FastMCP 2.0 protocol-level test fleet → v2
- In-memory SQLite mock → rejected
- pytest-xdist parallelism → already rejected in REQUIREMENTS.md
- pytest-freezer → v2
- Coverage trend tracking in CI → v2
- AppContext decomposition tests → v2
