# Phase 2: Conversation Export - Context

**Gathered:** 2026-04-12 (auto mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Fetch all conversations within a selected project, render each as a well-formatted Markdown file with proper handling of all content block types (text, thinking, tool use, tool results, artifacts), write to an organized folder structure with progress indication. Each conversation is persisted immediately (write-as-you-go). No file downloads in this phase -- that's Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Conversation Fetching
- **D-01:** Use `/api/organizations/{org}/chat_conversations/{conv}?tree=True&rendering_mode=messages&render_all_tools=true` for full message content
- **D-02:** List conversations via `/api/organizations/{org}/projects/{proj}/conversations_v2?limit=1000&offset=0`; paginate by incrementing offset until response returns empty data array
- **D-03:** Fetch conversations sequentially (one at a time) to minimize rate limit risk -- no parallel fetching

### Markdown Block Rendering
- **D-04:** Thinking/reasoning blocks rendered as collapsible `<details><summary>Thinking</summary>` sections -- keeps output scannable while preserving full thinking content
- **D-05:** `tool_use` blocks rendered as fenced code blocks with the tool name as a label: ````tool_use: {name}` followed by JSON-formatted input
- **D-06:** `tool_result` blocks rendered as fenced code blocks labeled `tool_result`
- **D-07:** Artifact references replaced with placeholder: `> [Artifact: content not available - Claude strips artifact source code server-side]`
- **D-08:** Text blocks rendered as-is with line breaks preserved
- **D-09:** Each message prefixed with sender label and timestamp: `### Human` or `### Assistant` followed by `*{ISO timestamp}*`

### Markdown File Structure
- **D-10:** Each conversation file starts with a YAML-style metadata header:
  ```
  ---
  title: {conversation name}
  model: {model used}
  created: {created_at}
  updated: {updated_at}
  uuid: {conversation uuid}
  ---
  ```
- **D-11:** Conversation summary (from API `summary` field) included after the header when available, as a blockquote

### Output Structure
- **D-12:** Output folder: `{output_dir}/conversations/` (per OUT-01)
- **D-13:** Filename format: `{YYYY-MM-DD}_{sanitized-title}_{uuid[:8]}.md` (per OUT-02)
- **D-14:** Title sanitization: lowercase, replace spaces with hyphens, strip non-alphanumeric except hyphens/underscores, collapse consecutive hyphens, truncate to 100 chars

### Progress and Resilience
- **D-15:** Rich progress bar showing `Exporting conversation {N}/{total}: {name}` with a visual progress bar (per RES-02)
- **D-16:** Write-as-you-go: each conversation written to disk immediately after rendering, not buffered in memory (per RES-03)
- **D-17:** If session expires mid-export (SessionExpiredError), halt with clear message; already-exported files remain intact on disk
- **D-18:** Add new Pydantic models for Conversation (metadata) and ChatMessage (content blocks) with `extra="ignore"`

### CLI Integration
- **D-19:** The existing `dump` command in cli.py gets the export logic wired in -- after project selection, call the exporter
- **D-20:** `--output` flag (already defined in cli.py) specifies the root output directory, defaults to current directory

### Claude's Discretion
- Exact Rich progress bar styling and refresh rate
- Whether to add a `--dry-run` flag for listing conversations without exporting
- Internal module organization (exporter.py vs markdown.py split)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### API Endpoints and Response Shapes
- `.planning/research/FEATURES.md` -- Complete API endpoint documentation: conversation listing, message fetching, content block types, query parameters
- `.planning/research/FEATURES.md` §Message Content Structure -- Block types: text, thinking, tool_use, tool_result with field names

### Architecture and Patterns
- `.planning/research/ARCHITECTURE.md` -- Module structure, data flow patterns, exporter design
- `.planning/research/PITFALLS.md` -- P5 (API response defensiveness), P4 (rate limiting), P3 (message ordering)

### Existing Implementation
- `src/claude_dump/client.py` -- ClaudeAPIClient with _request retry logic; add new methods here
- `src/claude_dump/models.py` -- Pydantic models with extra="ignore" pattern; add Conversation and ChatMessage models here
- `src/claude_dump/cli.py` -- Click CLI with dump command; wire exporter into the dump command

### Prior Phase Context
- `.planning/phases/01-auth-and-project-discovery/01-CONTEXT.md` -- Phase 1 decisions that carry forward

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ClaudeAPIClient` (client.py): Add `list_conversations()` and `get_conversation()` methods following the existing pattern
- `_extract_list()` helper (client.py): Handles both bare array and `{"data": [...]}` response wrapper -- reuse for conversation listing
- Pydantic model pattern (models.py): `ConfigDict(extra="ignore")` established; follow for new Conversation/ChatMessage models
- Rich is already a dependency: use `rich.progress` for progress bar display

### Established Patterns
- Sync-only HTTP client (no async) -- per Phase 1 decision
- All HTTP calls go through `_request()` which handles retry/backoff
- `_require_org_id()` validation before org-scoped calls
- Models are pure data (no methods, no I/O)

### Integration Points
- `cli.py` `dump` command already has `--project` and `--output` options; needs exporter call wired in
- `_authenticate()` helper in cli.py returns configured client -- exporter receives this client
- New module `exporter.py` orchestrates: list conversations -> fetch each -> render markdown -> write file
- New module `markdown.py` handles: ChatMessage content blocks -> Markdown string conversion

</code_context>

<specifics>
## Specific Ideas

- The `.env` file has `CLAUDE_PROJECT_UUID=019af253-8b25-7137-aaaf-3d10d7a49442` for the DT One project -- useful for testing
- Thinking blocks may include a "characters truncated" note -- preserve this in the output
- The `attachments[].extracted_content` field contains text extracted from PDFs -- include this inline in Markdown for Phase 2 (it's already in the API response, no download needed)

</specifics>

<deferred>
## Deferred Ideas

None -- analysis stayed within phase scope

</deferred>

---

*Phase: 02-conversation-export*
*Context gathered: 2026-04-12*
