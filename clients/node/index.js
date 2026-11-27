// Client for the YieldTerminal Pro Earnings Data API.
// Zero dependencies: uses the global fetch (Node 18+, Deno, Bun, browsers).
// Docs: https://yieldterminalpro.com/developers  Spec: https://yieldterminalpro.com/openapi.json

export const VERSION = "0.1.0";
export const DEFAULT_BASE_URL =
  "https://yieldterminalpro.com/api/apps/6a44fce3122251d9ebac82ed/functions";
export const API_KEY_ENV = "YIELDTERMINAL_API_KEY";
export const SAMPLE_TICKERS = Object.freeze(["NVDA", "WMT", "TJX", "HD", "TGT"]);
export const SANDBOX_TICKERS = Object.freeze([
  "AAPL", "MSFT", "NVDA", "AMZN", "GOOG", "META", "TSLA", "JPM", "WMT", "KO",
]);
const DEVELOPERS_URL = "https://yieldterminalpro.com/developers";

// ---------------------------------------------------------------- errors

export class YieldTerminalError extends Error {
  constructor(message, { status = null, code = null, body = null } = {}) {
    super(message);
    this.name = new.target.name;
    this.status = status;
    this.code = code;
    this.body = body;
  }
}
export class BadRequestError extends YieldTerminalError {}
export class AuthenticationError extends YieldTerminalError {}
export class MissingAPIKeyError extends AuthenticationError {
  constructor() {
    super(
      `No API key. Pass { apiKey } or set the ${API_KEY_ENV} environment variable. ` +
        `Get a free key at ${DEVELOPERS_URL}. sample() and status() work without a key.`,
    );
  }
}
export class PaymentRequiredError extends YieldTerminalError {}
export class PermissionDeniedError extends YieldTerminalError {}
export class NotFoundError extends YieldTerminalError {}
export class RateLimitError extends YieldTerminalError {}
export class ServerError extends YieldTerminalError {}
export class ConnectionFailedError extends YieldTerminalError {}

const BY_STATUS = {
  400: BadRequestError,
  401: AuthenticationError,
  402: PaymentRequiredError,
  403: PermissionDeniedError,
  404: NotFoundError,
  429: RateLimitError,
};

function errorForStatus(status, body, text) {
  let message = (body && typeof body === "object" && body.error) || (text || "").trim().slice(0, 300) || "Request failed";
  const code = (body && typeof body === "object" && body.code) || null;
  if (status === 429) message += " (daily limit; resets at 00:00 UTC)";
  if (status === 401 && !message.includes(DEVELOPERS_URL)) message += ` (keys: ${DEVELOPERS_URL})`;
  const Cls = BY_STATUS[status] || (status >= 500 ? ServerError : YieldTerminalError);
  return new Cls(message, { status, code, body: body && typeof body === "object" ? body : null });
}

// ---------------------------------------------------------------- helpers

function envKey() {
  try {
    // eslint-disable-next-line no-undef
    return typeof process !== "undefined" && process.env ? process.env[API_KEY_ENV] : undefined;
  } catch {
    return undefined;
  }
}

function toDate(value) {
  if (value == null) return undefined;
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  return String(value);
}

function toIsoTime(value) {
  if (value instanceof Date) return value.toISOString().replace(/\.\d{3}Z$/, "Z");
  return String(value);
}

function toTicker(value) {
  return value ? String(value).trim().toUpperCase() : undefined;
}

function toTickers(value) {
  if (value == null) return undefined;
  const list = (Array.isArray(value) ? value : String(value).split(","))
    .map((t) => String(t).trim().toUpperCase())
    .filter(Boolean);
  if (list.length < 1 || list.length > 25) throw new RangeError("tickers takes 1 to 25 symbols");
  return list.join(",");
}

function toInt(value) {
  const n = value == null ? NaN : parseInt(value, 10);
  return Number.isFinite(n) ? n : null;
}

// ---------------------------------------------------------------- client

export class YieldTerminal {
  /**
   * @param {object} [options]
   * @param {string} [options.apiKey]  ytp_ + 48 hex. Defaults to process.env.YIELDTERMINAL_API_KEY.
   * @param {number} [options.timeoutMs=30000]
   * @param {string} [options.baseUrl]
   * @param {typeof fetch} [options.fetch]  custom fetch (for tests or older runtimes)
   */
  constructor({ apiKey, timeoutMs = 30000, baseUrl = DEFAULT_BASE_URL, fetch: fetchImpl, userAgent } = {}) {
    const key = apiKey !== undefined ? apiKey : envKey();
    this.apiKey = key ? String(key).trim() : null;
    this.timeoutMs = timeoutMs;
    this.baseUrl = String(baseUrl).replace(/\/+$/, "");
    this.userAgent = userAgent || `yieldterminal-node/${VERSION}`;
    this.lastRateLimit = null;
    this._fetch = fetchImpl || globalThis.fetch;
    if (typeof this._fetch !== "function") {
      throw new YieldTerminalError("No global fetch. Use Node 18+ or pass { fetch }.");
    }
  }

