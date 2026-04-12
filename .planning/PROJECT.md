# Claude Project Dumper

## What This Is

A command-line tool that exports all conversations and uploaded files (transcripts, documents) from a Claude.ai Project into a local folder structure with Markdown-formatted conversations. It targets macOS users who provide their session cookie manually.

## Core Value

Reliably dump every conversation and every attached file from a Claude.ai Project into organized, readable local Markdown files.

## Requirements

### Validated

- [x] Authenticate to Claude.ai API using a manually provided session cookie — Validated in Phase 1: auth-and-project-discovery
- [x] List and select Claude.ai Projects from the user's account — Validated in Phase 1: auth-and-project-discovery

### Active
- [ ] Fetch all conversations within a selected Project
- [ ] Export each conversation as a well-formatted Markdown file
- [ ] Download files/transcripts attached to individual chats
- [ ] Download Project Knowledge files
- [ ] Organize output into a structured local folder hierarchy
- [ ] Run on macOS without platform-specific dependencies (Windows DPAPI etc.)

### Out of Scope

- GUI / web interface -- CLI-only tool
- Automatic cookie extraction from browser -- user provides cookie manually
- Artifact export -- Claude strips artifact source code server-side, no known endpoint returns it
- Real-time sync or watching for new conversations
- Import/restore back into Claude.ai
- Windows/Linux-specific features -- macOS-first (though should work cross-platform via Python)

## Context

- Claude.ai exposes internal REST APIs (e.g. `/api/organizations/{org_id}/projects`, `/api/organizations/{org_id}/chat_conversations`) that can be called with session cookies
- The `withLinda/claude-project-conversations-exporter` (JS, browser console) and `Rahul-999-alpha/claudexit` (Python, Windows-only) are prior art
- `claudexit` uses Windows DPAPI for cookie extraction which doesn't work on macOS
- The browser-based exporters require manual console pasting and can't easily save files to disk
- Claude's internal API uses organization IDs that need to be discovered first
- Files/transcripts attached to chats are served via separate endpoints
- Session cookies expire and may require re-authentication

## Constraints

- **Auth**: Session cookie only -- no OAuth or API key available for claude.ai web
- **API stability**: Internal APIs are undocumented and may change without notice
- **Language**: Python preferred (widely available on macOS, good HTTP/file handling)
- **Dependencies**: Minimal -- requests library at most, no heavy frameworks
- **Rate limiting**: Must respect any rate limits to avoid account issues

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python over JS/Node | Better file I/O, no browser dependency, widely available on macOS | -- Pending |
| Manual cookie input over auto-extraction | Cross-platform, simpler, no keychain/DPAPI complexity | -- Pending |
| Markdown output format | Human-readable, versionable, works with any editor/Obsidian | -- Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check -- still the right priority?
3. Audit Out of Scope -- reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-12 after initialization*
