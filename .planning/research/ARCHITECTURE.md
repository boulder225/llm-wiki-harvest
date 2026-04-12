# Architecture Patterns

**Domain:** CLI tool for exporting Claude.ai project data
**Researched:** 2026-04-12

## Recommended Architecture

A single-process Python CLI with four clean layers. No framework needed -- just `requests` (or `urllib`) and `argparse`. The tool is inherently sequential: authenticate, discover, fetch, render, write.

```
CLI Entry Point (main.py)
    |
    v
Auth Layer (auth.py)           -- cookie management, session validation
    |
    v
API Client (api_client.py)     -- all Claude.ai HTTP calls, retry logic
    |
    v
Data Models (models.py)        -- typed representations of API responses
    |
    v
Export Pipeline (exporter.py)  -- orchestrates fetch + render + write
    |
    +---> Renderer (renderer.py)   -- conversation/message -> Markdown
    +---> Writer (writer.py)       -- file I/O, directory structure, dedup
```

### Why This Shape

Claudexit (prior art) uses a FastAPI + Electron + React stack because it is a desktop GUI with migration features. That complexity is unnecessary for a CLI-only exporter. The browser-based exporter (withLinda) is a single JS file -- good for a bookmarklet, but not maintainable as a project grows. Our tool sits between: structured enough for maintainability, simple enough for a single-purpose CLI.

## Component Boundaries

| Component | Responsibility | Depends On | Communicates With |
|-----------|---------------|------------|-------------------|
| `main.py` | CLI argument parsing, orchestration, exit codes | All components | auth, exporter |
| `auth.py` | Cookie storage/retrieval, session validation | api_client | api_client |
| `api_client.py` | All HTTP requests to claude.ai, retry/backoff | models | claude.ai API |
| `models.py` | Dataclasses for Organization, Project, Conversation, Message, FileRef | None (leaf) | None |
| `exporter.py` | High-level export logic: what to fetch, in what order | api_client, renderer, writer | api_client, renderer, writer |
| `renderer.py` | Conversation dict -> Markdown string | models | None |
| `writer.py` | Markdown/JSON strings -> filesystem, directory creation | None | filesystem |

### Boundary Rules

- **api_client.py** is the ONLY module that makes HTTP calls. Everything else goes through it.
- **writer.py** is the ONLY module that touches the filesystem for output. (`auth.py` may read/write a cookie cache file.)
- **renderer.py** is pure: dict in, string out. No I/O.
- **models.py** is pure data. No logic, no I/O.

## Data Flow

### Full Export Flow

```
1. User runs: claude-dump --cookie "sk-ant-..." --project "My Project" --output ./export

2. main.py:
   - Parses args
   - Calls auth.validate_session(cookie)

3. auth.py:
   - Stores cookie string
   - Calls api_client.get_organizations() to discover org_id
   - Caches org_id for subsequent calls
   - Returns AuthSession(cookie, org_id)

4. exporter.py (orchestration):
   a. api_client.list_projects(org_id)        -> [Project, ...]
   b. User selects project (or --project flag matches)
   c. api_client.get_project_docs(project_id) -> [Doc, ...]
   d. api_client.list_conversations(org_id)   -> [ConvSummary, ...]
      Filter to project_id
   e. For each conversation:
      - api_client.get_conversation(conv_id)  -> FullConversation
      - renderer.render_conversation(conv)    -> markdown_string
      - writer.write_markdown(path, string)
      - writer.write_json(path, raw_dict)     # optional
      - For each file attachment:
        - api_client.download_file(file_id)   -> bytes
        - writer.write_binary(path, bytes)
   f. For each knowledge doc:
      - writer.write_text(knowledge_dir / name, content)

5. main.py: Print summary, exit 0
```

### Data Transformation Chain

```
Claude.ai JSON response
    |  (api_client returns raw dict)
    v
Python dict (raw API shape)
    |  (models.py parses into typed objects -- optional, can start with dicts)
    v
Typed model objects (Organization, Project, Conversation, Message)
    |  (renderer.py formats)
    v
Markdown string
    |  (writer.py persists)
    v
Files on disk
```

