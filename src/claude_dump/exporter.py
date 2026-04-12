"""Export pipeline: fetch conversations, render to Markdown, write to disk."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)

from claude_dump.markdown import make_filename, render_conversation
from claude_dump.models import Conversation, FileRef, SessionExpiredError

if TYPE_CHECKING:
    from claude_dump.client import ClaudeAPIClient


@dataclass
class ExportResult:
    """Counts for each stage of the export pipeline."""

    conversations_exported: int = 0
    conversations_failed: int = 0
    knowledge_exported: int = 0
    knowledge_failed: int = 0
    files_exported: int = 0
    files_failed: int = 0


def _sanitize_filename(name: str) -> str:
    """Strip directory components and path traversal from a filename (T-03-01, T-03-04)."""
    if not name:
        return name
    # Use PurePosixPath to handle both / and collapse .. sequences,
    # then take only the final component.
    safe = PurePosixPath(name.replace("\\", "/")).name
    # Remove any remaining .. just in case
    return safe.replace("..", "")


def export_project(
    client: ClaudeAPIClient,
    project_uuid: str,
    project_name: str,
    output_dir: str | Path,
    skip_knowledge: bool = False,
    skip_files: bool = False,
) -> ExportResult:
    """Export all conversations, knowledge docs, and file attachments.

    Args:
        client: Authenticated API client with org_id set.
        project_uuid: UUID of the project to export.
        project_name: Human-readable project name (for console output).
        output_dir: Root output directory.
        skip_knowledge: If True, skip knowledge file download.
        skip_files: If True, skip file attachment download.

    Returns:
        ExportResult with counts for all three stages.
    """
    output_path = Path(output_dir)
    conv_dir = output_path / "conversations"
    conv_dir.mkdir(parents=True, exist_ok=True)

    if not skip_knowledge:
        knowledge_dir = output_path / "knowledge"
        knowledge_dir.mkdir(parents=True, exist_ok=True)

    if not skip_files:
        files_dir = output_path / "files"
        files_dir.mkdir(parents=True, exist_ok=True)

    result = ExportResult()

    # Step 1: List all conversations (pagination handled by client)
    conversations = client.list_conversations(project_uuid)

    # Collect unique file references for deduplication (D-05)
    all_file_refs: dict[str, FileRef] = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        transient=False,
    ) as progress:

        # --- Stage 1: Conversations ---
        if conversations:
            conv_task = progress.add_task(
                f"Exporting {project_name}",
                total=len(conversations),
            )

            for conv_meta in conversations:
                progress.update(
                    conv_task,
                    description=f"Exporting: {conv_meta.name or 'Untitled'}",
                )

                try:
                    full_conv = client.get_conversation(conv_meta.uuid)

                    # Collect file refs for later download (D-05)
                    for msg in full_conv.chat_messages:
                        for ref in msg.files_v2:
                            if ref.file_uuid:
                                all_file_refs[ref.file_uuid] = ref

                    markdown = render_conversation(full_conv)
                    filename = make_filename(full_conv)
                    filepath = conv_dir / filename
                    filepath.write_text(markdown, encoding="utf-8")

                    result.conversations_exported += 1

                except SessionExpiredError:
                    progress.stop()
                    raise

                except Exception:  # noqa: BLE001
                    result.conversations_failed += 1

                finally:
                    progress.advance(conv_task)

        # --- Stage 2: Knowledge files (D-02, D-03, D-20, D-21) ---
        if not skip_knowledge:
            try:
                knowledge_docs = client.list_knowledge_docs(project_uuid)
            except SessionExpiredError:
                raise
            except Exception:  # noqa: BLE001
                knowledge_docs = []

            if knowledge_docs:
                know_task = progress.add_task(
                    "Downloading knowledge files",
                    total=len(knowledge_docs),
                )

                for doc in knowledge_docs:
                    display_name = doc.file_name or doc.uuid[:8]
                    progress.update(
                        know_task,
                        description=f"Downloading: {display_name}",
                    )

                    try:
                        # Determine filename with sanitization (T-03-04)
                        if doc.file_name:
                            fname = _sanitize_filename(doc.file_name)
                        else:
                            fname = f"{doc.uuid[:8]}.md"

                        if not fname:
                            fname = f"{doc.uuid[:8]}.md"

                        (knowledge_dir / fname).write_text(
                            doc.content, encoding="utf-8"
                        )
                        result.knowledge_exported += 1

                    except SessionExpiredError:
                        raise

                    except Exception:  # noqa: BLE001
                        result.knowledge_failed += 1

                    finally:
                        progress.advance(know_task)

        # --- Stage 3: File attachments (D-08, D-10, D-20, D-21) ---
        if not skip_files and all_file_refs:
            file_task = progress.add_task(
                "Downloading file attachments",
                total=len(all_file_refs),
            )

            for file_uuid, ref in all_file_refs.items():
                display_name = ref.file_name or ref.file_uuid[:8]
                progress.update(
                    file_task,
                    description=f"Downloading: {display_name}",
                )

                try:
                    data = client.download_file_with_fallback(
                        ref.file_uuid, ref.file_kind
                    )

                    if data is None:
                        result.files_failed += 1
                        progress.console.print(
                            f"[yellow]Warning: Failed to download"
                            f" {ref.file_name or ref.file_uuid[:8]}[/yellow]"
                        )
                        progress.advance(file_task)
                        continue

                    # Build filename with sanitization (T-03-01)
                    safe_name = _sanitize_filename(ref.file_name)
                    if safe_name:
                        fname = f"{ref.file_uuid[:8]}_{safe_name}"
                    else:
                        fname = ref.file_uuid[:8]

                    (files_dir / fname).write_bytes(data)
                    result.files_exported += 1

                except SessionExpiredError:
                    raise

                except Exception:  # noqa: BLE001
                    result.files_failed += 1

                finally:
                    progress.advance(file_task)

    # Generate index.md after all exports complete (D-15)
    generate_index(output_path, conversations, result)

    return result


def generate_index(
    output_dir: str | Path,
    conversations: list[Conversation],
    result: ExportResult,
) -> None:
    """Create an index.md file summarising the export.

    Args:
        output_dir: Root output directory.
        conversations: Conversation metadata list (from list_conversations).
        result: Export counts for all three stages.
    """
    from datetime import date

    output_path = Path(output_dir)

    # Sort conversations newest-first (D-12)
    sorted_convs = sorted(conversations, key=lambda c: c.created_at or "", reverse=True)

    lines: list[str] = [
        "# Project Export Index",
        "",
        f"**Exported:** {date.today().isoformat()}",
        "",
        "| Category | Count |",
        "|----------|-------|",
        f"| Conversations | {result.conversations_exported} |",
        f"| Knowledge files | {result.knowledge_exported} |",
        f"| File attachments | {result.files_exported} |",
        "",
        "## Conversations",
        "",
        "| Date | Title | Link |",
        "|------|-------|------|",
    ]

    for conv in sorted_convs:
        conv_date = conv.created_at[:10] if conv.created_at else "Unknown"
        title = conv.name or "Untitled"
        link = f"conversations/{make_filename(conv)}"
        lines.append(f"| {conv_date} | {title} | [Open]({link}) |")

    lines.append("")

    # Knowledge files section (D-14)
    lines.append("## Knowledge Files")
    lines.append("")
    knowledge_dir = output_path / "knowledge"
    if knowledge_dir.is_dir():
        knowledge_files = sorted(f.name for f in knowledge_dir.iterdir() if f.is_file())
    else:
        knowledge_files = []

    if knowledge_files:
        for fname in knowledge_files:
            lines.append(f"- [{fname}](knowledge/{fname})")
    else:
        lines.append("No knowledge files exported.")

    lines.append("")

    # File attachments section
    lines.append("## File Attachments")
    lines.append("")
    files_dir = output_path / "files"
    if files_dir.is_dir():
        attachment_files = sorted(f.name for f in files_dir.iterdir() if f.is_file())
    else:
        attachment_files = []

    if attachment_files:
        for fname in attachment_files:
            lines.append(f"- [{fname}](files/{fname})")
    else:
        lines.append("No file attachments exported.")

    lines.append("")

    (output_path / "index.md").write_text("\n".join(lines), encoding="utf-8")
