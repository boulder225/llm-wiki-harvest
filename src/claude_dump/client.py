"""HTTP client for Claude.ai internal API with retry/backoff logic."""

from __future__ import annotations

import sys
import time
from typing import TYPE_CHECKING

import httpx

from claude_dump.models import (
    APIError,
    Organization,
    Project,
    RateLimitError,
    SessionExpiredError,
)

if TYPE_CHECKING:
    from types import TracebackType


# Retryable HTTP status codes
_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 529, 500, 502, 503})

# Rate-limit specific codes (raise RateLimitError instead of APIError)
_RATE_LIMIT_CODES: frozenset[int] = frozenset({429, 529})

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

_MAX_RETRIES = 5
_INITIAL_BACKOFF_SECONDS = 2.0


def _extract_list(data: object) -> list[dict]:
    """Handle both bare array ``[...]`` and ``{"data": [...]}`` wrapper."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    if isinstance(data, dict):
        # Fallback: if the dict has no 'data' key, wrap in a list so
        # callers get *something* rather than an obscure error.
        return [data]
    return []


class ClaudeAPIClient:
    """Synchronous HTTP client for the Claude.ai internal REST API.

    Usage::

        with ClaudeAPIClient(cookie="sk-ant-...") as client:
            orgs = client.get_organizations()
            client.org_id = orgs[0].uuid
            projects = client.list_projects()
    """

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

    # -- org_id property (updates Cookie header when set) ------------------

    @property
    def org_id(self) -> str | None:
        return self._org_id

    @org_id.setter
    def org_id(self, value: str | None) -> None:
        self._org_id = value
        self._http.headers.update({"cookie": self._cookie_header_value()})

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

    # -- public API methods ------------------------------------------------

    def get_organizations(self) -> list[Organization]:
        """GET /organizations -- list all orgs for the authenticated user."""
        resp = self._request("GET", "/organizations")
        items = _extract_list(resp.json())
        return [Organization.model_validate(o) for o in items]

    def list_projects(self) -> list[Project]:
        """GET /organizations/{org}/projects -- list projects in the org."""
        self._require_org_id()
        resp = self._request("GET", f"/organizations/{self._org_id}/projects")
        items = _extract_list(resp.json())
        return [Project.model_validate(p) for p in items]

    # -- internal request with retry/backoff --------------------------------

    def _request(self, method: str, path: str) -> httpx.Response:
        """Execute an HTTP request with exponential-backoff retry.

        Retry strategy (per ARCHITECTURE.md / PITFALLS.md):
        - Initial delay: 2 s, doubling each retry, max 5 retries
        - Honour ``Retry-After`` header when present
        - 401 -> raise SessionExpiredError immediately (no retry)
        - 429/529 after exhausting retries -> raise RateLimitError
        - Other non-retryable 4xx/5xx -> raise APIError
        """
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

    # -- helpers -----------------------------------------------------------

    def _require_org_id(self) -> None:
        if not self._org_id:
            raise ValueError(
                "org_id is required. Call get_organizations() first and set "
                "client.org_id = orgs[0].uuid"
            )

    def _build_headers(self) -> dict[str, str]:
        return {
            "cookie": self._cookie_header_value(),
            "user-agent": _USER_AGENT,
            "accept": "application/json",
            "referer": "https://claude.ai/",
            "origin": "https://claude.ai",
        }

    def _cookie_header_value(self) -> str:
        value = f"sessionKey={self._cookie}"
        if self._org_id:
            value += f"; lastActiveOrg={self._org_id}"
        return value

    @staticmethod
    def _backoff_delay(attempt: int, resp: httpx.Response) -> float:
        """Compute delay: use Retry-After header when present, else exponential."""
        retry_after = ClaudeAPIClient._parse_retry_after(resp)
        if retry_after is not None:
            return retry_after
        return _INITIAL_BACKOFF_SECONDS * (2 ** attempt)

    @staticmethod
    def _parse_retry_after(resp: httpx.Response) -> float | None:
        raw = resp.headers.get("retry-after") or resp.headers.get("Retry-After")
        if raw is None:
            return None
        try:
            return float(raw)
        except (ValueError, TypeError):
            return None

    def _log_retry(self, attempt: int, status_code: int, delay: float) -> None:
        if not self._verbose:
            return
        if self._console is None:
            from rich.console import Console

            self._console = Console(stderr=True)
        self._console.print(
            f"[yellow]Retry {attempt}/{_MAX_RETRIES} after HTTP {status_code} "
            f"(waiting {delay:.1f}s)[/yellow]"
        )
