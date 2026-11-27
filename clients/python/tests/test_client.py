"""Tests for the yieldterminal client.

Live tests call only the no-key endpoints (data-sample and data-status). Nothing here calls
data-api or data-free-key, so no key is needed and no quota is used. Error mapping is tested
offline with a stubbed urlopen.

Run:  python -m unittest discover -s tests -v      (or: pytest)
Set YIELDTERMINAL_SKIP_LIVE=1 to skip the network tests.
"""

from __future__ import annotations

import io
import json
import os
import unittest
from email.message import Message
from unittest import mock
from urllib.error import HTTPError

import yieldterminal
from yieldterminal import Client
from yieldterminal import client as client_module

SKIP_LIVE = os.environ.get("YIELDTERMINAL_SKIP_LIVE") == "1"


@unittest.skipIf(SKIP_LIVE, "YIELDTERMINAL_SKIP_LIVE=1")
class LiveNoKeyTests(unittest.TestCase):
    def test_status(self) -> None:
        st = yieldterminal.status()
        self.assertTrue(st.get("ok"), st)
        self.assertRegex(st["latest_filing_day"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertIn("latest_update_utc", st)

    def test_company_sample_default_nvda(self) -> None:
        co = yieldterminal.sample()
        self.assertTrue(co.get("sample"))
        self.assertEqual(co["endpoint"], "company")
        self.assertEqual(co["ticker"], "NVDA")
        self.assertGreater(len(co["results"]), 0)
        for r in co["results"]:
            self.assertTrue(r["source_url"].startswith("https://www.sec.gov/"), r["source_url"])
        self.assertGreater(len(co["quarterly_history"]), 0)

    def test_every_sample_ticker(self) -> None:
        for ticker in yieldterminal.SAMPLE_TICKERS:
            with self.subTest(ticker=ticker):
                co = yieldterminal.sample(ticker.lower())  # lower case is upper-cased by the client
                self.assertEqual(co["ticker"], ticker)

    def test_results_sample_withheld_is_never_zero(self) -> None:
        day = yieldterminal.sample(endpoint="results")
        self.assertEqual(day["endpoint"], "results")
        self.assertLessEqual(len(day["results"]), 3)
        for r in day["results"]:
            self.assertTrue(r["source_url"].startswith("https://www.sec.gov/"))
            for fig in ("revenue", "net_income", "eps"):
                if r.get(f"{fig}_text") is None:
                    self.assertNotIn(f"{fig}_value", r, "a withheld figure must not carry a number")

    def test_outlook_sample(self) -> None:
        ol = yieldterminal.sample(endpoint="outlook")
        self.assertEqual(ol["endpoint"], "outlook")
        self.assertIsInstance(ol["outlook"], list)

    def test_sample_ticker_not_covered(self) -> None:
        with self.assertRaises(yieldterminal.BadRequestError) as ctx:
            yieldterminal.sample("AAPL")
        self.assertEqual(ctx.exception.status, 400)
        self.assertEqual(ctx.exception.code, "sample_ticker_not_covered")

    def test_frames_on_live_sample(self) -> None:
        try:
            import pandas  # noqa: F401
        except ImportError:
            self.skipTest("pandas not installed")
        from yieldterminal.frames import history_frame, results_frame

        co = yieldterminal.sample("TJX")
        hist = history_frame(co)
        self.assertEqual(len(hist), len(co["quarterly_history"]))
        for col in ("period_end", "revenue", "revenue_unit", "revenue_derived", "revenue_restated"):
            self.assertIn(col, hist.columns)
        res = results_frame(co)
        self.assertEqual(len(res), len(co["results"]))


def _http_error(status: int, body: object) -> HTTPError:
    raw = json.dumps(body).encode() if not isinstance(body, bytes) else body
    return HTTPError("https://example.invalid", status, "err", Message(), io.BytesIO(raw))


class OfflineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = mock.patch.dict(os.environ, {}, clear=False)
        self._env.start()
        os.environ.pop(yieldterminal.API_KEY_ENV, None)

    def tearDown(self) -> None:
        self._env.stop()

    def test_missing_key_raises_before_request(self) -> None:
        with mock.patch.object(client_module, "urlopen") as op:
            with self.assertRaises(yieldterminal.MissingAPIKeyError):
                Client().results()
            op.assert_not_called()

    def test_key_from_env(self) -> None:
        os.environ[yieldterminal.API_KEY_ENV] = "ytp_" + "0" * 48
        self.assertEqual(Client().api_key, "ytp_" + "0" * 48)
        self.assertEqual(Client(api_key="ytp_" + "1" * 48).api_key, "ytp_" + "1" * 48)

    def test_key_goes_in_header_not_url(self) -> None:
        seen = {}

        class FakeResponse(io.BytesIO):
            headers = {"X-RateLimit-Limit": "100", "X-RateLimit-Remaining": "99"}

            def __enter__(self):  # noqa: D401
                return self

            def __exit__(self, *a):
                return False

        def fake_urlopen(req, timeout=None):
            seen["url"] = req.full_url
            seen["key"] = req.get_header("X-api-key")
            return FakeResponse(b'{"endpoint": "results", "results": []}')

        key = "ytp_" + "a" * 48
        with mock.patch.object(client_module, "urlopen", fake_urlopen):
            c = Client(api_key=key)
            out = c.company("brk.b")
        self.assertEqual(out["endpoint"], "results")
        self.assertEqual(seen["key"], key)
        self.assertNotIn(key, seen["url"])
        self.assertIn("endpoint=company", seen["url"])
        self.assertIn("ticker=BRK.B", seen["url"])
        self.assertEqual(c.last_rate_limit.limit, 100)
        self.assertEqual(c.last_rate_limit.remaining, 99)

    def test_error_mapping(self) -> None:
        cases = [
            (400, {"error": "bad", "code": "bad_ticker"}, yieldterminal.BadRequestError),
            (401, {"error": "Unknown or replaced API key."}, yieldterminal.AuthenticationError),
            (402, {"error": "past_due"}, yieldterminal.PaymentRequiredError),
            (403, {"error": "not on free", "code": "free_ticker"}, yieldterminal.PermissionDeniedError),
            (404, {"error": "none", "code": "no_row"}, yieldterminal.NotFoundError),
            (429, {"error": "Daily limit reached"}, yieldterminal.RateLimitError),
            (500, {"error": "boom"}, yieldterminal.ServerError),
            (503, b"<html>down</html>", yieldterminal.ServerError),
        ]
        for status, body, cls in cases:
            with self.subTest(status=status):
                with mock.patch.object(client_module, "urlopen", side_effect=_http_error(status, body)):
                    with self.assertRaises(cls) as ctx:
                        Client(api_key="ytp_" + "0" * 48).capital("ORCL")
                self.assertEqual(ctx.exception.status, status)
                if isinstance(body, dict):
                    self.assertEqual(ctx.exception.code, body.get("code"))
        # 429 message names the reset time
        with mock.patch.object(client_module, "urlopen", side_effect=_http_error(429, {"error": "x"})):
            with self.assertRaises(yieldterminal.RateLimitError) as ctx:
                Client(api_key="ytp_" + "0" * 48).results()
        self.assertIn("00:00 UTC", str(ctx.exception))

    def test_tickers_validation(self) -> None:
        with self.assertRaises(ValueError):
            Client(api_key="k").capital(tickers=[f"T{i}" for i in range(26)])
        with self.assertRaises(ValueError):
            Client(api_key="k").sample(endpoint="company")


if __name__ == "__main__":
    unittest.main()
