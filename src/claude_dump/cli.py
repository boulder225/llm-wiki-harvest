"""Click CLI with auth validation, project listing, and project selection."""

from __future__ import annotations

import sys
import traceback

import click
from rich.console import Console
from rich.table import Table

from claude_dump.client import ClaudeAPIClient
from claude_dump.config import resolve_cookie, resolve_org_id, resolve_project_uuid
from claude_dump.exporter import ExportResult, export_project
from claude_dump.fireflies_client import FirefliesClient
from claude_dump.fireflies_config import resolve_fireflies_api_key
from claude_dump.fireflies_exporter import FirefliesExportResult, export_fireflies_transcripts
from claude_dump.fireflies_markdown import format_timestamp
from claude_dump.fireflies_models import FirefliesAPIError, FirefliesAuthError
from claude_dump.models import (
    APIError,
    Organization,
    Project,
    RateLimitError,
    SessionExpiredError,
)

console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Shared authentication helper
# ---------------------------------------------------------------------------


def _authenticate(ctx: click.Context) -> tuple[ClaudeAPIClient, Organization]:
    """Resolve cookie, create client, validate session, and select org.

    Returns the configured client (with ``org_id`` set) and the selected
    :class:`Organization`.  The caller is responsible for closing the client.
    """
    cookie = resolve_cookie(ctx.obj["cookie"])
    verbose: bool = ctx.obj["verbose"]

    client = ClaudeAPIClient(cookie=cookie, verbose=verbose)

    # Validate cookie by fetching organisations (D-12, AUTH-03)
    orgs = client.get_organizations()

    # Org selection
    explicit_org = resolve_org_id(ctx.obj["org"])
    if explicit_org:
        # User supplied org explicitly -- trust it
        client.org_id = explicit_org
        selected = Organization(uuid=explicit_org, name=explicit_org)
        # Try to find a matching org object for a nicer display name
        for o in orgs:
            if o.uuid == explicit_org:
                selected = o
                break
        console.print(f"Using organization: {selected.name}")
        return client, selected

    if len(orgs) == 1:
        # Auto-select single org (D-05)
        selected = orgs[0]
        client.org_id = selected.uuid
        console.print(f"Using organization: {selected.name}")
        return client, selected

    if len(orgs) == 0:
        err_console.print(
            "[bold red]Error:[/bold red] No organizations found for this account.",
        )
        client.close()
        sys.exit(1)

    # Multiple orgs -- prompt user to select
    table = Table(title="Organizations")
    table.add_column("#", style="bold", width=4)
    table.add_column("Name")
    table.add_column("Email")
    for idx, org in enumerate(orgs, 1):
        table.add_row(str(idx), org.name, org.email_address)
    console.print(table)

    choice = click.prompt(
        "Select organization",
        type=click.IntRange(1, len(orgs)),
    )
    selected = orgs[choice - 1]
    client.org_id = selected.uuid
    console.print(f"Using organization: {selected.name}")
    return client, selected


