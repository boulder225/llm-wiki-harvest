# Domain Pitfalls

**Domain:** Claude.ai Project data exporter (internal API scraping)
**Researched:** 2026-04-12
**Sources:** withLinda/claude-project-conversations-exporter (source code analysis), Rahul-999-alpha/claudexit (source code analysis), Claude.ai internal API behavior observed in both tools

## Critical Pitfalls

Mistakes that cause total export failure, data loss, or account issues.

### Pitfall 1: Artifact Content Is Stripped Server-Side

**What goes wrong:** The Claude.ai API does not return artifact source code (interactive code blocks, HTML previews, React components) in conversation responses. The `content` array in `chat_messages` contains tool_use/tool_result blocks referencing artifacts, but the actual rendered source is absent. Building an exporter that assumes all conversation content is in the API response will silently produce incomplete exports.

**Why it happens:** Artifacts are rendered client-side from a separate content store. The `chat_conversations` endpoint returns message-level content only. There is no known public or internal endpoint that returns artifact source code.

**Consequences:** Users export conversations expecting complete code, but get truncated tool references instead. This is the single most common user disappointment with export tools.

**Warning signs:** Tool_use blocks with `name: "artifact"` but no corresponding source in the response. Content that appears in the web UI but is missing from API output.

**Prevention:** Explicitly document this limitation upfront. Parse tool_use blocks for artifact metadata (title, type, language) and include a placeholder: `[Artifact: "filename.py" - source not available via API]`. Do NOT silently omit these blocks.

**Detection:** Compare exported markdown character count against what a user sees in the web UI for a conversation with known artifacts.

**Phase relevance:** Phase 1 (core export). Must be handled from the start; retrofitting artifact placeholders is messy.

---

### Pitfall 2: Organization ID Discovery Fragility

**What goes wrong:** Every Claude.ai API endpoint requires an organization UUID in the path (`/api/organizations/{org_id}/...`). For a CLI tool that receives only a session cookie, discovering this org ID is non-trivial. The browser-based exporter (withLinda) uses 5+ fallback methods (cookie `lastActiveOrg`, localStorage, sessionStorage, window globals, cookie scanning). A CLI tool cannot access any of these except the cookie.

**Why it happens:** Claude.ai uses org-scoped API paths but does not expose a simple `/api/me` or `/api/whoami` endpoint that returns the org ID given just a session cookie. The `lastActiveOrg` cookie is the primary source, but users pasting a `sessionKey` cookie may not think to also paste `lastActiveOrg`.

**Consequences:** Tool cannot make any API calls at all. Total failure with a confusing error.

**Warning signs:** 403 or 404 responses on the first API call. User provides only `sessionKey` but not the org cookie.

**Prevention:**
1. Require users to provide the full cookie header string (not just `sessionKey`), which naturally includes `lastActiveOrg`.
2. Alternatively, call a known endpoint like `GET /api/auth/current_account` or `GET /api/organizations` with just the session cookie to discover available orgs. The claudexit tool implicitly does this via the `lastActiveOrg` cookie.
3. Provide clear instructions: "Copy the full Cookie header from a request in DevTools Network tab."
4. Validate that org ID is present before attempting any other API call, with a specific error message if missing.

**Detection:** First API call returns non-200. Parse the error and guide the user.

**Phase relevance:** Phase 1 (authentication). This is literally the first thing that must work.

---

### Pitfall 3: Session Cookie Expiry Mid-Export

**What goes wrong:** Claude.ai session cookies (`sessionKey`) expire. For large projects with 100+ conversations, an export can take 10-20 minutes. If the cookie expires mid-export, later conversations fail while earlier ones succeeded, producing a partial export that the user may not realize is incomplete.

**Why it happens:** Session cookies have a server-controlled TTL. Anthropic can invalidate sessions at any time. There is no refresh token mechanism for the web session.

**Consequences:** Partial export with no clear indication of which conversations were missed. User believes export is complete.

**Warning signs:** 401 responses appearing partway through a batch after earlier batches succeeded.

