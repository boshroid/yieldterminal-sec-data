// Live tests call only the no-key endpoints (data-sample, data-status): no key, no quota.
// Error mapping is tested offline with an injected fetch.
// Run: npm test   (Node 18+). Set YIELDTERMINAL_SKIP_LIVE=1 to skip the network tests.

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  YieldTerminal,
  sample,
  status,
  SAMPLE_TICKERS,
  BadRequestError,
  AuthenticationError,
  MissingAPIKeyError,
  PaymentRequiredError,
  PermissionDeniedError,
  NotFoundError,
  RateLimitError,
  ServerError,
} from "../index.js";

const skipLive = process.env.YIELDTERMINAL_SKIP_LIVE === "1";

test("status (live, no key)", { skip: skipLive }, async () => {
  const st = await status();
  assert.equal(st.ok, true);
  assert.match(st.latest_filing_day, /^\d{4}-\d{2}-\d{2}$/);
});

test("company sample defaults to NVDA (live, no key)", { skip: skipLive }, async () => {
  const co = await sample();
  assert.equal(co.sample, true);
  assert.equal(co.endpoint, "company");
  assert.equal(co.ticker, "NVDA");
  assert.ok(co.results.length > 0);
  for (const r of co.results) assert.ok(r.source_url.startsWith("https://www.sec.gov/"), r.source_url);
  assert.ok(co.quarterly_history.length > 0);
});

test("every sample ticker (live, no key)", { skip: skipLive }, async () => {
  for (const t of SAMPLE_TICKERS) {
    const co = await sample(t.toLowerCase());
    assert.equal(co.ticker, t);
  }
});

test("results sample: a withheld figure never carries a number (live, no key)", { skip: skipLive }, async () => {
  const day = await sample({ endpoint: "results" });
  assert.equal(day.endpoint, "results");
  assert.ok(day.results.length <= 3);
  for (const r of day.results) {
    for (const fig of ["revenue", "net_income", "eps"]) {
      if (r[`${fig}_text`] == null) assert.equal(r[`${fig}_value`], undefined);
    }
  }
});

test("outlook sample (live, no key)", { skip: skipLive }, async () => {
  const ol = await sample({ endpoint: "outlook" });
  assert.equal(ol.endpoint, "outlook");
  assert.ok(Array.isArray(ol.outlook));
});

test("sample outside the five tickers is a 400 with a code (live, no key)", { skip: skipLive }, async () => {
  await assert.rejects(sample("AAPL"), (err) => {
    assert.ok(err instanceof BadRequestError);
    assert.equal(err.status, 400);
    assert.equal(err.code, "sample_ticker_not_covered");
    return true;
  });
});

// ---------------------------------------------------------------- offline

function fakeFetch(status, body, headers = {}) {
  const calls = [];
  const fn = async (url, init) => {
    calls.push({ url, init });
    const text = typeof body === "string" ? body : JSON.stringify(body);
    return {
      ok: status >= 200 && status < 300,
      status,
      text: async () => text,
      headers: { get: (k) => headers[k] ?? null },
    };
  };
  fn.calls = calls;
  return fn;
}

test("missing key throws before any request", async () => {
  const saved = process.env.YIELDTERMINAL_API_KEY;
  delete process.env.YIELDTERMINAL_API_KEY;
  try {
    const f = fakeFetch(200, {});
    const c = new YieldTerminal({ fetch: f });
    await assert.rejects(c.results(), MissingAPIKeyError);
    assert.equal(f.calls.length, 0);
  } finally {
    if (saved !== undefined) process.env.YIELDTERMINAL_API_KEY = saved;
  }
});

test("key from env; key goes in the header, never the URL", async () => {
  const saved = process.env.YIELDTERMINAL_API_KEY;
  const key = "ytp_" + "a".repeat(48);
  process.env.YIELDTERMINAL_API_KEY = key;
  try {
    const f = fakeFetch(200, { endpoint: "company", results: [] }, { "X-RateLimit-Limit": "100", "X-RateLimit-Remaining": "97" });
    const c = new YieldTerminal({ fetch: f });
    await c.company("brk.b");
    const { url, init } = f.calls[0];
    assert.equal(init.headers["x-api-key"], key);
    assert.ok(!url.includes(key));
    assert.ok(url.includes("endpoint=company"));
    assert.ok(url.includes("ticker=BRK.B"));
    assert.deepEqual(c.lastRateLimit, { limit: 100, remaining: 97 });
  } finally {
    if (saved === undefined) delete process.env.YIELDTERMINAL_API_KEY;
    else process.env.YIELDTERMINAL_API_KEY = saved;
  }
});

test("HTTP errors map to classes with status and code", async () => {
  const cases = [
    [400, { error: "bad", code: "bad_ticker" }, BadRequestError],
    [401, { error: "Unknown or replaced API key." }, AuthenticationError],
    [402, { error: "past_due" }, PaymentRequiredError],
    [403, { error: "not on free", code: "free_ticker" }, PermissionDeniedError],
    [404, { error: "none", code: "no_row" }, NotFoundError],
    [429, { error: "Daily limit reached" }, RateLimitError],
    [500, { error: "boom" }, ServerError],
    [503, "<html>down</html>", ServerError],
  ];
  for (const [code, body, Cls] of cases) {
    const c = new YieldTerminal({ apiKey: "ytp_" + "0".repeat(48), fetch: fakeFetch(code, body) });
    await assert.rejects(c.capital({ ticker: "ORCL" }), (err) => {
      assert.ok(err instanceof Cls, `${code} -> ${err.name}`);
      assert.equal(err.status, code);
      if (typeof body === "object") assert.equal(err.code, body.code ?? null);
      if (code === 429) assert.ok(err.message.includes("00:00 UTC"));
      return true;
    });
  }
});

test("argument checks", async () => {
  const c = new YieldTerminal({ apiKey: "k", fetch: fakeFetch(200, {}) });
  assert.throws(() => c.capital({ tickers: Array.from({ length: 26 }, (_, i) => `T${i}`) }), RangeError);
  assert.throws(() => c.sample({ endpoint: "company" }), RangeError);
});
