# yieldterminal-sec-data

Quarterly revenue, net income and diluted EPS read from companies' SEC results filings, with the filing link and
cross-check flags on every figure. This repository holds runnable examples for the
[YieldTerminal Pro](https://yieldterminalpro.com) Earnings Data API, the MCP connector setup, a copy of the OpenAPI
spec and a small reproducible study on the free archive sample.

> `openapi.json` here is a copy taken on 2026-11-26 (spec version 2026-11-26). The live file at
> https://yieldterminalpro.com/openapi.json is canonical; if they differ, trust the live one.

Educational data, not investment advice.

## What the data is

- **Source.** For each company results filing on SEC EDGAR (Form 8-K Item 2.02 for a U.S. filer, Form 6-K for a
  foreign filer), code reads the quarter's revenue, net income and diluted EPS from the release itself. No analyst
  estimates are involved, so nothing is labelled a beat or a miss.
- **Withholding rule.** A figure is published only when the number in the release's financial table agrees with a
  second source: the release's own text, or the figures the company filed with the SEC for this quarter and the
  year-ago quarter. For a U.S. filer, revenue and net income must also match SEC data (this quarter's 10-Q or the
  year-ago quarter). Anything that fails is withheld. A withheld figure is blank (or absent in JSON), never zero.
- **Links.** Every result carries `source_url`, the release on SEC.gov, and the accession number.
- **10-Q re-check.** When the 10-Q arrives, the figure is compared again. `..._matches_10q = true` means it matched;
  `false` means not checked yet or no 10-Q exists (fiscal Q4 goes in the 10-K), never that the 10-Q disagrees: a
  figure the 10-Q contradicts is withheld or taken down.
- **History.** Company responses also carry up to 20 quarters of revenue, net income and diluted EPS from the
  company's own XBRL data (10-Q and 10-K), as first reported, with later restatements marked separately. Most
  companies' history starts in 2021.
- **Outlook changes.** Outlook (guidance) figures in a release next to the same figure in the company's previous
  release, with both sentences and both SEC links, for releases filed from 2026-10-06 on.
- **Coverage.** Results filings in five earnings-season windows: Oct 1 to Nov 21, 2025; Jan 12 to Mar 13, 2026;
  Apr 13 to May 22, 2026; Jul 13 to Aug 21, 2026; and from Oct 1, 2026 on. It is the releases the parser could
  read, not every company that reported.

## How it is checked, in numbers

I publish the counts at https://yieldterminalpro.com/accuracy, rebuilt from the published data on each site build;
the raw numbers are at https://yieldterminalpro.com/data/accuracy.json. The figures below are from the build of
**2026-11-27T01:00:20Z** (filings dated 2025-10-01 to 2026-11-25). They move with every build.

15,819 results filings (14,439 Form 8-K, 1,380 Form 6-K) from 4,103 companies. Of 47,457 possible figures (three
per filing), 37,526 were published (79.1%) and 9,931 withheld.

| Figure | Published | Withheld | Matches the later 10-Q (of checkable) | Awaiting re-check | Year-ago matches SEC |
|---|---|---|---|---|---|
| Revenue | 11,900 (75.2%) | 3,919 | 9,467 of 10,824 (87.5%) | 98 | 10,753 (90.4%) |
| Net income | 13,231 (83.6%) | 2,588 | 10,954 of 12,282 (89.2%) | 79 | 12,220 (92.4%) |
| Diluted EPS | 12,395 (78.4%) | 3,424 | 10,269 of 11,646 (88.2%) | 162 | not checked |

- Across all three figures, 30,690 published figures match the 10-Q: 81.8% of everything published, 88.3% of the
  figures a 10-Q check can cover (U.S. filers reporting in U.S. dollars).
- Published figures the 10-Q contradicts: **0**. That is zero by construction, not a measured error rate: a figure
  whose 10-Q value differs is withheld before publication or taken down during the 45-day re-check window.
- What the accuracy page does not measure: whether the company's own numbers are right (if a release and its 10-Q
  share an error, so does this data), releases the parser did not read, and any comparison with another vendor.

