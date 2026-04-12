# Feature Landscape

**Domain:** Claude.ai Project Data Exporter (CLI)
**Researched:** 2026-04-12

## Claude.ai API Endpoints (Verified from Source Code)

All endpoints use base URL `https://claude.ai/api` and require session cookie authentication.

### Authentication & Organization Discovery

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/organizations` | GET | List all orgs for authenticated user | `[{"uuid": "...", "name": "...", "email_address": "..."}]` |

**Auth headers required on all requests:**
```
Cookie: sessionKey=sk-ant-...; lastActiveOrg=<org-uuid>
User-Agent: Mozilla/5.0 (Windows NT 10.0; ...) Chrome/128...
Accept: application/json
Referer: https://claude.ai/
Origin: https://claude.ai
```

The `lastActiveOrg` cookie provides the org UUID directly, but it can also be resolved via `/api/organizations` (returns array of org objects, first entry is primary).

### Project Endpoints

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/organizations/{org}/projects` | GET | List all projects | `[{"uuid": "...", "name": "...", "description": "...", "created_at": "...", "is_private": true}]` |
| `/api/organizations/{org}/projects/{proj}/docs` | GET | List project knowledge files | `[{"uuid": "...", "file_name": "...", "content": "...(full markdown)..."}]` |
| `/api/organizations/{org}/projects/{proj}/conversations_v2?limit=1000&offset=0` | GET | List conversations in a project (paginated) | `{"data": [{"uuid": "...", "name": "...", "model": "...", "created_at": "...", "updated_at": "..."}]}` |

**Key detail:** The `/projects/{proj}/docs` endpoint returns the **full markdown content** of knowledge files inline in the response -- no separate download step needed.

### Conversation Endpoints

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/organizations/{org}/chat_conversations` | GET | List ALL conversations (metadata only, no messages) | `[{"uuid": "...", "name": "...", "model": "...", "project_uuid": "...", "created_at": "...", "updated_at": "...", "summary": "..."}]` |
| `/api/organizations/{org}/chat_conversations/{conv}?tree=True&rendering_mode=messages` | GET | Fetch single conversation with all messages | Full conversation object with `chat_messages` array |
| `/api/organizations/{org}/chat_conversations/{conv}?tree=True&rendering_mode=messages&render_all_tools=true` | GET | Fetch conversation with tool use details | Same as above but tool calls fully rendered |

**Query parameters:**
- `tree=True` -- returns message tree structure
- `rendering_mode=messages` -- returns structured message content blocks
- `render_all_tools=true` -- includes full tool use/result blocks

### File Download Endpoints

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/{org}/files/{file_uuid}/document_pdf` | GET | Download document as PDF | Binary PDF data |
| `/api/{org}/files/{file_uuid}/preview` | GET | Download file preview (images) | Binary image data |
| `/api/{org}/files/{file_uuid}/thumbnail` | GET | Download file thumbnail | Binary image data |

**Note on file URL structure:** File downloads use `/api/{org}/files/...` NOT `/api/organizations/{org}/files/...` -- the `organizations` segment is absent.

**File variant strategy (from claudexit):**
- Documents: try `document_pdf` variant
- Images: try `preview`, then `thumbnail`
- Unknown: try `document_pdf`, then `preview`, then `thumbnail`

