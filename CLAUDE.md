<!-- GSD:project-start source:PROJECT.md -->
## Project

**Claude Project Dumper**

A command-line tool that exports all conversations and uploaded files (transcripts, documents) from a Claude.ai Project into a local folder structure with Markdown-formatted conversations. It targets macOS users who provide their session cookie manually.

**Core Value:** Reliably dump every conversation and every attached file from a Claude.ai Project into organized, readable local Markdown files.

### Constraints

- **Auth**: Session cookie only -- no OAuth or API key available for claude.ai web
- **API stability**: Internal APIs are undocumented and may change without notice
- **Language**: Python preferred (widely available on macOS, good HTTP/file handling)
- **Dependencies**: Minimal -- requests library at most, no heavy frameworks
- **Rate limiting**: Must respect any rate limits to avoid account issues
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Language & Runtime
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12+ | Runtime | Universally available on macOS, excellent HTTP/file handling, project constraint |
| uv | 0.11.x | Package/project management | 10-100x faster than pip, handles venvs, lockfiles, and Python version management in one tool. Industry standard for new Python projects in 2025-2026 |
### HTTP Client
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| httpx | 0.28.x | HTTP requests to Claude.ai APIs | Modern, async-capable, supports HTTP/2, session/cookie handling built-in, clean API. Better than requests for new projects |
### CLI Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| click | 8.3.x | CLI argument parsing, commands, prompts | Mature, stable, minimal magic, explicit. The project needs simple commands (dump, list-projects), not complex type-annotated interfaces |
### Terminal Output & Progress
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| rich | 15.0.x | Progress bars, formatted terminal output, tables | Best-in-class terminal formatting. Shows download progress, conversation lists, error messages beautifully |
### Data Modeling (Optional but Recommended)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pydantic | 2.12.x | Type-safe API response parsing | Claude.ai API responses are undocumented JSON. Pydantic models catch shape changes early with clear errors instead of silent KeyError failures deep in the code |
### Markdown Generation
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| None (stdlib) | -- | Generate Markdown output files | Markdown is plain text with formatting conventions. No library needed. Use f-strings and `textwrap.dedent` |
### File I/O
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pathlib (stdlib) | -- | File and directory operations | Modern, object-oriented path handling. Built-in since Python 3.4. No reason to use `os.path` in 2026 |
### Configuration / Cookie Storage
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| None (plain file) | -- | Store session cookie between runs | Write cookie to `~/.config/claude-dump/cookie` (plain text). No TOML/YAML/JSON config library needed for a single value |
## Complete Dependency List
### Core Dependencies (5 packages)
### Dev Dependencies
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| HTTP client | httpx | requests 2.33.x | No HTTP/2, no async, legacy API patterns |
| HTTP client | httpx | curl-cffi 0.15.x | Heavy C dependency; hold as escape hatch if fingerprint-blocked |
| HTTP client | httpx | aiohttp 3.x | Async-only, more complex for a simple CLI tool |
| CLI framework | click | typer 0.24.x | Still 0.x, unnecessary abstraction for 3-5 commands |
| CLI framework | click | argparse (stdlib) | Verbose, no prompting, poor UX |
| Progress bars | rich | tqdm 4.67.x | Rich does progress + formatting; tqdm is progress-only |
| Data modeling | pydantic | dataclasses (stdlib) | No validation, no JSON parsing, misses the whole point |
| Data modeling | pydantic | attrs | Less ecosystem support, no built-in JSON schema validation |
| Config | plain file | python-dotenv | Overkill for one value |
| Markdown | string formatting | mdutils | Unnecessary abstraction for simple output |
| Pkg manager | uv | poetry | Slower, heavier, uv is the current standard |
| Pkg manager | uv | pip + venv | No lockfile, no Python version management |
## Project Setup
# Initialize project with uv
# Add dependencies
# Add dev dependencies
# Project structure
# src/claude_dump/
#   __init__.py
#   cli.py          # Click commands
#   client.py       # httpx client, API calls
#   models.py       # Pydantic models for API responses
#   markdown.py     # Markdown generation helpers
#   exporter.py     # Orchestrates fetch -> format -> write
#   config.py       # Cookie/config management
## Key Design Decisions
### Sync over Async
- CLI tool runs sequentially: list projects -> pick one -> fetch conversations -> write files
- No concurrent requests needed (and concurrent requests risk rate limiting)
- Async adds complexity (asyncio.run, async def everywhere) with no benefit here
- If parallelism is ever needed, httpx supports async as an upgrade path
### Pin to Ranges, Not Exact Versions
### Minimal Dependencies Philosophy
- httpx: HTTP is the core function
- click: CLI UX matters for manual cookie input
- rich: Progress feedback during long exports
- pydantic: Safety net for undocumented API changes
## Sources
- httpx 0.28.1: https://pypi.org/project/httpx/ (verified 2026-04-12)
- click 8.3.2: https://pypi.org/project/click/ (verified 2026-04-12)
- rich 15.0.0: https://pypi.org/project/rich/ (verified 2026-04-12)
- pydantic 2.12.5: https://pypi.org/project/pydantic/ (verified 2026-04-12)
- requests 2.33.1: https://pypi.org/project/requests/ (verified 2026-04-12, considered and rejected)
- typer 0.24.1: https://pypi.org/project/typer/ (verified 2026-04-12, considered and rejected)
- curl-cffi 0.15.0: https://pypi.org/project/curl-cffi/ (verified 2026-04-12, flagged as escape hatch)
- uv 0.11.6: https://pypi.org/project/uv/ (verified 2026-04-12)
- tqdm 4.67.3: https://pypi.org/project/tqdm/ (verified 2026-04-12, considered and rejected)
- claudexit prior art: https://github.com/Rahul-999-alpha/claudexit (reviewed for patterns)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
