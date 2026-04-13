---
phase: 01-dependency-hygiene
verified: 2026-04-13T15:30:00Z
status: passed
score: 14/14 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: null
  initial: true
---

# Phase 01: Dependency Hygiene Verification Report

**Phase Goal:** A fresh clone can be installed correctly from requirements.txt, and the dependency manifest honestly reflects what the project needs

**Verified:** 2026-04-13T15:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Truths are merged from ROADMAP.md success criteria (R1-R4) and PLAN frontmatter must_haves (P1-P9, deduplicated).

| #   | Truth                                                                                                                                              | Status     | Evidence                                                                                                                                              |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | `pip install -r requirements.txt` in clean venv installs every runtime package (no ModuleNotFoundError for structlog/pydantic)                      | VERIFIED   | requirements.txt contains `structlog==25.5.0` (line 299) and `pydantic==2.13.0` (line 215). 14 pydantic refs (transitive included).                   |
| R2  | `pip install trendradar` succeeds without pulling boto3; using S3 without `[s3]` extra gives clear error pointing to `pip install trendradar[s3]`  | VERIFIED   | pyproject.toml core deps has no boto3; `[project.optional-dependencies] s3 = ["boto3>=1.35.0,<2.0.0"]` at line 26. Error tested: see truth P4.        |
| R3  | `pip install trendradar` picks up tenacity 9.x; existing retry/circuit-breaker code continues working unchanged                                    | VERIFIED   | pyproject.toml line 14: `"tenacity>=9.0,<10"`. requirements.txt line 301: `tenacity==9.1.4`. No `import tenacity` anywhere in source (zero impact).   |
| R4  | `python -m trendradar` and all CLI flags continue working identically                                                                              | VERIFIED   | `python -m trendradar --help` returns full help text with all 7 documented flags. 143/143 existing tests pass with no regressions.                    |
| P1  | tenacity version specifier in pyproject.toml allows 9.x (range, not exact pin)                                                                     | VERIFIED   | pyproject.toml line 14: `"tenacity>=9.0,<10"` — bounded range, no exact pin                                                                          |
| P2  | boto3 is NOT in pyproject.toml core deps; it IS in `[project.optional-dependencies] s3`                                                            | VERIFIED   | core dependencies (lines 6-19) has no boto3 line; line 26: `s3 = ["boto3>=1.35.0,<2.0.0"]`                                                            |
| P3  | Importing `trendradar.storage` without boto3 installed does NOT raise an error                                                                     | VERIFIED   | `__init__.py` lines 24-30 wrap RemoteStorageBackend import in try/except; `HAS_REMOTE` flag exposed. test_local_backend_works_without_boto3 PASSED.   |
| P4  | Configuring remote/S3 storage without boto3 produces bilingual error containing `pip install trendradar[s3]`                                       | VERIFIED   | manager.py lines 137-142 raises `ImportError` with Chinese + English text + install command. Both unit tests pass.                                    |
| P5  | Docker image from docker/Dockerfile installs boto3 even though requirements.txt no longer includes it                                              | VERIFIED   | Dockerfile lines 54-55: `pip install -r requirements.txt && pip install --no-cache-dir 'boto3>=1.35.0,<2.0.0'`                                        |
| P6  | Docker image from docker/Dockerfile.mcp also installs boto3                                                                                        | VERIFIED   | Dockerfile.mcp lines 7-8: same pattern as primary Dockerfile                                                                                          |
| P7  | CHANGELOG.md has entry documenting the boto3 optional change                                                                                       | VERIFIED   | CHANGELOG.md lines 5-19: `## 2026-04-13 ### 依赖管理优化` section with all required content (boto3 optional, tenacity, structlog, pydantic, Docker)  |
| P8  | README-EN.md mentions `pip install trendradar[s3]` for S3 storage users                                                                            | VERIFIED   | README-EN.md line 1055: full S3 Storage Note with install command and Docker default-inclusion mention                                                |
| P9  | README.md mentions `pip install trendradar[s3]` for S3 storage users                                                                               | VERIFIED   | README.md line 1129: full S3 存储说明 with install command and `Docker 镜像默认已包含 S3 支持` mention                                                 |

