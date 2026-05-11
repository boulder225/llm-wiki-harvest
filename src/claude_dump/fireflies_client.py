"""HTTP client for Fireflies.ai GraphQL API with retry/backoff logic."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import httpx

from claude_dump.fireflies_models import (
    FirefliesAPIError,
    FirefliesAuthError,
    FirefliesTranscript,
    FirefliesTranscriptSummaryItem,
)

if TYPE_CHECKING:
    from types import TracebackType


# Retryable HTTP status codes
_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503})

_MAX_RETRIES = 5
_INITIAL_BACKOFF_SECONDS = 2.0

# ---------------------------------------------------------------------------
# GraphQL query strings
# ---------------------------------------------------------------------------

_LIST_TRANSCRIPTS_QUERY = """\
query Transcripts($limit: Int, $skip: Int) {
  transcripts(limit: $limit, skip: $skip) {
    id
    title
    date
    duration
    transcript_url
    participants
  }
}"""

_GET_TRANSCRIPT_QUERY = """\
query Transcript($transcriptId: String!) {
  transcript(id: $transcriptId) {
    title
    date
    duration
    transcript_url
    audio_url
    video_url
    speakers {
      id
      name
    }
    meeting_attendees {
      displayName
      email
    }
    sentences {
      speaker_name
      text
      raw_text
      start_time
      end_time
    }
    summary {
      keywords
      action_items
      overview
      shorthand_bullet
      outline
    }
  }
}"""


class FirefliesClient:
    """Synchronous GraphQL client for the Fireflies.ai API.

    Usage::

        with FirefliesClient(api_key="...") as client:
            transcripts = client.list_all_transcripts()
            detail = client.get_transcript(transcripts[0].id)
    """

    def __init__(self, api_key: str, verbose: bool = False) -> None:
        self._api_key = api_key
        self._verbose = verbose
        self._console = None  # lazy-init if verbose

        self._http = httpx.Client(
            base_url="https://api.fireflies.ai",
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            follow_redirects=True,
        )

    # -- context manager ---------------------------------------------------

    def __enter__(self) -> FirefliesClient:
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

    def list_transcripts(
        self, limit: int = 50, skip: int = 0
    ) -> list[FirefliesTranscriptSummaryItem]:
        """Fetch a page of transcript summaries.

        Args:
            limit: Maximum items per page (Fireflies caps at 50).
            skip: Number of items to skip for pagination.
        """
        data = self._graphql(
            _LIST_TRANSCRIPTS_QUERY,
            variables={"limit": limit, "skip": skip},
        )
        items = data.get("transcripts") or []
        return [FirefliesTranscriptSummaryItem.model_validate(t) for t in items]

    def list_all_transcripts(self) -> list[FirefliesTranscriptSummaryItem]:
        """Fetch all transcripts, paginating automatically."""
        all_items: list[FirefliesTranscriptSummaryItem] = []
        page_size = 50
        offset = 0

        while True:
            page = self.list_transcripts(limit=page_size, skip=offset)
            all_items.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        return all_items

    def get_transcript(self, transcript_id: str) -> FirefliesTranscript:
        """Fetch full transcript detail including sentences, speakers, summary."""
        data = self._graphql(
            _GET_TRANSCRIPT_QUERY,
            variables={"transcriptId": transcript_id},
        )
        raw = data.get("transcript") or {}
        result = FirefliesTranscript.model_validate({"id": transcript_id, **raw})
        return result

    # -- internal GraphQL request with retry/backoff -----------------------

    def _graphql(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query with exponential-backoff retry.

        Retry strategy (mirrors ClaudeAPIClient._request):
        - Initial delay: 2 s, doubling each retry, max 5 retries
        - Honour ``Retry-After`` header when present
        - 401/403 -> raise FirefliesAuthError immediately (no retry)
        - 429/500/502/503 -> retryable with backoff
        - GraphQL-level errors (200 with errors array, null data) -> raise FirefliesAPIError
        """
        payload = {"query": query, "variables": variables or {}}
        last_response: httpx.Response | None = None

        for attempt in range(_MAX_RETRIES + 1):
            resp = self._http.post("/graphql", json=payload)

            # 401/403 -- auth failure, never retry
            if resp.status_code in (401, 403):
                raise FirefliesAuthError()

            if resp.is_success:
                body = resp.json()
                # GraphQL-level errors
                if body.get("errors") and body.get("data") is None:
                    raise FirefliesAPIError(
                        status_code=200,
                        response_body=str(body["errors"]),
                    )
                return body.get("data") or {}

            # Non-retryable HTTP error
            if resp.status_code not in _RETRYABLE_STATUS_CODES:
                raise FirefliesAPIError(
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
        raise FirefliesAPIError(
            status_code=last_response.status_code,
            response_body=last_response.text[:500],
        )

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _backoff_delay(attempt: int, resp: httpx.Response) -> float:
        """Compute delay: use Retry-After header when present, else exponential."""
        retry_after = FirefliesClient._parse_retry_after(resp)
        if retry_after is not None:
            return retry_after
        return _INITIAL_BACKOFF_SECONDS * (2**attempt)

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
