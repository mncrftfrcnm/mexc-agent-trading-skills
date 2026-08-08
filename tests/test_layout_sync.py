import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LayoutSyncTests(unittest.TestCase):
    def assert_same_text(self, *paths: str) -> None:
        contents = [(ROOT / path).read_text(encoding="utf-8") for path in paths]
        for index, content in enumerate(contents[1:], start=1):
            self.assertEqual(contents[0], content, msg=f"layout drift: {paths[0]} != {paths[index]}")

    def test_common_helper_is_identical_across_layouts(self):
        self.assert_same_text(
            "codex_mexc_skills/skills/mexc_common.py",
            "claude_mexc_skills/.claude/skills/mexc_common.py",
            "claude_mexc_skills/claude/skills/mexc_common.py",
        )

    def test_spot_request_helper_is_identical_across_layouts(self):
        self.assert_same_text(
            "codex_mexc_skills/skills/mexc-spot-rest/scripts/mexc_spot_request.py",
            "claude_mexc_skills/.claude/skills/mexc-spot-rest/scripts/mexc_spot_request.py",
            "claude_mexc_skills/claude/skills/mexc-spot-rest/scripts/mexc_spot_request.py",
        )

    def test_futures_request_helper_is_identical_across_layouts(self):
        self.assert_same_text(
            "codex_mexc_skills/skills/mexc-futures-rest/scripts/mexc_futures_request.py",
            "claude_mexc_skills/.claude/skills/mexc-futures-rest/scripts/mexc_futures_request.py",
            "claude_mexc_skills/claude/skills/mexc-futures-rest/scripts/mexc_futures_request.py",
        )

    def test_futures_helper_uses_contract_host(self):
        helper = (ROOT / "codex_mexc_skills/skills/mexc-futures-rest/scripts/mexc_futures_request.py").read_text(encoding="utf-8")
        self.assertIn('BASE_URL = "https://contract.mexc.com"', helper)
        self.assertIn('AUTHENTICATED_HOSTS = {"contract.mexc.com"}', helper)
        self.assertNotIn('AUTHENTICATED_HOSTS = {"api.mexc.com"}', helper)


if __name__ == "__main__":
    unittest.main()
