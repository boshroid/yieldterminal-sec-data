#!/usr/bin/env python3
"""First reported vs later filed, on the free YieldTerminal archive sample (AAPL, MSFT, NVDA).

What it does, using only the Python standard library:

1. Downloads the free sample zip from yieldterminalpro.com (or reads a local copy with --zip).
2. Checks every CSV against the SHA-256 in the zip's manifest.json.
3. Counts rows flagged restated = true in the two company tables and prints each one.
4. Compares each 8-K results-release figure with the first-reported SEC XBRL figure (10-Q, or
   10-K for a derived fiscal Q4) for the same quarter, and the release's printed year-ago figure
   with what the company first reported for that year-ago quarter.
5. Prints the days from quarter end to the 8-K, and from the 8-K to the 10-Q / 10-K.

Usage:
    python studies/first_reported_vs_restated.py            # download the sample, then report
    python studies/first_reported_vs_restated.py --zip PATH # use a zip you already downloaded

Educational data, not investment advice.
"""

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import statistics
import sys
import urllib.request
import zipfile

SAMPLE_URL = "https://yieldterminalpro.com/data/yieldterminal-archive-sample.zip"
USER_AGENT = "yieldterminal-sec-data-study/1.0"
FIELDS = ("revenue", "net_income", "eps_diluted")


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as fh:
        fh.write(data)
    return data


def load_zip(data):
    """Return {file name: bytes} for the files inside the zip's single top folder."""
    out = {}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            out[os.path.basename(info.filename)] = zf.read(info)
    return out


def read_csv(files, name):
    text = files[name].decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def day(s):
    return dt.date.fromisoformat(s)


def num(s):
    return float(s) if s not in (None, "") else None


def same(field, a, b):
    if a is None or b is None:
        return None
    if field == "eps_diluted":
        return round(a, 2) == round(b, 2)
    return a == b


def rounding_only(field, a, b):
    """True when two money figures differ by less than 0.05%: the size of rounding to the
    precision a release prints in its headline text (for example $57.00 billion)."""
    if field == "eps_diluted" or not a or not b:
        return False
    return abs(a - b) / abs(b) < 0.0005


