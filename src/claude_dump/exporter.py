"""Export pipeline: fetch conversations, render to Markdown, write to disk."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)

from claude_dump.markdown import make_filename, render_conversation
from claude_dump.models import SessionExpiredError

if TYPE_CHECKING:
    from claude_dump.client import ClaudeAPIClient


def export_project(
    client: ClaudeAPIClient,
    project_uuid: str,
    project_name: str,
    output_dir: str | Path,
) -> tuple[int, int]:
    """Export all conversations in a project to Markdown files.

    Args:
        client: Authenticated API client with org_id set.
        project_uuid: UUID of the project to export.
        project_name: Human-readable project name (for console output).
        output_dir: Root output directory. Conversations go into {output_dir}/conversations/.

    Returns:
        Tuple of (exported_count, failed_count).
    """
    output_path = Path(output_dir)
    conv_dir = output_path / "conversations"
    conv_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: List all conversations (pagination handled by client)
    conversations = client.list_conversations(project_uuid)

    if not conversations:
        return (0, 0)

    exported = 0
    failed = 0

    # Step 2: Fetch each conversation sequentially, render, and write
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        transient=False,
    ) as progress:
        task_id = progress.add_task(
            f"Exporting {project_name}",
            total=len(conversations),
        )

        for conv_meta in conversations:
            # Update progress description
            progress.update(
                task_id,
                description=f"Exporting: {conv_meta.name or 'Untitled'}",
            )

            try:
                # Fetch full conversation with messages
                full_conv = client.get_conversation(conv_meta.uuid)

                # Render to Markdown
                markdown = render_conversation(full_conv)

                # Generate filename
                filename = make_filename(full_conv)

                # Write immediately to disk (write-as-you-go)
                filepath = conv_dir / filename
                filepath.write_text(markdown, encoding="utf-8")

                exported += 1

            except SessionExpiredError:
                # Halt immediately, already-exported files remain intact
                progress.stop()
                raise

            except Exception:  # noqa: BLE001
                # Non-fatal: skip this conversation, continue with rest
                failed += 1

            finally:
                progress.advance(task_id)

    return (exported, failed)
