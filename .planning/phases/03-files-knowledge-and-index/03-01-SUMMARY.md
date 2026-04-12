---
phase: 03-files-knowledge-and-index
plan: 01
subsystem: client, models, exporter
tags: [knowledge-docs, file-attachments, variant-fallback, progress-bars]
dependency_graph:
  requires: [01-01, 01-02, 02-01, 02-02, 02-03]
  provides: [knowledge-download, file-download, export-result]
  affects: [cli.py, exporter.py, client.py, models.py]
tech_stack:
  added: []
  patterns: [variant-fallback, filename-sanitization, deduplication-by-uuid]
key_files:
  created: []
  modified:
    - src/claude_dump/models.py
    - src/claude_dump/client.py
    - src/claude_dump/exporter.py
    - src/claude_dump/cli.py
decisions:
  - "Filename sanitization via PurePosixPath.name to prevent path traversal (T-03-01, T-03-04)"
  - "ExportResult dataclass replaces tuple return for richer reporting"
metrics:
  duration: 2min
  completed: "2026-04-12T13:42:00Z"
  tasks: 2
  files: 4
---

# Phase 03 Plan 01: Knowledge Docs and File Attachments Summary

KnowledgeDoc model, file download with variant fallback per file_kind, and extended export pipeline with Rich progress for all three stages.

## What Was Built

### Task 1: KnowledgeDoc model and client methods (431a2de)

- Added `KnowledgeDoc` Pydantic model with `extra="ignore"` pattern
- Added `list_knowledge_docs()` fetching `/organizations/{org}/projects/{proj}/docs`
- Added `download_file()` using correct `/api/{org}/files/{uuid}/{variant}` URL path
- Added `download_file_with_fallback()` with variant strategy: images try preview/thumbnail, documents try document_pdf, unknown tries all three

### Task 2: Extended export pipeline (b175292)

- Added `ExportResult` dataclass with counts for conversations, knowledge, and files
- Knowledge stage: fetches docs, writes content to `knowledge/` folder
- File attachment stage: deduplicates by file_uuid, downloads with fallback, writes to `files/`
- Single Rich Progress wraps all three stages with separate task bars
- Filename sanitization prevents path traversal (threat mitigations T-03-01, T-03-04)
- Updated CLI to display counts for all three export stages

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed CLI tuple unpacking broken by new ExportResult return type**
- **Found during:** Task 2
- **Issue:** cli.py used `exported, failed = export_project(...)` which broke with ExportResult
- **Fix:** Updated CLI to use `result = export_project(...)` and access named fields
- **Files modified:** src/claude_dump/cli.py
- **Commit:** b175292

## Threat Mitigations Applied

| Threat | File | Mitigation |
|--------|------|------------|
| T-03-01 | exporter.py | `_sanitize_filename()` strips path components from file attachment names |
| T-03-04 | exporter.py | Same sanitizer applied to knowledge doc filenames |

## Known Stubs

None -- all data flows are wired to real API calls.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 431a2de | feat(03-01): add KnowledgeDoc model and file download client methods |
| 2 | b175292 | feat(03-01): extend export pipeline with knowledge docs and file attachments |

## Self-Check: PASSED
