# Project Research Summary

**Project:** Claude Project Dumper
**Domain:** CLI data exporter (internal API scraping)
**Researched:** 2026-04-12
**Confidence:** MEDIUM-HIGH

## Executive Summary

This project is a Python CLI tool that exports Claude.ai project data (conversations, knowledge files, file attachments) via Claude.ai's undocumented internal web API. Two prior-art implementations exist: claudexit (Python/Electron, Windows-only) and claude-project-conversations-exporter (JavaScript, browser-only). Neither serves macOS CLI users, which is the primary gap this tool fills. The API surface is well-mapped from reverse-engineering both codebases -- endpoints for organizations, projects, conversations, knowledge docs, and file downloads are confirmed by two independent implementations.

The recommended approach is a lean Python CLI with 4 runtime dependencies (httpx, click, rich, pydantic) managed by uv. The architecture is a simple layered pipeline: auth -> API client -> exporter orchestrator -> renderer + writer. The entire tool should be under 700 lines across 7 modules. Synchronous HTTP is the right choice -- rate limiting makes parallelism counterproductive, and the sequential CLI workflow gains nothing from async. Start with the API client and authentication since they are the riskiest components (undocumented API, cookie-based auth, rate limiting), then layer on rendering and file output.

The key risks are: (1) the API is undocumented and can change without notice, requiring defensive parsing and a single-module API boundary; (2) artifact content is stripped server-side with no workaround, which must be documented upfront; (3) session cookies expire mid-export on large projects, requiring progress tracking and resume capability; (4) aggressive API usage risks rate limiting or account flags, requiring conservative request pacing from day one. All of these are manageable with the patterns identified in research.

## Key Findings

### Recommended Stack

A minimal, modern Python stack with 4 runtime dependencies. Each dependency earns its place; everything else uses stdlib. See [STACK.md](STACK.md) for full rationale.

**Core technologies:**
- **Python 3.12+ / uv**: Runtime and project management -- universal availability, fast tooling
- **httpx 0.28.x**: HTTP client -- HTTP/2 support, modern API, async upgrade path if needed
- **click 8.3.x**: CLI framework -- mature, handles prompting for cookie input, no magic
- **rich 15.0.x**: Terminal output -- progress bars, tables, colored output in one package
- **pydantic 2.12.x**: Data validation -- catches API response shape changes early (critical for undocumented API)
- **pathlib / stdlib**: File I/O, Markdown generation, config storage -- no extra deps needed

**Critical version note:** Use pydantic with `model_config = {"extra": "ignore"}` to tolerate undocumented field additions.

### Expected Features

See [FEATURES.md](FEATURES.md) for full feature landscape and API endpoint documentation.

**Must have (table stakes):**
- Session cookie authentication (CLI arg, env var, interactive prompt)
- Organization discovery and project listing/selection
- Fetch and export all conversations in a project as Markdown
- Download project knowledge files (content returned inline by API)
- Download file attachments from conversations (with variant fallback)
- Organized folder output structure (conversations/, knowledge/, files/)
- Rate limit handling with exponential backoff
- Progress indication during export
- Thinking block and tool use rendering in Markdown output

**Should have (differentiators):**
- JSON + Markdown dual output format
- Index file generation for navigating exports
- Incremental/resumable export (skip already-exported conversations)
- Configurable output format (--format md|json|both)
- Conversation summary in Markdown header
- File attachment extracted text content inline in Markdown

**Defer (v2+):**
- Memory export (account-global, tangential to project export)
- Selective conversation export by UUID
- Account-to-account migration
- Artifact export (server-side limitation, no known workaround)
- Automatic cookie extraction from browser (platform-specific complexity)

### Architecture Approach

A single-process, synchronous, layered CLI with strict module boundaries. The API client is the only module making HTTP calls. The renderer is pure (dict in, string out). The writer is the only module touching the output filesystem. This separation enables testability and contains API change impact to one module. See [ARCHITECTURE.md](ARCHITECTURE.md) for component details and data flow diagrams.

