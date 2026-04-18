# Milestone v1.1: AI Agent News API — Requirements

**Status:** Defining
**Started:** 2026-04-17

**Goal:** Provide a pull-based, backend-less structured news summary endpoint for general AI Agent frameworks (LangChain, CrewAI, AutoGPT, etc.) to consume TrendRadar's aggregated trend data on demand.

**Core constraint:** All existing user-facing behavior must keep working identically (CLI, config.yaml, Docker, MCP server, Web UI).

## Requirements

### API Data Generation

- [ ] **API-01**: AI Agent can fetch a JSON file per keyword group (`reports/api/daily/{group_slug}.json`) containing that group's daily aggregated news items
- [ ] **API-02**: AI Agent can fetch `reports/api/daily/_index.json` listing all available keyword groups with update timestamps and file paths
- [ ] **API-03**: Each group JSON includes a top-level `summary` field (human+AI readable one-paragraph overview of the day's hotspots)
- [ ] **API-04**: Each group JSON includes a `trend` block (today vs. yesterday counts, direction, new topics, declining topics) enabling trend analysis
- [ ] **API-05**: Each item in the `items` array aggregates cross-platform occurrences (same news across 微博/知乎/抖音 merged with per-platform ranks/URLs)
- [ ] **API-06**: Each item includes a `heat_trend` marker (`new` / `rising` / `stable` / `falling`) reflecting per-item trend
- [ ] **API-07**: API JSON files are auto-generated during GitHub Actions runs and published to GitHub Pages (same pipeline as existing `reports/` hub)
- [ ] **API-08**: Local `python -m trendradar` runs do NOT produce `reports/api/` output (env-based routing, same as existing `github_pages_dir` logic)

### Documentation & Examples

- [ ] **DOC-01**: Repository contains an AI Agent integration guide (markdown) explaining the API structure, endpoint URLs, and field semantics
- [ ] **DOC-02**: Integration guide includes a `curl` example showing how to fetch `_index.json` and a group JSON
- [ ] **DOC-03**: Integration guide includes a minimal Python example (using `requests`) demonstrating the index→group fetch flow
- [ ] **DOC-04**: Integration guide includes a LangChain tool/example showing how to wrap the API as an agent-callable tool
- [ ] **DOC-05**: Integration guide clarifies the relationship between new API and existing MCP server (when to use which)
- [ ] **DOC-06**: Repository README links to the integration guide and mentions AI Agent support as a core capability

## Future Requirements (deferred)

- **API-future-01**: Long-period aggregations (`weekly.json`, `monthly.json`) — defer until daily format proves adoption
- **API-future-02**: Per-item `ai_summary` field from dedicated prompt — defer; v1.1 reuses existing AI analysis output when available
- **API-future-03**: Real-time streaming endpoint (SSE/WebSocket) — defer; pull-mode covers v1.1 scope
- **API-future-04**: Authentication and rate-limit tokens — defer; GitHub Pages static hosting has no auth layer
- **DOC-future-01**: OpenAPI 3.x spec file — defer; JSON schema + markdown guide sufficient for v1.1

## Out of Scope

- **Push notifications to AI Agents** — subscription management requires backend; wrong fit for static-file architecture
- **AI Agent discovery protocols** (AGID, etc.) — no standard has clear adoption; premature commitment
- **Replacing MCP server** — MCP and new API serve different use cases (real-time query vs. batch pull); keep both
- **Non-English documentation** — v1.1 docs match existing project language (Chinese with English technical terms); translation is separate effort
- **Web UI for API browsing** — JSON files are self-describing; human browsing served by existing HTML hub

## Traceability

*Phase mapping will be filled by `gsd-roadmapper`.*

| REQ-ID | Phase | Success Criterion |
|--------|-------|-------------------|
| API-01 | TBD | TBD |
| API-02 | TBD | TBD |
| API-03 | TBD | TBD |
| API-04 | TBD | TBD |
| API-05 | TBD | TBD |
| API-06 | TBD | TBD |
| API-07 | TBD | TBD |
| API-08 | TBD | TBD |
| DOC-01 | TBD | TBD |
| DOC-02 | TBD | TBD |
| DOC-03 | TBD | TBD |
| DOC-04 | TBD | TBD |
| DOC-05 | TBD | TBD |
| DOC-06 | TBD | TBD |

---
*Requirements version: v1.1 | Last updated: 2026-04-17*
