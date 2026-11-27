// Types for the yieldterminal client. Field lists follow https://yieldterminalpro.com/openapi.json.
// A withheld figure is left out of the response (its *_text is null), never sent as 0,
// so figure fields are optional.

export declare const VERSION: string;
export declare const DEFAULT_BASE_URL: string;
export declare const API_KEY_ENV: "YIELDTERMINAL_API_KEY";
export declare const SAMPLE_TICKERS: readonly ["NVDA", "WMT", "TJX", "HD", "TGT"];
export declare const SANDBOX_TICKERS: readonly string[];

export type DateLike = string | Date;
export type SampleTicker = "NVDA" | "WMT" | "TJX" | "HD" | "TGT";
export type EventItem = "5.02" | "2.03" | "2.04";

export interface Status {
  latest_filing_day: string;
  latest_update_utc: string;
  hours_since_update: number;
  ok: boolean;
  error?: string;
  code?: string;
}

export interface Result {
  accession: string;
  form: string;
  ticker: string;
  company: string;
  cik: number;
  filed: string;
  accepted?: string;
  quarter_ended?: string;
  revenue_text?: string | null;
  revenue_value?: number;
  revenue_year_ago?: number;
  revenue_currency?: string;
  revenue_label?: string | null;
  revenue_matches_10q?: boolean | null;
  revenue_year_ago_matches_sec?: boolean | null;
  net_income_text?: string | null;
  net_income_value?: number;
  net_income_year_ago?: number;
  net_income_currency?: string;
  net_income_label?: string | null;
  net_income_matches_10q?: boolean | null;
  net_income_year_ago_matches_sec?: boolean | null;
  eps_text?: string | null;
  eps_value?: number;
  eps_year_ago?: number;
  eps_label?: string | null;
  eps_matches_10q?: boolean | null;
  source_url: string;
  published_at?: string;
  pushed_at?: string;
  status?: "published" | "withdrawn" | string;
  [extra: string]: unknown;
}

export interface ResultsResponse {
  endpoint: "results";
  date: string;
  count: number;
  free_sandbox?: boolean;
  results: Result[];
  note?: string;
  sample?: boolean;
  sample_note?: string;
}

/** v value, u unit, d 1 when derived (full year less Q1-Q3), r later restated value. */
export interface HistoryValue {
  v: number;
  u: string;
  d?: 1;
  r?: number;
  a?: string;
}

export interface HistoryQuarter {
  period_end: string;
  fiscal_year?: number;
  fiscal_period?: string;
  revenue?: HistoryValue;
  net_income?: HistoryValue;
  eps?: HistoryValue;
}

export interface CompanyResult {
  accession: string;
  form: string;
  filed: string;
  quarter_ended?: string;
  source_url: string;
  revenue_text?: string | null;
  revenue_value?: number;
  revenue_label?: string | null;
  revenue_proof?: string[];
  revenue_matches_10q?: boolean | null;
  revenue_year_ago_matches_sec?: boolean | null;
  net_income_text?: string | null;
  net_income_value?: number;
  net_income_label?: string | null;
  net_income_proof?: string[];
  net_income_matches_10q?: boolean | null;
  net_income_year_ago_matches_sec?: boolean | null;
  eps_text?: string | null;
  eps_value?: number;
  eps_label?: string | null;
  eps_proof?: string[];
  eps_matches_10q?: boolean | null;
  [extra: string]: unknown;
}

export interface CompanyResponse {
  endpoint: "company";
  ticker: string;
  company: string;
  cik: number;
  as_of: string;
  latest_filed: string;
  results: CompanyResult[];
  quarterly_history: HistoryQuarter[];
  history_note?: string;
  history_ext?: Array<Record<string, unknown>>;
  history_ext_note?: string;
  note?: string;
  sample?: boolean;
  sample_note?: string;
}

export interface OutlookRow {
  key: string;
  ticker: string;
  company: string;
  cik: number;
  filed: string;
  prev_filed: string;
  accession: string;
  prev_accession: string;
  source_url: string;
  prev_source_url: string;
  metric: string;
  period?: string;
  basis?: string;
  unit?: string;
  ccy?: string;
  old_low?: number;
  old_high?: number;
  new_low?: number;
  new_high?: number;
  old_text?: string;
  new_text?: string;
  sentence?: string;
  prev_sentence?: string;
  note?: string;
  [extra: string]: unknown;
}

