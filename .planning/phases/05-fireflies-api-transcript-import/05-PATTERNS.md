# Phase 5: Fireflies API Transcript Import - Pattern Map

**Mapped:** 2026-05-11
**Files analyzed:** 6
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/claude_dump/fireflies_client.py` | service | request-response | `src/claude_dump/client.py` | exact |
| `src/claude_dump/fireflies_models.py` | model | transform | `src/claude_dump/models.py` | exact |
| `src/claude_dump/fireflies_markdown.py` | utility | transform | `src/claude_dump/markdown.py` | exact |
| `src/claude_dump/cli.py` (modified) | controller | request-response | `src/claude_dump/cli.py` | exact |
| `src/claude_dump/config.py` (modified) | config | resolution | `src/claude_dump/config.py` | exact |
| `src/claude_dump/fireflies_exporter.py` | service | pipeline | `src/claude_dump/exporter.py` | exact |

## Pattern Assignments

### `src/claude_dump/fireflies_client.py` (service, request-response)

**Analog:** `src/claude_dump/client.py`

**Imports pattern** (lines 1-19):
```python
"""HTTP client for Fireflies.ai GraphQL API with retry/backoff logic."""

from __future__ import annotations

import sys
import time
from typing import TYPE_CHECKING

import httpx

from claude_dump.fireflies_models import (
    FirefliesAPIError,
    FirefliesRateLimitError,
    Transcript,
)

if TYPE_CHECKING:
    from types import TracebackType
```

**Client class structure** (lines 54-108):
```python
class ClaudeAPIClient:
    """Synchronous HTTP client for the Claude.ai internal REST API."""

    def __init__(
        self,
        cookie: str,
        org_id: str | None = None,
        verbose: bool = False,
    ) -> None:
        self._cookie = cookie
        self._org_id = org_id
        self._verbose = verbose
        self._console = None  # lazy-init if verbose

        self._http = httpx.Client(
            base_url="https://claude.ai/api",
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers=self._build_headers(),
            follow_redirects=True,
        )

    # -- context manager ---------------------------------------------------

    def __enter__(self) -> ClaudeAPIClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()
```

**Retry logic pattern** (lines 223-269):
```python
def _request(self, method: str, path: str) -> httpx.Response:
    """Execute an HTTP request with exponential-backoff retry."""
    last_response: httpx.Response | None = None

    for attempt in range(_MAX_RETRIES + 1):
        resp = self._http.request(method, path)

        if resp.is_success:
            return resp

        # 401 -- session expired, never retry
        if resp.status_code == 401:
            raise SessionExpiredError()

        # Non-retryable error
        if resp.status_code not in _RETRYABLE_STATUS_CODES:
            raise APIError(
                status_code=resp.status_code,
                response_body=resp.text[:500],
            )

        last_response = resp

        # Retryable -- back off unless this was the last attempt
        if attempt < _MAX_RETRIES:
            delay = self._backoff_delay(attempt, resp)
            self._log_retry(attempt + 1, resp.status_code, delay)
            time.sleep(delay)

    # Retries exhausted
    assert last_response is not None
    if last_response.status_code in _RATE_LIMIT_CODES:
        retry_after = self._parse_retry_after(last_response)
        raise RateLimitError(retry_after=retry_after)

    raise APIError(
        status_code=last_response.status_code,
        response_body=last_response.text[:500],
    )
```

**Key adaptation notes for GraphQL:**
- Change `base_url` to `https://api.fireflies.ai/graphql`
- Replace `_request(method, path)` with `_query(query: str, variables: dict)` that POSTs JSON
- Auth header becomes `Authorization: Bearer {api_key}` instead of cookie
- Response extraction: `resp.json()["data"]` with error check on `resp.json().get("errors")`

---

### `src/claude_dump/fireflies_models.py` (model, transform)

**Analog:** `src/claude_dump/models.py`

**Model pattern** (lines 1-30):
```python
"""Pydantic models for Claude.ai API responses and custom exceptions."""

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# API response models
# ---------------------------------------------------------------------------

class Organization(BaseModel):
    """Parsed from GET /api/organizations response items."""

    model_config = ConfigDict(extra="ignore")

    uuid: str
    name: str
    email_address: str = ""
```

**Key conventions:**
- Every model uses `model_config = ConfigDict(extra="ignore")` to tolerate unknown fields
- Fields have safe defaults (empty string, empty list via `Field(default_factory=list)`)
- Models are validated with `Model.model_validate(data_dict)`
- Docstring states which API endpoint the model corresponds to

