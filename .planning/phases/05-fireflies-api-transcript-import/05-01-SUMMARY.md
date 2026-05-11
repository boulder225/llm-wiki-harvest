---
phase: "05"
plan: "01"
subsystem: fireflies-api-client
tags: [fireflies, graphql, pydantic, httpx, api-client]
dependency_graph:
  requires: []
  provides: [fireflies-models, fireflies-client, fireflies-config]
  affects: [fireflies-exporter, fireflies-cli]
tech_stack:
  added: []
  patterns: [graphql-client, pydantic-extra-ignore, 4-step-config-resolution, exponential-backoff-retry]
key_files:
  created:
    - src/claude_dump/fireflies_models.py
    - src/claude_dump/fireflies_client.py
    - src/claude_dump/fireflies_config.py
    - tests/test_fireflies_models.py
    - tests/test_fireflies_client.py
  modified: []
decisions:
  - "Used base_url https://api.fireflies.ai with /graphql path (not full URL as base) for clean httpx Client setup"
  - "Set transcript id after model_validate since detail query does not return id in response body"
  - "Merged 401 and 403 into single FirefliesAuthError (both mean invalid key for Fireflies)"
metrics:
  duration: "2m 9s"
  completed: "2026-05-11"
  tasks_completed: 2
  tasks_total: 2
  test_count: 14
  test_pass: 14
---

# Phase 5 Plan 1: Fireflies API Client Layer Summary

Pydantic models, sync GraphQL client with retry/backoff, and API key resolution for Fireflies.ai transcript import -- mirroring existing ClaudeAPIClient patterns exactly.

## What Was Built

### Models (fireflies_models.py)
- 6 Pydantic models: `Speaker`, `MeetingAttendee`, `Sentence`, `TranscriptSummary`, `FirefliesTranscript`, `FirefliesTranscriptSummaryItem`
- All use `ConfigDict(extra="ignore")` per project convention
- 2 custom exceptions: `FirefliesAPIError` (with status_code/response_body), `FirefliesAuthError` (invalid API key)

### Client (fireflies_client.py)
- `FirefliesClient` class with context manager, identical structure to `ClaudeAPIClient`
- `_graphql()` method with exponential backoff retry (5 retries, 2s initial, doubling)
- Retryable: 429, 500, 502, 503. Immediate auth error: 401, 403
- GraphQL-level error detection (200 status with errors array and null data)
- Three public methods: `list_transcripts`, `list_all_transcripts` (auto-paginating), `get_transcript`

### Config (fireflies_config.py)
- `resolve_fireflies_api_key()` with 4-step resolution: CLI flag, FIREFLIES_API_KEY env var, .env file, interactive prompt (masked)
- Imports `_read_env_value` from existing `claude_dump.config` to reuse .env parsing

### Tests
- 6 model tests: full parsing, extra field tolerance, defaults, partial data
- 8 client tests: pagination, empty responses, full transcript detail, 401/403 auth, 429 retry, GraphQL errors

## Decisions Made

1. **base_url vs full graphql URL**: Used `base_url="https://api.fireflies.ai"` with POST to `/graphql` path, keeping the httpx Client pattern consistent with ClaudeAPIClient.
2. **id injection on get_transcript**: The Fireflies detail query does not return `id` in the response body, so the client injects it via `{"id": transcript_id, **raw}` before model_validate.
3. **401+403 combined**: Both 401 and 403 from Fireflies indicate an invalid API key, so both raise `FirefliesAuthError` without retry (unlike Claude API which only has 401).

## Deviations from Plan

None - plan executed exactly as written.

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|------------|
| T-05-01 (Spoofing) | Bearer token auth over HTTPS-only base_url; no HTTP fallback |
| T-05-02 (Tampering) | All models use extra="ignore"; no dynamic code execution from API data |
| T-05-03 (Info Disclosure) | API key not logged even in verbose mode; prompted with hide_input=True |
| T-05-04 (DoS) | Pagination capped at limit=50; retry backoff prevents tight loops on 429 |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 0d1c33e | Fireflies Pydantic models and API key config |
| 2 | 86c7025 | Fireflies GraphQL client with retry/backoff |

## Self-Check: PASSED

All 5 created files verified on disk. Both task commits (0d1c33e, 86c7025) confirmed in git log.
