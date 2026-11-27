// YieldTerminal Pro earnings data: quick start in JavaScript (Node 18+ built-in fetch, no packages).
//
// Part 1 calls the public sample endpoint, which needs no key.
// Part 2 runs only when the YT_API_KEY environment variable is set; the key is sent in the
// x-api-key header, never in the address.
//
//   node examples/js/quickstart.mjs
//   YT_API_KEY=ytp_... node examples/js/quickstart.mjs
//
// Educational data, not investment advice. Attribute to YieldTerminal Pro (yieldterminalpro.com).

const BASE = "https://yieldterminalpro.com/api/apps/6a44fce3122251d9ebac82ed/functions";

async function get(path, params = {}, key) {
  const url = new URL(`${BASE}/${path}`);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
  const headers = { Accept: "application/json", "User-Agent": "yieldterminal-sec-data-examples/1.0" };
  if (key) headers["x-api-key"] = key;
  const res = await fetch(url, { headers });
  const body = await res.text();
  if (!res.ok) throw new Error(`HTTP ${res.status} from ${path}: ${body}`);
  return JSON.parse(body);
}

// A withheld figure has no number and no text: print it as withheld, never as zero.
const show = (v) => v ?? "withheld";

// ---- Part 1: no key ---------------------------------------------------------------
const status = await get("data-status");
console.log(`Data status: latest filing day ${status.latest_filing_day}, last update ${status.latest_update_utc} (${status.hours_since_update} hours ago)`);

const co = await get("data-sample", { ticker: "NVDA" }); // sample tickers: NVDA, WMT, TJX, HD, TGT
console.log(`\n${co.ticker} ${co.company}: ${co.results.length} results releases, latest filed ${co.latest_filed}`);
for (const r of co.results.slice(0, 3)) {
  console.log(`  ${r.filed} ${r.form}  revenue ${show(r.revenue_text)}`);
  console.log(`             net income ${show(r.net_income_text)}  EPS ${show(r.eps_text)}`);
  console.log(`             10-Q confirms revenue: ${r.revenue_matches_10q}  source ${r.source_url}`);
}

const day = await get("data-sample", { endpoint: "results" });
console.log(`\nLatest filing day ${day.date}: showing ${day.count} results`);
for (const r of day.results) console.log(`  ${r.ticker.padEnd(6)} revenue ${show(r.revenue_text)}  EPS ${show(r.eps_text)}`);

const out = await get("data-sample", { endpoint: "outlook" });
console.log(`\nLatest outlook day ${out.date}: showing ${out.count} rows`);
for (const o of out.outlook) console.log(`  ${o.ticker.padEnd(6)} ${o.metric} ${o.period}: ${o.old_text} -> ${o.new_text}`);

// ---- Part 2: with a key -----------------------------------------------------------
const key = process.env.YT_API_KEY;
if (!key) {
  console.log("\nYT_API_KEY is not set, so the keyed calls were skipped.");
  console.log("A free key (100 calls a day, personal use): https://yieldterminalpro.com/developers");
} else {
  const res = await get("data-api", { endpoint: "results" }, key); // latest filing day; add date: "YYYY-MM-DD"
  console.log(`\nKeyed: ${res.results.length} results filed ${res.date}`);
  for (const r of res.results.slice(0, 5)) console.log(`  ${r.ticker.padEnd(6)} revenue ${show(r.revenue_text)}  ${r.source_url}`);

  const aapl = await get("data-api", { endpoint: "company", ticker: "AAPL" }, key);
  const hist = aapl.quarterly_history ?? [];
  console.log(`\nKeyed: AAPL latest release ${aapl.latest_filed}, ${hist.length} quarters of SEC history (as of ${aapl.as_of})`);
  if (hist.length) console.log("  newest history row:", hist.at(-1));
}