def fmt(field, v):
    if v is None:
        return "-"
    if field == "eps_diluted":
        return f"{v:.2f}"
    return f"{v / 1e9:,.3f}B"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--zip", help="path to a local copy of the sample zip (skips the download)")
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--cache", default=os.path.join(here, "data", "yieldterminal-archive-sample.zip"),
                    help="where to save the downloaded zip (default: studies/data/)")
    args = ap.parse_args()

    if args.zip:
        with open(args.zip, "rb") as fh:
            data = fh.read()
        print(f"Using local zip: {args.zip}")
    else:
        data = download(SAMPLE_URL, args.cache)
        print(f"Downloaded {SAMPLE_URL} ({len(data):,} bytes) to {args.cache}")

    files = load_zip(data)
    manifest = json.loads(files["manifest.json"])
    print(f"Sample build: {manifest['name']} (built {manifest['built_utc']}), tickers {', '.join(manifest['sample_tickers'])}")

    bad = []
    for name, meta in manifest["files"].items():
        got = hashlib.sha256(files[name]).hexdigest()
        if got != meta["sha256"]:
            bad.append(name)
    print("SHA-256 check against manifest.json:", "all files match" if not bad else f"MISMATCH in {bad}")
    if bad:
        sys.exit(1)

    results = read_csv(files, "earnings_results.csv")
    history = read_csv(files, "company_quarterly_history.csv")
    fundamentals = read_csv(files, "company_quarterly_fundamentals.csv")

    # ------------------------------------------------------------------ 1. restatement flags
    print("\n== 1. Rows flagged restated = true ==")
    for label, rows in (("company_quarterly_history", history), ("company_quarterly_fundamentals", fundamentals)):
        print(f"\n{label}: {len(rows)} rows")
        for t in manifest["sample_tickers"]:
            mine = [r for r in rows if r["ticker"] == t]
            ends = sorted(r["period_end"] for r in mine)
            n = sum(r["restated"] == "true" for r in mine)
            span = f"{ends[0]} to {ends[-1]}" if ends else "none"
            print(f"  {t}: {len(mine)} rows, quarters ending {span}, restated {n}")
        flagged = [r for r in rows if r["restated"] == "true"]
        for r in flagged:
            reason = r.get("restated_reason") or "(no reason given)"
            later = r.get("restated_accession") or "a later filing"
            print(f"  -> {r['ticker']} {r['field']} quarter ending {r['period_end']}: first reported "
                  f"{float(r['value']):,.0f} {r['unit']} (accession {r['accession']}), "
                  f"later {float(r['restated_value']):,.0f} in {later}; reason: {reason}")
        if not flagged:
            print("  -> none")

    # ------------------------------------------------------------------ 2. release vs XBRL
    hist = {}  # (ticker, period_end) -> {field: row}
    for r in history:
        hist.setdefault((r["ticker"], r["period_end"]), {})[r["field"]] = r
    ends_by_ticker = {}
    for (t, pe) in hist:
        ends_by_ticker.setdefault(t, []).append(pe)
    filed_by_accession = {r["accession"]: (r["filed"], r["form"]) for r in fundamentals}

    def quarter_for(ticker, filed, lo, hi):
        """The history quarter end that is lo..hi days before the filing date (unique for these windows)."""
        hits = [pe for pe in ends_by_ticker.get(ticker, []) if lo < (day(filed) - day(pe)).days < hi]
        return max(hits) if hits else None

    print("\n== 2. 8-K release figures vs the first-reported SEC XBRL figures ==")
    print("Current quarter = XBRL quarter ending 1-89 days before the 8-K. Year-ago quarter = 359-454 days before.\n")
    tally = {"cur_same": 0, "cur_round": 0, "cur_diff": 0, "cur_no_xbrl": 0,
             "ya_same": 0, "ya_round": 0, "ya_diff": 0, "ya_no_xbrl": 0}
    matched_quarters = set()
    diffs = []
    lags_q_to_8k, lags_8k_to_10q = [], []
    header = f"{'ticker':6} {'8-K filed':10} {'quarter end':11} {'days':>4}  {'10-Q/10-K':10} {'days':>4}  checks"
    print(header)
    print("-" * len(header))
    for r in sorted(results, key=lambda x: (x["ticker"], x["filed"])):
        t, filed = r["ticker"], r["filed"]
        q = quarter_for(t, filed, 0, 90)
        y = quarter_for(t, filed, 358, 455)
        notes = []
        tenq_txt, tenq_days, q_days = "-", "", ""
        if q:
            matched_quarters.add((t, q))
            q_days = str((day(filed) - day(q)).days)
            lags_q_to_8k.append(int(q_days))
            accs = {row["accession"] for row in hist[(t, q)].values()}
            dates = [filed_by_accession[a] for a in accs if a in filed_by_accession]
            if dates:
                f10, form = min(dates)
                tenq_txt = f10
                tenq_days = str((day(f10) - day(filed)).days)
                lags_8k_to_10q.append(int(tenq_days))
                tenq_txt = f"{f10} {form}"
        for f in FIELDS:
            rel = num(r[f])
            if rel is None:
                notes.append(f"{f}: withheld")
                continue
            cur = num(hist[(t, q)][f]["value"]) if q and f in hist[(t, q)] else None
            s = same(f, rel, cur)
            if s is None:
                tally["cur_no_xbrl"] += 1
                notes.append(f"{f}: no XBRL row")
            elif s:
                tally["cur_same"] += 1
            elif rounding_only(f, rel, cur):
                tally["cur_round"] += 1
                diffs.append(f"{t} {filed} {f}: release {fmt(f, rel)} vs XBRL {fmt(f, cur)} (rounding only)")
                notes.append(f"{f}: rounding only")
            else:
                tally["cur_diff"] += 1
                diffs.append(f"{t} {filed} {f}: release {fmt(f, rel)} vs XBRL {fmt(f, cur)}")
                notes.append(f"{f}: DIFFERS")
            rel_ya = num(r[f + "_year_ago"])
            ya = num(hist[(t, y)][f]["value"]) if y and (t, y) in hist and f in hist[(t, y)] else None
            s2 = same(f, rel_ya, ya)
            if s2 is None:
                tally["ya_no_xbrl"] += 1
            elif s2:
                tally["ya_same"] += 1
            elif rounding_only(f, rel_ya, ya):
                tally["ya_round"] += 1
                diffs.append(f"{t} {filed} {f} year-ago: release {fmt(f, rel_ya)} vs first reported "
                             f"{fmt(f, ya)} for the quarter ending {y} (rounding only; the archive's "
                             f"{f}_year_ago_matches_sec flag for this row is '{r.get(f + '_year_ago_matches_sec')}')")
            else:
                tally["ya_diff"] += 1
                diffs.append(f"{t} {filed} {f} year-ago: release prints {fmt(f, rel_ya)}, first reported {fmt(f, ya)} (quarter ending {y})")
        q_txt = q or "(no 10-Q yet)"
        print(f"{t:6} {filed:10} {q_txt:11} {q_days:>4}  {tenq_txt:15} {tenq_days:>4}  {'; '.join(notes) or 'all published figures equal'}")

    n_rel = sum(1 for r in results for f in FIELDS if num(r[f]) is not None)
    print(f"\nPublished release figures: {n_rel} (of {len(results) * 3} slots in {len(results)} releases)")
    print(f"  equal to the first-reported XBRL figure: {tally['cur_same']}")
    print(f"  different by rounding only (<0.05%):     {tally['cur_round']}")
    print(f"  different by more than rounding:         {tally['cur_diff']}")
    print(f"  no XBRL figure to compare yet / ever:    {tally['cur_no_xbrl']}")
    print("Year-ago figures printed in those releases vs what was first reported a year earlier:")
    print(f"  equal: {tally['ya_same']}, rounding only: {tally['ya_round']}, "
          f"different by more than rounding: {tally['ya_diff']}, nothing to compare: {tally['ya_no_xbrl']}")
    for d in diffs:
        print("  -> " + d)

    # XBRL quarters inside the results coverage that have no release row in the archive
    first_filed = min(r["filed"] for r in results)
    print(f"\nXBRL quarters first filed on or after {first_filed} (the first release in the sample) with no 8-K row:")
    missing = 0
    for (t, pe), rows in sorted(hist.items()):
        accs = {row["accession"] for row in rows.values()}
        dates = sorted(filed_by_accession[a] for a in accs if a in filed_by_accession)
        if not dates or dates[0][0] < first_filed or (t, pe) in matched_quarters:
            continue
        missing += 1
        print(f"  -> {t} quarter ending {pe}: {dates[0][1]} filed {dates[0][0]}, no results-release row")
    if not missing:
        print("  -> none")

    # ------------------------------------------------------------------ 3. timing
    print("\n== 3. Timing ==")
    if lags_q_to_8k:
        print(f"Quarter end to 8-K results release: median {statistics.median(lags_q_to_8k):g} days "
              f"(range {min(lags_q_to_8k)}-{max(lags_q_to_8k)}, n={len(lags_q_to_8k)})")
    if lags_8k_to_10q:
        print(f"8-K results release to 10-Q / 10-K:  median {statistics.median(lags_8k_to_10q):g} days "
              f"(range {min(lags_8k_to_10q)}-{max(lags_8k_to_10q)}, n={len(lags_8k_to_10q)})")
    print("\nEducational data, not investment advice. Source: yieldterminalpro.com, read from SEC EDGAR filings.")


if __name__ == "__main__":
    main()
