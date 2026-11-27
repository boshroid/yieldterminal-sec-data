# YieldTerminal Earnings Results

Quarterly revenue, net income and diluted EPS read from each company's own results filing on SEC EDGAR (Form 8-K
Item 2.02, or Form 6-K for a foreign filer), with a link to that filing on every figure. This Actor calls the
[YieldTerminal Pro Earnings Data API](https://yieldterminalpro.com/developers) and writes the rows to a dataset you
can export as JSON, CSV or Excel, or send to Google Sheets, a webhook or your own code.

Educational data, not investment advice. No analyst estimates, no forecasts, no share prices.

## Free, with your own key

The Actor itself is free: there is no per-result or per-run charge from me. Apify bills the run's platform usage to
your Apify account, as it does for any Actor; a run is one small Node.js process making a few HTTP calls.

You bring your own YieldTerminal API key. You can get a free key (100 calls a day, personal non-commercial use) at
https://yieldterminalpro.com/developers. The live samples and the status check need no key, so you can see the
output before you get one: the default input (the NVDA company sample) runs as is.

## What you get

| Data set | One row per | `kind` | Key needed |
|---|---|---|---|
| Company | Results release, plus one row per quarter of history as first reported (up to 20) | `release`, `history` | Yes (free key works) |
| Results | Result filed on the chosen day | `result` | Yes |
| Outlook changes | Outlook figure next to the same figure in the previous release, with both quotes and both filing links | `outlook` | Yes |
| Capex board | Company and quarter on the AI spenders board | `capex` | Yes (free key gets the whole board) |
| Scorecard | Reported figure vs the company's own outlook for that quarter | `score` | Yes |
| Levels | Dated chart level and what the price did 1, 5 and 20 sessions later | `level` | Yes |
| 13F holders | Tracked manager holding the ticker, or no longer holding it | `holder`, `holder_gone` | Yes |
| Capital | Quarter of buybacks, dividends, stock-based pay and share-count change | `capital` | Yes |
| Risk | Risk-factor heading added, removed or reworded between the last two 10-K filings | `risk_added`, `risk_removed`, `risk_reworded` | Yes |
| Events | Form 8-K Item 5.02, 2.03 or 2.04 filing | `event` | Yes |
| Updates, Archive | Result published, corrected or withdrawn; every published result | `result` | Pro key |
| Samples | Live samples for NVDA, WMT, TJX, HD, TGT; first 3 results or outlook rows of the latest day | as above, plus `sample: true` | No |
| Status | Data freshness | `status` | No |

Every row has `kind` and, where the data has one, `ticker`. Every result row has `source_url`, the SEC.gov link to
the document the figures were read from, and the SEC accession number. The API's attribution note is saved once per
run in the run's key-value store as `ATTRIBUTION`.

Turn off **One row per result** to push each API response whole instead.

## How the figures are checked

A figure is published only when the release's financial table agrees with a second source: the release's own text,
or the figures the company filed with the SEC for this quarter and the year-ago quarter. Otherwise it is withheld.
**A withheld figure is left out of the row, never filled with zero.** When the company's later 10-Q arrives, the
figure is checked again: `*_matches_10q: true` means the 10-Q carries the same number; `false` means not checked yet
or no 10-Q exists, never that it differs, because a figure the 10-Q contradicts is withheld.

Published and withheld counts, recounted on every site build: https://yieldterminalpro.com/accuracy

## Input

- **Data set**: pick one from the list. The default, the NVDA company sample, runs with no key.
- **Tickers**: for company, 13F, levels, outlook and capex, one call per ticker; for capital, risk and events, up to
  25 tickers in one call.
- **Filing day**, **From/To**, **8-K item**, **Scorecard season**, **Since**: only used by the data sets named in
  each field's description.
- **Max pages**: updates, archive and capital/risk by Since follow the API's paging and stop after this many calls.
  The log says where to continue if more rows remain.
- **Your API key**: optional for the samples and status, needed for everything else. Stored encrypted by Apify, sent
  only in the `x-api-key` header, and never written to the log, the dataset or the key-value store.

Example input (one company, free key):

```json
{ "endpoint": "company", "tickers": ["AAPL"], "apiKey": "ytp_..." }
```

Example output row (company data set, results release, trimmed):

```json
{
  "kind": "release",
  "ticker": "NVDA",
  "company": "NVIDIA CORP",
  "cik": 1045810,
  "form": "8-K",
  "filed": "2026-11-17",
  "source_url": "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000088/q3fy27pr.htm",
  "accession": "0001045810-26-000088",
  "revenue_text": "$115.80 billion (+103% vs $57.00 billion a year earlier)",
  "revenue_value": 115800000000,
  "revenue_currency": "USD",
  "eps_text": "$2.70 (vs $1.30 a year earlier)",
  "eps_value": 2.7
}
```

(From the live NVDA sample on 2026-11-27. Net income was withheld for this release, so its fields are absent: the
row does not say zero.)

## When a run stops

- No key on a data set that needs one: the run fails at once with a link to the free key, and pushes nothing.
- 401: the key was not accepted. 402: the subscription behind the key is not active. Both stop the run.
- 403 (the key's plan does not cover the request; the log shows the API's code, for example `free_ticker`) and 404
  (no row for that ticker): with several tickers, that ticker is skipped and the rest still run.
- 429: the key's daily limit is reached. The run stops and says how many rows were pushed before it.

## Limits and terms

- Each API call counts against your key's daily limit (free 100, Developer 1,000, Pro 20,000; resets 00:00 UTC). The
  samples and status do not count.
- A free key covers results and outlook rows filed in the last 30 days, the full history for AAPL, MSFT, NVDA, AMZN,
  GOOG, META, TSLA, JPM, WMT and KO, the company endpoint with no date limit, the whole capex board and the latest
  scorecard season. 13F, capital, risk and events by ticker are limited to those ten tickers on a free key.
- Your key's plan terms apply to the data: free key personal non-commercial; Developer ($29 a month) personal and
  internal use; Pro ($99 a month) commercial display with attribution. Reselling the data, passing the raw dataset
  on, or training a model on it is not included in any plan. Details: https://yieldterminalpro.com/developers
- Attribute the data to YieldTerminal Pro (yieldterminalpro.com) when you show it.

## Other ways in

- Free CSV snapshot: https://yieldterminalpro.com/dataset
- Python: `pip install yieldterminal`. Node: `npm install yieldterminal` (this Actor uses the same Node client).
- MCP connector for Claude and other AI assistants: https://yieldterminalpro.com/connector

If you have a question, or think a figure is wrong, email me at yieldterminalpro@gmail.com.