**Major components:**
1. **auth.py** -- Cookie storage, session validation, org ID discovery
2. **api_client.py** -- All HTTP requests, retry/backoff logic, centralized error handling
3. **models.py** -- Typed representations of API responses (Pydantic with extra="ignore")
4. **exporter.py** -- Orchestrates fetch -> render -> write pipeline
5. **renderer.py** -- Conversation/message data to Markdown string (pure function)
6. **writer.py** -- File I/O, directory creation, filename sanitization
7. **cli.py** -- Click commands, argument parsing, user prompts

**Key patterns:**
- Write-as-you-go (not buffer-then-dump) for crash resilience and flat memory usage
- Filename convention: `{date}_{sanitized-title}_{uuid[:8]}.md` for sort order and collision avoidance
- File download with variant fallback based on file_kind metadata
- Cookie priority: CLI flag > env var > config file

### Critical Pitfalls

See [PITFALLS.md](PITFALLS.md) for all 13 identified pitfalls with prevention strategies.

1. **Artifact content stripped server-side** -- No API endpoint returns artifact source code. Detect artifact tool_use blocks and insert clear placeholders. Document the limitation prominently.
2. **Organization ID discovery fragility** -- Require full cookie header (not just sessionKey). Fall back to `/api/organizations` endpoint. Validate org ID before any other API call.
3. **Session cookie expiry mid-export** -- Detect 401 mid-run and halt immediately. Track success/failure counts. Implement resume by skipping already-exported UUIDs on re-run.
4. **Rate limiting and account flags** -- Sequential requests (no parallelism), exponential backoff on 429/529, mandatory delays between requests, user-configurable `--delay` flag.
5. **API response shape changes** -- Defensive `.get()` parsing, pydantic with extra="ignore", all API interaction in one module, informative error messages with raw response snippets.

## Implications for Roadmap

Based on combined research, the project naturally splits into 4 phases following the dependency chain and risk gradient.

### Phase 1: Authentication and API Foundation
**Rationale:** The API client is the riskiest component. Authentication and org discovery must work before anything else. Both prior-art tools confirm this is the hardest part to get right.
**Delivers:** A working CLI that can authenticate, discover orgs, list projects, and list conversations. Validates that the API interaction layer works end-to-end.
**Features addressed:** Session cookie auth, org discovery, project listing, conversation listing
**Pitfalls to handle:** Org ID discovery fragility (P2), rate limiting basics (P4), API response defensiveness (P5), cookie format normalization
**Components built:** cli.py (minimal), auth.py, api_client.py, models.py (initial TypedDicts or Pydantic)

### Phase 2: Conversation Export Pipeline
**Rationale:** With a working API client, the export pipeline is pure transformation -- low risk, high value. This phase delivers the core product value: conversations as Markdown files on disk.
**Delivers:** Full conversation export as Markdown with proper folder structure, thinking blocks, tool use rendering, artifact placeholders, and progress indication.
**Features addressed:** Conversation fetch, Markdown export, folder structure, progress indication, thinking blocks, tool use rendering
**Pitfalls to handle:** Artifact placeholder insertion (P1), session expiry detection (P3), filename sanitization (P9), thinking truncation markers (P8), pagination (P6), write-as-you-go for memory (P11), UTC timestamps (P10)
**Components built:** renderer.py, writer.py, exporter.py

### Phase 3: Files and Knowledge Documents
**Rationale:** File downloads extend the API client with variant fallback logic. Knowledge docs use a separate endpoint. Both are independent of conversation rendering and can be added after the core pipeline works.
**Delivers:** Complete project export including knowledge documents and conversation file attachments.
**Features addressed:** Knowledge file download, file attachment download, file variant fallback
**Pitfalls to handle:** File variant guessing (P7), content-type mismatch (P13), knowledge file endpoint (P12)
**Components extended:** api_client.py (download_file, get_project_docs), exporter.py, writer.py

