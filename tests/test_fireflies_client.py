"""Tests for FirefliesClient GraphQL methods using pytest-httpx."""

import pytest
from pytest_httpx import HTTPXMock

from claude_dump.fireflies_client import FirefliesClient
from claude_dump.fireflies_models import (
    FirefliesAPIError,
    FirefliesAuthError,
    FirefliesTranscript,
    FirefliesTranscriptSummaryItem,
)


@pytest.fixture
def client() -> FirefliesClient:
    """Create a Fireflies client with a test API key."""
    c = FirefliesClient(api_key="test-key")
    yield c
    c.close()


# ---------------------------------------------------------------------------
# list_transcripts
# ---------------------------------------------------------------------------


class TestListTranscripts:
    def test_single_page(self, client: FirefliesClient, httpx_mock: HTTPXMock):
        """Returns list of FirefliesTranscriptSummaryItem from a single page."""
        httpx_mock.add_response(
            url="https://api.fireflies.ai/graphql",
            json={
                "data": {
                    "transcripts": [
                        {
                            "id": "tx-1",
                            "title": "Standup",
                            "date": "2026-05-10T09:00:00Z",
                            "duration": 900.0,
                            "transcript_url": "https://app.fireflies.ai/view/tx-1",
                            "participants": ["Alice", "Bob"],
                        },
                        {
                            "id": "tx-2",
                            "title": "Retro",
                            "date": "2026-05-10T10:00:00Z",
                            "duration": 1800.0,
                            "transcript_url": "https://app.fireflies.ai/view/tx-2",
                            "participants": ["Alice"],
                        },
                    ]
                }
            },
        )

        result = client.list_transcripts(limit=50, skip=0)

        assert len(result) == 2
        assert all(isinstance(t, FirefliesTranscriptSummaryItem) for t in result)
        assert result[0].id == "tx-1"
        assert result[0].title == "Standup"
        assert result[1].participants == ["Alice"]

    def test_empty_response(self, client: FirefliesClient, httpx_mock: HTTPXMock):
        """Empty transcript list returns []."""
        httpx_mock.add_response(
            url="https://api.fireflies.ai/graphql",
            json={"data": {"transcripts": []}},
        )

        result = client.list_transcripts()

        assert result == []


# ---------------------------------------------------------------------------
# list_all_transcripts
# ---------------------------------------------------------------------------


class TestListAllTranscripts:
    def test_pagination_two_pages(self, client: FirefliesClient, httpx_mock: HTTPXMock):
        """Paginates across two pages: first=50, second=10 -> 60 total."""
        page1 = [
            {"id": f"tx-{i}", "title": f"Meeting {i}", "date": "", "duration": 0, "transcript_url": "", "participants": []}
            for i in range(50)
        ]
        page2 = [
            {"id": f"tx-{50 + i}", "title": f"Meeting {50 + i}", "date": "", "duration": 0, "transcript_url": "", "participants": []}
            for i in range(10)
        ]

        # First call returns 50 items
        httpx_mock.add_response(
            url="https://api.fireflies.ai/graphql",
            json={"data": {"transcripts": page1}},
        )
        # Second call returns 10 items (< 50, stops)
        httpx_mock.add_response(
            url="https://api.fireflies.ai/graphql",
            json={"data": {"transcripts": page2}},
        )

        result = client.list_all_transcripts()

        assert len(result) == 60
        assert result[0].id == "tx-0"
        assert result[59].id == "tx-59"


# ---------------------------------------------------------------------------
# get_transcript
# ---------------------------------------------------------------------------


