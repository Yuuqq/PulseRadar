---
phase: 01-dependency-hygiene
plan: 02
subsystem: infra
tags: [docker, dockerfile, boto3, changelog, readme, s3, optional-dependencies]

# Dependency graph
requires:
  - phase: 01-dependency-hygiene/01
    provides: "boto3 moved to optional [s3] extra in pyproject.toml, requirements.txt regenerated"
provides:
  - Docker images (Dockerfile and Dockerfile.mcp) explicitly install boto3 after requirements.txt
  - CHANGELOG entry documenting the dependency hygiene changes
  - README install docs updated with pip install trendradar[s3] guidance
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: ["Docker pip install chaining: requirements.txt first, then explicit extras via &&"]

key-files:
  created: []
  modified:
    - docker/Dockerfile
    - docker/Dockerfile.mcp
    - CHANGELOG.md
    - README-EN.md
    - README.md

key-decisions:
  - "Used single RUN layer with && chaining for boto3 install to minimize Docker layer count"
  - "S3 note placed in Quick Start section after deployment options for maximum visibility"

patterns-established:
  - "Docker extra-dependency pattern: chain separate pip install after requirements.txt for optional packages needed at runtime"

requirements-completed: [DEPS-03]

# Metrics
duration: 6min
completed: 2026-04-13
---

# Phase 01 Plan 02: Docker and Documentation Updates Summary

**Both Dockerfiles updated to explicitly install boto3 after requirements.txt, CHANGELOG entry documenting all dependency hygiene changes, and bilingual README notes directing pip users to `pip install trendradar[s3]`**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-13T14:37:57Z
- **Completed:** 2026-04-13T14:43:45Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Docker images will continue to include boto3 for S3 support even though it was removed from requirements.txt (moved to pyproject.toml optional extra)
- CHANGELOG documents all dependency changes (boto3 optional, tenacity unpin, requirements.txt regeneration) with migration guidance
- Both READMEs inform pip-install users about the new `trendradar[s3]` extra and confirm Docker deployments need no changes

## Task Commits

Each task was committed atomically:

1. **Task 1: Update Dockerfiles to install boto3 separately** - `5c14d674` (chore)
2. **Task 2: Add CHANGELOG entry and update README install instructions** - `23338a34` (docs)

## Files Created/Modified
- `docker/Dockerfile` - Added `pip install --no-cache-dir 'boto3>=1.35.0,<2.0.0'` chained after requirements.txt install
- `docker/Dockerfile.mcp` - Same boto3 install added for MCP image consistency
- `CHANGELOG.md` - New 2026-04-13 section documenting dependency hygiene changes (boto3, tenacity, structlog, pydantic)
- `README-EN.md` - Added S3 storage note in Quick Start section with `pip install trendradar[s3]` and Docker default inclusion
- `README.md` - Added Chinese S3 storage note in Quick速开始 section with same content

## Decisions Made
- Used single RUN layer with `&&` chaining (not a separate `RUN` instruction) to avoid adding an extra Docker layer -- this matches the existing pattern and keeps the build efficient
- Placed the S3 storage note in the Quick Start section after the deployment option comparison, where users make their deployment choice -- this ensures it is seen before users start the install steps

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 01 (dependency-hygiene) is fully complete: pyproject.toml updated (plan 01), Dockerfiles patched, documentation written (plan 02)
- All 143 existing tests pass -- no regressions from any dependency hygiene changes
- Phase 02 can proceed without any blockers from dependency management

---
*Phase: 01-dependency-hygiene*
*Completed: 2026-04-13*

## Self-Check: PASSED

All claimed artifacts verified on disk:
- docker/Dockerfile: FOUND
- docker/Dockerfile.mcp: FOUND
- CHANGELOG.md: FOUND
- README-EN.md: FOUND
- README.md: FOUND
- .planning/phases/01-dependency-hygiene/01-02-SUMMARY.md: FOUND

All claimed commits verified in git log:
- 5c14d674 (Task 1): FOUND
- 23338a34 (Task 2): FOUND
