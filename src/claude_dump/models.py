"""Pydantic models for Claude.ai API responses and custom exceptions."""

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# API response models
# ---------------------------------------------------------------------------

class Organization(BaseModel):
    """Parsed from GET /api/organizations response items."""

    model_config = ConfigDict(extra="ignore")

    uuid: str
    name: str
    email_address: str = ""


class Project(BaseModel):
    """Parsed from GET /api/organizations/{org}/projects response items."""

    model_config = ConfigDict(extra="ignore")

    uuid: str
    name: str
    description: str = ""
    created_at: str = ""
    is_private: bool = True


class ContentBlock(BaseModel):
    """A single content block within a chat message.

    Discriminated by ``type``: text, thinking, tool_use, tool_result.
    All optional fields default to safe empty values so unknown block
    types are silently accepted.
    """

    model_config = ConfigDict(extra="ignore")

    type: str
    text: str = ""
    thinking: str = ""
    name: str = ""
    input: dict = Field(default_factory=dict)
    content: list[dict] = Field(default_factory=list)


class Attachment(BaseModel):
    """File attachment metadata with extracted text content."""

    model_config = ConfigDict(extra="ignore")

    file_name: str = ""
    file_type: str = ""
    extracted_content: str = ""


class FileRef(BaseModel):
    """Reference to an uploaded file (from ``files_v2`` array)."""

    model_config = ConfigDict(extra="ignore")

    file_uuid: str = ""
    file_name: str = ""
    file_kind: str = ""


class ChatMessage(BaseModel):
    """A single message in a conversation (human or assistant turn)."""

    model_config = ConfigDict(extra="ignore")

    uuid: str = ""
    sender: str
    created_at: str = ""
    content: list[ContentBlock] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)
    files_v2: list[FileRef] = Field(default_factory=list)


class Conversation(BaseModel):
    """Conversation metadata and (optionally) full chat messages.

    When fetched from the list endpoint, ``chat_messages`` is empty.
    When fetched individually, ``chat_messages`` contains the full thread.
    """

    model_config = ConfigDict(extra="ignore")

    uuid: str
    name: str = ""
    model: str = ""
    created_at: str = ""
    updated_at: str = ""
    summary: str = ""
    chat_messages: list[ChatMessage] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class APIError(Exception):
    """Base exception for non-retryable API errors."""

    def __init__(self, status_code: int, response_body: str) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(
            f"API error {status_code}: {response_body[:200]}"
        )


class SessionExpiredError(Exception):
    """Raised on HTTP 401 -- session cookie is no longer valid."""

    def __init__(self) -> None:
        self.message = (
            "Session cookie may be expired. "
            "Re-extract from browser DevTools > Application > Cookies > sessionKey"
        )
        super().__init__(self.message)


class RateLimitError(Exception):
    """Raised on HTTP 429/529 after retry attempts are exhausted."""

    def __init__(self, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        msg = "Rate limited by Claude.ai API"
        if retry_after is not None:
            msg += f" (retry after {retry_after}s)"
        super().__init__(msg)
