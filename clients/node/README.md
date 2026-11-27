# yieldterminal

JavaScript client for the [YieldTerminal Pro Earnings Data API](https://yieldterminalpro.com/developers).
ESM, zero dependencies (uses the global `fetch`), TypeScript types included. Node 18 or later, Deno, Bun or a
browser (the API sends open CORS headers).

The API returns quarterly revenue, net income and diluted EPS read from each company's own results filing
(Form 8-K Item 2.02, or Form 6-K for a foreign filer), with a link to that filing on SEC.gov on every figure.
A figure is published only when the release's financial table agrees with a second source; otherwise it is
withheld, and a withheld figure is left out of the response, never sent as zero. There are no analyst estimates,
no forecasts, and no language model in the numbers.

Educational data, not investment advice.

## Quick start, no key

```js
import { sample } from "yieldterminal";
const co = await sample("NVDA"); // live sample: NVDA, WMT, TJX, HD or TGT
const latest = co.results[0];
console.log(co.company, latest.filed, latest.revenue_text ?? "withheld");
console.log(latest.source_url); // the filing on SEC.gov
```

`sample({ endpoint: "results" })` returns the first three results of the latest filing day, and `status()` returns
how fresh the data is. Neither needs a key or counts against one.

## Install

```bash
npm install yieldterminal
```

## With a key

Get a free key at https://yieldterminalpro.com/developers, then pass it or set `YIELDTERMINAL_API_KEY`:

```js
import { YieldTerminal } from "yieldterminal";

const yt = new YieldTerminal(); // or new YieldTerminal({ apiKey: "ytp_..." })

const day = await yt.results("2026-11-25"); // every published result filed that day
for (const r of day.results) console.log(r.ticker, r.revenue_text ?? "withheld", r.source_url);

const aapl = await yt.company("AAPL"); // releases + up to 20 quarters of history as first reported
console.log(aapl.latest_filed, aapl.quarterly_history.at(-1));

console.log(yt.lastRateLimit); // { limit: 100, remaining: 98 }
```

The key is sent in the `x-api-key` header, never in the address. In a browser, anyone who can open the page can
read a key you ship in it, so call the keyed endpoints from a server.

### Methods

| Method | Endpoint | Notes |
|---|---|---|
| `sample(ticker = "NVDA")`, `sample({ endpoint: "results" \| "outlook" })` | data-sample | No key |
| `status()` | data-status | No key |
| `results(date?)` | results | Every published result filed that day; default the latest filing day |
| `company(ticker)` | company | Results releases plus up to 20 quarters of history as first reported |
| `outlook({ date?, ticker? })` | outlook | Outlook changes, each next to the same figure in the previous release |
| `levels({ ticker?, date? })` | levels | Dated chart levels and tracked outcomes |
| `capex({ ticker? })` | capex | The AI spenders capex board |
| `scorecard({ season? })` | scorecard | Reported figure vs the company's own outlook, e.g. `"2026-fall"` |
| `holders13f(ticker)` | 13f | Tracked managers' latest 13F share counts vs the quarter before |
| `capital({ ticker?, tickers?, since?, after? })` | capital | Buybacks, dividends, dilution per quarter |
| `risk({ ticker?, tickers?, since?, after? })` | risk | 10-K risk-factor headings added, removed, reworded |
| `events({ ticker?, tickers?, date?, from?, to?, item? })` | events | 8-K Items 5.02, 2.03, 2.04 |
| `updates(since)`, `iterUpdates(since)` | updates | Pro plan |
| `archive(after?)`, `iterArchive(after?)` | archive | Pro plan |

Full field list: the [OpenAPI 3.1 spec](https://yieldterminalpro.com/openapi.json) and the
[plain-text reference](https://yieldterminalpro.com/llms-full.txt).

### Reading figures

- Use `??`: a withheld figure's `*_value` is absent and its `*_text` is null.
- `*_matches_10q` is `true` when the company's later Form 10-Q carries the same figure. `false` means not checked
  yet or no 10-Q exists (a fiscal fourth quarter is in the 10-K), never that the 10-Q disagrees.
- In `company()`, `results` holds the figures read from each results release and `quarterly_history` holds the
  company's XBRL figures from its 10-Q and 10-K filings as first reported. They are never merged. In the history,
  `d: 1` marks a fourth quarter derived as the full year less the first three quarters, and `r` holds a later
  restated value.

### Errors

All errors extend `YieldTerminalError` and carry `status`, `code` (the API's machine-readable code, when sent) and
`body`: `MissingAPIKeyError` (no key, thrown before any request), `BadRequestError` (400),
`AuthenticationError` (401), `PaymentRequiredError` (402), `PermissionDeniedError` (403, for example `free_ticker`
or `free_season`), `NotFoundError` (404), `RateLimitError` (429, resets at 00:00 UTC), `ServerError` (5xx) and
`ConnectionFailedError` (no response).

```js
import { YieldTerminal, PermissionDeniedError } from "yieldterminal";
try {
  await new YieldTerminal().capital({ ticker: "ORCL" });
} catch (e) {
  if (e instanceof PermissionDeniedError) console.log(e.code, e.message);
  else throw e;
}
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
- Python client: `pip install yieldterminal`

## Licence

The client code is MIT licensed (see `LICENSE`). The data the API returns is covered by the plan terms above, not
by the MIT licence. Attribute the data to YieldTerminal Pro (yieldterminalpro.com) when you show it.

Questions or a figure you think is wrong: yieldterminalpro@gmail.com
