"""Fireflies API key resolution following the resolve_cookie pattern."""

from __future__ import annotations

import os

import click

from claude_dump.config import _read_env_value


def resolve_fireflies_api_key(cli_api_key: str | None) -> str:
    """Resolve the Fireflies API key from CLI flag, env var, .env file, or prompt.

    Priority order (mirrors resolve_cookie):
    1. ``--api-key`` CLI flag
    2. ``FIREFLIES_API_KEY`` environment variable
    3. ``.env`` file in current directory
    4. Interactive masked prompt via click
    """
    # 1. CLI flag
    if cli_api_key:
        return cli_api_key.strip()

    # 2. Environment variable
    env_val = os.environ.get("FIREFLIES_API_KEY", "").strip()
    if env_val:
        return env_val

    # 3. .env file
    dotenv_val = _read_env_value("FIREFLIES_API_KEY")
    if dotenv_val:
        return dotenv_val

    # 4. Interactive prompt (masked)
    prompted = click.prompt("Fireflies API key", hide_input=True)
    return prompted.strip()
