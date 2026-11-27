"""Optional pandas helpers. Install with ``pip install "yieldterminal[pandas]"``.

Withheld figures become NaN, never 0.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

_FIGURES = ("revenue", "net_income", "eps")


def _pd() -> Any:
    try:
        import pandas as pd  # type: ignore
    except ImportError:  # pragma: no cover - depends on the environment
        raise ImportError(
            'pandas is not installed. Install it with: pip install "yieldterminal[pandas]"'
        ) from None
    return pd


def results_frame(response: Mapping[str, Any]) -> Any:
    """DataFrame of the ``results`` rows of a results, updates, archive, company or sample response.

    Columns follow the API field names. ``filed`` becomes a date. Withheld figures are NaN.
    """
    pd = _pd()
    rows = list(response.get("results") or [])
    frame = pd.DataFrame(rows)
    if "filed" in frame.columns:
        frame["filed"] = pd.to_datetime(frame["filed"], errors="coerce").dt.date
    return frame


def history_frame(response: Mapping[str, Any]) -> Any:
    """DataFrame of a company response's ``quarterly_history``, one row per quarter, oldest first.

    For each of revenue, net_income and eps there are four columns: the first-reported value,
    ``<figure>_unit``, ``<figure>_derived`` (True when the fourth quarter was derived as the full
    year less the first three quarters) and ``<figure>_restated`` (the later restated value,
    or NaN when there was none). The first-reported value is what was known on its filing date;
    the restated value was not.
    """
    pd = _pd()
    out: List[Dict[str, Any]] = []
    for quarter in response.get("quarterly_history") or []:
        row: Dict[str, Any] = {
            "period_end": quarter.get("period_end"),
            "fiscal_year": quarter.get("fiscal_year"),
            "fiscal_period": quarter.get("fiscal_period"),
        }
        for name in _FIGURES:
            cell = quarter.get(name) or {}
            row[name] = cell.get("v")
            row[f"{name}_unit"] = cell.get("u")
            row[f"{name}_derived"] = bool(cell.get("d"))
            row[f"{name}_restated"] = cell.get("r")
        out.append(row)
    frame = pd.DataFrame(out)
    if not frame.empty:
        frame["period_end"] = pd.to_datetime(frame["period_end"], errors="coerce").dt.date
    return frame


def outlook_frame(response: Mapping[str, Any]) -> Any:
    """DataFrame of the ``outlook`` rows of an outlook response."""
    pd = _pd()
    return pd.DataFrame(list(response.get("outlook") or []))
