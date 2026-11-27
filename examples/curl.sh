#!/usr/bin/env bash
# YieldTerminal Pro earnings data: quick start with curl.
#
# The first four calls need no key. The keyed calls run only when YT_API_KEY is set; the key is
# sent in the x-api-key header, never in the address.
#
#   bash examples/curl.sh
#   YT_API_KEY=ytp_... bash examples/curl.sh
#
# Educational data, not investment advice. Attribute to YieldTerminal Pro (yieldterminalpro.com).
set -euo pipefail

BASE="https://yieldterminalpro.com/api/apps/6a44fce3122251d9ebac82ed/functions"

echo "== data freshness (no key)"
curl -sS "$BASE/data-status"; echo

echo "== company sample, NVDA (no key; samples: NVDA, WMT, TJX, HD, TGT)"
curl -sS "$BASE/data-sample?ticker=NVDA" | head -c 1200; echo " ..."

echo "== latest filing day, first 3 results (no key)"
curl -sS "$BASE/data-sample?endpoint=results" | head -c 1200; echo " ..."

echo "== latest outlook day, first 3 rows (no key)"
curl -sS "$BASE/data-sample?endpoint=outlook" | head -c 1200; echo " ..."

if [ -z "${YT_API_KEY:-}" ]; then
  echo "YT_API_KEY is not set, so the keyed calls were skipped."
  echo "A free key (100 calls a day, personal use): https://yieldterminalpro.com/developers"
  exit 0
fi

echo "== results for one filing day (key)"
curl -sS -H "x-api-key: $YT_API_KEY" "$BASE/data-api?endpoint=results&date=2026-11-25" | head -c 1200; echo " ..."

echo "== one company: release figures plus up to 20 quarters of SEC history (key)"
curl -sS -H "x-api-key: $YT_API_KEY" "$BASE/data-api?endpoint=company&ticker=AAPL" | head -c 1200; echo " ..."
