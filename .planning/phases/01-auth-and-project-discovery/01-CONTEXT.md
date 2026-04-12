# Phase 1: Auth and Project Discovery - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Authenticate to Claude.ai's internal API using a session cookie, discover the user's organization, list all projects, and let the user select one. This phase delivers a working CLI skeleton that validates auth and enables project selection — no export logic yet.

</domain>

<decisions>
## Implementation Decisions

### Cookie Input
- **D-01:** Accept session cookie via three methods in priority order: `--cookie` CLI flag > `CLAUDE_SESSION_COOKIE` env var > interactive prompt (masked input)
- **D-02:** Support both bare `sessionKey` value and full cookie header string (auto-detect and normalize)
- **D-03:** Store `.env` file with `CLAUDE_SESSION_COOKIE` and `CLAUDE_PROJECT_UUID` for convenience — user already has one

### Org Discovery
- **D-04:** Call `/api/organizations` to discover orgs from the session cookie
- **D-05:** Auto-select first org if only one exists; prompt user to select if multiple orgs found
- **D-06:** Support `--org` flag to skip interactive selection for scripting

### Project Selection
- **D-07:** Interactive prompt shows project name, created date, and file/doc counts
- **D-08:** Support `--project` flag accepting project UUID for non-interactive use
- **D-09:** Support `CLAUDE_PROJECT_UUID` env var as fallback (already in .env)

### Error Messaging
- **D-10:** Friendly error messages on auth failure with hint: "Session cookie may be expired. Re-extract from browser DevTools > Application > Cookies > sessionKey"
- **D-11:** `--verbose` flag shows raw HTTP status, headers, and response body for debugging
- **D-12:** Validate cookie immediately on startup (call `/api/organizations`) before proceeding to any other operation

### Rate Limiting
- **D-13:** Exponential backoff on HTTP 429/529: initial 2s delay, doubling per retry, max 5 retries
- **D-14:** Respect `Retry-After` header when present
- **D-15:** Log retry attempts in verbose mode

### Claude's Discretion
- Exact CLI help text formatting
- Whether to use `click.prompt` or `rich.prompt` for interactive input
- HTTP client configuration details (timeouts, user-agent string)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### API Endpoints
- `.planning/research/FEATURES.md` — Complete API endpoint documentation with request/response patterns, verified from two independent implementations
- `.planning/research/ARCHITECTURE.md` — Module structure, data flow, component boundaries

### Pitfalls
- `.planning/research/PITFALLS.md` — 13 domain-specific pitfalls with prevention strategies; P2 (org discovery), P4 (rate limiting), P5 (API response defensiveness) are critical for this phase

### Stack
- `.planning/research/STACK.md` — Technology choices: httpx, click, rich, pydantic with versions and rationale

### Environment
- `.env` — Contains `CLAUDE_PROJECT_UUID` for the DT One project (pre-populated)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None — this phase establishes the foundational patterns (project structure, API client, models)

### Integration Points
- `.env` file already exists with project UUID placeholder
- `.gitignore` already configured

</code_context>

<specifics>
## Specific Ideas

- User has already provided a sample API response for `/projects` showing the DT One project structure — models should match this shape
- The `.env` file is pre-populated with `CLAUDE_PROJECT_UUID=019af253-8b25-7137-aaaf-3d10d7a49442` for the DT One project
- Cookie should support both `sk-ant-...` bare value and full `sessionKey=sk-ant-...` header format

</specifics>

<deferred>
## Deferred Ideas

None — analysis stayed within phase scope

</deferred>

---

*Phase: 01-auth-and-project-discovery*
*Context gathered: 2026-04-12*
