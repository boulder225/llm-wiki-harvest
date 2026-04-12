# Technology Stack

**Project:** Claude Project Dumper
**Researched:** 2026-04-12

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

**Why httpx over requests:** `requests` (2.33.x) is battle-tested but lacks HTTP/2, async support, and has a less modern API. `httpx` is API-compatible with `requests` (nearly drop-in) but adds HTTP/2, async, and better timeout handling. For a tool hitting internal web APIs that may expect HTTP/2 behavior, httpx is the right choice.

**Why not curl-cffi:** `curl-cffi` (0.15.x) impersonates browser TLS fingerprints, which could help if Claude.ai blocks non-browser clients. However, it adds a compiled C dependency (libcurl), making installation heavier. Start with httpx -- if Claude.ai starts fingerprint-blocking, curl-cffi is the escape hatch. Flag this as a risk in PITFALLS.

**Confidence:** HIGH -- httpx is well-established, actively maintained, and the standard recommendation for new Python HTTP work.

### CLI Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| click | 8.3.x | CLI argument parsing, commands, prompts | Mature, stable, minimal magic, explicit. The project needs simple commands (dump, list-projects), not complex type-annotated interfaces |

**Why click over typer:** Typer (0.24.x) wraps click with type-hint magic and auto-generates help. It is nice for large CLIs with many subcommands. This tool has 3-5 commands max. Click is simpler, has no extra abstraction layer, and is a direct dependency rather than a wrapper. Typer's version is still 0.x, meaning API is not yet stable.

**Why not argparse:** Built-in but verbose, no built-in prompting, poor UX for interactive cookie input. Click handles prompts, password masking, and colored output natively.

**Confidence:** HIGH -- click is the most widely-used Python CLI library, rock-solid.

### Terminal Output & Progress

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| rich | 15.0.x | Progress bars, formatted terminal output, tables | Best-in-class terminal formatting. Shows download progress, conversation lists, error messages beautifully |

**Why rich over tqdm + manual formatting:** `tqdm` (4.67.x) does progress bars only. `rich` does progress bars AND tables AND colored output AND panels AND spinners. One dependency instead of cobbling together tqdm + colorama + tabulate. Rich's `Console` and `Progress` APIs are clean and well-documented.

**Confidence:** HIGH -- rich is the dominant terminal output library in the Python ecosystem.

### Data Modeling (Optional but Recommended)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pydantic | 2.12.x | Type-safe API response parsing | Claude.ai API responses are undocumented JSON. Pydantic models catch shape changes early with clear errors instead of silent KeyError failures deep in the code |

**Why use it:** The internal API will change without notice. Pydantic validation surfaces "API response changed" errors immediately at parse time, not deep in Markdown generation. This is critical for an undocumented API.

**Why it's optional:** For a small tool, raw dicts with careful `response.get()` calls work fine. Pydantic adds ~15MB to install size. Include it if the response shapes are complex (they likely are -- conversations have nested messages, attachments, metadata).

**Recommendation:** Include it. The API response complexity justifies the dependency.

**Confidence:** HIGH -- pydantic v2 is fast, mature, industry standard.

### Markdown Generation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| None (stdlib) | -- | Generate Markdown output files | Markdown is plain text with formatting conventions. No library needed. Use f-strings and `textwrap.dedent` |

**Why no library:** Libraries like `mdutils` or `marko` are for parsing Markdown or building complex documents programmatically. This tool generates simple, predictable Markdown: headers, paragraphs, code blocks. String formatting is clearer and more maintainable than learning a Markdown builder API.

**Pattern:** Create a small `markdown.py` module with helper functions:

```python
def heading(text: str, level: int = 1) -> str:
    return f"{'#' * level} {text}\n"

def code_block(code: str, lang: str = "") -> str:
    return f"```{lang}\n{code}\n```\n"

def conversation_to_markdown(conversation: Conversation) -> str:
    # Simple, readable, no dependencies
    ...
```

**Confidence:** HIGH -- this is universally accepted practice for simple Markdown generation.

### File I/O

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pathlib (stdlib) | -- | File and directory operations | Modern, object-oriented path handling. Built-in since Python 3.4. No reason to use `os.path` in 2026 |

**Pattern:** Use `pathlib.Path` for all path construction and file writing. Use `Path.mkdir(parents=True, exist_ok=True)` for directory creation.

**Confidence:** HIGH -- standard library, universally recommended.

### Configuration / Cookie Storage

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| None (plain file) | -- | Store session cookie between runs | Write cookie to `~/.config/claude-dump/cookie` (plain text). No TOML/YAML/JSON config library needed for a single value |

**Why not keyring/keychain:** Project explicitly scopes out automatic cookie extraction and complex platform-specific auth. A plain text file in `~/.config` is the simplest approach. Users already accept they are pasting cookies manually.

**Why not dotenv:** Overkill for one value. If config grows (e.g., default output dir, org preference), upgrade to a simple TOML file using `tomllib` (stdlib in Python 3.11+).

**Confidence:** HIGH -- matches project constraints perfectly.

## Complete Dependency List

### Core Dependencies (5 packages)

```
httpx>=0.28,<0.29
click>=8.3,<9
rich>=15,<16
pydantic>=2.12,<3
```

### Dev Dependencies

```
ruff              # Linting + formatting (replaces black, isort, flake8)
pytest            # Testing
pytest-httpx      # Mock httpx requests in tests
```

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

```bash
# Initialize project with uv
uv init claude-dump
cd claude-dump

# Add dependencies
uv add httpx click rich pydantic

# Add dev dependencies
uv add --dev ruff pytest pytest-httpx

# Project structure
# src/claude_dump/
#   __init__.py
#   cli.py          # Click commands
#   client.py       # httpx client, API calls
#   models.py       # Pydantic models for API responses
#   markdown.py     # Markdown generation helpers
#   exporter.py     # Orchestrates fetch -> format -> write
#   config.py       # Cookie/config management
```

## Key Design Decisions

### Sync over Async

Use httpx in synchronous mode. Rationale:
- CLI tool runs sequentially: list projects -> pick one -> fetch conversations -> write files
- No concurrent requests needed (and concurrent requests risk rate limiting)
- Async adds complexity (asyncio.run, async def everywhere) with no benefit here
- If parallelism is ever needed, httpx supports async as an upgrade path

### Pin to Ranges, Not Exact Versions

Use `>=X.Y,<X+1` ranges in pyproject.toml. The lockfile (uv.lock) pins exact versions. This allows security patches while preventing breaking changes.

### Minimal Dependencies Philosophy

4 runtime dependencies is the sweet spot for this project. Each earns its place:
- httpx: HTTP is the core function
- click: CLI UX matters for manual cookie input
- rich: Progress feedback during long exports
- pydantic: Safety net for undocumented API changes

Do NOT add dependencies for: JSON handling (stdlib), file I/O (stdlib), Markdown generation (string formatting), config (plain file), logging (stdlib).

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