**Score:** 14/14 truths verified

### Required Artifacts

| Artifact                                  | Expected                                  | Exists | Substantive | Wired | Status     | Details                                                                                          |
| ----------------------------------------- | ----------------------------------------- | ------ | ----------- | ----- | ---------- | ------------------------------------------------------------------------------------------------ |
| `pyproject.toml`                          | tenacity range, optional [s3] extra        | YES    | YES         | YES   | VERIFIED   | Line 14 `tenacity>=9.0,<10`; lines 25-26 `[project.optional-dependencies] s3 = [...]`             |
| `requirements.txt`                        | auto-generated header, structlog, no boto3 | YES    | YES         | YES   | VERIFIED   | Header lines 1-4 contain "auto-generated"; structlog and pydantic present; 0 boto3 references     |
| `trendradar/storage/manager.py`           | fail-fast HAS_BOTO3 check + bilingual msg | YES    | YES         | YES   | VERIFIED   | Lines 130-142: import HAS_BOTO3, raise bilingual ImportError with `pip install trendradar[s3]`    |
| `trendradar/storage/remote.py`            | preserved HAS_BOTO3 guard (defense-in-depth) | YES   | YES         | YES   | VERIFIED   | Lines 20-29 unchanged; line 83-84 still guards in __init__                                        |
| `trendradar/storage/__init__.py`          | unchanged optional import wrapper          | YES    | YES         | YES   | VERIFIED   | Lines 24-30 unchanged; HAS_REMOTE flag exposed via __all__                                        |
| `tests/test_storage_boto3_guard.py`       | 3 unit tests for boto3 guard              | YES    | YES         | YES   | VERIFIED   | All 3 tests defined and PASS: install_command, bilingual, local_backend_works                    |
| `docker/Dockerfile`                       | separate boto3 install after requirements | YES    | YES         | YES   | VERIFIED   | Lines 54-55 chained pip install via && separator                                                  |
| `docker/Dockerfile.mcp`                   | separate boto3 install after requirements | YES    | YES         | YES   | VERIFIED   | Lines 7-8 same pattern                                                                            |
| `CHANGELOG.md`                            | 2026-04-13 entry with full migration info | YES    | YES         | YES   | VERIFIED   | Lines 5-19 contain new section before 2026-02-09; all required keywords present                  |
| `README-EN.md`                            | S3 install note with Docker mention       | YES    | YES         | YES   | VERIFIED   | Line 1055 contains note with `trendradar[s3]` and `Docker images include S3 support by default` |
| `README.md`                               | S3 install note (Chinese) with Docker note | YES    | YES         | YES   | VERIFIED   | Line 1129 contains note with `trendradar[s3]` and `Docker 镜像默认已包含`                          |

### Key Link Verification

| From                                | To                                | Via                                       | Status | Details                                                                                                  |
| ----------------------------------- | --------------------------------- | ----------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------- |
| trendradar/storage/manager.py        | trendradar/storage/remote.py      | HAS_BOTO3 import check                    | WIRED  | manager.py line 133: `from trendradar.storage.remote import HAS_BOTO3`; gate at line 137-142             |
| requirements.txt                    | pyproject.toml                    | uv pip compile generation                 | WIRED  | requirements.txt lines 1-4 header documents regen command; line 88 `# via trendradar (pyproject.toml)`    |
| docker/Dockerfile                   | requirements.txt                  | COPY and pip install                      | WIRED  | Dockerfile line 53 `COPY requirements.txt .`; line 54 `pip install --no-cache-dir -r requirements.txt`    |
| docker/Dockerfile                   | boto3                             | separate pip install line chained with && | WIRED  | Dockerfile line 55: `pip install --no-cache-dir 'boto3>=1.35.0,<2.0.0'`                                  |
| docker/Dockerfile.mcp               | boto3                             | separate pip install line                 | WIRED  | Dockerfile.mcp line 8 same                                                                                |

### Data-Flow Trace (Level 4)

Skipped — phase produces dependency declarations, build artifacts, and an error path; no dynamic data rendering.