### Memory Endpoints

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/organizations/{org}/memory` | GET | Fetch account-level memory | `{"memory_text": "...", ...}` |
| `/api/organizations/{org}/memory?project_uuid={proj}` | GET | Fetch project-scoped memory | Same structure, scoped to project |

### Message Content Structure

Messages in `chat_messages` have a `content` field that is an array of typed blocks:

| Block Type | Fields | Notes |
|------------|--------|-------|
| `text` | `text` | Main message text |
| `thinking` | `thinking` | Extended thinking / reasoning (may be truncated with "characters truncated" note) |
| `tool_use` | `name`, `input` | Tool invocation |
| `tool_result` | `content` (array of `{type, text}`) | Tool execution result |

Messages also have:
- `sender`: `"human"` or `"assistant"`
- `created_at`: ISO timestamp
- `files_v2`: array of file attachment objects with `file_uuid`, `file_name`, `file_kind`
- `attachments`: array with `file_name`, `file_type`, `extracted_content`

### Rate Limiting

- HTTP 429 and 529 indicate rate limiting
- `Retry-After` header may be present
- Claudexit uses exponential backoff: initial 2s, doubling per retry, max 5 retries
- Browser exporter uses batch sizes of 5 concurrent requests with 500-1000ms delays between batches
- Larger projects (200+) need 1000ms delays; medium projects need 500-750ms

### Known Limitations

- **Artifacts:** Claude strips artifact source code server-side. No known endpoint returns artifact content.
- **Deleted conversations:** Not returned by any endpoint.
- **Older conversations:** API may not return conversations beyond "sidebar visibility" limit (exact threshold unknown).
- **Session expiry:** Cookies expire periodically, requiring re-authentication.

---

## Existing Tool Comparison

| Feature | claudexit (Python/Electron) | claude-project-conversations-exporter (JS/Browser) | This Project (Target) |
|---------|---------------------------|---------------------------------------------------|----------------------|
| Platform | Windows only (DPAPI) | Any browser | macOS CLI (Python) |
| Auth | Auto cookie extraction | Browser session | Manual cookie paste |
| Scope | All projects + standalone | Single project | Single project (MVP) |
| Output | JSON + Markdown + files | Markdown only | Markdown + files |
| Knowledge files | Yes | No | Yes |
| File attachments | Yes (with variant detection) | No (text only) | Yes |
| Memory export | Yes (global + per-project) | No | No (out of scope) |
| Migration | Yes (account-to-account) | No | No (out of scope) |
| Thinking blocks | Yes (toggleable) | Yes | Yes |
| Tool use rendering | Yes | Yes | Yes |
| Progress tracking | WebSocket real-time | Console + notifications | CLI progress |
| Rate limit handling | Exponential backoff | Simple retry + delays | Exponential backoff |
| Batch size | Configurable | 5 concurrent | Configurable |

---

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Session cookie authentication | Only auth method available for claude.ai web | Low | Accept `sessionKey` cookie via CLI arg, env var, or prompt. Include `lastActiveOrg` or resolve via `/api/organizations`. |
| List and select a project | Core workflow is project-scoped export | Low | GET `/api/organizations/{org}/projects` then prompt user to select |
| Fetch all conversations in a project | This IS the product | Medium | GET `/api/organizations/{org}/projects/{proj}/conversations_v2?limit=1000&offset=0`. Handle pagination if >1000. |
| Export conversations as Markdown | Primary output format users want | Medium | Convert `chat_messages` array to readable Markdown with sender labels, timestamps, content blocks |
| Download project knowledge files | Users uploaded these files specifically; losing them defeats the purpose | Low | GET `/api/organizations/{org}/projects/{proj}/docs` returns content inline. Write each to `knowledge/` folder. |
| Download file attachments from conversations | Users attached PDFs/images to chats; export should be complete | Medium | Collect `files_v2` from messages, download via `/api/{org}/files/{uuid}/{variant}` with fallback variants |
| Organized folder structure | Output must be navigable, not a flat dump | Low | `project_name/markdown/`, `project_name/knowledge/`, `project_name/files/` |
| Rate limit handling with retry | Without it, large projects fail silently | Medium | Exponential backoff on 429/529, respect `Retry-After` header |
| Progress indication | Large projects take minutes; silent CLI feels broken | Low | Simple counter: "Fetching conversation 12/47..." |
| Thinking block support | Extended thinking is increasingly common; omitting it loses context | Low | Render `thinking` content blocks, optionally in collapsible `<details>` tags |
| Tool use rendering | Many conversations use tools; skipping them breaks context | Low | Render `tool_use` and `tool_result` blocks in code fences |

## Differentiators

Features that set this product apart from existing tools.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| macOS native support (no DPAPI) | claudexit is Windows-only; browser tools require manual console pasting. This is the first macOS CLI tool. | Low | Manual cookie input sidesteps all platform-specific crypto. This IS the differentiator. |
| JSON + Markdown dual output | claudexit does this but browser tools don't. Having raw JSON enables future processing. | Low | Save both `json/` and `markdown/` per conversation |
| Conversation summary in Markdown header | Quick scan of what each conversation was about | Low | Use `summary` field from API response |
| Index file generation | Navigate exports without opening every file | Low | Generate `index.md` listing all conversations with dates and links |
| Incremental/resumable export | Don't re-download already-exported conversations | Medium | Check if `{date}_{name}_{uuid[:8]}.md` already exists, skip. Saves time on re-runs and handles interrupted exports. |
| Configurable output format | Some users want only Markdown, some want only JSON | Low | `--format md|json|both` flag |
| Selective conversation export | Export specific conversations, not always everything | Low | `--conversation <uuid>` flag or interactive selection |
| File attachment content extraction | Show extracted text content from PDFs inline in Markdown | Low | `attachments[].extracted_content` is already in the API response; include it in Markdown output |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Automatic cookie extraction from browser | Requires platform-specific crypto (DPAPI on Windows, Keychain on macOS), brittle across browser updates, and security-sensitive. claudexit's biggest complexity source. | Accept cookie as CLI argument, env var, or interactive prompt. Document how to extract from browser DevTools (10-second process). |
| GUI / web interface | Adds massive complexity (Electron, React, etc.) for a tool that runs once every few weeks | CLI only. The output files ARE the interface -- open them in any editor/Obsidian. |
| Account-to-account migration | Complex write operations (create projects, upload files, send messages). High risk of data loss or API abuse. | Export only. Users can manually re-import if needed. |
| Memory export | Tangential to project data export. Memory is account-global, not project-specific. | Out of scope. Could add later as `--include-memory` flag if requested. |
| Artifact export | Claude strips artifact source code server-side. No API endpoint returns it. Building a workaround would be fragile and unreliable. | Document the limitation. Artifacts visible in-browser only. |
| Real-time sync / watch mode | Polling an undocumented API continuously risks account rate limiting or flagging | One-shot export tool. Run it when you need a snapshot. |
| Windows DPAPI cookie extraction | Platform-specific, complex, and the exact thing that makes claudexit macOS-incompatible | Manual cookie input works everywhere. |

## Feature Dependencies

```
Session Cookie Auth --> List Organizations --> List Projects --> Select Project
                                                                      |
                                                          +-----------+-----------+
                                                          |           |           |
                                                   Fetch Convos  Knowledge   Project Memory
                                                          |        Files      (deferred)
                                                          |           |
                                                   +------+------+   |
                                                   |      |      |   |
                                                 JSON  Markdown  Files
                                                   |      |      |
                                                   +------+------+
                                                          |
                                                   Folder Structure
                                                          |
                                                     Index File
