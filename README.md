# llm-wiki-harvest

A CLI tool that harvests conversations and meeting transcripts from AI platforms (Claude.ai, Fireflies.ai) into Markdown — designed to feed an [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

## Inspiration

Andrej Karpathy proposed the idea of a personal wiki maintained by an LLM — a living knowledge base that ingests raw material (conversations, meetings, notes) and organizes it into structured, searchable knowledge. See [his original gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) and [balukosuri's implementation](https://github.com/balukosuri/llm-wiki-karpathy).

This tool is the **harvester** — it pulls raw conversations and transcripts from upstream platforms and writes them as Markdown files ready for wiki ingestion.

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

### Post-export hook

Run a command for each exported file automatically:

```bash
export CLAUDE_DUMP_POST_CMD='~/run-claude-from-env.sh -p "ingest raw/{}"'
```

The `{}` placeholder is replaced with each exported filename. The command runs from the parent of the output directory. Can also be set in `.env`.

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

### Example output

```
$ claude-dump dump --project <UUID> --output ./raw --last 1

Using organization: user@example.com's Organization
Selected project: My Project (019af253-...)

Export Report
  Output: ./raw
Category             Exported   Skipped   Failed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Conversations               0       156        -
Knowledge files             0         -        -
File attachments            0         -        -
Fireflies transcripts       1         -        -

Done. Index: ./raw/index.md
Delta: ./raw/.last-delta.json (1 files)

New/updated files:
  2026-05-12-weekly-standup.md
```

## Pipeline Integration

The tool is designed to feed into downstream ingestion pipelines (like an LLM Wiki). After export:

1. **Harvest** — `claude-dump` writes Markdown files to an output directory
2. **Delta** — `.last-delta.json` records which files were new/updated
3. **Ingest** — post-export hook runs a command per new file

### Single-command pipeline

Set `CLAUDE_DUMP_POST_CMD` in your `.env` and run everything in one shot:

```bash
claude-dump dump --project <UUID> --output ./raw --last 1
```

This exports conversations, imports Fireflies transcripts, and runs the ingest hook for each new file.

### Manual orchestration (`sync.sh`)

```bash
#!/bin/bash
set -e

# Dump Claude conversations (incremental)
claude-dump dump --project $PROJECT_UUID --output ./raw

# Import recent Fireflies transcripts
claude-dump import-fireflies --last $N --output ./raw

# Ingest new/updated files into the LLM wiki
for f in $(new_files_from_delta); do
  wiki-ingest "raw/$f"
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

MIT
