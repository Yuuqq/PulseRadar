# Roadmap: TrendRadar

## Milestones

- ✅ **v1.0 Tech Debt** — Phases 1-4 (shipped 2026-04-16) — [archive](milestones/v1.0-ROADMAP.md)
- 🚧 **v1.1 AI Agent News API** — Phases 5-6 (started 2026-04-17)

## Phases

<details>
<summary>✅ v1.0 Tech Debt (Phases 1-4) — SHIPPED 2026-04-16</summary>

- [x] Phase 1: Dependency Hygiene (2/2 plans) — completed 2026-04-13
- [x] Phase 2: Test Safety Net (7/7 plans) — completed 2026-04-14
- [x] Phase 3: God Object Decomposition (4/4 plans) — completed 2026-04-15
- [x] Phase 4: Quality Gates (3/3 plans) — completed 2026-04-16

</details>

### v1.1 AI Agent News API (Phases 5-6)

#### Phase 5: API Data Generation

**Goal:** Generate structured JSON API files per keyword group during GitHub Actions runs, published to GitHub Pages alongside the existing hub.

**Requirements:** API-01, API-02, API-03, API-04, API-05, API-06, API-07, API-08

**Success Criteria:**
1. Running the crawler in GitHub Actions produces `reports/api/daily/_index.json` and one `{group_slug}.json` per configured keyword group
2. Each group JSON validates against the agreed schema (top-level `summary`, `trend` block, cross-platform aggregated `items` with `heat_trend`)
3. Trend data (today vs yesterday, new/declining topics) is accurate against local SQLite history
4. Local `python -m trendradar` runs do NOT create `reports/api/` — env-based routing works correctly
5. Existing CLI, config.yaml, Docker, MCP server, Web UI, and `reports/` hub remain byte-identical in output

**Depends on:** —

#### Phase 6: Integration Documentation

**Goal:** Ship an AI Agent integration guide with runnable examples covering the main consumption patterns.

**Requirements:** DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06

**Success Criteria:**
1. `docs/ai-agent-api.md` (or equivalent) exists with endpoint structure, field semantics, and full JSON schema reference
2. Guide includes a working `curl` example that fetches `_index.json` and a sample group JSON
3. Guide includes a runnable Python `requests` example demonstrating index→group fetch pattern
4. Guide includes a LangChain tool wrapper example showing how to expose the API as an agent-callable tool
5. Guide clearly explains MCP Server vs new API decision criteria (real-time query vs scheduled pull)
6. README links to the guide and lists AI Agent support in the project capabilities section

**Depends on:** Phase 5 (API output must exist to document accurately)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Dependency Hygiene | v1.0 | 2/2 | ✅ Complete | 2026-04-13 |
| 2. Test Safety Net | v1.0 | 7/7 | ✅ Complete | 2026-04-14 |
| 3. God Object Decomposition | v1.0 | 4/4 | ✅ Complete | 2026-04-15 |
| 4. Quality Gates | v1.0 | 3/3 | ✅ Complete | 2026-04-16 |
| 5. API Data Generation | v1.1 | 0/? | 🚧 Planning | — |
| 6. Integration Documentation | v1.1 | 0/? | ⏳ Pending | — |