**Key decision: Start with raw dicts, add typed models later.** The Claude.ai API is undocumented and may change. Starting with raw dicts means the tool works even when API shapes shift slightly. Typed models (dataclasses or Pydantic) should be added in a second phase for better code readability, but should be tolerant of unknown fields.

## Claude.ai API Endpoints (Discovered from Prior Art)

All endpoints are under `https://claude.ai/api`. Authentication is via `Cookie` header with session cookie. A `User-Agent` header mimicking a browser is required.

| Endpoint | Method | Returns |
|----------|--------|---------|
| `/organizations` | GET | List of orgs. Use `[0]["uuid"]` for org_id |
| `/organizations/{org}/projects` | GET | List of projects with uuid, name |
| `/organizations/{org}/projects/{proj}/docs` | GET | Knowledge docs with file_name, content |
| `/organizations/{org}/projects/{proj}/conversations_v2?limit=N&offset=M` | GET | Paginated conversation list (alternative) |
| `/organizations/{org}/chat_conversations` | GET | All conversations (filter by project_uuid client-side) |
| `/organizations/{org}/chat_conversations/{conv}?tree=True&rendering_mode=messages` | GET | Full conversation with chat_messages array |
| `/organizations/{org}/memory` | GET | Global memory |
| `/organizations/{org}/memory?project_uuid={proj}` | GET | Project-scoped memory |
| `/{org}/files/{file_uuid}/{variant}` | GET | Binary file content (variants: document_pdf, preview, thumbnail) |

**Organization ID discovery:** The `lastActiveOrg` cookie often contains it. Fallback: call `/organizations` and use the first result.

**Rate limiting:** Claude.ai returns 429 (and sometimes 529) for rate limiting. Use exponential backoff with `Retry-After` header respect. Claudexit uses 5 retries with 2s initial backoff doubling each attempt. Retryable status codes: 429, 529, 500, 502, 503.

## Patterns to Follow

### Pattern 1: Thin API Client with Retry

The API client should be a thin wrapper. Each method = one endpoint. Retry logic is centralized in a single `_request` method.

```python
class ClaudeAPIClient:
    BASE_URL = "https://claude.ai/api"
    RETRYABLE = {429, 529, 500, 502, 503}
    MAX_RETRIES = 5

    def __init__(self, cookie: str, org_id: str | None = None):
        self.cookie = cookie
        self.org_id = org_id

    def _request(self, url: str, accept: str = "application/json") -> bytes:
        """Single retry-aware GET. All public methods call this."""
        # headers: Cookie, User-Agent (browser-like), Referer, Origin
        # exponential backoff on RETRYABLE codes
        # respect Retry-After header
        ...

    def _get(self, path: str) -> dict | list:
        """GET /api/organizations/{org_id}/{path}"""
        return json.loads(self._request(f"{self.BASE_URL}/organizations/{self.org_id}/{path}"))

    def get_organizations(self) -> list[dict]: ...
    def list_projects(self) -> list[dict]: ...
    def list_conversations(self) -> list[dict]: ...
    def get_conversation(self, uuid: str) -> dict: ...
    def get_project_docs(self, project_uuid: str) -> list[dict]: ...
    def download_file(self, file_uuid: str, variant: str) -> bytes: ...
```

### Pattern 2: Progressive Output (Write as You Go)

Do NOT buffer all conversations in memory, then write. Write each conversation to disk immediately after fetching and rendering. This means:
- Partial exports are usable if the tool crashes mid-run
- Memory usage stays flat regardless of project size
- User sees progress (files appearing on disk)

### Pattern 3: Filename Convention from Claudexit

Use `{date}_{sanitized-title}_{uuid-prefix}.md` for conversation files. This gives:
- Chronological sorting by date prefix
- Human-readable names
- Collision avoidance via UUID suffix

