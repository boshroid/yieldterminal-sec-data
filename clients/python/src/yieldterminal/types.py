"""Response shapes, as TypedDicts.

These follow the OpenAPI 3.1 spec at https://yieldterminalpro.com/openapi.json. They list the
fields most code needs; responses can carry more, and the spec is the full reference. Every
dict is ``total=False`` because a withheld figure is left out of the response rather than sent
as zero: always use ``.get()`` for figure fields.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict, Union


class Status(TypedDict, total=False):
    latest_filing_day: str
    latest_update_utc: str
    hours_since_update: float
    ok: bool
    error: str
    code: str


class Result(TypedDict, total=False):
    """One results filing (endpoint=results, updates, archive)."""

    accession: str
    form: str
    ticker: str
    company: str
    cik: int
    filed: str
    accepted: str
    quarter_ended: str
    revenue_text: Optional[str]
    revenue_value: float
    revenue_year_ago: float
    revenue_currency: str
    revenue_label: Optional[str]
    revenue_matches_10q: Optional[bool]
    revenue_year_ago_matches_sec: Optional[bool]
    net_income_text: Optional[str]
    net_income_value: float
    net_income_year_ago: float
    net_income_currency: str
    net_income_label: Optional[str]
    net_income_matches_10q: Optional[bool]
    net_income_year_ago_matches_sec: Optional[bool]
    eps_text: Optional[str]
    eps_value: float
    eps_year_ago: float
    eps_label: Optional[str]
    eps_matches_10q: Optional[bool]
    source_url: str
    published_at: str
    pushed_at: str
    status: str


class ResultsResponse(TypedDict, total=False):
    endpoint: str
    date: str
    count: int
    free_sandbox: bool
    results: List[Result]
    note: str


class HistoryValue(TypedDict, total=False):
    """One figure in quarterly_history: v value, u unit, d 1 when derived (FY minus Q1-Q3), r restated value."""

    v: float
    u: str
    d: int
    r: float
    a: str


class HistoryQuarter(TypedDict, total=False):
    period_end: str
    fiscal_year: int
    fiscal_period: str
    revenue: HistoryValue
    net_income: HistoryValue
    eps: HistoryValue


class CompanyResult(TypedDict, total=False):
    accession: str
    form: str
    filed: str
    quarter_ended: str
    source_url: str
    revenue_text: Optional[str]
    revenue_value: float
    revenue_label: Optional[str]
    revenue_proof: List[str]
    revenue_matches_10q: Optional[bool]
    revenue_year_ago_matches_sec: Optional[bool]
    net_income_text: Optional[str]
    net_income_value: float
    net_income_label: Optional[str]
    net_income_proof: List[str]
    net_income_matches_10q: Optional[bool]
    net_income_year_ago_matches_sec: Optional[bool]
    eps_text: Optional[str]
    eps_value: float
    eps_label: Optional[str]
    eps_proof: List[str]
    eps_matches_10q: Optional[bool]


class CompanyResponse(TypedDict, total=False):
    endpoint: str
    ticker: str
    company: str
    cik: int
    as_of: str
    latest_filed: str
    results: List[CompanyResult]
    quarterly_history: List[HistoryQuarter]
    history_note: str
    history_ext: List[Dict[str, Any]]
    history_ext_note: str
    note: str
    sample: bool
    sample_note: str


class OutlookRow(TypedDict, total=False):
    key: str
    ticker: str
    company: str
    cik: int
    filed: str
    prev_filed: str
    accession: str
    prev_accession: str
    source_url: str
    prev_source_url: str
    metric: str
    period: str
    basis: str
    unit: str
    ccy: str
    old_low: float
    old_high: float
    new_low: float
    new_high: float
    old_text: str
    new_text: str
    sentence: str
    prev_sentence: str
    note: str


class OutlookResponse(TypedDict, total=False):
    endpoint: str
    date: str
    ticker: str
    count: int
    free_sandbox: bool
    outlook: List[OutlookRow]
    note: str
    sample: bool
    sample_note: str


class PagedResponse(TypedDict, total=False):
    """updates (Pro) and archive (Pro)."""

    endpoint: str
    since: str
    after: str
    count: int
    more: bool
    next_since: str
    next_after: str
    results: List[Result]
    note: str


# The remaining endpoints (levels, capex, scorecard, 13f, capital, risk, events) return
# documented JSON objects; see the spec. They are typed as plain dicts here.
JSONDict = Dict[str, Any]
SampleResponse = Union[CompanyResponse, ResultsResponse, OutlookResponse]