**Exception pattern** (lines 115-146):
```python
class APIError(Exception):
    """Base exception for non-retryable API errors."""

    def __init__(self, status_code: int, response_body: str) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(
            f"API error {status_code}: {response_body[:200]}"
        )


class RateLimitError(Exception):
    """Raised on HTTP 429/529 after retry attempts are exhausted."""

    def __init__(self, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        msg = "Rate limited by Claude.ai API"
        if retry_after is not None:
            msg += f" (retry after {retry_after}s)"
        super().__init__(msg)
```

---

### `src/claude_dump/fireflies_markdown.py` (utility, transform)

**Analog:** `src/claude_dump/markdown.py`

**Module docstring and imports pattern** (lines 1-10):
```python
"""Markdown rendering for Claude.ai conversation export.

Pure transformation layer: converts Conversation/ChatMessage/ContentBlock
model objects into well-formatted Markdown strings.  No I/O, no HTTP calls.
"""

import json
import re

from claude_dump.models import ChatMessage, ContentBlock, Conversation
```

**Render function pattern** (lines 92-119):
```python
def render_conversation(conv: Conversation) -> str:
    """Render a full conversation to a Markdown document."""
    lines: list[str] = [
        "---",
        f"title: {conv.name}",
        f"model: {conv.model}",
        f"created: {conv.created_at}",
        f"updated: {conv.updated_at}",
        f"uuid: {conv.uuid}",
        "---",
    ]

    if conv.summary:
        lines.append(f"> {conv.summary}")
        lines.append("")

    lines.append("")
    lines.append(f"# {conv.name}")
    lines.append("")

    messages = [render_message(m) for m in conv.chat_messages]
    lines.append("\n\n---\n\n".join(messages))

    return "\n".join(lines)
```

**Filename utility pattern** (lines 127-151):
```python
def sanitize_title(title: str) -> str:
    """Convert a conversation title into a filesystem-safe slug."""
    result = title.lower()
    result = result.replace(" ", "-")
    result = re.sub(r"[^a-z0-9_-]", "", result)
    result = re.sub(r"-{2,}", "-", result)
    result = result.strip("-")
    result = result[:100]
    return result or "untitled"


def make_filename(conv: Conversation) -> str:
    """Generate a sort-friendly, collision-resistant Markdown filename."""
    date = conv.created_at[:10] if conv.created_at else "0000-00-00"
    sanitized = sanitize_title(conv.name)
    short_uuid = conv.uuid[:8]
    return f"{date}_{sanitized}_{short_uuid}.md"
```

---

### `src/claude_dump/cli.py` (modified - new commands)

**Analog:** `src/claude_dump/cli.py` (self)

**CLI group and option pattern** (lines 143-153):
```python
@click.group()
@click.option("--cookie", default=None, help="Session cookie (sessionKey value or full cookie header)")
@click.option("--org", default=None, help="Organization UUID (skip org discovery)")
@click.option("--verbose", is_flag=True, help="Show raw HTTP details for debugging")
@click.pass_context
def main(ctx: click.Context, cookie: str | None, org: str | None, verbose: bool) -> None:
    """Export Claude.ai project conversations and files."""
    ctx.ensure_object(dict)
    ctx.obj["cookie"] = cookie
    ctx.obj["org"] = org
    ctx.obj["verbose"] = verbose
```

**Command pattern** (lines 156-174):
```python
@main.command("list-projects")
@click.pass_context
def list_projects_cmd(ctx: click.Context) -> None:
    """List all projects in your Claude.ai account."""
    verbose: bool = ctx.obj["verbose"]
    try:
        client, _org = _authenticate(ctx)
        try:
            projects = client.list_projects()
            if not projects:
                console.print("No projects found.")
                return
            _display_projects(projects)
        finally:
            client.close()
    except (SessionExpiredError, RateLimitError, APIError, KeyboardInterrupt) as e:
        _handle_error(e, verbose)
    except Exception as e:  # noqa: BLE001
        _handle_error(e, verbose)
```

**Error handling pattern** (lines 107-135):
```python
def _handle_error(e: Exception, verbose: bool) -> None:
    """Print a friendly error message and exit."""
    if isinstance(e, SessionExpiredError):
        err_console.print(
            "[bold red]Error:[/bold red] Session cookie is invalid or expired.\n"
            "Hint: Re-extract from browser DevTools > Application > Cookies > sessionKey",
        )
        sys.exit(1)
    if isinstance(e, RateLimitError):
        err_console.print(
            "[bold red]Error:[/bold red] Rate limited by Claude.ai. "
            "Try again in a few minutes.",
        )
        sys.exit(1)
    # ... etc
```

---

### `src/claude_dump/config.py` (modified - API key resolution)

**Analog:** `src/claude_dump/config.py` (self)

