# Roadmap: Claude Project Dumper

## Overview

This project delivers a Python CLI tool that exports Claude.ai project data (conversations, knowledge files, attachments) to organized local Markdown files. The roadmap follows the data flow: authenticate and discover projects first, then export the core value (conversations as Markdown), then complete the picture with file downloads and an index. Each phase produces a usable tool that does more than the last.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Auth and Project Discovery** - Authenticate via session cookie, discover orgs, list and select projects
- [ ] **Phase 2: Conversation Export** - Fetch and render all conversations as Markdown with structured output
- [ ] **Phase 3: Files, Knowledge, and Index** - Download all attached files, knowledge docs, and generate an index

## Phase Details

### Phase 1: Auth and Project Discovery
**Goal**: Users can authenticate and browse their Claude.ai projects from the command line
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, PROJ-01, PROJ-02, RES-01, RES-04
**Success Criteria** (what must be TRUE):
  1. User can provide a session cookie (via CLI flag, env var, or interactive prompt) and the tool validates it before proceeding
  2. User can see a list of all projects in their Claude.ai account
  3. User can select a project to export (interactively or via --project flag)
  4. Tool detects expired or invalid cookies and shows a clear error message instead of cryptic failures
  5. Tool handles HTTP 429/529 responses with retry/backoff instead of crashing
**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md -- Project scaffold, Pydantic models, API client with retry/backoff
- [x] 01-02-PLAN.md -- Cookie config, CLI entry point, auth validation, project selection

### Phase 2: Conversation Export
**Goal**: Users get every conversation in a selected project as well-formatted Markdown files on disk
**Depends on**: Phase 1
**Requirements**: CONV-01, CONV-02, CONV-03, CONV-04, CONV-05, CONV-06, OUT-01, OUT-02, RES-02, RES-03
**Success Criteria** (what must be TRUE):
  1. Running the tool on a project produces a `conversations/` folder with one Markdown file per conversation, named with date-title-uuid format for sorting
  2. Each Markdown file has sender labels, timestamps, thinking blocks, tool use in code fences, and artifact placeholders
  3. User sees a progress counter during export showing which conversation is being processed
  4. Each conversation is written to disk immediately (not buffered), so partial exports are usable if interrupted
  5. If the session expires mid-export, the tool halts with a clear message and the conversations already exported remain intact
**Plans:** 3 plans

Plans:
- [x] 02-01-PLAN.md -- Pydantic models for conversations/messages, API client methods with pagination
- [x] 02-02-PLAN.md -- Markdown renderer for all content block types, filename sanitization
- [x] 02-03-PLAN.md -- Exporter pipeline with write-as-you-go, CLI wiring with Rich progress

### Phase 3: Files, Knowledge, and Index
**Goal**: Users get a complete project export including all knowledge documents, file attachments, and a navigable index
**Depends on**: Phase 2
**Requirements**: FILE-01, FILE-02, FILE-03, OUT-01, OUT-03
**Success Criteria** (what must be TRUE):
  1. Running the tool produces a `knowledge/` folder with all project knowledge files downloaded
  2. Running the tool produces a `files/` folder with all conversation file attachments downloaded (using variant fallback for different file types)
  3. An `index.md` file is generated listing all exported conversations with dates and links
  4. The complete output folder structure (`conversations/`, `knowledge/`, `files/`, `index.md`) is self-contained and navigable
**Plans:** 2 plans

Plans:
- [ ] 03-01-PLAN.md -- KnowledgeDoc model, client methods for knowledge/file download, exporter pipeline with progress
- [ ] 03-02-PLAN.md -- Index.md generation, --skip-knowledge/--skip-files CLI flags, completion summary

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Auth and Project Discovery | 2/2 | Complete | 2026-04-12 |
| 2. Conversation Export | 0/3 | Planned | - |
| 3. Files, Knowledge, and Index | 0/2 | Planned | - |