To see the current numbers yourself:

```bash
curl -s https://yieldterminalpro.com/data/accuracy.json | python -m json.tool | head -60
```

## Quick start (no key)

The sample endpoint returns real responses in the same format as the paid API, with no key: the company endpoint for
NVDA, WMT, TJX, HD and TGT, and the first three results of the latest filing day or outlook rows of the latest outlook
day. It is cached for 5 minutes and CORS is open.

```bash
BASE=https://yieldterminalpro.com/api/apps/6a44fce3122251d9ebac82ed/functions
curl -s "$BASE/data-sample?ticker=NVDA"          # one company: releases + SEC history
curl -s "$BASE/data-sample?endpoint=results"     # latest filing day, first 3 results
curl -s "$BASE/data-sample?endpoint=outlook"     # latest outlook day, first 3 rows
curl -s "$BASE/data-status"                      # data freshness
```

Python (standard library only):

```python
import json, urllib.request

BASE = "https://yieldterminalpro.com/api/apps/6a44fce3122251d9ebac82ed/functions"
req = urllib.request.Request(f"{BASE}/data-sample?ticker=NVDA", headers={"User-Agent": "my-script/1.0"})
co = json.load(urllib.request.urlopen(req, timeout=30))
for r in co["results"]:
    print(r["filed"], r.get("revenue_text") or "withheld", r.get("net_income_text") or "withheld", r["source_url"])
```

JavaScript (Node 18+ or a browser):

```js
const BASE = "https://yieldterminalpro.com/api/apps/6a44fce3122251d9ebac82ed/functions";
const co = await fetch(`${BASE}/data-sample?ticker=NVDA`).then((r) => r.json());
for (const r of co.results) console.log(r.filed, r.revenue_text ?? "withheld", r.net_income_text ?? "withheld", r.source_url);
```

Full runnable versions are in [`examples/`](examples):

```bash
python examples/python/quickstart.py
node examples/js/quickstart.mjs
bash examples/curl.sh
```

Each runs the no-key calls, then the keyed calls only if `YT_API_KEY` is set.

## With a key

Get a key at https://yieldterminalpro.com/developers (the free key takes an email address). Put it in an environment
variable rather than in code; the examples read `YT_API_KEY` and send it in the `x-api-key` header. (`?key=` in the
address still works but is deprecated, because addresses end up in logs.)

```bash
export YT_API_KEY=ytp_your_key_here
curl -s -H "x-api-key: $YT_API_KEY" \
  "https://yieldterminalpro.com/api/apps/6a44fce3122251d9ebac82ed/functions/data-api?endpoint=company&ticker=AAPL"
```

| `endpoint=` | Parameters | Returns |
|---|---|---|
| `results` | `date=YYYY-MM-DD` (optional) | Every published result filed that day (default: latest filing day). |
| `company` | `ticker=` | The company's latest results and up to 20 quarters of SEC history. |
| `outlook` | `date=` or `ticker=` (optional) | Outlook figures next to the same figure in the previous release. |
| `levels` | `ticker=` or `date=` (optional) | Dated chart levels published on the site and their tracked outcomes. |
| `capex` | `ticker=` (optional) | The AI spenders capex board, from 10-Q and 10-K XBRL data. |
| `scorecard` | `season=` (optional) | Reported quarter vs the company's own prior outlook for it. |
| `13f` | `ticker=` | Which of the 19 tracked managers reported the ticker's shares in their latest 13F filings vs the quarter before (free key: the 10 sandbox tickers only). |
| `updates` (Pro) | `since=` ISO time | Results first published, corrected or withdrawn since then. |
| `archive` (Pro) | `after=<accession>` (optional) | Every published result, 1,000 per call. |