**Prevention:**
1. Track and report success/failure counts prominently: "Exported 87/142 conversations (55 failed)".
2. Detect 401 mid-export and halt immediately with a clear message rather than continuing to fail on every remaining conversation.
3. Implement resume capability: save progress state so re-running with a fresh cookie picks up where it left off (skip already-exported conversations by UUID).
4. Validate the cookie with a lightweight API call before starting the full export.

**Detection:** Monitor HTTP status codes per request. A 401 after successful requests = expired session.

**Phase relevance:** Phase 1 (core export) for detection/reporting. Phase 2 for resume capability.

---

### Pitfall 4: Rate Limiting Causing Account Flags

**What goes wrong:** Hammering the Claude.ai internal API too aggressively can trigger rate limiting (429 responses) or potentially flag the account for unusual activity. Unlike the official Anthropic API, the web API's rate limits are undocumented and can change without notice.

**Why it happens:** The internal API is designed for interactive browser use (one conversation at a time), not bulk data extraction. Fetching 200 conversations in parallel is not a usage pattern the API expects.

**Consequences:** 429 errors slow down export. In the worst case, the session could be invalidated or the account temporarily restricted.

**Warning signs:** Increasing frequency of 429 responses. Sudden 403 after many successful requests.

**Prevention:**
1. Conservative defaults: batch size of 3-5 concurrent requests (withLinda uses 5).
2. Mandatory delays between batches: 500ms minimum, scaling up for larger projects (withLinda uses 750ms for >50 convos, 1000ms for >200).
3. Exponential backoff on 429: start at 1s, cap at 10s, max 3 retries per conversation.
4. Include a `--delay` CLI flag so users can increase delays if they encounter issues.
5. Never parallelize conversation list fetching AND conversation detail fetching simultaneously.

**Detection:** Log all 429 responses with timestamps. If 3+ consecutive 429s occur, automatically increase delay.

**Phase relevance:** Phase 1 (core export). Must be baked in from the start; adding rate limiting to an already-built parallel fetcher is a rewrite.

## Moderate Pitfalls

### Pitfall 5: API Response Structure Changes Without Notice

**What goes wrong:** The internal Claude.ai API is undocumented and Anthropic can change response shapes at any time. The withLinda exporter already handles two response formats for the conversations list endpoint: `{ data: [...] }` and a bare array `[...]`. Field names, nesting, and available fields can change between deployments.

**Why it happens:** This is an internal API, not a public contract. Anthropic has no obligation to maintain backward compatibility.

**Prevention:**
1. Defensive parsing: check for expected fields, provide fallbacks, never assume a field exists.
2. Wrap all API response parsing in try/except with informative errors that include the actual response shape.
3. Version-stamp exports with the date so users know when the tool last worked.
4. Keep API interaction in a single module so changes require updating one file, not scattered parsing logic.

**Detection:** Any `KeyError`, `TypeError`, or unexpected `None` during response parsing. Log the raw response (first 500 chars) on failure for debugging.

**Phase relevance:** Phase 1 (API client). Design the API client module with change resilience from day one.

---

### Pitfall 6: Pagination Assumptions on Conversation Lists

**What goes wrong:** The conversations list endpoint (`conversations_v2`) accepts `limit` and `offset` parameters. The withLinda exporter requests `limit=1000` and assumes all conversations come back in one call. For very active projects, this may not return everything. The claudexit tool fetches `chat_conversations` (all conversations, not project-scoped) with no visible pagination handling.

**Why it happens:** Most projects have <100 conversations, so a single call with limit=1000 works. But there is no guarantee the API honors arbitrary limit values, and large projects could exceed any assumed maximum.

**Consequences:** Silently missing conversations. User exports 1000 conversations from a project with 1200 and never knows about the missing 200.

**Prevention:**
1. Always paginate: fetch with a reasonable page size (e.g., 100), check if the response count equals the page size, and fetch the next page if so.
2. Compare the count of fetched conversations against any total count in the API response (if available).
3. Log the total fetched and warn if it equals exactly the limit (suggesting truncation).

**Detection:** Response array length equals the requested limit exactly.