```python
def make_filename(conv: dict) -> str:
    date = conv.get("created_at", "")[:10]
    title = sanitize(conv.get("name", "Untitled"))
    short_id = conv["uuid"][:8]
    return f"{date}_{title}_{short_id}"
```

### Pattern 4: File Download with Variant Fallback

Files on Claude.ai have multiple variants (document_pdf, preview, thumbnail). Try the best variant first, fall back to alternatives. This pattern from claudexit handles the unpredictable file serving.

```python
async def download_best_variant(self, file_info: dict) -> tuple[bytes, str] | None:
    kind = file_info.get("file_kind", "")
    variants = {
        "document": ["document_pdf"],
        "image": ["preview", "thumbnail"],
    }.get(kind, ["document_pdf", "preview", "thumbnail"])

    for variant in variants:
        try:
            return self.download_file(file_info["file_uuid"], variant)
        except Exception:
            continue
    return None
```

### Pattern 5: Cookie as Config, Not Embedded

Accept cookie via:
1. `--cookie` CLI flag (for one-off use)
2. Environment variable `CLAUDE_COOKIE` (for repeated use)
3. Config file `~/.config/claude-dump/cookie` (for persistence)

Priority: flag > env > file. Never store cookies in project directories.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Async for a CLI Tool

**What:** Using `asyncio` for a sequential CLI exporter.
**Why bad:** Claudexit uses async because it is a server (FastAPI). A CLI tool that fetches conversations one-at-a-time does not benefit from async -- it adds complexity (event loop, async/await everywhere) with no throughput gain. Rate limiting means you cannot parallelize API calls anyway.
**Instead:** Use synchronous `requests` or `urllib`. If you want progress indication, use a simple print-based progress bar. Async can be added later IF parallel downloads prove valuable and rate limits allow it.

### Anti-Pattern 2: Heavy Framework for Simple CLI

**What:** Using Click, Typer, Rich, or other frameworks for argument parsing and output.
**Why bad:** The tool has ~5 flags. `argparse` from stdlib handles this fine. Adding frameworks increases install friction and dependency surface for no user-visible gain.
**Instead:** `argparse` for CLI, `print()` for output. Add `rich` in a later phase if pretty progress bars become a priority, but it is not needed for v1.

### Anti-Pattern 3: Pydantic Models for Unstable API

**What:** Strict Pydantic validation of Claude.ai API responses.
**Why bad:** The API is undocumented and internal. Field names may change, new fields appear, optional fields disappear. Strict validation will break the tool on minor API changes.
**Instead:** Start with plain dicts. If you add models, use `dataclasses` with `**kwargs` tolerance or Pydantic with `model_config = {"extra": "ignore"}`. Parse defensively with `.get()` and defaults.

### Anti-Pattern 4: Single Monolithic File

**What:** Putting everything in one `claude_dump.py` file.
**Why bad:** The withLinda exporter is a single file because it runs in a browser console. A proper CLI tool needs separation of concerns for testability and maintainability. The API client, renderer, and file writer have zero overlap.
**Instead:** Use the module structure described above. Each module is <200 lines.

## Output Folder Structure Recommendation

```
{output_dir}/
  {ProjectName}/
    knowledge/
      document1.md
      document2.pdf
    conversations/
      2026-01-15_Chat-about-architecture_a1b2c3d4.md
      2026-01-15_Chat-about-architecture_a1b2c3d4.json    # optional
      2026-02-01_Debugging-session_e5f6g7h8.md
    files/
      uploaded-image.png
      reference-doc.pdf
    project_memory.md
  _metadata/
    export_manifest.json     # what was exported, when, from which org
```

**Differences from claudexit structure:**
- `conversations/` instead of separate `json/` and `markdown/` dirs. Keeping JSON and MD side-by-side for the same conversation is more intuitive.
- `_metadata/` at root for export metadata rather than scattered index files.
- No `_no_project/` for v1 -- scope is single-project export. Can add later for full-account dump.

