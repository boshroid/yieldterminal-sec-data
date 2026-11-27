// YieldTerminal Earnings Results: a free Apify Actor that moves YieldTerminal Pro Earnings Data API
// responses into an Apify dataset. The user brings their own key; samples and status need none.
// API client: the published `yieldterminal` npm package. Spec: https://yieldterminalpro.com/openapi.json
import { Actor, log } from 'apify';
import { YieldTerminal, SAMPLE_TICKERS, VERSION } from 'yieldterminal';

const DEVELOPERS_URL = 'https://yieldterminalpro.com/developers';
const NEEDS_KEY = `This data set needs a YieldTerminal API key: get a free one at ${DEVELOPERS_URL}`;
const NO_KEY = new Set(['sample-company', 'sample-results', 'sample-outlook', 'status']);
const KEYED = new Set(['company', 'results', 'outlook', 'capex', 'scorecard', 'levels', '13f', 'capital',
    'risk', 'events', 'updates', 'archive']);

// Arrays in each response that become one dataset item per element: [response field, item kind].
const ROWS = {
    results: [['results', 'result']],
    updates: [['results', 'result']],
    archive: [['results', 'result']],
    company: [['results', 'release'], ['quarterly_history', 'history'], ['history_ext', 'history_ext']],
    outlook: [['outlook', 'outlook']],
    levels: [['levels', 'level']],
    scorecard: [['rows', 'score']],
    '13f': [['holders', 'holder'], ['gone', 'holder_gone']],
    capital: [['quarters', 'capital']],
    risk: [['added', 'risk_added'], ['removed', 'risk_removed'], ['reworded', 'risk_reworded']],
    events: [['events', 'event']],
};
// Copied from the response onto each item when the item lacks them (company history rows, for example).
const PARENT_FIELDS = ['ticker', 'company', 'cik'];
// Per-ticker errors that skip that ticker instead of stopping the run.
const SKIPPABLE = new Set([400, 403, 404]);

const isObj = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
const day = (v) => (v ? String(v).trim().slice(0, 10) : undefined);

let apiKey = '';
// Belt and braces: the key is only ever sent as a header, but scrub it from anything we print anyway.
const redact = (text) => {
    const s = String(text ?? '');
    return apiKey ? s.split(apiKey).join('[key]') : s;
};

function describe(err) {
    const msg = redact(err?.message || err);
    const code = err?.code ? `, code ${err.code}` : '';
    switch (err?.status) {
        case 400: return `The API rejected the request (400${code}): ${msg}`;
        case 401: return `The API key was not accepted (401${code}): ${msg}`;
        case 402: return `The subscription behind this API key is not active (402${code}): ${msg}`;
        case 403: return `This key's plan does not cover that request (403${code}): ${msg}`;
        case 404: return `No data for that request (404${code}): ${msg}`;
        case 429: return `Daily call limit reached (429): ${msg}`;
        default: return msg;
    }
}

function makeRow(kind, row, parent, sample) {
    const item = { kind };
    const src = isObj(row) ? row : { value: row };
    for (const f of PARENT_FIELDS) {
        const v = src[f] ?? parent[f];
        if (v !== undefined && v !== null) item[f] = v;
    }
    // Spread as-is: a withheld figure stays absent (never filled with 0).
    Object.assign(item, src);
    if (sample) item.sample = true;
    return item;
}

// If a multi-ticker response is keyed by ticker ({ AAPL: {...}, MSFT: {...} }), split it into one body per ticker.
function splitByTicker(body) {
    if (body.ticker) return null;
    for (const v of Object.values(body)) {
        const entries = isObj(v) ? Object.entries(v) : [];
        if (entries.length && entries.every(([t, x]) => /^[A-Z][A-Z0-9.-]{0,9}$/.test(t) && isObj(x))) {
            return entries.map(([t, x]) => ({ ticker: t, ...x }));
        }
    }
    return null;
}

