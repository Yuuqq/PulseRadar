# Phase 1: Dependency Hygiene - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-13
**Phase:** 01-dependency-hygiene
**Areas discussed:** Missing boto3 error UX, requirements.txt strategy, Docker image handling

---

## Missing boto3 error UX

### Q1: When should the error surface?

| Option | Description | Selected |
|--------|-------------|----------|
| At startup/config load | Fail fast when config.yaml declares S3 but boto3 missing. Cheapest failure, clearest signal. | ✓ |
| On first S3 operation | Let app start, fail when RemoteStorageBackend is first used. More lenient but wastes work. | |
| You decide | Pick whichever fits the existing storage_manager flow best. | |

**User's choice:** At startup/config load
**Notes:** Fail-fast semantics before any crawling begins.

### Q2: What should the error message say?

| Option | Description | Selected |
|--------|-------------|----------|
| Directive with install command | "S3 storage is configured but boto3 is not installed. Install with: pip install trendradar[s3]" | ✓ |
| Short generic ImportError | Standard ImportError without install hint. | |
| Directive + env var hint | Install command plus a note about disabling S3. Longer but covers both paths. | |

**User's choice:** Directive with install command
**Notes:** Message teaches the user how to fix it in one line.

### Q3: Error message language?

| Option | Description | Selected |
|--------|-------------|----------|
| Bilingual (Chinese + English) | Match existing project style. Helps international + Chinese users. | ✓ |
| English only | Simpler, universal for pip/pypi users. | |
| Chinese only | Matches most docstrings but excludes international contributors. | |

**User's choice:** Bilingual (Chinese + English)
**Notes:** Install command stays in English (literal shell command), explanation bilingual.

### Q4: Test for the error message?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — unit test with import mock | Monkey-patch boto3 to None and assert expected message. Locks UX contract. | ✓ |
| No — just implement it | Ship the error, rely on Phase 2 safety net. | |
| You decide | Pick based on existing test structure. | |

**User's choice:** Yes — unit test with import mock
**Notes:** Locks the UX contract now rather than relying on Phase 2.

---

## requirements.txt strategy

### Q1: How should requirements.txt be maintained?

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-generate via pip-compile/uv | Lock file generated from pyproject.toml. Drift becomes structurally impossible. | ✓ |
| Manual + CI drift check | Keep manual, add CI check. Catches drift but doesn't prevent it. | |
| Delete requirements.txt entirely | Rely on `pip install -e .`. Breaks Docker/CI. | |
| Manual one-time sync | Just edit this once. No prevention mechanism. | |

**User's choice:** Auto-generate via pip-compile/uv
**Notes:** Root-cause fix — prevents the drift from recurring.

### Q2: Strict lock or loose mirror?

| Option | Description | Selected |
|--------|-------------|----------|
| Loose mirror (same ranges) | Same version ranges as pyproject.toml, flattened. Compatible with current Docker/CI. | ✓ |
| Strict lock with hashes | Pinned versions + hashes. Reproducible but invasive. | |
| You decide | Pick based on current Docker/CI expectations. | |

**User's choice:** Loose mirror (same ranges)
**Notes:** Preserves existing `pip install -r` UX.

### Q3: Generator tool as dev dependency?

| Option | Description | Selected |
|--------|-------------|----------|
| Document in CONTRIBUTING/README only | Ad-hoc install. Minimal dep footprint. | ✓ |
| Add as dev dependency | pip-tools or uv in dependency-groups dev. | |
| You decide | Pick based on dev workflow conventions. | |

**User's choice:** Document in CONTRIBUTING/README only
**Notes:** Keeps dev dependencies lean.

### Q4: Enforce regen or trust-based?

| Option | Description | Selected |
|--------|-------------|----------|
| Trust-based for Phase 1 | Regen manually now. Defer CI enforcement to Phase 4. | ✓ |
| Add CI check now | GitHub Actions job fails on drift. Expands Phase 1 scope. | |
| No enforcement ever | Document and rely on discipline forever. | |

**User's choice:** Trust-based for Phase 1
**Notes:** Phase 4 (Quality Gates) is the right home for CI enforcement.

---

## Docker image handling

### Q1: How should Docker builds include boto3?

| Option | Description | Selected |
|--------|-------------|----------|
| Install [s3] extra explicitly | Docker always has S3 available. Matches Docker users' expectations. | ✓ |
| Match local default | No boto3 in Docker by default. Breaks existing S3 users. | |
| Split into two images | Core + -s3 variants. Affects compose files and tags. | |
| You decide | Pick based on Docker backward compatibility. | |

**User's choice:** Install [s3] extra explicitly
**Notes:** Docker users expect S3 to work out of the box.

### Q2: requirements.txt vs pip install -e .[s3]?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep requirements.txt + add boto3 line | Minimal change. requirements.txt stays the lock source. | ✓ |
| Switch to pip install -e .[s3] | Single source of truth. Changes layer caching. | |
| You decide | Pick based on layer caching and Dockerfile structure. | |

**User's choice:** Keep requirements.txt + add boto3 line
**Notes:** Minimal change to existing Docker layer caching behavior.

### Q3: MCP Dockerfile — include boto3?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — include boto3 for consistency | One mental model. Small size cost. | ✓ |
| No — MCP stays lean | MCP skips boto3. Two image shapes. | |
| You decide | Pick based on MCP's current storage use. | |

**User's choice:** Yes — include boto3 for consistency
**Notes:** Consistency across images beats the ~100MB saving.

### Q4: CHANGELOG / release notes for boto3 change?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — prominent CHANGELOG entry | BREAKING CHANGE note. Helps users upgrade. | ✓ |
| Yes — README + CHANGELOG | Most visibility. | |
| No — just ship | Startup error is enough signal. | |

**User's choice:** Yes — prominent CHANGELOG entry
**Notes:** README install instructions also updated (implied; planner decides exact scope).

---

## Claude's Discretion

- Exact module/function that performs the startup check (likely in `StorageManager` or `trendradar/storage/__init__.py`).
- Whether `HAS_BOTO3` is renamed, kept, or supplemented by a helper.
- Exact Docker install syntax (extra `pip install` line vs `docker-requirements.txt` overlay vs build-arg).
- Exact regen-command documentation location (README vs CONTRIBUTING.md vs both).
- Exact CHANGELOG wording.
- Whether `trendradar/storage/__init__.py`'s `RemoteStorageBackend` re-export needs to become lazy (likely yes).

## Deferred Ideas

- CI drift check for requirements.txt ↔ pyproject.toml — Phase 4.
- Adding `pip-tools` / `uv` as a formal dev dependency — revisit after Phase 4.
- Strict hash-pinned lock file — out of scope for this milestone.
- Splitting Docker into core + -s3 images — rejected.
- MCP image dropping boto3 for size optimization — rejected.
- Env-var path for disabling S3 instead of installing `[s3]` — rejected for error message.
