# Phase 1: Auth and Project Discovery - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 01-auth-and-project-discovery
**Areas discussed:** Cookie input, Org discovery, Project selection, Error messaging

---

## Cookie Input

| Option | Description | Selected |
|--------|-------------|----------|
| All three (flag + env + prompt) | Priority chain: --cookie > env var > interactive prompt | ✓ |
| Flag only | --cookie required, no fallbacks | |
| Env var only | CLAUDE_SESSION_COOKIE only | |

**User's choice:** All three (auto-selected recommended default)
**Notes:** User already has a .env file with project UUID, so env var support is natural

---

## Org Discovery

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-select first, --org override | Auto if single org, prompt if multiple, --org flag for scripting | ✓ |
| Always prompt | Force user to select org every time | |
| Require --org flag | No auto-detection | |

**User's choice:** Auto-select first, --org override (auto-selected recommended default)
**Notes:** Most users have a single org; multi-org is an edge case worth handling gracefully

---

## Project Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Interactive + --project flag | Rich prompt showing name/date/counts, with flag for scripting | ✓ |
| Flag only | Require --project UUID, no interactive mode | |
| Always interactive | No flag, always prompt | |

**User's choice:** Interactive + --project flag (auto-selected recommended default)
**Notes:** Env var CLAUDE_PROJECT_UUID also supported as fallback

---

## Error Messaging

| Option | Description | Selected |
|--------|-------------|----------|
| Friendly + --verbose raw | User-friendly messages by default, raw response with --verbose | ✓ |
| Always verbose | Show raw API response on every error | |
| Minimal | Just "auth failed" with exit code | |

**User's choice:** Friendly + --verbose raw (auto-selected recommended default)
**Notes:** Include re-extraction hint on auth failure

---

## Claude's Discretion

- CLI help text formatting
- Interactive input library choice (click.prompt vs rich.prompt)
- HTTP client configuration (timeouts, user-agent)

## Deferred Ideas

None — analysis stayed within phase scope
