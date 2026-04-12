"""Cookie input, normalization, and environment variable loading."""

from __future__ import annotations

import os
from pathlib import Path

import click


def normalize_cookie(raw: str) -> str:
    """Normalize a session cookie value.

    Accepts both a bare ``sk-ant-...`` sessionKey value and a full cookie
    header string like ``sessionKey=sk-ant-abc; lastActiveOrg=xyz``.
    Returns the bare sessionKey value.
    """
    raw = raw.strip()

    # Full cookie header containing sessionKey=...
    if "sessionKey=" in raw:
        # Extract value after 'sessionKey=' up to next ';' or end
        start = raw.index("sessionKey=") + len("sessionKey=")
        rest = raw[start:]
        if ";" in rest:
            return rest[: rest.index(";")].strip()
        return rest.strip()

    # Bare value (sk-ant-... or any other token)
    return raw


def _read_env_value(key: str) -> str | None:
    """Read a value from the .env file in the current directory.

    Simple line-by-line parsing -- no python-dotenv dependency.
    """
    env_path = Path(".env")
    if not env_path.is_file():
        return None
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            if line.startswith(f"{key}="):
                value = line.split("=", 1)[1].strip()
                if value:
                    return value
    except OSError:
        return None
    return None


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


def resolve_project_uuid(cli_project: str | None) -> str | None:
    """Resolve the project UUID from CLI flag, env var, or .env file.

    Priority order (per D-08, D-09):
    1. ``--project`` CLI flag
    2. ``CLAUDE_PROJECT_UUID`` environment variable
    3. ``.env`` file in current directory
    4. None (will trigger interactive selection later)
    """
    if cli_project:
        return cli_project

    env_val = os.environ.get("CLAUDE_PROJECT_UUID", "").strip()
    if env_val:
        return env_val

    dotenv_val = _read_env_value("CLAUDE_PROJECT_UUID")
    if dotenv_val:
        return dotenv_val

    return None


def resolve_org_id(cli_org: str | None) -> str | None:
    """Resolve the organization ID from CLI flag, env var, or .env file.

    Priority order (per D-06):
    1. ``--org`` CLI flag
    2. ``CLAUDE_ORG_ID`` environment variable
    3. ``.env`` file in current directory
    4. None (will trigger API discovery)
    """
    if cli_org:
        return cli_org

    env_val = os.environ.get("CLAUDE_ORG_ID", "").strip()
    if env_val:
        return env_val

    dotenv_val = _read_env_value("CLAUDE_ORG_ID")
    if dotenv_val:
        return dotenv_val

    return None