def _display_projects(projects: list[Project]) -> None:
    """Print a Rich table of projects."""
    table = Table(title="Projects")
    table.add_column("#", style="bold", width=4)
    table.add_column("Name")
    table.add_column("Created")
    table.add_column("Description")
    for idx, proj in enumerate(projects, 1):
        # Show date portion only if created_at is available
        created = proj.created_at[:10] if proj.created_at else ""
        table.add_row(str(idx), proj.name, created, proj.description or "")
    console.print(table)


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
    if isinstance(e, APIError):
        err_console.print(
            f"[bold red]Error:[/bold red] API request failed (HTTP {e.status_code})",
        )
        if verbose:
            err_console.print(e.response_body)
        sys.exit(1)
    if isinstance(e, KeyboardInterrupt):
        err_console.print("\nAborted.")
        sys.exit(130)
    # Unexpected
    err_console.print(f"[bold red]Unexpected error:[/bold red] {e}")
    if verbose:
        traceback.print_exc(file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# CLI group and commands
# ---------------------------------------------------------------------------


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


@main.command()
@click.option("--project", default=None, help="Project UUID to export")
@click.option("--output", "-o", default=".", help="Output directory", type=click.Path())
@click.option("--skip-knowledge", is_flag=True, help="Skip downloading knowledge files")
@click.option("--skip-files", is_flag=True, help="Skip downloading file attachments")
@click.option("--full", is_flag=True, help="Force full re-export, ignoring previous export state")
@click.option("--last", default=None, type=int, help="Also import the N most recent Fireflies transcripts")
@click.option("--fireflies-api-key", default=None, help="Fireflies API key (or set FIREFLIES_API_KEY env var)")
@click.pass_context
def dump(ctx: click.Context, project: str | None, output: str, skip_knowledge: bool, skip_files: bool, full: bool, last: int | None, fireflies_api_key: str | None) -> None:
    """Export a Claude.ai project's conversations and files."""
    verbose: bool = ctx.obj["verbose"]
    try:
        client, _org = _authenticate(ctx)
        try:
            projects = client.list_projects()
            if not projects:
                err_console.print("[bold red]Error:[/bold red] No projects found.")
                sys.exit(1)

            # Resolve project UUID
            project_uuid = resolve_project_uuid(project)
            selected: Project | None = None

            if project_uuid:
                # Verify it exists in the project list
                for p in projects:
                    if p.uuid == project_uuid:
                        selected = p
                        break
                if selected is None:
                    err_console.print(
                        f"[bold red]Error:[/bold red] Project UUID "
                        f"'{project_uuid}' not found in your projects.",
                    )
                    sys.exit(1)
            else:
                # Interactive selection
                _display_projects(projects)
                choice = click.prompt(
                    "Select project to export",
                    type=click.IntRange(1, len(projects)),
                )
                selected = projects[choice - 1]

            console.print(
                f"Selected project: {selected.name} ({selected.uuid})",
            )

            # Export conversations, knowledge docs, and file attachments
            result = export_project(
                client=client,
                project_uuid=selected.uuid,
                project_name=selected.name,
                output_dir=output,
                skip_knowledge=skip_knowledge,
                skip_files=skip_files,
                full=full,
            )

            # Fireflies import (if --last specified)
            ff_result: FirefliesExportResult | None = None
            if last is not None:
                console.print("\nImporting Fireflies transcripts...")
                ff_key = resolve_fireflies_api_key(fireflies_api_key)
                with FirefliesClient(api_key=ff_key, verbose=verbose) as ff_client:
                    ff_result = export_fireflies_transcripts(ff_client, output, last=last, verbose=verbose)

            # Print combined report
            console.print()
            console.print("[bold]Export Report[/bold]")
            console.print(f"  Output: {output}")

            table = Table(show_header=True, show_edge=False, pad_edge=False)
            table.add_column("Category", style="bold")
            table.add_column("Exported", justify="right", style="green")
            table.add_column("Skipped", justify="right", style="dim")
            table.add_column("Failed", justify="right", style="red")

            table.add_row(
                "Conversations",
                str(result.conversations_exported),
                str(result.conversations_skipped),
                str(result.conversations_failed) if result.conversations_failed else "-",
            )
            if not skip_knowledge:
                table.add_row(
                    "Knowledge files",
                    str(result.knowledge_exported),
                    "-",
                    str(result.knowledge_failed) if result.knowledge_failed else "-",
                )
            if not skip_files:
                table.add_row(
                    "File attachments",
                    str(result.files_exported),
                    "-",
                    str(result.files_failed) if result.files_failed else "-",
                )
            if ff_result is not None:
                table.add_row(
                    "Fireflies transcripts",
                    str(ff_result.transcripts_exported),
                    "-",
                    str(ff_result.transcripts_failed) if ff_result.transcripts_failed else "-",
                )

            console.print(table)

            all_files = list(result.exported_files or [])
            if ff_result is not None:
                all_files.extend(ff_result.exported_files)

            total = result.conversations_exported + result.knowledge_exported + result.files_exported
            if ff_result is not None:
                total += ff_result.transcripts_exported

            if total == 0:
                console.print("\nNo new content to export.")
            else:
                console.print(f"\n[bold]Done.[/bold] Index: {output}/index.md")
                if all_files:
                    console.print(f"Delta: {output}/.last-delta.json ({len(result.exported_files or [])} files)")
                    console.print("\n[bold]New/updated files:[/bold]")
                    for f in all_files:
                        console.print(f"  {f}")
        finally:
            client.close()
    except (SessionExpiredError, RateLimitError, APIError, FirefliesAuthError, FirefliesAPIError, KeyboardInterrupt) as e:
        if isinstance(e, (FirefliesAuthError, FirefliesAPIError)):
            _handle_fireflies_error(e, verbose)
        else:
            _handle_error(e, verbose)
    except Exception as e:  # noqa: BLE001
        _handle_error(e, verbose)


# ---------------------------------------------------------------------------
# Fireflies commands
# ---------------------------------------------------------------------------


def _handle_fireflies_error(e: Exception, verbose: bool) -> None:
    """Print a friendly error message for Fireflies commands and exit."""
    if isinstance(e, FirefliesAuthError):
        err_console.print(
            "[bold red]Error:[/bold red] Fireflies API key is invalid. "
            "Check your key at https://app.fireflies.ai/integrations",
        )
        sys.exit(1)
    if isinstance(e, FirefliesAPIError):
        err_console.print(
            f"[bold red]Error:[/bold red] Fireflies API error (HTTP {e.status_code})",
        )
        if verbose:
            err_console.print(e.response_body)
        sys.exit(1)
    if isinstance(e, KeyboardInterrupt):
        err_console.print("\nAborted.")
        sys.exit(130)
    # Unexpected
    err_console.print(f"[bold red]Unexpected error:[/bold red] {e}")
    if verbose:
        traceback.print_exc(file=sys.stderr)
    sys.exit(1)


@main.command("list-fireflies")
@click.option("--api-key", default=None, help="Fireflies API key")
@click.pass_context
def list_fireflies_cmd(ctx: click.Context, api_key: str | None) -> None:
    """List all transcripts in your Fireflies.ai account."""
    verbose: bool = ctx.obj["verbose"]
    try:
        key = resolve_fireflies_api_key(api_key)
        with FirefliesClient(api_key=key, verbose=verbose) as client:
            transcripts = client.list_all_transcripts()

            if not transcripts:
                console.print("No transcripts found.")
                return

            table = Table(title="Fireflies Transcripts")
            table.add_column("#", style="bold", width=4)
            table.add_column("Title")
            table.add_column("Date")
            table.add_column("Duration")
            table.add_column("Participants")

            for idx, t in enumerate(transcripts, 1):
                date = t.date[:10] if t.date else ""
                duration = format_timestamp(t.duration)
                participants = ", ".join(t.participants) if t.participants else ""
                table.add_row(str(idx), t.title, date, duration, participants)

            console.print(table)
    except (FirefliesAuthError, FirefliesAPIError, KeyboardInterrupt) as e:
        _handle_fireflies_error(e, verbose)
    except Exception as e:  # noqa: BLE001
        _handle_fireflies_error(e, verbose)


@main.command("import-fireflies")
@click.option("--api-key", default=None, help="Fireflies API key")
@click.option("--output", "-o", default=".", help="Output directory", type=click.Path())
@click.option("--last", default=None, type=int, help="Import only the N most recent transcripts")
@click.pass_context
def import_fireflies_cmd(ctx: click.Context, api_key: str | None, output: str, last: int | None) -> None:
    """Import Fireflies.ai transcripts as Markdown files."""
    verbose: bool = ctx.obj["verbose"]
    try:
        key = resolve_fireflies_api_key(api_key)
        with FirefliesClient(api_key=key, verbose=verbose) as client:
            result = export_fireflies_transcripts(client, output, last=last, verbose=verbose)

            # Print summary report
            console.print()
            console.print("[bold]Import Report[/bold]")
            console.print(f"  Output: {output}")

            table = Table(show_header=True, show_edge=False, pad_edge=False)
            table.add_column("Category", style="bold")
            table.add_column("Exported", justify="right", style="green")
            table.add_column("Failed", justify="right", style="red")

            table.add_row(
                "Transcripts",
                str(result.transcripts_exported),
                str(result.transcripts_failed) if result.transcripts_failed else "-",
            )
            console.print(table)

            if result.transcripts_exported > 0:
                console.print(
                    f"\n[bold]Done.[/bold] {result.transcripts_exported} "
                    f"transcript(s) imported to {output}",
                )
            else:
                console.print("\nNo transcripts found.")
    except (FirefliesAuthError, FirefliesAPIError, KeyboardInterrupt) as e:
        _handle_fireflies_error(e, verbose)
    except Exception as e:  # noqa: BLE001
        _handle_fireflies_error(e, verbose)
