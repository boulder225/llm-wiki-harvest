"""Pydantic models for Claude.ai API responses and custom exceptions."""

from pydantic import BaseModel, ConfigDict


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
