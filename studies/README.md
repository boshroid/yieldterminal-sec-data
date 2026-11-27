# Study: first reported vs later filed (AAPL, MSFT, NVDA sample)

`first_reported_vs_restated.py` downloads the free archive sample
(https://yieldterminalpro.com/data/yieldterminal-archive-sample.zip), checks each CSV against the SHA-256 in its
`manifest.json`, and asks three questions of it:

1. How many quarterly figures did a later SEC filing report at a different value (`restated = true`)?
2. Does each figure in the 8-K results release equal the figure the company first tagged in its 10-Q (or 10-K) XBRL
   data for the same quarter? And does the year-ago figure printed in the release equal what was first reported a
   year earlier?
3. How many days pass from quarter end to the 8-K, and from the 8-K to the 10-Q / 10-K?

It uses only the Python standard library (3.8+):

```
python studies/first_reported_vs_restated.py
python studies/first_reported_vs_restated.py --zip path/to/yieldterminal-archive-sample.zip
```

## Short answer

The sample is too small for the restatement question to be interesting, and I would rather say so than stretch it.
For these three companies, over the quarters in the sample (period ends 2021-10-31 to 2026-09-30):

- **No revenue, net income or diluted EPS figure was restated.** `company_quarterly_history` has 157 rows and 0 are
  flagged.
- **3 of 637 fundamentals rows are flagged, all NVDA diluted share counts, all marked as a share split** (each
  later value is ten times the first). Example: diluted shares for the quarter ending 2023-07-30 were first reported as 2,499,000,000
  (accession 0001045810-23-000175) and a later filing (0001045810-24-000264) carries 24,994,000,000. The archive
  marks these `restated_reason = share split`: the later value reflects the split, not a correction.
- **All 32 release figures that have a matching XBRL figure are equal to it.** 6 more have nothing to compare yet:
  fiscal Q4 diluted EPS (the history does not derive Q4 EPS) and NVDA's November 2026 release, whose 10-Q was not in
  this build.
- **Of the year-ago figures printed in the releases, 33 equal the first-reported value and 1 differs by rounding
  only**: NVDA's 2026-11-17 release prints year-ago revenue as $57.00 billion; the first-reported XBRL value was
  $57.006 billion. The archive's own `revenue_year_ago_matches_sec` flag for that row is `yes`.
- **One quarter has a 10-Q but no release row**: NVDA's quarter ending 2026-07-26 (10-Q filed 2026-08-26). The
  coverage windows on https://yieldterminalpro.com/developers list the summer 2026 window as Jul 13 to Aug 21, 2026,
  which is the likely reason; I did not check the 8-K's filing date on EDGAR for this note.
- **Timing**: the 8-K came a median 29 days after quarter end (range 24 to 37, 13 releases), and the 10-Q or 10-K
  followed 0 to 1 days later (MSFT and NVDA the same day, AAPL the next day).

So for these three companies the first-reported numbers held up. The full archive has the same columns for 3,788
companies (per https://yieldterminalpro.com/dataset); I have not run this script on it for this note, so nothing here
is a rate for the full archive.

## Full output

Run on 2026-11-26 against the sample built 2026-11-26T22:03:46Z:

```
Downloaded https://yieldterminalpro.com/data/yieldterminal-archive-sample.zip (20,607 bytes) to studies/data/yieldterminal-archive-sample.zip
Sample build: yieldterminal-archive-sample-2026-11-26 (built 2026-11-26T22:03:46Z), tickers AAPL, MSFT, NVDA
SHA-256 check against manifest.json: all files match

== 1. Rows flagged restated = true ==

company_quarterly_history: 157 rows
  AAPL: 55 rows, quarters ending 2021-12-25 to 2026-09-26, restated 0
  MSFT: 55 rows, quarters ending 2021-12-31 to 2026-09-30, restated 0
  NVDA: 47 rows, quarters ending 2021-10-31 to 2026-07-26, restated 0
  -> none

company_quarterly_fundamentals: 637 rows
  AAPL: 215 rows, quarters ending 2021-12-25 to 2026-09-26, restated 0
  MSFT: 215 rows, quarters ending 2021-12-31 to 2026-09-30, restated 0
  NVDA: 207 rows, quarters ending 2021-10-31 to 2026-07-26, restated 3
  -> NVDA diluted_shares quarter ending 2023-07-30: first reported 2,499,000,000 shares (accession 0001045810-23-000175), later 24,994,000,000 in 0001045810-24-000264; reason: share split
  -> NVDA diluted_shares quarter ending 2023-10-29: first reported 2,494,000,000 shares (accession 0001045810-23-000227), later 24,940,000,000 in 0001045810-24-000316; reason: share split
  -> NVDA diluted_shares quarter ending 2024-04-28: first reported 2,489,000,000 shares (accession 0001045810-24-000124), later 24,890,000,000 in 0001045810-25-000116; reason: share split

== 2. 8-K release figures vs the first-reported SEC XBRL figures ==
Current quarter = XBRL quarter ending 1-89 days before the 8-K. Year-ago quarter = 359-454 days before.

ticker 8-K filed  quarter end days  10-Q/10-K  days  checks
-----------------------------------------------------------
AAPL   2025-10-30 2025-09-27    33  2025-10-31 10-K    1  net_income: withheld; eps_diluted: no XBRL row
AAPL   2026-01-29 2025-12-27    33  2026-01-30 10-Q    1  all published figures equal
AAPL   2026-04-30 2026-03-28    33  2026-05-01 10-Q    1  all published figures equal
AAPL   2026-07-30 2026-06-27    33  2026-07-31 10-Q    1  all published figures equal
AAPL   2026-11-02 2026-09-26    37  2026-11-03 10-K    1  net_income: withheld; eps_diluted: no XBRL row
MSFT   2025-10-29 2025-09-30    29  2025-10-29 10-Q    0  all published figures equal
MSFT   2026-01-28 2025-12-31    28  2026-01-28 10-Q    0  all published figures equal
MSFT   2026-04-29 2026-03-31    29  2026-04-29 10-Q    0  all published figures equal
MSFT   2026-07-29 2026-06-30    29  2026-07-29 10-K    0  eps_diluted: no XBRL row
MSFT   2026-10-28 2026-09-30    28  2026-10-28 10-Q    0  all published figures equal
NVDA   2025-11-19 2025-10-26    24  2025-11-19 10-Q    0  all published figures equal
NVDA   2026-02-25 2026-01-25    31  2026-02-25 10-K    0  net_income: withheld; eps_diluted: no XBRL row
NVDA   2026-05-20 2026-04-26    24  2026-05-20 10-Q    0  all published figures equal
NVDA   2026-11-17 (no 10-Q yet)       -                     revenue: no XBRL row; net_income: withheld; eps_diluted: no XBRL row

Published release figures: 38 (of 42 slots in 14 releases)
  equal to the first-reported XBRL figure: 32
  different by rounding only (<0.05%):     0
  different by more than rounding:         0
  no XBRL figure to compare yet / ever:    6
Year-ago figures printed in those releases vs what was first reported a year earlier:
  equal: 33, rounding only: 1, different by more than rounding: 0, nothing to compare: 4
  -> NVDA 2026-11-17 revenue year-ago: release 57.000B vs first reported 57.006B for the quarter ending 2025-10-26 (rounding only; the archive's revenue_year_ago_matches_sec flag for this row is 'yes')

XBRL quarters first filed on or after 2025-10-29 (the first release in the sample) with no 8-K row:
  -> NVDA quarter ending 2026-07-26: 10-Q filed 2026-08-26, no results-release row

== 3. Timing ==
Quarter end to 8-K results release: median 29 days (range 24-37, n=13)
8-K results release to 10-Q / 10-K:  median 0 days (range 0-1, n=13)

Educational data, not investment advice. Source: yieldterminalpro.com, read from SEC EDGAR filings.
```

## Method notes

- "First reported" in the company tables is the value in the earliest SEC filing that carried the quarter (usually the
  10-Q, or the 10-K for a fiscal Q4). A later different value goes in `restated_value`; `value` is never overwritten.
  For revenue and net income a difference under 0.1% is not flagged; for EPS any difference is. See the README inside
  the zip.
- Quarter matching: the release's quarter is the XBRL quarter ending 1 to 89 days before the 8-K was filed; the
  year-ago quarter is the one ending 359 to 454 days before. For these three companies each window holds exactly one
  quarter.
- "Rounding only" means the two values are less than 0.05% apart, the size of rounding to the precision a release
  prints in its headline text.
- The 10-Q / 10-K filing date is looked up from `company_quarterly_fundamentals` by accession number.

Educational data, not investment advice.
