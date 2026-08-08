import json
import os
import secrets
import string
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

    def test_unauthenticated_http_is_localhost_only(self):
        self.assertEqual(
            common.validate_base_url("http://127.0.0.1:8080"),
            "http://127.0.0.1:8080",
        )
        with self.assertRaises(SystemExit):
            common.validate_base_url("http://evil.example")

    def test_path_rejects_urls_and_control_characters(self):
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

    def test_signed_query_is_rejected(self):
        with self.assertRaises(SystemExit):
            common.ensure_no_signed_query("/api/v3/account?x=1", True)

    def test_live_authenticated_mutation_requires_confirmation(self):
        with self.assertRaises(SystemExit):
            common.validate_live_execution(
                execute=True,
                confirm_live=False,
                method="POST",
                path="/api/v3/order",
                authenticated=True,
            )

    def test_confirmation_without_execute_is_rejected(self):
        with self.assertRaises(SystemExit):
            common.validate_live_execution(
                execute=False,
                confirm_live=True,
                method="POST",
                path="/api/v3/order",
                authenticated=True,
            )

    def test_get_and_unauthenticated_mutations_do_not_need_confirmation(self):
        common.validate_live_execution(
            execute=True,
            confirm_live=False,
            method="GET",
            path="/api/v3/account",
            authenticated=True,
        )
        common.validate_live_execution(
            execute=True,
            confirm_live=False,
            method="POST",
            path="/api/v3/public-test",
            authenticated=False,
        )

    def test_credentials_with_newlines_are_rejected(self):
        with mock.patch.dict(os.environ, {"MEXC_API_KEY": "abc\ndef"}, clear=False):
            with self.assertRaises(SystemExit):
                common.read_mexc_api_key()


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
        self.assertEqual(data["http_status"], 200)

    def test_non_json_private_payload_is_not_echoed(self):
        secret = "private-text-secret"
        output = common.format_http_response(
            secret,
            status=500,
            authenticated=True,
            show_private_response=True,
        )
        self.assertNotIn(secret, output)
        self.assertEqual(output, "<redacted non-JSON payload>")

    def test_query_redaction(self):
        output = common.redact_query_params(
            "symbol=BTCUSDT&signature=secret&listenKey=private",
            common.DEFAULT_SENSITIVE_KEYS,
        )
        self.assertNotIn("secret", output)
        self.assertNotIn("private", output)
        self.assertIn("symbol=BTCUSDT", output)


class RepeatedAdversarialTests(unittest.TestCase):
    def test_100_untrusted_authenticated_hosts_are_rejected(self):
        alphabet = string.ascii_lowercase + string.digits
        for _ in range(100):
            label = "evil-" + "".join(secrets.choice(alphabet) for _ in range(16))
            with self.assertRaises(SystemExit):
                common.validate_base_url(
                    f"https://{label}.example",
                    authenticated=True,
                    allowed_authenticated_hosts={"api.mexc.com"},
                )

    def test_100_random_secrets_do_not_survive_redaction(self):
        for _ in range(100):
            secret = secrets.token_urlsafe(32)
            payload = {
                "apiKey": secret,
                "nested": {
                    "listenKey": secret,
                    "items": [{"signature": secret}, {"safe": "visible"}],
                },
            }
            output = common.redact_json_text(json.dumps(payload))
            self.assertNotIn(secret, output)
            self.assertIn("visible", output)


if __name__ == "__main__":
    unittest.main()
