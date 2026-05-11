"""Pydantic models for Fireflies.ai GraphQL API responses and custom exceptions."""

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# API response models
# ---------------------------------------------------------------------------


class Speaker(BaseModel):
    """Speaker entry from Fireflies transcript detail query."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    name: str = ""


class MeetingAttendee(BaseModel):
    """Meeting attendee from Fireflies transcript detail query."""

    model_config = ConfigDict(extra="ignore")

    displayName: str = ""
    email: str = ""


class Sentence(BaseModel):
    """A single sentence/utterance from the transcript."""

    model_config = ConfigDict(extra="ignore")

    speaker_name: str = ""
    text: str = ""
    raw_text: str = ""
    start_time: float = 0.0
    end_time: float = 0.0


class TranscriptSummary(BaseModel):
    """AI-generated summary fields from Fireflies transcript detail query."""

    model_config = ConfigDict(extra="ignore")

    keywords: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    overview: str = ""
    shorthand_bullet: str = ""
    outline: str = ""


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
