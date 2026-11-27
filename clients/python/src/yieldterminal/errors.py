"""Exceptions raised by the yieldterminal client."""

from __future__ import annotations

from typing import Any, Dict, Optional

DEVELOPERS_URL = "https://yieldterminalpro.com/developers"


class YieldTerminalError(Exception):
    """Base class for every error this package raises.

    Attributes:
        status: HTTP status code, or None when the request never got a response.
        code: the machine-readable ``code`` from the API's JSON error body, when it sends one
            (for example ``free_ticker``, ``free_season``, ``no_row``).
        body: the decoded JSON error body, or None.
    """

    def __init__(
        self,
        message: str,
        status: Optional[int] = None,
        code: Optional[str] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.body = body

    def __str__(self) -> str:
        parts = []
        if self.status is not None:
            parts.append(f"HTTP {self.status}")
        if self.code:
            parts.append(self.code)
        prefix = " ".join(parts)
        return f"{prefix}: {self.message}" if prefix else self.message


class BadRequestError(YieldTerminalError):
    """400: a parameter is malformed (date, ticker, season, since, after) or the endpoint is unknown."""


class AuthenticationError(YieldTerminalError):
    """401: the API key is missing, malformed, unknown or replaced."""


class MissingAPIKeyError(AuthenticationError):
    """No key was passed and YIELDTERMINAL_API_KEY is not set. Raised before any request is made."""

    def __init__(self) -> None:
        super().__init__(
            "No API key. Pass api_key=... or set the YIELDTERMINAL_API_KEY environment variable. "
            f"Get a free key at {DEVELOPERS_URL}. "
            "sample() and status() work without a key."
        )


class PaymentRequiredError(YieldTerminalError):
    """402: the key's paid subscription is not active (for example past_due or canceled)."""


class PermissionDeniedError(YieldTerminalError):
    """403: the key's plan does not cover this request.

    Typical codes: ``free_date`` / older day on a free key, ``free_season``, ``free_ticker``
    (13f, capital, risk or events outside the sandbox tickers), or updates/archive on a non-Pro key.
    """


class NotFoundError(YieldTerminalError):
    """404: no company page, no row for that ticker or day, season not found, ticker not on the capex board."""


class RateLimitError(YieldTerminalError):
    """429: the daily call limit is used up. Limits reset at 00:00 UTC."""


class ServerError(YieldTerminalError):
    """5xx: the server failed. Retrying later is reasonable."""


class ConnectionFailedError(YieldTerminalError):
    """The request did not get an HTTP response (DNS, TLS, timeout, connection reset)."""


_BY_STATUS = {
    400: BadRequestError,
    401: AuthenticationError,
    402: PaymentRequiredError,
    403: PermissionDeniedError,
    404: NotFoundError,
    429: RateLimitError,
}


def error_for_status(status: int, body: Optional[Dict[str, Any]], fallback_text: str = "") -> YieldTerminalError:
    """Build the matching exception for an HTTP error response."""
    message = ""
    code = None
    if isinstance(body, dict):
        message = str(body.get("error") or "")
        code = body.get("code")
    if not message:
        message = fallback_text.strip()[:300] or "Request failed"
    if status == 429:
        message += " (daily limit; resets at 00:00 UTC)"
    if status == 401 and DEVELOPERS_URL not in message:
        message += f" (keys: {DEVELOPERS_URL})"
    cls = _BY_STATUS.get(status)
    if cls is None:
        cls = ServerError if status >= 500 else YieldTerminalError
    return cls(message, status=status, code=code, body=body if isinstance(body, dict) else None)
