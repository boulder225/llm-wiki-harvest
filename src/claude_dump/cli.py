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
@click.pass_context
def dump(ctx: click.Context, project: str | None, output: str, skip_knowledge: bool, skip_files: bool) -> None:
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
            )

            # Print summary
            console.print()  # blank line
            if result.conversations_exported > 0:
                console.print(
                    f"[bold green]Exported {result.conversations_exported} conversation(s)[/bold green] "
                    f"to {output}/conversations/",
                )
            if result.conversations_failed > 0:
                err_console.print(
                    f"[yellow]Warning:[/yellow] {result.conversations_failed} conversation(s) failed to export.",
                )
            if result.knowledge_exported > 0:
                console.print(
                    f"[bold green]Downloaded {result.knowledge_exported} knowledge file(s)[/bold green] "
                    f"to {output}/knowledge/",
                )
            if result.knowledge_failed > 0:
                err_console.print(
                    f"[yellow]Warning:[/yellow] {result.knowledge_failed} knowledge file(s) failed to download.",
                )
            if result.files_exported > 0:
                console.print(
                    f"[bold green]Downloaded {result.files_exported} file attachment(s)[/bold green] "
                    f"to {output}/files/",
                )
            if result.files_failed > 0:
                err_console.print(
                    f"[yellow]Warning:[/yellow] {result.files_failed} file attachment(s) failed to download.",
                )

            total = result.conversations_exported + result.knowledge_exported + result.files_exported
            if total == 0:
                console.print("No content found in this project.")
            else:
                console.print(f"\n[bold]Index written to {output}/index.md[/bold]")
        finally:
            client.close()
    except (SessionExpiredError, RateLimitError, APIError, KeyboardInterrupt) as e:
        _handle_error(e, verbose)
    except Exception as e:  # noqa: BLE001
        _handle_error(e, verbose)