```

**Critical path:** Auth --> Org discovery --> Project list --> Conversation fetch --> Format & save

**Independent after project selection:**
- Knowledge file download (no dependency on conversations)
- Conversation fetch + export (no dependency on knowledge files)

## MVP Recommendation

**Phase 1 -- Core Export (must ship first):**
1. Session cookie authentication (CLI arg + env var + prompt)
2. Organization discovery via `/api/organizations`
3. Project listing and selection (interactive prompt)
4. Fetch all conversations in selected project
5. Export each conversation as Markdown
6. Download project knowledge files
7. Organized folder output structure
8. Basic progress indication (counter)
9. Rate limit handling with exponential backoff

**Phase 2 -- Completeness:**
1. File attachment downloads (with variant fallback)
2. JSON dual output format
3. Index file generation
4. Thinking block and tool use rendering
5. `--format` flag

**Defer:**
- Incremental export: Useful but not required for first working version
- Selective conversation export: Nice to have, not blocking
- Memory export: Out of scope per PROJECT.md

## Sources

- claudexit source code: `github.com/Rahul-999-alpha/claudexit` -- `backend/app/services/claude_api.py`, `backend/app/services/exporter.py`, `backend/app/utils.py`, `claude_chat_exporter.py` (HIGH confidence, direct code analysis)
- claude-project-conversations-exporter source: `github.com/withLinda/claude-project-conversations-exporter` -- `claude_project_export_script.js` (HIGH confidence, direct code analysis)
- Claude.ai API endpoint patterns verified across both independent implementations (HIGH confidence)
- Artifact limitation confirmed by both tools' documentation (HIGH confidence)
- Rate limiting behavior inferred from retry logic in both tools (MEDIUM confidence -- exact thresholds not documented by Anthropic)
