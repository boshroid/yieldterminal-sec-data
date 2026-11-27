"""Python client for the YieldTerminal Pro Earnings Data API.

Quarterly revenue, net income and diluted EPS read from each company's own results filing,
with the filing link on every figure. Docs: https://yieldterminalpro.com/developers

    import yieldterminal
    co = yieldterminal.sample("NVDA")          # no key needed
    client = yieldterminal.Client()            # reads YIELDTERMINAL_API_KEY
    day = client.results("2026-11-25")

Educational data, not investment advice. Attribute the data to YieldTerminal Pro
(yieldterminalpro.com) when you show it.
"""

from ._version import __version__
from .client import (
    API_KEY_ENV,
    DEFAULT_BASE_URL,
    SAMPLE_TICKERS,
    SANDBOX_TICKERS,
    Client,
    RateLimit,
    sample,
    status,
)
from .errors import (
    AuthenticationError,
    BadRequestError,
    ConnectionFailedError,
    MissingAPIKeyError,
    NotFoundError,
    PaymentRequiredError,
    PermissionDeniedError,
    RateLimitError,
    ServerError,
    YieldTerminalError,
)

__all__ = [
    "__version__",
    "API_KEY_ENV",
    "DEFAULT_BASE_URL",
    "SAMPLE_TICKERS",
    "SANDBOX_TICKERS",
    "Client",
    "RateLimit",
    "sample",
    "status",
    "YieldTerminalError",
    "BadRequestError",
    "AuthenticationError",
    "MissingAPIKeyError",
    "PaymentRequiredError",
    "PermissionDeniedError",
    "NotFoundError",
    "RateLimitError",
    "ServerError",
    "ConnectionFailedError",
]