**Phase relevance:** Phase 1 (conversation listing). Easy to implement correctly from the start, painful to retrofit.

---

### Pitfall 7: File Download Endpoint Variant Guessing

**What goes wrong:** Uploaded files in conversations are served via `/api/{org_id}/files/{file_uuid}/{variant}` where `variant` can be `document_pdf`, `preview`, `thumbnail`, or potentially others. The correct variant depends on the file type, and there is no endpoint to query available variants. The claudexit tool tries variants in sequence and silently skips files where all variants fail.

**Why it happens:** The file serving API is designed for the web UI which knows the correct variant from the upload metadata. External tools must guess.

**Consequences:** Missing files in export. PDF uploaded as an image variant, or vice versa, may download but be corrupted/wrong format.

**Prevention:**
1. Read `file_kind` from the `files_v2` array in message metadata to determine the correct variant (claudexit does this).
2. Map: `document` -> `document_pdf`, `image` -> `preview`, unknown -> try both.
3. Verify downloaded content: check file magic bytes match expected type.
4. Log all failed file downloads with UUID and attempted variants.
5. Save file metadata (original name, kind, UUID) in a manifest even when download fails, so users know what is missing.

**Detection:** Download returns 404 or content-type mismatch.

**Phase relevance:** Phase 2 (file downloads). Not needed for MVP conversation export.

---

### Pitfall 8: Thinking Block Truncation

**What goes wrong:** Extended thinking content in Claude's responses can be very large (10K+ characters). The API sometimes returns truncated thinking with a note like "X characters truncated." Exporters that naively include this get incomplete thinking blocks. Exporters that skip thinking entirely lose valuable context.

**Why it happens:** Server-side truncation to reduce response payload size. The web UI may have access to the full thinking via a separate mechanism.

**Consequences:** Incomplete thinking blocks in exported conversations. The withLinda exporter explicitly checks for "characters truncated" and adds a note, but the full content is still lost.

**Prevention:**
1. Check for truncation markers in thinking content.
2. Include thinking blocks in export but clearly mark truncated ones: `[Thinking truncated - X characters omitted by API]`.
3. Wrap thinking in collapsible sections (as claudexit does with `<details>`) since they can be very long.
4. Provide a `--no-thinking` flag for users who want cleaner exports.

**Detection:** String matching for "characters truncated" or thinking content that ends abruptly.

**Phase relevance:** Phase 1 (markdown conversion). Handle during initial message-to-markdown implementation.

---

### Pitfall 9: Conversation Name Sanitization for Filenames

**What goes wrong:** Conversation names are user-generated and can contain characters illegal in filenames (`/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`), Unicode characters, extremely long strings, or be empty/duplicate. Using raw conversation names as filenames causes crashes on certain filesystems, overwrites, or encoding errors.

**Why it happens:** Developers test with their own clean conversation names and miss edge cases.

**Consequences:** File creation errors, silent overwrites of different conversations with the same sanitized name, or mojibake filenames.