**Resolution function pattern** (lines 55-81):
```python
def resolve_cookie(cli_cookie: str | None) -> str:
    """Resolve the session cookie from CLI flag, env var, .env file, or prompt.

    Priority order (per D-01):
    1. ``--cookie`` CLI flag
    2. ``CLAUDE_SESSION_COOKIE`` environment variable
    3. ``.env`` file in current directory
    4. Interactive masked prompt via click
    """
    # 1. CLI flag
    if cli_cookie:
        return normalize_cookie(cli_cookie)

    # 2. Environment variable
    env_val = os.environ.get("CLAUDE_SESSION_COOKIE", "").strip()
    if env_val:
        return normalize_cookie(env_val)

    # 3. .env file
    dotenv_val = _read_env_value("CLAUDE_SESSION_COOKIE")
    if dotenv_val:
        return normalize_cookie(dotenv_val)

    # 4. Interactive prompt (masked)
    prompted = click.prompt("Session cookie", hide_input=True)
    return normalize_cookie(prompted)
```

**New function `resolve_fireflies_api_key` should follow this exact pattern** with:
- Env var: `FIREFLIES_API_KEY`
- .env key: `FIREFLIES_API_KEY`
- Prompt text: `"Fireflies API key"`

---

### `src/claude_dump/fireflies_exporter.py` (service, pipeline)

**Analog:** `src/claude_dump/exporter.py`

**Result dataclass pattern** (lines 25-36):
```python
@dataclass
class ExportResult:
    """Counts for each stage of the export pipeline."""

    conversations_exported: int = 0
    conversations_skipped: int = 0
    conversations_failed: int = 0
    knowledge_exported: int = 0
    knowledge_failed: int = 0
    files_exported: int = 0
    files_failed: int = 0
    exported_files: list[str] = field(default_factory=list)
```

**Pipeline function pattern** (lines 50-58):
```python
def export_project(
    client: ClaudeAPIClient,
    project_uuid: str,
    project_name: str,
    output_dir: str | Path,
    skip_knowledge: bool = False,
    skip_files: bool = False,
    full: bool = False,
) -> ExportResult:
```

**Progress bar pattern** (lines 100-106):
```python
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    MofNCompleteColumn(),
    transient=False,
) as progress:
```

**Error handling within pipeline** (lines 139-147):
```python
except SessionExpiredError:
    progress.stop()
    raise

except Exception:  # noqa: BLE001
    result.conversations_failed += 1

finally:
    progress.advance(conv_task)
```

---

## Shared Patterns

### Config Resolution (4-step priority)
**Source:** `src/claude_dump/config.py` lines 55-81
**Apply to:** New `resolve_fireflies_api_key` function
```python
# Pattern: CLI flag -> env var -> .env file -> interactive prompt
def resolve_X(cli_value: str | None) -> str:
    if cli_value:
        return cli_value
    env_val = os.environ.get("ENV_VAR_NAME", "").strip()
    if env_val:
        return env_val
    dotenv_val = _read_env_value("ENV_VAR_NAME")
    if dotenv_val:
        return dotenv_val
    prompted = click.prompt("Prompt text", hide_input=True)
    return prompted
```

### Error Handling (CLI layer)
**Source:** `src/claude_dump/cli.py` lines 107-135
**Apply to:** New `list-fireflies` and `import-fireflies` commands
```python
try:
    # main logic
    try:
        # api calls
    finally:
        client.close()
except (SpecificError1, SpecificError2, KeyboardInterrupt) as e:
    _handle_error(e, verbose)
except Exception as e:  # noqa: BLE001
    _handle_error(e, verbose)
```

### Pydantic Model Convention
**Source:** `src/claude_dump/models.py` (all models)
**Apply to:** All Fireflies response models
```python
class ModelName(BaseModel):
    """Docstring: which API endpoint this corresponds to."""

    model_config = ConfigDict(extra="ignore")

    required_field: str
    optional_field: str = ""
    list_field: list[SubModel] = Field(default_factory=list)
```

### httpx Client Setup
**Source:** `src/claude_dump/client.py` lines 76-81
**Apply to:** Fireflies client
```python
self._http = httpx.Client(
    base_url="https://api.fireflies.ai/graphql",
    timeout=httpx.Timeout(30.0, connect=10.0),
    headers=self._build_headers(),
    follow_redirects=True,
)
```

### Markdown Rendering (pure transform, no I/O)
**Source:** `src/claude_dump/markdown.py` module docstring
**Apply to:** `fireflies_markdown.py`
- YAML front matter with `---` delimiters
- Build `lines: list[str]`, join with `"\n"` at end
- `sanitize_title()` and `make_filename()` for output filenames

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none) | -- | -- | All new files have direct analogs in the existing codebase |

## Metadata

**Analog search scope:** `src/claude_dump/`
**Files scanned:** 7
**Pattern extraction date:** 2026-05-11
