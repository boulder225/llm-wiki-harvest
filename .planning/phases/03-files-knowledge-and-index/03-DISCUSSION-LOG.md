# Phase 3: Files, Knowledge, and Index - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 03-files-knowledge-and-index
**Mode:** auto
**Areas discussed:** Knowledge file output, File attachment downloads, Index generation, CLI integration, Progress reporting

---

## Knowledge File Output

| Option | Description | Selected |
|--------|-------------|----------|
| Write original content using file_name | Preserve content as-is to knowledge/ folder | auto |
| Add metadata header to each file | Wrap with YAML frontmatter (source, date) | |
| Rename to sanitized format | Use date_name_uuid format like conversations | |

**User's choice:** [auto] Write original content using file_name (recommended default)
**Notes:** /projects/{proj}/docs returns full markdown content inline -- no binary download needed

---

## File Attachment Organization

| Option | Description | Selected |
|--------|-------------|----------|
| Flat files/ with uuid prefix | {uuid[:8]}_{original_name} avoids collisions | auto |
| Per-conversation subfolders | files/{conv_uuid[:8]}/{original_name} | |
| Flat with original name only | Risk of collisions across conversations | |

**User's choice:** [auto] Flat files/ with uuid prefix (recommended default)
**Notes:** Simpler structure, UUID prefix handles collision, maintains readability

---

## Variant Fallback Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Per-kind fallback (FEATURES.md) | documents: document_pdf, images: preview->thumbnail, unknown: all three | auto |
| Always try all variants | Try document_pdf->preview->thumbnail for every file | |
| Single variant only | Just try document_pdf, skip on failure | |

**User's choice:** [auto] Per-kind fallback per FEATURES.md (recommended default)
**Notes:** Matches claudexit behavior, maximizes download success

---

## Index Content

| Option | Description | Selected |
|--------|-------------|----------|
| Full index with summary + links | Date, title, link per conversation + knowledge/files counts | auto |
| Minimal list | Just conversation names and links | |
| Structured with sections | Separate sections for conversations, knowledge, files | |

**User's choice:** [auto] Full index with summary + links (recommended default)
**Notes:** Provides navigable overview of entire export

---

## CLI Integration

| Option | Description | Selected |
|--------|-------------|----------|
| Extend dump with skip flags | --skip-knowledge, --skip-files on existing dump command | auto |
| Separate download commands | New `download-files` and `download-knowledge` commands | |
| All-in-one no flags | Always download everything, no skip options | |

**User's choice:** [auto] Extend dump with skip flags (recommended default)
**Notes:** Single command for full export, flags for selective runs

---

## Progress Reporting

| Option | Description | Selected |
|--------|-------------|----------|
| Separate progress tasks | Individual Rich progress tasks per stage | auto |
| Single combined progress | One progress bar for all operations | |
| Minimal logging | Just print completion messages | |

**User's choice:** [auto] Separate progress tasks per stage (recommended default)
**Notes:** Matches existing conversation progress pattern, clearer UX

---

## Claude's Discretion

- Rich progress bar styling for new stages
- Internal module organization for file download logic
- Index Markdown formatting details
- File size display in progress

## Deferred Ideas

None -- analysis stayed within phase scope