**Export manifest** (`export_manifest.json`):
```json
{
  "exported_at": "2026-04-12T10:30:00Z",
  "organization_id": "uuid",
  "project_id": "uuid",
  "project_name": "My Project",
  "conversation_count": 42,
  "knowledge_doc_count": 5,
  "file_count": 12,
  "tool_version": "0.1.0"
}
```

## Suggested Build Order

Dependencies between components dictate the build order. Each phase produces a working tool with increasing capability.

```
Phase 1: Core Pipeline (MVP)
  models.py       (data shapes -- even if just TypedDicts initially)
  api_client.py   (HTTP layer with retry -- the hardest part to get right)
  auth.py         (cookie input + org discovery)
  main.py         (minimal CLI: --cookie, --output)

  Deliverable: Can authenticate and list projects/conversations to stdout.

Phase 2: Export Conversations
  renderer.py     (conversation -> markdown)
  writer.py       (filesystem output)
  exporter.py     (orchestration: fetch -> render -> write)

  Deliverable: Can export a project's conversations as Markdown files.

Phase 3: Files and Knowledge
  Add to api_client: download_file, get_project_docs
  Add to exporter: knowledge doc export, file attachment download
  Add to writer: binary file writing, knowledge dir

  Deliverable: Full project export including knowledge docs and attachments.

Phase 4: Polish
  Progress reporting (conversation N of M)
  Error summary at end of run
  Export manifest
  --format flag (md/json/both)
  Cookie persistence (~/.config/claude-dump/cookie)

  Deliverable: Production-quality CLI tool.
```

**Why this order:**
1. The API client is the riskiest component (undocumented API, auth quirks, rate limiting). Build and validate it first.
2. Markdown rendering is pure transformation -- easy to build, easy to test, no external dependencies.
3. File downloads are an extension of the API client, not a new concept. Add after conversations work.
4. Polish (progress, manifest, config) is low-risk and should not block core functionality.

## Scalability Considerations

| Concern | Small project (10 convos) | Large project (500+ convos) | Mitigation |
|---------|---------------------------|----------------------------|------------|
| Memory | No issue | Message content could be large | Write-as-you-go pattern |
| Rate limiting | Unlikely to hit | Will definitely hit 429s | Exponential backoff, configurable delay |
| Runtime | Seconds | 10+ minutes | Progress reporting, partial export resilience |
| Disk space | Trivial | Could be GBs with file attachments | Report total size, warn before large downloads |
| API pagination | Single page | Need offset/limit pagination | Use conversations_v2 endpoint with pagination |

## Module Size Targets

Keep modules small and focused:

| Module | Target Lines | Complexity |
|--------|-------------|-----------|
| `main.py` | ~80 | Low -- argparse + orchestration |
| `auth.py` | ~60 | Low -- cookie handling + validation |
| `api_client.py` | ~150 | Medium -- HTTP, retry, all endpoints |
| `models.py` | ~50 | Low -- dataclasses/TypedDicts |
| `exporter.py` | ~120 | Medium -- orchestration logic |
| `renderer.py` | ~100 | Low -- pure string formatting |
| `writer.py` | ~60 | Low -- filesystem operations |
| **Total** | **~620** | Entire tool in <700 lines |

## Sources

- **claudexit** (Rahul-999-alpha/claudexit): Electron+FastAPI desktop app. Studied `backend/app/services/claude_api.py` (API endpoints, retry logic, file variant downloads), `backend/app/models.py` (Pydantic models), `backend/app/services/exporter.py` (export pipeline, directory structure), `backend/app/utils.py` (markdown rendering, file collection). HIGH confidence -- direct source code review.
- **claude-project-conversations-exporter** (withLinda): Browser JS exporter. Studied `claude_project_export_script.js` for API endpoint patterns, org_id discovery, message content block types, rate limiting approach. HIGH confidence -- direct source code review.
- Claude.ai API endpoints: Reverse-engineered from both projects above. MEDIUM confidence -- undocumented internal API, may change without notice.