export interface OutlookResponse {
  endpoint: "outlook";
  date?: string;
  ticker?: string;
  count: number;
  free_sandbox?: boolean;
  outlook: OutlookRow[];
  note?: string;
  sample?: boolean;
  sample_note?: string;
}

export interface PagedResponse {
  endpoint: "updates" | "archive";
  since?: string;
  after?: string;
  count: number;
  more: boolean;
  next_since?: string;
  next_after?: string;
  results: Result[];
  note?: string;
}

/** levels, capex, scorecard, 13f, capital, risk, events: see the OpenAPI spec for fields. */
export type JSONObject = { endpoint: string; [key: string]: unknown };

export interface RateLimitInfo {
  limit: number | null;
  remaining: number | null;
}

export interface ClientOptions {
  /** ytp_ + 48 hex. Defaults to process.env.YIELDTERMINAL_API_KEY. */
  apiKey?: string;
  timeoutMs?: number;
  baseUrl?: string;
  fetch?: typeof fetch;
  userAgent?: string;
}

export declare class YieldTerminal {
  constructor(options?: ClientOptions);
  readonly apiKey: string | null;
  readonly baseUrl: string;
  timeoutMs: number;
  /** X-RateLimit-* headers of the last successful data-api call (null before the first). */
  lastRateLimit: RateLimitInfo | null;

  status(): Promise<Status>;
  sample(ticker?: SampleTicker | string): Promise<CompanyResponse>;
  sample(options: { endpoint: "results" }): Promise<ResultsResponse>;
  sample(options: { endpoint: "outlook" }): Promise<OutlookResponse>;
  sample(options: { ticker?: SampleTicker | string }): Promise<CompanyResponse>;

  results(date?: DateLike): Promise<ResultsResponse>;
  company(ticker: string): Promise<CompanyResponse>;
  outlook(options?: { date?: DateLike; ticker?: string }): Promise<OutlookResponse>;
  levels(options?: { ticker?: string; date?: DateLike }): Promise<JSONObject>;
  capex(options?: { ticker?: string }): Promise<JSONObject>;
  scorecard(options?: { season?: string }): Promise<JSONObject>;
  holders13f(ticker: string): Promise<JSONObject>;
  capital(options?: { ticker?: string; tickers?: string | string[]; since?: DateLike; after?: string }): Promise<JSONObject>;
  risk(options?: { ticker?: string; tickers?: string | string[]; since?: DateLike; after?: string }): Promise<JSONObject>;
  events(options?: {
    ticker?: string;
    tickers?: string | string[];
    date?: DateLike;
    from?: DateLike;
    to?: DateLike;
    item?: EventItem;
  }): Promise<JSONObject>;
  /** Pro plan. */
  updates(since: string | Date): Promise<PagedResponse>;
  /** Pro plan. */
  archive(after?: string): Promise<PagedResponse>;
  /** Pro plan. */
  iterUpdates(since: string | Date): AsyncGenerator<Result, void, unknown>;
  /** Pro plan. */
  iterArchive(after?: string): AsyncGenerator<Result, void, unknown>;
}

export declare function sample(ticker?: SampleTicker | string): Promise<CompanyResponse>;
export declare function sample(options: { endpoint: "results" }): Promise<ResultsResponse>;
export declare function sample(options: { endpoint: "outlook" }): Promise<OutlookResponse>;
export declare function sample(options: { ticker?: SampleTicker | string }): Promise<CompanyResponse>;
export declare function status(): Promise<Status>;

export interface ErrorInit {
  status?: number | null;
  code?: string | null;
  body?: Record<string, unknown> | null;
}

export declare class YieldTerminalError extends Error {
  constructor(message: string, init?: ErrorInit);
  /** HTTP status, or null when no response arrived. */
  status: number | null;
  /** Machine-readable code from the API (free_ticker, free_season, no_row, ...), when sent. */
  code: string | null;
  body: Record<string, unknown> | null;
}
export declare class BadRequestError extends YieldTerminalError {}
export declare class AuthenticationError extends YieldTerminalError {}
export declare class MissingAPIKeyError extends AuthenticationError {
  constructor();
}
export declare class PaymentRequiredError extends YieldTerminalError {}
export declare class PermissionDeniedError extends YieldTerminalError {}
export declare class NotFoundError extends YieldTerminalError {}
export declare class RateLimitError extends YieldTerminalError {}
export declare class ServerError extends YieldTerminalError {}
export declare class ConnectionFailedError extends YieldTerminalError {}

export default YieldTerminal;
