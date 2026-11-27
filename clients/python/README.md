# yieldterminal

Python client for the [YieldTerminal Pro Earnings Data API](https://yieldterminalpro.com/developers).

The API returns quarterly revenue, net income and diluted EPS read from each company's own results filing
(Form 8-K Item 2.02, or Form 6-K for a foreign filer), with a link to that filing on SEC.gov on every figure.
A figure is published only when the release's financial table agrees with a second source; otherwise it is
withheld, and a withheld figure is left out of the response, never sent as zero. There are no analyst estimates,
no forecasts, and no language model in the numbers.

Standard library only. Python 3.8 or later. Educational data, not investment advice.

## Quick start, no key

```python
import yieldterminal
co = yieldterminal.sample("NVDA")  # live sample: NVDA, WMT, TJX, HD or TGT
latest = co["results"][0]
print(co["company"], latest["filed"], latest.get("revenue_text") or "withheld")
print(latest["source_url"])  # the filing on SEC.gov
```

`yieldterminal.sample(endpoint="results")` returns the first three results of the latest filing day, and
`yieldterminal.status()` returns how fresh the data is. Neither needs a key or counts against one.

## Install

```bash
pip install yieldterminal
pip install "yieldterminal[pandas]"   # adds the DataFrame helpers
```

## With a key

Get a free key at https://yieldterminalpro.com/developers, then pass it or set it in the environment:

```bash
export YIELDTERMINAL_API_KEY=ytp_...
```

```python
from yieldterminal import Client

client = Client()                      # or Client(api_key="ytp_...")

day = client.results("2026-11-25")     # every published result filed that day
for r in day["results"]:
    print(r["ticker"], r.get("revenue_text") or "withheld", r["source_url"])

aapl = client.company("AAPL")          # releases + up to 20 quarters of history as first reported
print(aapl["latest_filed"], aapl["quarterly_history"][-1])

print(client.last_rate_limit)          # RateLimit(limit=100, remaining=98)
```

The key is sent in the `x-api-key` header. The client never puts it in the address.

### Methods

| Method | Endpoint | Notes |
|---|---|---|
| `sample(ticker="NVDA", endpoint=None)` | data-sample | No key. Company sample for NVDA, WMT, TJX, HD, TGT; or `endpoint="results"` / `"outlook"` |
| `status()` | data-status | No key. Latest filing day and last update time |
| `results(date=None)` | results | Every published result filed that day; default the latest filing day |
| `company(ticker)` | company | Results releases plus up to 20 quarters of history as first reported |
| `outlook(date=None, ticker=None)` | outlook | Outlook changes, each next to the same figure in the previous release |
| `levels(ticker=None, date=None)` | levels | Dated chart levels and tracked outcomes |
| `capex(ticker=None)` | capex | The AI spenders capex board |
| `scorecard(season=None)` | scorecard | Reported figure vs the company's own outlook, e.g. `"2026-fall"` |
| `holders_13f(ticker)` | 13f | Tracked managers' latest 13F share counts vs the quarter before |
| `capital(ticker=None, tickers=None, since=None, after=None)` | capital | Buybacks, dividends, dilution per quarter |
| `risk(ticker=None, tickers=None, since=None, after=None)` | risk | 10-K risk-factor headings added, removed, reworded |
| `events(ticker=None, tickers=None, date=None, start=None, end=None, item=None)` | events | 8-K Items 5.02, 2.03, 2.04; `start`/`end` map to `from`/`to` |
| `updates(since)`, `iter_updates(since)` | updates | Pro plan. Results published, corrected or withdrawn since a UTC time |
| `archive(after=None)`, `iter_archive(after=None)` | archive | Pro plan. Every published result, 1,000 per call |

Each method returns the decoded JSON as a dict. The full field list is in the
[OpenAPI 3.1 spec](https://yieldterminalpro.com/openapi.json) and the
[plain-text reference](https://yieldterminalpro.com/llms-full.txt).

### Reading figures

- Use `.get()`: a withheld figure's `*_value` is absent and its `*_text` is null.
- `*_matches_10q` is `True` when the company's later Form 10-Q carries the same figure. `False` means not checked
  yet or no 10-Q exists (a fiscal fourth quarter is in the 10-K), never that the 10-Q disagrees: a figure the 10-Q
  contradicts is withheld.
- In `company()`, `results` holds the figures read from each results release and `quarterly_history` holds the
  company's XBRL figures from its 10-Q and 10-K filings as first reported. They are separate readings and are never
  merged. In the history, `d: 1` marks a fourth quarter derived as the full year less the first three quarters, and
  `r` holds a later restated value.

### Errors

Every error is a subclass of `yieldterminal.YieldTerminalError`, with `.status`, `.code` (the API's machine-readable
code, when it sends one) and `.body`.

| Status | Exception | Typical cause |
|---|---|---|
| none | `MissingAPIKeyError` | No key passed and `YIELDTERMINAL_API_KEY` not set (raised before any request) |
| 400 | `BadRequestError` | Malformed date, ticker, season, or a sample ticker outside the five |
| 401 | `AuthenticationError` | Missing, malformed, unknown or replaced key |
| 402 | `PaymentRequiredError` | Paid subscription not active |
| 403 | `PermissionDeniedError` | The plan does not cover the request (`free_date`, `free_season`, `free_ticker`, Pro-only endpoint) |
| 404 | `NotFoundError` | No company page, no row, season not found |
| 429 | `RateLimitError` | Daily limit used up; resets at 00:00 UTC |
| 5xx | `ServerError` | Server error |
| none | `ConnectionFailedError` | No HTTP response (network, TLS, timeout) |

```python
from yieldterminal import Client, PermissionDeniedError

try:
    Client().capital("ORCL")
except PermissionDeniedError as e:
    print(e.code, e)   # free_ticker: a free key covers the sandbox tickers for this endpoint
```

### pandas

```python
from yieldterminal import Client
from yieldterminal.frames import results_frame, history_frame

client = Client()
df = results_frame(client.results("2026-11-25"))     # withheld figures are NaN
hist = history_frame(client.company("MSFT"))         # value, unit, derived, restated per figure
```

## Plans

As listed on https://yieldterminalpro.com/developers on 2026-11-27:

- **Free key**: 100 calls a day, personal non-commercial use with attribution. Results and outlook rows filed in the
  last 30 days, with full history for AAPL, MSFT, NVDA, AMZN, GOOG, META, TSLA, JPM, WMT and KO; the company
  endpoint with no date limit; the full capex board; the latest scorecard season.
- **Developer**: US$29 a month (or US$290 a year), 1,000 calls a day, personal and internal use.
- **Pro**: US$99 a month (or US$990 a year), 20,000 calls a day, the updates and archive endpoints, and commercial
  display inside your own product with attribution.

Reselling the data, passing the raw dataset on, or training a model on it is not included in any plan.
Write to yieldterminalpro@gmail.com about a separate licence.

## Other ways in

- Free CSV snapshot of every published result: https://yieldterminalpro.com/dataset
- Accuracy and coverage counts: https://yieldterminalpro.com/accuracy
- MCP connector for Claude and other AI assistants: https://yieldterminalpro.com/connector
- Node.js client: `npm install yieldterminal`

## Licence

The client code is MIT licensed (see `LICENSE`). The data the API returns is covered by the plan terms above, not
by the MIT licence. Attribute the data to YieldTerminal Pro (yieldterminalpro.com) when you show it.

Questions or a figure you think is wrong: yieldterminalpro@gmail.com
