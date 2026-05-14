"""Pydantic models for Fireflies.ai GraphQL API responses and custom exceptions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# API response models
# ---------------------------------------------------------------------------


class Speaker(BaseModel):
    """Speaker entry from Fireflies transcript detail query."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    name: str = ""

    @field_validator("id", "name", mode="before")
    @classmethod
    def _coerce_str(cls, v: Any) -> str:
        return "" if v is None else str(v)


class MeetingAttendee(BaseModel):
    """Meeting attendee from Fireflies transcript detail query."""

    model_config = ConfigDict(extra="ignore")

    displayName: str = ""
    email: str = ""

    @field_validator("displayName", "email", mode="before")
    @classmethod
    def _coerce_str(cls, v: Any) -> str:
        return "" if v is None else str(v)


class Sentence(BaseModel):
    """A single sentence/utterance from the transcript."""

    model_config = ConfigDict(extra="ignore")

    speaker_name: str = ""
    text: str = ""
    raw_text: str = ""
    start_time: float = 0.0
    end_time: float = 0.0

    @field_validator("speaker_name", "text", "raw_text", mode="before")
    @classmethod
    def _coerce_str(cls, v: Any) -> str:
        return "" if v is None else str(v)

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> float:
        return 0.0 if v is None else float(v)


class TranscriptSummary(BaseModel):
    """AI-generated summary fields from Fireflies transcript detail query."""

    model_config = ConfigDict(extra="ignore")

    keywords: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    overview: str = ""
    shorthand_bullet: str = ""
    outline: str = ""

    @field_validator("keywords", "action_items", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            # API sometimes returns a string instead of a list
            return [v] if v.strip() else []
        if isinstance(v, list):
            return [str(item) for item in v if item is not None]
        return []

    @field_validator("overview", "shorthand_bullet", "outline", mode="before")
    @classmethod
    def _coerce_str(cls, v: Any) -> str:
        return "" if v is None else str(v)


def _coerce_date(v: Any) -> str:
    """Coerce date from int (epoch ms), float, None, or string to ISO string."""
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v / 1000, tz=UTC).isoformat()
    return str(v)


def _coerce_float(v: Any) -> float:
    """Coerce None to 0.0, pass through numbers."""
    if v is None:
        return 0.0
    return float(v)


def _coerce_str(v: Any) -> str:
    """Coerce None to empty string."""
    if v is None:
        return ""
    return str(v)


class FirefliesTranscript(BaseModel):
    """Full transcript detail from Fireflies GraphQL transcript(id) query."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str = ""
    date: str = ""
    duration: float = 0.0
    transcript_url: str = ""
    audio_url: str = ""
    video_url: str = ""
    speakers: list[Speaker] = Field(default_factory=list)
    meeting_attendees: list[MeetingAttendee] = Field(default_factory=list)
    sentences: list[Sentence] = Field(default_factory=list)
    summary: TranscriptSummary | None = None

    @field_validator("date", mode="before")
    @classmethod
    def _coerce_date(cls, v: Any) -> str:
        return _coerce_date(v)

    @field_validator("duration", mode="before")
    @classmethod
    def _coerce_duration(cls, v: Any) -> float:
        return _coerce_float(v)

    @field_validator("transcript_url", "audio_url", "video_url", mode="before")
    @classmethod
    def _coerce_urls(cls, v: Any) -> str:
        return _coerce_str(v)


class FirefliesTranscriptSummaryItem(BaseModel):
    """Transcript list item from Fireflies GraphQL transcripts query.

    Lighter shape than FirefliesTranscript -- no sentences, speakers, or summary.
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str = ""
    date: str = ""
    duration: float = 0.0
    transcript_url: str = ""
    participants: list[str] = Field(default_factory=list)

    @field_validator("date", mode="before")
    @classmethod
    def _coerce_date(cls, v: Any) -> str:
        return _coerce_date(v)

    @field_validator("duration", mode="before")
    @classmethod
    def _coerce_duration(cls, v: Any) -> float:
        return _coerce_float(v)

    @field_validator("transcript_url", mode="before")
    @classmethod
    def _coerce_url(cls, v: Any) -> str:
        return _coerce_str(v)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class FirefliesAPIError(Exception):
    """Base exception for non-retryable Fireflies API errors."""

    def __init__(self, status_code: int, response_body: str) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(
            f"Fireflies API error {status_code}: {response_body[:200]}"
        )


class FirefliesAuthError(Exception):
    """Raised on HTTP 401/403 -- Fireflies API key is invalid."""

    def __init__(self) -> None:
        self.message = (
            "Fireflies API key is invalid or expired. "
            "Get a new key from https://app.fireflies.ai/integrations/custom/fireflies"
        )
        super().__init__(self.message)
