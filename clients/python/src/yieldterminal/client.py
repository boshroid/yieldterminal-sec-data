"""HTTP client for the YieldTerminal Pro Earnings Data API.

Standard library only. Every call is one HTTP GET; the API key goes in the ``x-api-key``
header, never in the address.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import socket
from typing import Any, Dict, Iterable, Iterator, Mapping, Optional, Union, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ._version import __version__
from .errors import ConnectionFailedError, MissingAPIKeyError, YieldTerminalError, error_for_status
from .types import (
    CompanyResponse,
    JSONDict,
    OutlookResponse,
    PagedResponse,
    ResultsResponse,
    SampleResponse,
    Status,
)

DEFAULT_BASE_URL = "https://yieldterminalpro.com/api/apps/6a44fce3122251d9ebac82ed/functions"
API_KEY_ENV = "YIELDTERMINAL_API_KEY"
SAMPLE_TICKERS = ("NVDA", "WMT", "TJX", "HD", "TGT")
SANDBOX_TICKERS = ("AAPL", "MSFT", "NVDA", "AMZN", "GOOG", "META", "TSLA", "JPM", "WMT", "KO")

DateLike = Union[str, _dt.date, _dt.datetime]


def _date(value: Optional[DateLike]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        return value.date().isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    return str(value)


def _iso_time(value: Union[str, _dt.datetime]) -> str:
    if isinstance(value, _dt.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=_dt.timezone.utc)
        return value.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(value)


def _ticker(value: Optional[str]) -> Optional[str]:
    return value.strip().upper() if value else None


def _tickers(value: Union[None, str, Iterable[str]]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        items = [t for t in value.split(",")]
    else:
        items = list(value)
    cleaned = [t.strip().upper() for t in items if t and t.strip()]
    if not 1 <= len(cleaned) <= 25:
        raise ValueError("tickers takes 1 to 25 symbols")
    return ",".join(cleaned)


class RateLimit:
    """The X-RateLimit-* headers of the last successful data-api call."""

    __slots__ = ("limit", "remaining")

    def __init__(self, limit: Optional[int], remaining: Optional[int]) -> None:
        self.limit = limit
        self.remaining = remaining

    def __repr__(self) -> str:
        return f"RateLimit(limit={self.limit}, remaining={self.remaining})"


class Client:
    """Client for the Earnings Data API.

    Args:
        api_key: your key (``ytp_`` followed by 48 hex characters). If omitted, the
            ``YIELDTERMINAL_API_KEY`` environment variable is used. ``sample()`` and
            ``status()`` need no key.
        timeout: seconds to wait for each response.
        base_url: override the API base (for testing).

    Every method returns the decoded JSON body. A figure the API withheld is absent (or its
    ``*_text`` is None); it never comes back as zero, so read figures with ``.get()``.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        timeout: float = 30.0,
        base_url: str = DEFAULT_BASE_URL,
        user_agent: Optional[str] = None,
    ) -> None:
        key = api_key if api_key is not None else os.environ.get(API_KEY_ENV)
        self.api_key = key.strip() if key else None
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent or f"yieldterminal-python/{__version__}"
        self.last_rate_limit: Optional[RateLimit] = None

    def __repr__(self) -> str:
        return f"Client(api_key={'set' if self.api_key else 'not set'}, base_url={self.base_url!r})"

    # ------------------------------------------------------------------ transport

    def _get(self, function: str, params: Mapping[str, Any], *, key: bool) -> Any:
        query = {k: v for k, v in params.items() if v is not None}
        url = f"{self.base_url}/{function}"
        if query:
            url += "?" + urlencode(query)
        headers = {"Accept": "application/json", "User-Agent": self.user_agent}
        if key:
            if not self.api_key:
                raise MissingAPIKeyError()
            headers["x-api-key"] = self.api_key
        request = Request(url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                if key:
                    self.last_rate_limit = RateLimit(
                        _int_or_none(response.headers.get("X-RateLimit-Limit")),
                        _int_or_none(response.headers.get("X-RateLimit-Remaining")),
                    )
        except HTTPError as exc:
            text = ""
            body = None
            try:
                text = exc.read().decode("utf-8", "replace")
                body = json.loads(text)
            except Exception:
                pass
            raise error_for_status(exc.code, body, text) from None
        except (URLError, socket.timeout, TimeoutError, ConnectionError) as exc:
            reason = getattr(exc, "reason", exc)
            raise ConnectionFailedError(f"Could not reach {self.base_url}: {reason}") from None
        try:
            return json.loads(raw.decode("utf-8"))
        except ValueError:
            raise YieldTerminalError("The API returned a body that is not JSON") from None

    def _data(self, endpoint: str, **params: Any) -> Any:
        return self._get("data-api", dict(endpoint=endpoint, **params), key=True)

    # ------------------------------------------------------------------ no key

    def status(self) -> Status:
        """Data freshness: latest filing day and when the newest result was pushed. No key, no quota."""
        return cast(Status, self._get("data-status", {}, key=False))

    def sample(self, ticker: str = "NVDA", *, endpoint: Optional[str] = None) -> SampleResponse:
        """A live sample in the same format as the paid API, with no key.

        ``sample("TJX")`` returns the company response for NVDA, WMT, TJX, HD or TGT.
        ``sample(endpoint="results")`` returns the first 3 results of the latest filing day;
        ``sample(endpoint="outlook")`` the first 3 outlook rows of the latest outlook day.
        """
        if endpoint is not None:
            if endpoint not in ("results", "outlook"):
                raise ValueError("sample endpoint must be 'results' or 'outlook' (or omit it for a company)")
            return cast(SampleResponse, self._get("data-sample", {"endpoint": endpoint}, key=False))
        return cast(SampleResponse, self._get("data-sample", {"ticker": _ticker(ticker)}, key=False))

    # ------------------------------------------------------------------ key required

    def results(self, date: Optional[DateLike] = None) -> ResultsResponse:
        """Every published result filed on ``date`` (YYYY-MM-DD). Default: the latest filing day."""
        return cast(ResultsResponse, self._data("results", date=_date(date)))

    def company(self, ticker: str) -> CompanyResponse:
        """One company: its results releases plus up to 20 quarters of SEC history as first reported."""
        if not ticker:
            raise ValueError("company() needs a ticker")
        return cast(CompanyResponse, self._data("company", ticker=_ticker(ticker)))

    def outlook(self, date: Optional[DateLike] = None, ticker: Optional[str] = None) -> OutlookResponse:
        """Outlook (guidance) changes by filing day or ticker. ticker takes precedence over date."""
        return cast(OutlookResponse, self._data("outlook", date=_date(date), ticker=_ticker(ticker)))

    def levels(self, ticker: Optional[str] = None, date: Optional[DateLike] = None) -> JSONDict:
        """Published dated chart levels and tracked outcomes, by ticker or board day."""
        return cast(JSONDict, self._data("levels", ticker=_ticker(ticker), date=_date(date)))

    def capex(self, ticker: Optional[str] = None) -> JSONDict:
        """The AI spenders capex board, or one company on it."""
        return cast(JSONDict, self._data("capex", ticker=_ticker(ticker)))

    def scorecard(self, season: Optional[str] = None) -> JSONDict:
        """Outlook scorecard rows for a season such as ``"2026-fall"``. Default: the latest season."""
        return cast(JSONDict, self._data("scorecard", season=season))

    def holders_13f(self, ticker: str) -> JSONDict:
        """Which tracked managers reported the ticker in their latest 13F filings vs the quarter before."""
        return cast(JSONDict, self._data("13f", ticker=_ticker(ticker)))

    def capital(
        self,
        ticker: Optional[str] = None,
        *,
        tickers: Union[None, str, Iterable[str]] = None,
        since: Optional[DateLike] = None,
        after: Optional[str] = None,
    ) -> JSONDict:
        """Buybacks, dividends, stock-based pay and share-count change per quarter, as first reported."""
        return cast(
            JSONDict,
            self._data("capital", ticker=_ticker(ticker), tickers=_tickers(tickers), since=_date(since), after=after),
        )

    def risk(
        self,
        ticker: Optional[str] = None,
        *,
        tickers: Union[None, str, Iterable[str]] = None,
        since: Optional[DateLike] = None,
        after: Optional[str] = None,
    ) -> JSONDict:
        """Risk-factor headings added, removed and reworded between the latest two Form 10-K filings."""
        return cast(
            JSONDict,
            self._data("risk", ticker=_ticker(ticker), tickers=_tickers(tickers), since=_date(since), after=after),
        )

    def events(
        self,
        ticker: Optional[str] = None,
        *,
        tickers: Union[None, str, Iterable[str]] = None,
        date: Optional[DateLike] = None,
        start: Optional[DateLike] = None,
        end: Optional[DateLike] = None,
        item: Optional[str] = None,
    ) -> JSONDict:
        """Form 8-K Items 5.02, 2.03 and 2.04 by ticker, tickers, filing day, or a start/end range.

        ``start``/``end`` map to the API's ``from``/``to`` (at most 23 business days).
        ``item`` is one of ``"5.02"``, ``"2.03"``, ``"2.04"``.
        """
        params: Dict[str, Any] = {
            "ticker": _ticker(ticker),
            "tickers": _tickers(tickers),
            "date": _date(date),
            "from": _date(start),
            "to": _date(end),
            "item": item,
        }
        return cast(JSONDict, self._data("events", **params))

    def updates(self, since: Union[str, _dt.datetime]) -> PagedResponse:
        """Pro: results first published, corrected or withdrawn after ``since`` (an ISO UTC time)."""
        return cast(PagedResponse, self._data("updates", since=_iso_time(since)))

    def archive(self, after: Optional[str] = None) -> PagedResponse:
        """Pro: every published result, 1,000 per call, in accession-number order."""
        return cast(PagedResponse, self._data("archive", after=after))

    def iter_updates(self, since: Union[str, _dt.datetime]) -> Iterator[Dict[str, Any]]:
        """Pro: yield every row from ``updates``, following ``next_since`` while ``more`` is true."""
        cursor = _iso_time(since)
        while True:
            page = self.updates(cursor)
            for row in page.get("results", []):
                yield cast(Dict[str, Any], row)
            if not page.get("more") or not page.get("next_since"):
                return
            cursor = page["next_since"]

    def iter_archive(self, after: Optional[str] = None) -> Iterator[Dict[str, Any]]:
        """Pro: yield every published result, following ``next_after`` while ``more`` is true."""
        cursor = after
        while True:
            page = self.archive(cursor)
            for row in page.get("results", []):
                yield cast(Dict[str, Any], row)
            if not page.get("more") or not page.get("next_after"):
                return
            cursor = page["next_after"]


def _int_or_none(value: Optional[str]) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


# Module-level helpers for the no-key endpoints.


def sample(ticker: str = "NVDA", *, endpoint: Optional[str] = None, timeout: float = 30.0) -> SampleResponse:
    """Live sample, no key. See :meth:`Client.sample`."""
    return Client(api_key="", timeout=timeout).sample(ticker, endpoint=endpoint)


def status(timeout: float = 30.0) -> Status:
    """Data freshness, no key. See :meth:`Client.status`."""
    return Client(api_key="", timeout=timeout).status()
