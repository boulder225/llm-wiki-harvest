---
phase: 01-auth-and-project-discovery
plan: 01
subsystem: api
tags: [httpx, pydantic, retry, backoff, claude-api]

# Dependency graph
requires: []
provides:
  - "Python package scaffold with uv (pyproject.toml, lockfile, venv)"
  - "Pydantic models for Organization and Project API responses"
  - "ClaudeAPIClient with exponential backoff retry logic"
  - "Custom exceptions: SessionExpiredError, RateLimitError, APIError"
affects: [01-02, 02-conversation-export, 03-files-and-knowledge]

# Tech tracking
tech-stack:
  added: [httpx 0.28.x, click 8.3.x, rich 15.x, pydantic 2.12.x, ruff, pytest, pytest-httpx]
  patterns: [sync httpx client, Pydantic extra=ignore for API tolerance, centralized _request with retry]

key-files:
  created:
    - pyproject.toml
    - src/claude_dump/__init__.py
    - src/claude_dump/models.py
    - src/claude_dump/client.py
  modified: []

key-decisions:
  - "Sync httpx client (no async) per STACK.md design decision"
  - "Pydantic models with extra=ignore to tolerate undocumented API field changes"
  - "Centralized _request method as single point for all HTTP calls and retry logic"
  - "Cookie header includes lastActiveOrg when org_id is set (org_id property setter)"

patterns-established:
  - "Pattern: All HTTP calls go through ClaudeAPIClient._request -- single retry point"
  - "Pattern: API response dual-format handling via _extract_list (bare array or {data: [...]})"
  - "Pattern: Verbose logging to stderr via rich.Console (never to stdout)"

requirements-completed: [RES-01, RES-04]

# Metrics
duration: 3min
completed: 2026-04-12
---

# Phase 01 Plan 01: Project Scaffold and API Client Summary

**httpx-based API client with exponential backoff (2s/doubling/5 retries), Pydantic models for Org/Project, and session expiry detection**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-12T11:43:06Z
- **Completed:** 2026-04-12T11:46:34Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Python project scaffolded with uv, all 4 runtime + 3 dev dependencies installed
- Pydantic models parse Organization and Project responses defensively (extra="ignore")
- API client implements exponential backoff on 429/529/500/502/503 with Retry-After header support
- Clear exception hierarchy: SessionExpiredError (401), RateLimitError (429/529), APIError (other)

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold Python project with uv and install dependencies** - `208d840` (feat)
2. **Task 2: Create Pydantic models for Claude.ai API responses** - `3a5d681` (feat)
3. **Task 3: Build API client with exponential backoff retry logic** - `39cc23d` (feat)

## Files Created/Modified
- `pyproject.toml` - Project metadata, dependencies, CLI entry point
- `src/claude_dump/__init__.py` - Package init with __version__ = "0.1.0"
- `src/claude_dump/models.py` - Organization, Project models + exception classes
- `src/claude_dump/client.py` - ClaudeAPIClient with retry/backoff logic

## Decisions Made
- Sync httpx client (no async) -- per STACK.md, CLI runs sequentially and async adds complexity with no benefit
- Pydantic models with `extra="ignore"` -- undocumented API may add fields at any time (Pitfall P5)
- Centralized `_request` method -- all HTTP calls route through one method for consistent retry behavior
- Cookie header dynamically includes `lastActiveOrg` when org_id is set via property setter
- Verbose retry logging uses rich.Console(stderr=True) to avoid polluting stdout

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Python version pin updated from 3.11 to 3.12**
- **Found during:** Task 1 (uv sync)
- **Issue:** uv init created .python-version with 3.11 but pyproject.toml requires >=3.12
- **Fix:** Ran `uv python pin 3.12` to update .python-version
- **Files modified:** .python-version
- **Verification:** uv sync completed successfully, all imports work
- **Committed in:** 208d840 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Trivial version pin fix. No scope creep.

## Issues Encountered
None beyond the Python version pin fix documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- API client ready for use by Plan 02 (CLI + cookie config + project listing)
- Models ready for extension with Conversation, Message models in Phase 02
- All modules importable without errors

## Self-Check: PASSED

All 4 created files verified on disk. All 3 task commits verified in git log.

---
*Phase: 01-auth-and-project-discovery*
*Completed: 2026-04-12*