function toRows(endpoint, body, sample) {
    if (!isObj(body)) return [];
    if (endpoint === 'capex' && Array.isArray(body.companies)) {
        return body.companies.flatMap(({ quarters, ...co }) => (quarters || [])
            .map((q) => makeRow('capex', { unit: body.unit, ...co, ...q }, body, sample)));
    }
    const found = (ROWS[endpoint] || []).filter(([field]) => Array.isArray(body[field]));
    if (found.length) {
        return found.flatMap(([field, kind]) => body[field].map((r) => makeRow(kind, r, body, sample)));
    }
    const parts = splitByTicker(body);
    if (parts) return parts.flatMap((p) => toRows(endpoint, p, sample));
    // A shape not listed above (for example the compact rows of capital/risk "since"): first array of objects.
    const field = Object.keys(body).find((k) => Array.isArray(body[k]) && body[k].some(isObj));
    if (field) return body[field].map((r) => makeRow(endpoint, r, body, sample));
    // Status, or a response with nothing to list (a risk comparison that was withheld): push it whole.
    const { note, ...rest } = body;
    return [makeRow(endpoint, rest, {}, sample)];
}

await Actor.init();
let pushed = 0;
let calls = 0;

try {
    const input = (await Actor.getInput()) || {};
    const endpoint = String(input.endpoint || 'sample-company');
    apiKey = typeof input.apiKey === 'string' ? input.apiKey.trim() : '';
    const tickers = [...new Set((input.tickers || []).map((t) => String(t).trim().toUpperCase()).filter(Boolean))];
    const maxPages = Math.min(500, Math.max(1, parseInt(input.maxPages, 10) || 5));
    const flatten = input.flatten !== false;
    const since = input.since ? String(input.since).trim() : undefined;
    const item = input.item || undefined;

    if (!NO_KEY.has(endpoint) && !KEYED.has(endpoint)) throw new Error(`Unknown data set "${endpoint}".`);
    if (KEYED.has(endpoint) && !apiKey) throw new Error(NEEDS_KEY);

    const yt = new YieldTerminal({
        apiKey,
        timeoutMs: 60_000,
        userAgent: `yieldterminal-apify/0.1 (yieldterminal-node/${VERSION})`,
    });
    const shape = endpoint.startsWith('sample-') ? endpoint.slice(7) : endpoint;
    const sample = endpoint.startsWith('sample-');
    const notes = [];
    let attributionSaved = false;

    log.info(`Data set: ${endpoint}${tickers.length ? `, tickers: ${tickers.join(', ')}` : ''}, key: ${apiKey ? 'given' : 'none'}`);

    const fetchAndPush = async (label, fn) => {
        calls += 1;
        const body = await fn();
        if (!attributionSaved && isObj(body) && typeof body.note === 'string') {
            await Actor.setValue('ATTRIBUTION', {
                attribution: 'Data: YieldTerminal Pro (yieldterminalpro.com)',
                note: body.note,
                ...(body.sample_note ? { sample_note: body.sample_note } : {}),
            });
            attributionSaved = true;
        }
        if (Array.isArray(body?.not_covered) && body.not_covered.length) {
            const msg = `Not covered by this key's plan: ${body.not_covered.map(String).join(', ')}.`;
            log.warning(msg);
            notes.push(msg);
        }
        const rows = flatten ? toRows(shape, body, sample) : [{ kind: shape, ...body }];
        if (rows.length) await Actor.pushData(rows);
        pushed += rows.length;
        log.info(`${label}: ${rows.length} row(s)`);
        return body;
    };

    // One call per group of tickers; a 400/403/404 skips that group, anything else stops the run.
    const eachGroup = async (size, fn) => {
        if (!tickers.length) throw new Error(`The ${endpoint} data set needs at least one ticker.`);
        const groups = [];
        for (let i = 0; i < tickers.length; i += size) groups.push(tickers.slice(i, i + size));
        const failed = [];
        for (const g of groups) {
            try {
                await fetchAndPush(g.join(','), () => fn(g));
            } catch (err) {
                if (!SKIPPABLE.has(err?.status)) throw err;
                failed.push(`${g.join(',')}: ${describe(err)}`);
                log.warning(`Skipped ${failed.at(-1)}`);
            }
        }
        if (failed.length === groups.length) throw new Error(failed.join(' | '));
        if (failed.length) notes.push(`Skipped ${failed.length} of ${groups.length} call(s); see the log.`);
    };

    // Follow the API's cursor while more is true, at most maxPages calls.
    const paged = async (fn, nextField, start) => {
        let cursor = start;
        for (let page = 1; ; page += 1) {
            const body = await fetchAndPush(`Page ${page}`, () => fn(cursor));
            const next = body?.[nextField];
            if (!(body?.more ?? Boolean(next)) || !next) return;
            if (page >= maxPages) {
                const msg = `Stopped at Max pages (${maxPages}); more rows remain (continue from ${nextField} = ${next}).`;
                log.warning(msg);
                notes.push(msg);
                return;
            }
            cursor = next;
        }
    };

    const one = (fn) => (g) => fn(g[0]);
    const tickerOrTickers = (g) => (g.length === 1 ? { ticker: g[0] } : { tickers: g });

    switch (endpoint) {
        case 'sample-company': {
            const t = tickers[0] || 'NVDA';
            if (!SAMPLE_TICKERS.includes(t)) {
                throw new Error(`The company sample covers ${SAMPLE_TICKERS.join(', ')}. Other tickers need a key: get a free one at ${DEVELOPERS_URL}`);
            }
            await fetchAndPush(`Sample ${t}`, () => yt.sample(t));
            break;
        }
        case 'sample-results':
        case 'sample-outlook':
            await fetchAndPush('Sample', () => yt.sample({ endpoint: shape }));
            break;
        case 'status':
            await fetchAndPush('Status', () => yt.status());
            break;
        case 'company':
            await eachGroup(1, one((t) => yt.company(t)));
            break;
        case '13f':
            await eachGroup(1, one((t) => yt.holders13f(t)));
            break;
        case 'results':
            await fetchAndPush('Results', () => yt.results(day(input.date)));
            break;
        case 'outlook':
        case 'levels': {
            const fn = (o) => (endpoint === 'outlook' ? yt.outlook(o) : yt.levels(o));
            if (tickers.length) await eachGroup(1, one((t) => fn({ ticker: t })));
            else await fetchAndPush(endpoint, () => fn({ date: day(input.date) }));
            break;
        }
        case 'capex':
            if (tickers.length) await eachGroup(1, one((t) => yt.capex({ ticker: t })));
            else await fetchAndPush('Capex board', () => yt.capex());
            break;
        case 'scorecard':
            await fetchAndPush('Scorecard', () => yt.scorecard({ season: input.season || undefined }));
            break;
        case 'capital':
        case 'risk': {
            const fn = (o) => (endpoint === 'capital' ? yt.capital(o) : yt.risk(o));
            if (tickers.length) await eachGroup(25, (g) => fn(tickerOrTickers(g)));
            else if (since) await paged((after) => fn({ since: day(since), after }), 'next_after');
            else throw new Error(`The ${endpoint} data set needs tickers, or a Since day (YYYY-MM-DD).`);
            break;
        }
        case 'events': {
            const [from, to] = [day(input.dateFrom), day(input.dateTo)];
            if (tickers.length) await eachGroup(25, (g) => yt.events({ ...tickerOrTickers(g), item }));
            else if (from && to) await fetchAndPush(`Events ${from} to ${to}`, () => yt.events({ from, to, item }));
            else if (from || to) throw new Error('Events by range needs both From and To.');
            else await fetchAndPush('Events', () => yt.events({ date: day(input.date), item }));
            break;
        }
        case 'updates':
            if (!since) throw new Error('The updates data set needs Since, an ISO UTC time such as 2026-11-20T00:00:00Z.');
            await paged((s) => yt.updates(s), 'next_since', since);
            break;
        case 'archive':
            await paged((after) => yt.archive(after), 'next_after', undefined);
            break;
        default:
            throw new Error(`Unknown data set "${endpoint}".`);
    }

    const left = yt.lastRateLimit?.remaining;
    const summary = [`Pushed ${pushed} row(s) from ${calls} API call(s).`, ...notes,
        ...(Number.isFinite(left) ? [`Calls left today on this key: ${left}.`] : [])].join(' ');
    log.info(summary);
    await Actor.exit(redact(summary));
} catch (err) {
    let msg = describe(err);
    if (err?.status === 429) msg += `. Stopped the run; ${pushed} row(s) were pushed before the limit.`;
    log.error(msg);
    await Actor.fail(msg);
}
