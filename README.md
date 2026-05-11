# claude-dump

A CLI tool that exports conversations and files from a **Claude.ai Project** into local Markdown, and imports **Fireflies.ai** meeting transcripts alongside them.

## Features

- Export all conversations from a Claude.ai project as Markdown files
- Download knowledge base documents and file attachments
- Incremental exports — only fetches new/updated conversations on subsequent runs
- Import Fireflies.ai transcripts as Markdown with speaker-grouped formatting
- Delta tracking (`.last-delta.json`) for downstream pipeline integration

## Installation

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Configuration

### Claude.ai

Provide your session cookie via environment variable or CLI flag:

```bash
export CLAUDE_SESSION_COOKIE="your-session-cookie-value"
```

Extract from browser DevTools → Application → Cookies → `sessionKey`.

### Fireflies.ai

```bash
export FIREFLIES_API_KEY="your-fireflies-api-key"
```

Get your key at https://app.fireflies.ai/integrations.

## Usage

### List Claude projects

```bash
claude-dump list-projects
```

### Export a Claude project

```bash
claude-dump dump --project <UUID> --output ./raw
```

Options:
- `--skip-knowledge` — skip knowledge base files
- `--skip-files` — skip file attachments
- `--full` — force full re-export (ignore previous state)
- `--last N` — also import N most recent Fireflies transcripts

### List Fireflies transcripts

```bash
claude-dump list-fireflies
```

### Import Fireflies transcripts

```bash
claude-dump import-fireflies --last 5 --output ./raw
```

### Combined export (Claude + Fireflies)

```bash
claude-dump dump --project <UUID> --output ./raw --last 3
```

## Pipeline Integration

The tool is designed to feed into downstream ingestion pipelines. After export:

1. **Export** — `claude-dump` writes Markdown files to an output directory
2. **Delta** — `.last-delta.json` records which files were new/updated
3. **Ingest** — a sync script picks up new files and feeds them to a wiki or knowledge base

Example orchestration:

```bash
# Dump Claude conversations
claude-dump dump --project $UUID --output ./raw

# Import Fireflies transcripts
claude-dump import-fireflies --last $N --output ./raw

# Ingest new files into wiki
for f in $(new_files_from_delta); do
  ingest "raw/$f"
done
```

## Architecture

```
src/claude_dump/
├── cli.py                  # Click commands (dump, list-projects, import-fireflies, list-fireflies)
├── client.py               # Claude.ai HTTP client (httpx, cookie auth)
├── models.py               # Pydantic models for Claude API responses
├── markdown.py             # Conversation → Markdown renderer
├── exporter.py             # Claude export orchestrator
├── manifest.py             # Incremental export state tracking
├── config.py               # Cookie/org/project resolution
├── fireflies_client.py     # Fireflies GraphQL client (Bearer token auth)
├── fireflies_models.py     # Pydantic models for Fireflies API
├── fireflies_markdown.py   # Transcript → Markdown renderer (speaker grouping)
├── fireflies_exporter.py   # Fireflies export pipeline
└── fireflies_config.py     # API key resolution
```

## Development

```bash
uv sync --group dev
uv run pytest
uv run ruff check src/
```

## License

Private project.