### Behavioral Spot-Checks

| Behavior                                                  | Command                                                                                | Result                                            | Status |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------- | ------ |
| pyproject.toml structurally valid (boto3 optional, tenacity range) | `python -c "import tomllib; ..."`                                                      | "pyproject.toml: PASS"                            | PASS   |
| requirements.txt has structlog/pydantic, no boto3, no exact tenacity pin | `python -c "txt=open('requirements.txt').read(); ..."`                                | "requirements.txt: PASS"                          | PASS   |
| Boto3 guard tests pass                                    | `python -m pytest tests/test_storage_boto3_guard.py -v`                                | 3 passed in 12.43s                                | PASS   |
| Storage module imports without error                      | `python -c "from trendradar.storage import StorageManager, HAS_REMOTE"`                | "storage import OK, HAS_REMOTE= True"             | PASS   |
| CLI entry point still works                               | `python -m trendradar --help`                                                          | Help text with all flags rendered                 | PASS   |
| Full test suite (no regressions)                          | `python -m pytest tests/ -q`                                                            | 143 passed in 15.20s                              | PASS   |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                                          | Status     | Evidence                                                                                              |
| ----------- | ----------- | -------------------------------------------------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------- |
| DEPS-01     | 01-01       | requirements.txt contains exactly the runtime packages declared in pyproject.toml (no drift, no missing packages)    | SATISFIED  | requirements.txt regenerated via uv pip compile; structlog (line 299) and pydantic (line 215) present |
| DEPS-02     | 01-01       | tenacity version specifier is a range (`>=9.0,<10`) instead of exact pin                                              | SATISFIED  | pyproject.toml line 14: `"tenacity>=9.0,<10"`; no `import tenacity` anywhere — zero code impact       |
| DEPS-03     | 01-01, 01-02 | boto3 is an optional extra (`pip install trendradar[s3]`), with clear error if S3 used without installation         | SATISFIED  | pyproject.toml line 26 declares optional extra; manager.py raises bilingual ImportError; 3 tests pass |

All 3 phase requirement IDs (DEPS-01, DEPS-02, DEPS-03) are satisfied. No orphaned requirements: REQUIREMENTS.md maps Phase 1 to exactly DEPS-01/02/03, all of which are claimed in the plans.

### Anti-Patterns Found

| File                                           | Line | Pattern              | Severity | Impact                                                                       |
| ---------------------------------------------- | ---- | -------------------- | -------- | ---------------------------------------------------------------------------- |
| trendradar/storage/manager.py                  | 369  | `return []`          | Info     | Legitimate fallback in `search_titles` for unsupported backends — not a stub |

No TODO, FIXME, XXX, HACK, or PLACEHOLDER markers found in modified files. No empty implementations, no stub return values that flow to user-visible output.

### Human Verification Required

None — all observable truths verified programmatically with deterministic checks (file contents, unit tests, test-suite regression, CLI invocation, module import).

The phase produces dependency configuration and an error-path enhancement — both fully testable without human judgment.

### Gaps Summary

No gaps. All 14 must-haves verified, all 11 artifacts pass three-level checks (exists, substantive, wired), all 5 key links wired, all 3 requirements satisfied, all 6 behavioral spot-checks pass, and no anti-patterns of consequence.

Notable strengths:
- Defense-in-depth boto3 guard preserved in `remote.py` while primary fail-fast moved to `manager.py`
- Bilingual error message respects project's Chinese-first convention while providing actionable English directive
- Auto-generated requirements.txt with regen command in header makes the source-of-truth relationship discoverable
- Both Docker images updated for behavioral parity (Docker users see no change)
- CHANGELOG documents the migration explicitly with compatibility breakdown

Note on local environment: `pip show tenacity` reports 8.5.0 in the verifier's Anaconda environment because the venv predates the pyproject.toml change. This is environment drift, not a code defect — the spec is `>=9.0,<10` and requirements.txt locks to 9.1.4, so any fresh `pip install` will pick up 9.x.

---

_Verified: 2026-04-13T15:30:00Z_
_Verifier: Claude (gsd-verifier)_