**Prevention:**
1. Strip illegal characters (claudexit's `sanitize_filename` does this well).
2. Truncate to a max length (50 chars is reasonable; 255 is the filesystem max but too long for usability).
3. Append conversation UUID (first 8 chars) to prevent collisions: `my-conversation-a1b2c3d4.md`.
4. Handle empty names: fall back to `untitled-{uuid[:8]}`.
5. Use consistent encoding (UTF-8) for filenames.

**Detection:** Test with conversations named `foo/bar`, `CON` (Windows reserved), empty string, and 500-character names.

**Phase relevance:** Phase 1 (file output). Must handle from the start.

## Minor Pitfalls

### Pitfall 10: Timezone Handling in Timestamps

**What goes wrong:** The API returns ISO 8601 timestamps in UTC. Exporting these as-is or converting with `toLocaleString()` (which uses the system timezone) creates inconsistency. Different exports of the same conversation produce different timestamps on machines in different timezones.

**Prevention:** Always export UTC timestamps. Include timezone indicator: `2026-04-10T14:30:00Z`. Optionally add local time in parentheses.

**Phase relevance:** Phase 1. Trivial to handle correctly from the start.

---

### Pitfall 11: Memory/Performance on Very Large Conversations

**What goes wrong:** A single conversation can have hundreds of messages with long code blocks. Loading the full JSON response into memory, then building a markdown string, can consume significant RAM for a Python script processing many such conversations sequentially.

**Prevention:** Process conversations one at a time and write to disk immediately rather than accumulating all in memory. Use streaming writes for large markdown files.

**Phase relevance:** Phase 1 (core export loop). Process-and-write rather than accumulate-and-dump.

---

### Pitfall 12: Ignoring Project Knowledge Files

**What goes wrong:** Projects have knowledge documents (uploaded reference files) separate from conversation-attached files. The claudexit tool handles these via `get_project_docs`, but the endpoint returns metadata, and the actual content requires a separate download. Forgetting these means the export misses critical project context.

**Prevention:** Explicitly include project knowledge export as a feature. The endpoint is `GET /api/organizations/{org}/projects/{project_uuid}/docs`. Download each doc's content separately.

**Phase relevance:** Phase 2 (after core conversation export works).

---

### Pitfall 13: Content-Type Mismatch on File Downloads

**What goes wrong:** Downloaded files may not match their original format. A PDF uploaded to Claude might be served with a generic `application/octet-stream` content type, or an image might be served as a different resolution/format than the original.

**Prevention:** Use the original `file_name` from metadata for the saved filename (preserving extension). Do not rely on Content-Type headers to determine file extension. Verify file magic bytes for critical formats.

**Phase relevance:** Phase 2 (file downloads).

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Authentication (Phase 1) | Org ID not discovered from cookie alone | Provide clear instructions for full cookie header; attempt org discovery endpoint |
| Authentication (Phase 1) | Cookie format varies (some paste `sessionKey=...`, others paste full header) | Parse both formats; detect and normalize |
| Conversation listing (Phase 1) | Pagination not handled; conversations silently truncated | Always paginate; warn when response hits limit |
| Conversation fetching (Phase 1) | Session expires mid-export | Detect 401, halt, report progress, enable resume |
| Conversation fetching (Phase 1) | Rate limiting causes slow/failed export | Conservative concurrency, exponential backoff, user-configurable delay |
| Markdown conversion (Phase 1) | Artifacts appear as empty/broken in export | Detect artifact tool_use blocks, insert clear placeholder |
| Markdown conversion (Phase 1) | Thinking blocks truncated without notice | Detect truncation markers, label clearly |
| File output (Phase 1) | Filename collisions or illegal characters | Sanitize + UUID suffix |
| File downloads (Phase 2) | Wrong variant requested; file silently missing | Map file_kind to variant; log all failures |
| Project knowledge (Phase 2) | Knowledge docs forgotten entirely | Separate endpoint; plan for it explicitly |
| API stability (all phases) | Response format changes break parsing | Single API module, defensive parsing, version-stamped exports |

## Anti-Pattern: The "Happy Path Only" Exporter

Both existing tools exhibit a common anti-pattern: they handle the happy path well but degrade poorly on errors. The withLinda exporter returns `null` for failed conversations and skips them with a `console.warn`. The claudexit tool catches exceptions broadly and continues. Neither produces a clear report of what was missed.

**What to do instead:** Produce an export manifest (`export_manifest.json`) alongside the exported files. Include: every conversation UUID, its export status (success/failed/skipped), failure reason if applicable, file paths of exported content, and timestamps. This lets users verify completeness and re-run for failures.

## Sources

- withLinda/claude-project-conversations-exporter: full source code analysis of `claude_project_export_script.js` (CLAUDE.md, README, script)
- Rahul-999-alpha/claudexit: full source code analysis of `claude_chat_exporter.py` (README, exporter script)
- Claude.ai internal API endpoints observed in both codebases (MEDIUM confidence -- undocumented, may change)
- Artifact stripping behavior confirmed by both tools independently (HIGH confidence)
- Rate limiting behavior described in both tools' documentation (MEDIUM confidence)