### Phase 4: Polish and Durability
**Rationale:** Quality-of-life features that do not affect core functionality. Should not block shipping but make the tool production-grade.
**Delivers:** JSON dual output, index file, export manifest, cookie persistence, incremental export, configurable format flag.
**Features addressed:** JSON output, index generation, --format flag, incremental export, export manifest, cookie persistence
**Pitfalls to handle:** Partial export completeness reporting (anti-pattern from prior art)
**Components extended:** All modules (minor additions)

### Phase Ordering Rationale

- **Risk-first:** The API client and auth are where the tool will break. Validating these before building rendering logic avoids wasted work if the API behaves differently than expected.
- **Value gradient:** Phase 1 is infrastructure, Phase 2 delivers the core product, Phase 3 adds completeness, Phase 4 adds polish. Each phase produces a usable tool.
- **Dependency chain:** Auth -> API client -> Fetch -> Render -> Write mirrors the actual data flow. No phase depends on a later phase.
- **Pitfall containment:** The highest-severity pitfalls (P1-P4) are addressed in Phases 1-2, preventing them from compounding in later phases.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Authentication and org discovery have edge cases (cookie format variations, multi-org accounts) that may need experimentation against the live API.
- **Phase 3:** File download variant logic is the least-documented area. May need trial-and-error with different file types.

Phases with standard patterns (skip research-phase):
- **Phase 2:** Markdown rendering and file I/O are well-understood. The message content block types are documented in FEATURES.md from two independent source code analyses.
- **Phase 4:** All features are standard CLI patterns (config files, JSON serialization, index generation).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommended packages are mature, actively maintained, and standard choices for this type of project |
| Features | HIGH | API endpoints verified across two independent implementations. Message content block types confirmed. |
| Architecture | HIGH | Simple layered CLI is a well-established pattern. Module boundaries are clear and justified by prior art analysis. |
| Pitfalls | MEDIUM-HIGH | Pitfalls identified from real source code, but rate limit thresholds and session expiry timing are inferred, not documented by Anthropic. |

**Overall confidence:** MEDIUM-HIGH

The research is strong because it is based on direct source code analysis of two working implementations, not blog posts or speculation. The main uncertainty is the undocumented API itself -- it can change at any time, which is an inherent risk of the domain rather than a gap in research.

### Gaps to Address

- **Exact rate limit thresholds:** Neither prior-art tool documents precise limits. The tool must be conservative and adaptive. Validate during Phase 1 development against the live API.
- **Session cookie TTL:** Unknown how long cookies remain valid. Test empirically and document findings.
- **Multi-org account behavior:** Research assumes single org. If users have multiple orgs, the selection UX needs attention in Phase 1.
- **conversations_v2 vs chat_conversations endpoint:** Two different endpoints for listing conversations. The project-scoped `conversations_v2` is cleaner but less proven. Validate pagination behavior during Phase 1.
- **Large project scale:** No data on behavior above 500+ conversations. The write-as-you-go pattern mitigates memory, but runtime and rate limiting need empirical validation.

## Sources

### Primary (HIGH confidence)
- claudexit source code (Rahul-999-alpha/claudexit) -- API endpoints, retry logic, file variant downloads, Pydantic models, export pipeline, directory structure
- claude-project-conversations-exporter source (withLinda/claude-project-conversations-exporter) -- API endpoints, org discovery, message content blocks, rate limiting approach

### Secondary (MEDIUM confidence)
- Claude.ai API endpoints -- reverse-engineered from both projects, consistent across implementations but undocumented by Anthropic
- Rate limiting behavior -- inferred from retry logic in both tools, exact thresholds unknown

### Tertiary (LOW confidence)
- Session cookie expiry timing -- inferred from user reports, not empirically measured
- Artifact stripping mechanism -- confirmed absent from API responses but root cause (separate content store) is inference

---
*Research completed: 2026-04-12*
*Ready for roadmap: yes*
