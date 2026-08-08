import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
PINNED_ACTION_RE = re.compile(r"^[^\s@]+@([0-9a-f]{40})$")
REMOTE_INSTALLER_PIPE_RE = re.compile(
    r"(?i)(?:curl|wget)[^\n|]*\|\s*(?:sh|bash)\b"
)


class WorkflowSupplyChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflows = sorted(
            list(WORKFLOW_DIR.glob("*.yml")) + list(WORKFLOW_DIR.glob("*.yaml"))
        )
        if not cls.workflows:
            raise AssertionError("No GitHub Actions workflows found")

    def test_external_actions_are_pinned_to_full_commit_sha(self):
        failures = []
        for workflow in self.workflows:
            for lineno, line in enumerate(workflow.read_text().splitlines(), start=1):
                match = re.match(r"^\s*uses:\s*([^\s#]+)", line)
                if not match:
                    continue
                target = match.group(1)
                if target.startswith("./"):
                    continue
                if target.startswith("docker://"):
                    if "@sha256:" not in target:
                        failures.append(f"{workflow}:{lineno}: {target}")
                    continue
                if not PINNED_ACTION_RE.match(target):
                    failures.append(f"{workflow}:{lineno}: {target}")
        self.assertEqual(failures, [], "Unpinned external Actions:\n" + "\n".join(failures))

    def test_no_floating_latest_or_remote_installer_execution(self):
        failures = []
        for workflow in self.workflows:
            text = workflow.read_text()
            if "@latest" in text:
                failures.append(f"{workflow}: contains @latest")
            if REMOTE_INSTALLER_PIPE_RE.search(text):
                failures.append(f"{workflow}: pipes a remote download into a shell")
        self.assertEqual(failures, [], "Unsafe installer patterns:\n" + "\n".join(failures))

    def test_no_privileged_pull_request_target_trigger(self):
        failures = []
        for workflow in self.workflows:
            if re.search(r"(?m)^\s*pull_request_target\s*:", workflow.read_text()):
                failures.append(str(workflow))
        self.assertEqual(
            failures,
            [],
            "pull_request_target requires explicit security review: " + ", ".join(failures),
        )

    def test_workflows_declare_permissions(self):
        failures = []
        for workflow in self.workflows:
            text = workflow.read_text()
            if not re.search(r"(?m)^permissions\s*:", text):
                failures.append(str(workflow))
            if re.search(r"(?m)^\s*contents\s*:\s*write\s*$", text):
                failures.append(f"{workflow}: contents: write")
            if re.search(r"(?m)^\s*write-all\s*$", text):
                failures.append(f"{workflow}: write-all")
        self.assertEqual(failures, [], "Over-broad or missing permissions:\n" + "\n".join(failures))

    def test_checkout_does_not_persist_credentials(self):
        failures = []
        for workflow in self.workflows:
            text = workflow.read_text()
            if "actions/checkout@" in text and not re.search(
                r"(?m)^\s*persist-credentials\s*:\s*false\s*$", text
            ):
                failures.append(str(workflow))
        self.assertEqual(
            failures,
            [],
            "Checkout credentials are persisted in: " + ", ".join(failures),
        )


if __name__ == "__main__":
    unittest.main()
