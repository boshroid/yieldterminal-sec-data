#!/usr/bin/env python3
"""YieldTerminal Pro earnings data: quick start in Python (standard library only).

Part 1 calls the public sample endpoint, which needs no key.
Part 2 runs only when the YT_API_KEY environment variable is set; the key is sent in the
x-api-key header, never in the address.

    python examples/python/quickstart.py
    YT_API_KEY=ytp_... python examples/python/quickstart.py

Educational data, not investment advice. Attribute to YieldTerminal Pro (yieldterminalpro.com).
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://yieldterminalpro.com/api/apps/6a44fce3122251d9ebac82ed/functions"
UA = "yieldterminal-sec-data-examples/1.0"


def get(path, params=None, key=None):
    url = f"{BASE}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if key:
        headers["x-api-key"] = key
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", "replace")
        raise SystemExit(f"HTTP {err.code} from {path}: {body}")


def show(value):
    """A withheld figure has no number and no text: print it as withheld, never as zero."""
    return value if value is not None else "withheld"


def main():
    # ---- Part 1: no key -------------------------------------------------------------
    status = get("data-status")
    print(f"Data status: latest filing day {status.get('latest_filing_day')}, "
          f"last update {status.get('latest_update_utc')} ({status.get('hours_since_update')} hours ago)")

    co = get("data-sample", {"ticker": "NVDA"})  # sample tickers: NVDA, WMT, TJX, HD, TGT
    print(f"\n{co['ticker']} {co['company']}: {len(co['results'])} results releases, latest filed {co['latest_filed']}")
    for r in co["results"][:3]:
        print(f"  {r['filed']} {r['form']}  revenue {show(r.get('revenue_text'))}")
        print(f"             net income {show(r.get('net_income_text'))}  EPS {show(r.get('eps_text'))}")
        print(f"             10-Q confirms revenue: {r.get('revenue_matches_10q')}  source {r['source_url']}")

    day = get("data-sample", {"endpoint": "results"})
    print(f"\nLatest filing day {day['date']}: showing {day['count']} results")
    for r in day["results"]:
        print(f"  {r['ticker']:6} revenue {show(r.get('revenue_text'))}  EPS {show(r.get('eps_text'))}")

    out = get("data-sample", {"endpoint": "outlook"})
    print(f"\nLatest outlook day {out['date']}: showing {out['count']} rows")
    for o in out["outlook"]:
        print(f"  {o['ticker']:6} {o['metric']} {o['period']}: {o['old_text']} -> {o['new_text']}")

    # ---- Part 2: with a key ---------------------------------------------------------
    key = os.environ.get("YT_API_KEY")
    if not key:
        print("\nYT_API_KEY is not set, so the keyed calls were skipped.")
        print("A free key (100 calls a day, personal use): https://yieldterminalpro.com/developers")
        return

    res = get("data-api", {"endpoint": "results"}, key=key)  # latest filing day; add "date": "YYYY-MM-DD"
    print(f"\nKeyed: {len(res['results'])} results filed {res.get('date')}")
    for r in res["results"][:5]:
        print(f"  {r['ticker']:6} revenue {show(r.get('revenue_text'))}  {r['source_url']}")

    aapl = get("data-api", {"endpoint": "company", "ticker": "AAPL"}, key=key)
    hist = aapl.get("quarterly_history") or []
    print(f"\nKeyed: AAPL latest release {aapl.get('latest_filed')}, {len(hist)} quarters of SEC history (as of {aapl.get('as_of')})")
    if hist:
        print("  newest history row:", hist[-1])


if __name__ == "__main__":
    main()
