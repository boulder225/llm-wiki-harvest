# Phase 3: Files, Knowledge, and Index - Context

**Gathered:** 2026-04-12 (auto mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Download all project knowledge files, download all conversation file attachments (using variant fallback for different file types), and generate an index.md listing all exported conversations. The complete output folder structure (`conversations/`, `knowledge/`, `files/`, `index.md`) must be self-contained and navigable. No new conversation rendering or auth logic -- those are done.

</domain>

<decisions>
## Implementation Decisions

### Knowledge File Download
- **D-01:** Use `/api/organizations/{org}/projects/{proj}/docs` endpoint which returns full markdown content inline -- no binary download needed
- **D-02:** Write each knowledge file to `{output_dir}/knowledge/` folder using the original `file_name` from the API response
- **D-03:** Preserve original content as-is (no added metadata header). If `file_name` is missing, fall back to `{uuid[:8]}.md`
- **D-04:** Add `list_knowledge_docs()` method to ClaudeAPIClient returning a list of Pydantic models

### File Attachment Download
- **D-05:** Collect all unique `files_v2` entries across all conversation messages during the export pass (avoid re-downloading duplicates referenced in multiple messages)
- **D-06:** Download each file via `/api/{org}/files/{file_uuid}/{variant}` -- note the URL uses `/api/{org}/` NOT `/api/organizations/{org}/`
- **D-07:** Variant fallback strategy per file_kind: documents try `document_pdf` first, images try `preview` then `thumbnail`, unknown types try all three in order (`document_pdf` -> `preview` -> `thumbnail`)
- **D-08:** Save to `{output_dir}/files/` folder with filename `{file_uuid[:8]}_{original_name}` to avoid collisions while staying readable
- **D-09:** Add `download_file()` method to ClaudeAPIClient that returns binary content, using the existing `_request` retry pattern but accepting binary response
- **D-10:** Non-fatal failures: if a file download fails after retries, log a warning and continue (don't abort the whole export)

### Index Generation
- **D-11:** Generate `{output_dir}/index.md` listing all exported conversations with date, title, and relative link to the Markdown file
- **D-12:** Conversations sorted by date descending (newest first)
- **D-13:** Include summary sections at the top: total conversations exported, knowledge files count, file attachments count
- **D-14:** Include a knowledge files section listing each knowledge doc with link to `knowledge/{filename}`
- **D-15:** Index generated after all other exports complete (uses the actual files written to disk)

### CLI Integration
- **D-16:** Extend the existing `dump` command -- no new commands needed
- **D-17:** Add `--skip-knowledge` flag to skip knowledge file download
- **D-18:** Add `--skip-files` flag to skip file attachment download
- **D-19:** Update the completion summary to report knowledge files downloaded and attachments downloaded alongside conversation count

### Progress Reporting
- **D-20:** Separate Rich progress tasks for each stage: conversations (existing), knowledge files, file attachments
- **D-21:** File download progress shows `Downloading: {filename}` with spinner and M/N counter

### Claude's Discretion
- Exact Rich progress bar styling for new stages
- Whether to add file size info in progress display
- Internal helper organization (new module vs extending exporter.py)
- Index Markdown formatting details (table vs list for conversations)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### API Endpoints and File Download
- `.planning/research/FEATURES.md` -- File download endpoints (`/api/{org}/files/{uuid}/{variant}`), variant fallback strategy, knowledge docs endpoint (`/projects/{proj}/docs` returns content inline)
- `.planning/research/FEATURES.md` SS File Download Endpoints -- Critical URL structure note: `/api/{org}/files/` NOT `/api/organizations/{org}/files/`

### Architecture and Patterns
- `.planning/research/ARCHITECTURE.md` -- Module structure, data flow patterns
- `.planning/research/PITFALLS.md` -- P4 (rate limiting), P5 (API response defensiveness)

### Existing Implementation
- `src/claude_dump/client.py` -- ClaudeAPIClient with _request retry logic; add new methods here
- `src/claude_dump/models.py` -- FileRef and Attachment models already exist; add KnowledgeDoc model
- `src/claude_dump/exporter.py` -- Export pipeline; extend with knowledge and file download stages
- `src/claude_dump/cli.py` -- Click CLI dump command; add --skip-knowledge and --skip-files flags

### Prior Phase Context
- `.planning/phases/01-auth-and-project-discovery/01-CONTEXT.md` -- Auth patterns, client setup
- `.planning/phases/02-conversation-export/02-CONTEXT.md` -- Conversation export pipeline, write-as-you-go pattern, filename format

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ClaudeAPIClient._request()` (client.py): Retry/backoff logic -- extend for binary responses
- `_extract_list()` helper (client.py): Handles `[...]` and `{"data": [...]}` wrappers -- reuse for knowledge docs
- `FileRef` model (models.py): Already has `file_uuid`, `file_name`, `file_kind` -- use for deduplication
- `Attachment` model (models.py): Has `file_name`, `file_type`, `extracted_content`
- `Rich.progress` (exporter.py): Progress pattern already established for conversations -- extend with new tasks
- `make_filename()` (markdown.py): Filename sanitization logic -- reuse or adapt for file attachment naming

### Established Patterns
- Sync-only HTTP client (no async) -- per Phase 1 decision
- All HTTP calls through `_request()` with retry/backoff
- Pydantic models with `ConfigDict(extra="ignore")` for API tolerance
- Write-as-you-go: persist each item immediately after processing
- Sequential fetching to avoid rate limits

### Integration Points
- `export_project()` in exporter.py is the main orchestrator -- extend with knowledge and file download stages
- `dump` command in cli.py calls `export_project()` -- add new flags and update summary output
- File attachment UUIDs come from `ChatMessage.files_v2` which is already parsed during conversation fetch

</code_context>

<specifics>
## Specific Ideas

- Knowledge docs endpoint returns full content inline -- this is a simple write operation, not a binary download
- File download URL uses `/api/{org}/` prefix (not `/api/organizations/{org}/`) -- this is different from all other endpoints
- `files_v2` on messages may reference the same file across multiple messages -- deduplicate by `file_uuid` before downloading
- The `file_kind` field on FileRef can inform variant selection (e.g., "image" -> try preview first)

</specifics>

<deferred>
## Deferred Ideas

None -- analysis stayed within phase scope

</deferred>

---

*Phase: 03-files-knowledge-and-index*
*Context gathered: 2026-04-12*