Full reference: [`openapi.json`](openapi.json) (live: https://yieldterminalpro.com/openapi.json) and
https://yieldterminalpro.com/developers.

## MCP connector (Claude, Cursor, VS Code and other MCP clients)

A remote MCP server at `https://yieldterminalpro.com/api/mcp`, over HTTPS with OAuth 2.0 sign-in. It is free; the
first tool call opens a YieldTerminal sign-in (or free account creation) in your browser. Setup and the tool list:
https://yieldterminalpro.com/connector.

Claude Code:

```bash
claude mcp add --transport http yieldterminal https://yieldterminalpro.com/api/mcp
```

Cursor (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "yieldterminal": {
      "url": "https://yieldterminalpro.com/api/mcp"
    }
  }
}
```

VS Code (`.vscode/mcp.json`):

```json
{
  "servers": {
    "yieldterminal": {
      "type": "http",
      "url": "https://yieldterminalpro.com/api/mcp"
    }
  }
}
```

Claude (app): Settings, then Connectors, then Add custom connector; name it YieldTerminal and paste the server
address. Tools: `get_earnings_results`, `get_company_history`, `get_outlook_changes`, `get_sec_filings`,
`check_trading_rule`, `get_published_levels`, and `subscribe_to_sunday_recap` (which signs up only the signed-in
account's own email, and only after you say yes). Every answer carries the quoted sentence and the SEC.gov link.

## Free downloads

- **Results CSV**: https://yieldterminalpro.com/data/earnings-results.csv, one row per published results filing,
  the same rows the accuracy counts come from. Details and column list: https://yieldterminalpro.com/dataset.
  A dated snapshot (2026-11-27, 17,123 rows) is also on Kaggle, with a data card:
  https://www.kaggle.com/datasets/yieldterminalpro/sec-quarterly-earnings-results-source-linked
- **Archive sample**: https://yieldterminalpro.com/data/yieldterminal-archive-sample.zip, AAPL, MSFT and NVDA
  only, with the same files, columns and README as the paid archive (results, outlook changes, scorecard, company
  quarterly history and 11 more XBRL fields per quarter, up to 20 quarters per company, each value as first
  reported with any later restatement kept separately).

## Study

[`studies/`](studies) has `first_reported_vs_restated.py`, which downloads the archive sample, verifies it against
its manifest, and compares first-reported figures with later filings. Short version: in the sample, no revenue, net
income or EPS figure was restated; the only 3 flagged rows are NVDA share counts changed by a share split; and all 32
release figures with a matching XBRL figure equal it. The sample is too small to say anything about the full
archive. Full output in [`studies/README.md`](studies/README.md).

## Pricing

Free key $0 (100 calls a day, personal non-commercial use: results and outlook rows from the last 30 days, full
history for AAPL, MSFT, NVDA, AMZN, GOOG, META, TSLA, JPM, WMT and KO); Developer $29 a month (1,000 calls a day,
every filing day, 13F endpoint for every ticker, personal and internal use); Pro $99 a month (20,000 calls a day, updates and archive endpoints, commercial display
with attribution). The full historical archive is a one-time download, $49 personal or $149 commercial. The CSV and
the sample are free. Current details: https://yieldterminalpro.com/developers and https://yieldterminalpro.com/dataset.

## Licence and terms

- **Code** in this repository: MIT, see [LICENSE](LICENSE).
- **Data** returned by the API, the connector and the downloads is not covered by the MIT licence. It is under the
  site's terms: https://yieldterminalpro.com/terms. The free CSV may be used in research, articles, classes, apps and
  AI tools, naming YieldTerminal Pro as the source with a link to yieldterminalpro.com. The archive sample is free to
  use for evaluating the archive. API keys and the paid archive carry the plan or licence terms on
  /developers and /dataset; none of them allow reselling or redistributing the raw data as a dataset.
- **Attribution**: "Source: YieldTerminal Pro (yieldterminalpro.com), read from SEC EDGAR filings."
- The data is provided as is, with no warranty. The parser can be wrong: open `source_url` and read the filing before
  relying on a number. If you find an error, write to yieldterminalpro@gmail.com and I will fix it.

Educational data, not investment advice.