class TestGetTranscript:
    def test_full_response(self, client: FirefliesClient, httpx_mock: HTTPXMock):
        """Parses a full transcript detail response with all nested fields."""
        httpx_mock.add_response(
            url="https://api.fireflies.ai/graphql",
            json={
                "data": {
                    "transcript": {
                        "title": "Design Review",
                        "date": "2026-05-10T14:00:00Z",
                        "duration": 3600.0,
                        "transcript_url": "https://app.fireflies.ai/view/tx-100",
                        "audio_url": "https://storage.fireflies.ai/tx-100.mp3",
                        "video_url": "",
                        "speakers": [
                            {"id": "s1", "name": "Alice"},
                            {"id": "s2", "name": "Bob"},
                        ],
                        "meeting_attendees": [
                            {"displayName": "Alice Smith", "email": "alice@example.com"},
                        ],
                        "sentences": [
                            {
                                "speaker_name": "Alice",
                                "text": "Let's review the design.",
                                "raw_text": "Let's review the design.",
                                "start_time": 1.0,
                                "end_time": 3.5,
                            },
                        ],
                        "summary": {
                            "keywords": ["design", "review"],
                            "action_items": ["Update mockups"],
                            "overview": "Design review for Q3 feature.",
                            "shorthand_bullet": "- Review mockups",
                            "outline": "1. Review\n2. Feedback",
                        },
                    }
                }
            },
        )

        result = client.get_transcript("tx-100")

        assert isinstance(result, FirefliesTranscript)
        assert result.id == "tx-100"
        assert result.title == "Design Review"
        assert result.duration == 3600.0
        assert len(result.speakers) == 2
        assert len(result.sentences) == 1
        assert result.sentences[0].text == "Let's review the design."
        assert result.summary is not None
        assert result.summary.keywords == ["design", "review"]


# ---------------------------------------------------------------------------
# Auth errors
# ---------------------------------------------------------------------------


class TestAuth:
    def test_401_raises_auth_error(self, client: FirefliesClient, httpx_mock: HTTPXMock):
        """HTTP 401 raises FirefliesAuthError immediately."""
        httpx_mock.add_response(
            url="https://api.fireflies.ai/graphql",
            status_code=401,
        )

        with pytest.raises(FirefliesAuthError):
            client.list_transcripts()

    def test_403_raises_auth_error(self, client: FirefliesClient, httpx_mock: HTTPXMock):
        """HTTP 403 raises FirefliesAuthError immediately."""
        httpx_mock.add_response(
            url="https://api.fireflies.ai/graphql",
            status_code=403,
        )

        with pytest.raises(FirefliesAuthError):
            client.list_transcripts()


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------


class TestRetry:
    def test_429_is_retried(self, client: FirefliesClient, httpx_mock: HTTPXMock, monkeypatch):
        """429 is retried and succeeds on second attempt."""
        # Patch time.sleep to avoid real delay
        monkeypatch.setattr("claude_dump.fireflies_client.time.sleep", lambda _: None)

        # First response: 429
        httpx_mock.add_response(
            url="https://api.fireflies.ai/graphql",
            status_code=429,
        )
        # Second response: success
        httpx_mock.add_response(
            url="https://api.fireflies.ai/graphql",
            json={"data": {"transcripts": [{"id": "tx-1", "title": "OK", "date": "", "duration": 0, "transcript_url": "", "participants": []}]}},
        )

        result = client.list_transcripts()

        assert len(result) == 1
        assert result[0].id == "tx-1"


# ---------------------------------------------------------------------------
# GraphQL-level errors
# ---------------------------------------------------------------------------


class TestGraphQLErrors:
    def test_graphql_error_with_null_data(self, client: FirefliesClient, httpx_mock: HTTPXMock):
        """GraphQL error response (200 with errors and null data) raises FirefliesAPIError."""
        httpx_mock.add_response(
            url="https://api.fireflies.ai/graphql",
            json={
                "errors": [{"message": "Invalid query syntax"}],
                "data": None,
            },
        )

        with pytest.raises(FirefliesAPIError) as exc_info:
            client.list_transcripts()

        assert exc_info.value.status_code == 200
        assert "Invalid query syntax" in exc_info.value.response_body
