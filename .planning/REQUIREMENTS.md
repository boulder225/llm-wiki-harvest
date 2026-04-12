# Requirements: Claude Project Dumper

**Defined:** 2026-04-12
**Core Value:** Reliably dump every conversation and every attached file from a Claude.ai Project into organized, readable local Markdown files.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Authentication

- [x] **AUTH-01**: User can authenticate using a manually provided session cookie (via CLI arg, env var, or interactive prompt)
- [x] **AUTH-02**: Tool discovers organization ID from cookie or `/api/organizations` endpoint
- [x] **AUTH-03**: Tool validates session cookie before starting export (detect expired/invalid cookies early)

### Project Discovery

- [x] **PROJ-01**: User can list all projects in their Claude.ai account
- [x] **PROJ-02**: User can select a project to export (interactive prompt or `--project` flag)

### Conversation Export

- [x] **CONV-01**: Tool fetches all conversations within the selected project (with pagination support)
- [x] **CONV-02**: Each conversation is exported as a well-formatted Markdown file with sender labels and timestamps
- [x] **CONV-03**: Thinking/reasoning blocks are rendered in the Markdown output
- [x] **CONV-04**: Tool use and tool result blocks are rendered in code fences
- [x] **CONV-05**: Artifact references are replaced with clear placeholder text (content stripped server-side)
- [x] **CONV-06**: Conversation summary is included in the Markdown header when available

### File Downloads

- [x] **FILE-01**: Tool downloads all project knowledge files to a `knowledge/` folder
- [x] **FILE-02**: Tool downloads file attachments from conversations to a `files/` folder
- [x] **FILE-03**: File download uses variant fallback strategy (document_pdf, preview, thumbnail)

### Output Structure

- [x] **OUT-01**: Output is organized in a structured folder hierarchy (`conversations/`, `knowledge/`, `files/`)
- [x] **OUT-02**: Conversation filenames use `{date}_{sanitized-title}_{uuid[:8]}.md` format for sort order and collision avoidance
- [ ] **OUT-03**: An `index.md` file is generated listing all conversations with dates and links

### Resilience

- [x] **RES-01**: Tool handles rate limiting with exponential backoff on HTTP 429/529
- [x] **RES-02**: Tool shows progress indication during export (conversation counter)
- [x] **RES-03**: Tool uses write-as-you-go pattern (persist each conversation immediately, don't buffer all in memory)
- [x] **RES-04**: Tool detects session expiry mid-export and halts with a clear message

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enhanced Output

- **ENH-01**: JSON dual output format alongside Markdown
- **ENH-02**: Configurable output format via `--format md|json|both` flag
- **ENH-03**: Incremental/resumable export (skip already-exported conversations on re-run)

### Additional Data

- **ADD-01**: Export project-scoped memory
- **ADD-02**: Selective conversation export by UUID (`--conversation` flag)
- **ADD-03**: File attachment extracted text content inline in Markdown

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automatic cookie extraction from browser | Platform-specific crypto (DPAPI/Keychain), brittle, biggest complexity source in claudexit |
| GUI / web interface | CLI-only tool; output files are the interface |
| Account-to-account migration | Complex write operations, high risk of data loss |
| Artifact export | Claude strips artifact source code server-side; no known workaround |
| Real-time sync / watch mode | Polling undocumented API risks rate limiting or account flagging |
| Memory export (v1) | Account-global, tangential to project export |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Complete |
| AUTH-02 | Phase 1 | Complete |
| AUTH-03 | Phase 1 | Complete |
| PROJ-01 | Phase 1 | Complete |
| PROJ-02 | Phase 1 | Complete |
| CONV-01 | Phase 2 | Complete |
| CONV-02 | Phase 2 | Complete |
| CONV-03 | Phase 2 | Complete |
| CONV-04 | Phase 2 | Complete |
| CONV-05 | Phase 2 | Complete |
| CONV-06 | Phase 2 | Complete |
| FILE-01 | Phase 3 | Complete |
| FILE-02 | Phase 3 | Complete |
| FILE-03 | Phase 3 | Complete |
| OUT-01 | Phase 2 | Complete |
| OUT-02 | Phase 2 | Complete |
| OUT-03 | Phase 3 | Pending |
| RES-01 | Phase 1 | Complete |
| RES-02 | Phase 2 | Complete |
| RES-03 | Phase 2 | Complete |
| RES-04 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0

---
*Requirements defined: 2026-04-12*
*Last updated: 2026-04-12 after roadmap creation*
