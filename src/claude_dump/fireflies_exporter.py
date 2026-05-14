"""Export pipeline: fetch Fireflies transcripts, render to Markdown, write to disk."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)

from claude_dump.fireflies_markdown import make_transcript_filename, render_transcript
from claude_dump.fireflies_models import FirefliesAuthError

if TYPE_CHECKING:
    from claude_dump.fireflies_client import FirefliesClient


@dataclass
class FirefliesExportResult:
    """Counts for the Fireflies export pipeline."""

    transcripts_exported: int = 0
    transcripts_failed: int = 0
    exported_files: list[str] = field(default_factory=list)


def export_fireflies_transcripts(
    client: FirefliesClient,
    output_dir: str | Path,
    last: int | None = None,
    verbose: bool = False,
) -> FirefliesExportResult:
    """Export Fireflies transcripts as Markdown files.

    Args:
        client: Authenticated Fireflies API client.
        output_dir: Directory to write Markdown files into.
        last: If set, only export the N most recent transcripts.

    Returns:
        FirefliesExportResult with export counts.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    result = FirefliesExportResult()

    # Step 1: List all transcripts
    summaries = client.list_all_transcripts()

    if not summaries:
        return result

    # Step 1.5: Trim to most recent N if --last specified
    if last is not None:
        summaries.sort(key=lambda s: s.date or "", reverse=True)
        summaries = summaries[:last]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        transient=False,
    ) as progress:
        task = progress.add_task(
            "Importing Fireflies transcripts",
            total=len(summaries),
        )

        for summary in summaries:
            progress.update(
                task,
                description=f"Importing: {summary.title or 'Untitled'}",
            )

            try:
                full = client.get_transcript(summary.id)
                markdown = render_transcript(full)
                filename = make_transcript_filename(full)
                (output_path / filename).write_text(markdown, encoding="utf-8")

                result.transcripts_exported += 1
                result.exported_files.append(filename)

            except FirefliesAuthError:
                progress.stop()
                raise

            except Exception as exc:  # noqa: BLE001
                result.transcripts_failed += 1
                progress.console.print(f"[red]Failed: {summary.title}: {exc}[/red]")
                if verbose:
                    import traceback
                    traceback.print_exc()

            finally:
                progress.advance(task)

    return result