  async _get(fn, params, { key }) {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params || {})) if (v !== undefined && v !== null) qs.set(k, String(v));
    const url = `${this.baseUrl}/${fn}${qs.toString() ? `?${qs}` : ""}`;
    const headers = { Accept: "application/json" };
    // Browsers forbid setting User-Agent; only send it where it is allowed.
    if (typeof window === "undefined") headers["User-Agent"] = this.userAgent;
    if (key) {
      if (!this.apiKey) throw new MissingAPIKeyError();
      headers["x-api-key"] = this.apiKey;
    }
    let res;
    try {
      const signal = typeof AbortSignal !== "undefined" && AbortSignal.timeout ? AbortSignal.timeout(this.timeoutMs) : undefined;
      res = await this._fetch(url, { method: "GET", headers, signal });
    } catch (err) {
      throw new ConnectionFailedError(`Could not reach ${this.baseUrl}: ${err && err.message ? err.message : err}`);
    }
    const text = await res.text();
    let body = null;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      body = null;
    }
    if (!res.ok) throw errorForStatus(res.status, body, text);
    if (key && res.headers && typeof res.headers.get === "function") {
      this.lastRateLimit = {
        limit: toInt(res.headers.get("X-RateLimit-Limit")),
        remaining: toInt(res.headers.get("X-RateLimit-Remaining")),
      };
    }
    if (body === null) throw new YieldTerminalError("The API returned a body that is not JSON", { status: res.status });
    return body;
  }

  _data(endpoint, params = {}) {
    return this._get("data-api", { endpoint, ...params }, { key: true });
  }

  // ---- no key

  /** Data freshness. No key, no quota. */
  status() {
    return this._get("data-status", {}, { key: false });
  }

  /**
   * Live sample in the same format as the paid API, no key.
   * sample("TJX") -> company sample (NVDA, WMT, TJX, HD, TGT).
   * sample({ endpoint: "results" }) or sample({ endpoint: "outlook" }) -> first 3 rows of the latest day.
   */
  sample(tickerOrOptions = "NVDA") {
    if (tickerOrOptions && typeof tickerOrOptions === "object") {
      const { endpoint, ticker } = tickerOrOptions;
      if (endpoint !== undefined) {
        if (endpoint !== "results" && endpoint !== "outlook") {
          throw new RangeError('sample endpoint must be "results" or "outlook" (or omit it for a company)');
        }
        return this._get("data-sample", { endpoint }, { key: false });
      }
      return this._get("data-sample", { ticker: toTicker(ticker || "NVDA") }, { key: false });
    }
    return this._get("data-sample", { ticker: toTicker(tickerOrOptions || "NVDA") }, { key: false });
  }

  // ---- key required

  /** Every published result filed on date (YYYY-MM-DD). Default: the latest filing day. */
  results(date) {
    return this._data("results", { date: toDate(date) });
  }

  /** One company: results releases plus up to 20 quarters of SEC history as first reported. */
  company(ticker) {
    if (!ticker) throw new TypeError("company() needs a ticker");
    return this._data("company", { ticker: toTicker(ticker) });
  }

  /** Outlook changes by filing day or ticker (ticker wins). */
  outlook({ date, ticker } = {}) {
    return this._data("outlook", { date: toDate(date), ticker: toTicker(ticker) });
  }

  levels({ ticker, date } = {}) {
    return this._data("levels", { ticker: toTicker(ticker), date: toDate(date) });
  }

  capex({ ticker } = {}) {
    return this._data("capex", { ticker: toTicker(ticker) });
  }

  scorecard({ season } = {}) {
    return this._data("scorecard", { season });
  }

  holders13f(ticker) {
    return this._data("13f", { ticker: toTicker(ticker) });
  }

  capital({ ticker, tickers, since, after } = {}) {
    return this._data("capital", { ticker: toTicker(ticker), tickers: toTickers(tickers), since: toDate(since), after });
  }

  risk({ ticker, tickers, since, after } = {}) {
    return this._data("risk", { ticker: toTicker(ticker), tickers: toTickers(tickers), since: toDate(since), after });
  }

  /** 8-K Items 5.02, 2.03, 2.04. from/to: at most 23 business days. */
  events({ ticker, tickers, date, from, to, item } = {}) {
    return this._data("events", {
      ticker: toTicker(ticker),
      tickers: toTickers(tickers),
      date: toDate(date),
      from: toDate(from),
      to: toDate(to),
      item,
    });
  }

  /** Pro: results first published, corrected or withdrawn after `since` (ISO UTC time or Date). */
  updates(since) {
    if (!since) throw new TypeError("updates() needs since");
    return this._data("updates", { since: toIsoTime(since) });
  }

  /** Pro: every published result, 1,000 per call. */
  archive(after) {
    return this._data("archive", { after });
  }

  /** Pro: every row from updates, following next_since while more is true. */
  async *iterUpdates(since) {
    let cursor = toIsoTime(since);
    for (;;) {
      const page = await this.updates(cursor);
      for (const row of page.results || []) yield row;
      if (!page.more || !page.next_since) return;
      cursor = page.next_since;
    }
  }

  /** Pro: every published result, following next_after while more is true. */
  async *iterArchive(after) {
    let cursor = after;
    for (;;) {
      const page = await this.archive(cursor);
      for (const row of page.results || []) yield row;
      if (!page.more || !page.next_after) return;
      cursor = page.next_after;
    }
  }
}

// ---------------------------------------------------------------- no-key shortcuts

/** Live sample, no key. See YieldTerminal#sample. */
export function sample(tickerOrOptions = "NVDA") {
  return new YieldTerminal({ apiKey: "" }).sample(tickerOrOptions);
}

/** Data freshness, no key. */
export function status() {
  return new YieldTerminal({ apiKey: "" }).status();
}

export default YieldTerminal;
