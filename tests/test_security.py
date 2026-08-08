import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "codex_mexc_skills" / "skills"))

import mexc_common as common  # noqa: E402


class ValidationTests(unittest.TestCase):
    def test_authenticated_host_allowlist(self):
        self.assertEqual(
            common.validate_base_url(
                "https://api.mexc.com",
                authenticated=True,
                allowed_authenticated_hosts={"api.mexc.com"},
            ),
            "https://api.mexc.com",
        )
        for url in (
            "http://api.mexc.com",
            "https://evil.example",
            "https://api.mexc.com:444",
            "https://user:pass@api.mexc.com",
        ):
            with self.subTest(url=url), self.assertRaises(SystemExit):
                common.validate_base_url(
                    url,
                    authenticated=True,
                    allowed_authenticated_hosts={"api.mexc.com"},
                )

    def test_unauthenticated_local_http_only(self):
        self.assertEqual(
            common.validate_base_url("http://127.0.0.1:8080"),
            "http://127.0.0.1:8080",
        )
        with self.assertRaises(SystemExit):
            common.validate_base_url("http://evil.example")

    def test_path_rejects_url_and_control_characters(self):
        bad = (
            "https://evil.example/api/v3/time",
            "//evil.example/api/v3/time",
            "/api/v3/time\nX-Evil: yes",
            "/api/v3/a b",
            "/not-api/v1/test",
        )
        for value in bad:
            with self.subTest(value=value), self.assertRaises(SystemExit):
                common.normalize_path(value)

    def test_signed_query_rejected(self):
        with self.assertRaises(SystemExit):
            common.ensure_no_signed_query("/api/v3/account?x=1", True)

    def test_exact_safe_request_not_suffix(self):
        safe = {("POST", "/api/v3/order/test")}
        self.assertFalse(
            common.is_authenticated_mutation(
                "POST", "/api/v3/order/test", True, safe_requests=safe
            )
        )
        self.assertTrue(
            common.is_authenticated_mutation(
                "POST", "/api/v3/something/test", True, safe_requests=safe
            )
        )
        self.assertTrue(
            common.is_authenticated_mutation(
                "DELETE", "/api/v3/order/test", True, safe_requests=safe
            )
        )


class ConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ,
            {common.CONFIRMATION_DIR_ENV: self.tempdir.name},
        )
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tempdir.cleanup()

    def _prepare(self, params=None, ttl=60):
        return common.prepare_live_confirmation(
            method="POST",
            path="/api/v3/order",
            params=params
            or {"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.001"},
            authenticated=True,
            safe_requests={("POST", "/api/v3/order/test")},
            ttl_seconds=ttl,
        )

    def test_prepare_creates_private_receipt_and_consume_once(self):
        params = {"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.001"}
        prepared = self._prepare(params)
        digest = prepared["live_confirmation"]
        receipt = Path(self.tempdir.name) / f"{digest}.json"
        self.assertTrue(receipt.exists())
        if os.name == "posix":
            mode = stat.S_IMODE(receipt.stat().st_mode)
            self.assertEqual(mode & 0o077, 0)

        common.validate_live_execution(
            execute=True,
            confirm_live=digest,
            method="POST",
            path="/api/v3/order",
            params=params,
            authenticated=True,
            safe_requests={("POST", "/api/v3/order/test")},
        )
        self.assertFalse(receipt.exists())
        with self.assertRaises(SystemExit):
            common.validate_live_execution(
                execute=True,
                confirm_live=digest,
                method="POST",
                path="/api/v3/order",
                params=params,
                authenticated=True,
                safe_requests={("POST", "/api/v3/order/test")},
            )

    def test_changed_transaction_is_rejected_without_consuming_original(self):
        original = {"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.001"}
        digest = self._prepare(original)["live_confirmation"]
        with self.assertRaises(SystemExit):
            common.validate_live_execution(
                execute=True,
                confirm_live=digest,
                method="POST",
                path="/api/v3/order",
                params={**original, "quantity": "1"},
                authenticated=True,
            )
        self.assertTrue((Path(self.tempdir.name) / f"{digest}.json").exists())

    def test_expired_confirmation_is_rejected(self):
        with mock.patch("mexc_common.time.time", return_value=1000):
            digest = self._prepare(ttl=1)["live_confirmation"]
        with mock.patch("mexc_common.time.time", return_value=1002):
            with self.assertRaises(SystemExit):
                common.validate_live_execution(
                    execute=True,
                    confirm_live=digest,
                    method="POST",
                    path="/api/v3/order",
                    params={
                        "symbol": "BTCUSDT",
                        "side": "BUY",
                        "quantity": "0.001",
                    },
                    authenticated=True,
                )
        self.assertFalse((Path(self.tempdir.name) / f"{digest}.json").exists())

    def test_confirmation_required_for_live_mutation(self):
        with self.assertRaises(SystemExit):
            common.validate_live_execution(
                execute=True,
                confirm_live=None,
                method="POST",
                path="/api/v3/order",
                params={"symbol": "BTCUSDT"},
                authenticated=True,
            )

    def test_confirmation_not_required_for_exact_test_order(self):
        common.validate_live_execution(
            execute=True,
            confirm_live=None,
            method="POST",
            path="/api/v3/order/test",
            params={"symbol": "BTCUSDT"},
            authenticated=True,
            safe_requests={("POST", "/api/v3/order/test")},
        )

    def test_prepare_rejects_read_or_unauthenticated(self):
        for method, authenticated in (("GET", True), ("POST", False)):
            with self.subTest(
                method=method, authenticated=authenticated
            ), self.assertRaises(SystemExit):
                common.prepare_live_confirmation(
                    method=method,
                    path="/api/v3/order",
                    params={},
                    authenticated=authenticated,
                )


class RedactionTests(unittest.TestCase):
    def test_nested_secrets_are_redacted(self):
        secret = "super-secret-value"
        value = {
            "apiKey": secret,
            "nested": [{"listenKey": secret}, {"safe": "ok"}],
            "signature": secret,
        }
        output = common.redact_json_text(json.dumps(value))
        self.assertNotIn(secret, output)
        self.assertIn("<redacted>", output)
        self.assertIn("ok", output)

    def test_private_default_response_does_not_echo_payload(self):
        secret = "do-not-leak"
        output = common.format_http_response(
            json.dumps(
                {
                    "apiKey": secret,
                    "balance": "100",
                    "orders": [{"orderId": secret}],
                }
            ),
            status=200,
            authenticated=True,
            show_private_response=False,
        )
        self.assertNotIn(secret, output)
        self.assertNotIn("100", output)
        data = json.loads(output)
        self.assertTrue(data["private_response"])

    def test_query_redaction(self):
        output = common.redact_query_params(
            "symbol=BTCUSDT&signature=secret&listenKey=private",
            common.DEFAULT_SENSITIVE_KEYS,
        )
        self.assertNotIn("secret", output)
        self.assertNotIn("private", output)
        self.assertIn("symbol=BTCUSDT", output)


if __name__ == "__main__":
    unittest.main()
