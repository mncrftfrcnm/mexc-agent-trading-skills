import os
import secrets
import string
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "codex_mexc_skills" / "skills"))

import mexc_common as common  # noqa: E402


class RepeatedAdversarialTests(unittest.TestCase):
    def test_100_untrusted_authenticated_hosts_are_rejected(self):
        alphabet = string.ascii_lowercase + string.digits
        for _ in range(100):
            label = "evil-" + "".join(secrets.choice(alphabet) for _ in range(16))
            url = f"https://{label}.example"
            with self.assertRaises(SystemExit):
                common.validate_base_url(
                    url,
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
            output = common.redact_json_text(__import__("json").dumps(payload))
            self.assertNotIn(secret, output)
            self.assertIn("visible", output)

    def test_100_transaction_mutations_cannot_reuse_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {common.CONFIRMATION_DIR_ENV: directory}):
                for index in range(100):
                    original = {
                        "symbol": "BTCUSDT",
                        "side": "BUY",
                        "type": "LIMIT",
                        "quantity": f"0.{index + 1:04d}",
                        "price": str(50000 + index),
                    }
                    prepared = common.prepare_live_confirmation(
                        method="POST",
                        path="/api/v3/order",
                        params=original,
                        authenticated=True,
                    )
                    digest = prepared["live_confirmation"]
                    changed = {**original, "price": str(int(original["price"]) + 1)}
                    with self.assertRaises(SystemExit):
                        common.validate_live_execution(
                            execute=True,
                            confirm_live=digest,
                            method="POST",
                            path="/api/v3/order",
                            params=changed,
                            authenticated=True,
                        )
                    self.assertTrue((Path(directory) / f"{digest}.json").exists())

    def test_100_path_tampering_attempts_cannot_reuse_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {common.CONFIRMATION_DIR_ENV: directory}):
                for index in range(100):
                    params = {
                        "symbol": "BTCUSDT",
                        "side": "SELL",
                        "quantity": f"0.{index + 1:04d}",
                    }
                    prepared = common.prepare_live_confirmation(
                        method="POST",
                        path="/api/v3/order",
                        params=params,
                        authenticated=True,
                    )
                    digest = prepared["live_confirmation"]
                    with self.assertRaises(SystemExit):
                        common.validate_live_execution(
                            execute=True,
                            confirm_live=digest,
                            method="POST",
                            path="/api/v3/order/cancel",
                            params=params,
                            authenticated=True,
                        )
                    self.assertTrue((Path(directory) / f"{digest}.json").exists())


if __name__ == "__main__":
    unittest.main()
