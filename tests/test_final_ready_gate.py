"""Final-Ready source gate: tests only; never launches an Android build."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_final_ready.sh"


def run(*args, cwd):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


class FinalReadyGateTests(unittest.TestCase):
    def test_unapproved_or_changed_source_never_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "docs").mkdir()
            shutil.copyfile(SCRIPT, root / "scripts/check_final_ready.sh")
            (root / "source.txt").write_text("original\n", encoding="utf-8")
            self.assertEqual(run("git", "init", "-q", cwd=root).returncode, 0)
            self.assertEqual(run("git", "add", ".", cwd=root).returncode, 0)
            self.assertNotEqual(run("bash", "scripts/check_final_ready.sh", cwd=root).returncode, 0)
            digest = run(
                "bash", "-c",
                "git ls-files -z -- . ':(exclude)docs/FINAL_READY_APPROVAL.txt' | "
                "xargs -0 -r sha256sum | sha256sum | cut -d' ' -f1",
                cwd=root,
            )
            self.assertEqual(digest.returncode, 0, digest.stderr)
            approval = root / "docs/FINAL_READY_APPROVAL.txt"
            approval.write_text(
                "FINAL_READY=YES\nREQUIREMENTS_COMPLETE=YES\n"
                "SOURCE_RECHECK=PASS\nACCEPTANCE_REVIEW=PASS\n"
                f"SOURCE_DIGEST_SHA256={digest.stdout.strip()}\n",
                encoding="utf-8",
            )
            self.assertEqual(run("bash", "scripts/check_final_ready.sh", cwd=root).returncode, 0)
            (root / "source.txt").write_text("modified\n", encoding="utf-8")
            self.assertNotEqual(run("bash", "scripts/check_final_ready.sh", cwd=root).returncode, 0)

    def test_approval_requires_every_independent_gate(self):
        body = SCRIPT.read_text(encoding="utf-8")
        for required in ("FINAL_READY=YES", "REQUIREMENTS_COMPLETE=YES",
                         "SOURCE_RECHECK=PASS", "ACCEPTANCE_REVIEW=PASS",
                         "SOURCE_DIGEST_SHA256="):
            self.assertIn(required, body)
        self.assertNotIn("assembleDebug", body)
        self.assertNotIn("gh workflow run", body)

    def test_native_and_queue_workflows_are_manual_only_and_gate_before_dispatch(self):
        native = (ROOT / ".github/workflows/android-native.yml").read_text(encoding="utf-8")
        queue = (ROOT / ".github/workflows/queue-current-native-once.yml").read_text(encoding="utf-8")
        for name, body in (("native", native), ("queue", queue)):
            with self.subTest(name=name):
                trigger = body.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
                self.assertIn("workflow_dispatch:", trigger)
                self.assertNotIn("\n  push:", trigger)
                self.assertNotIn("\n  pull_request:", trigger)
                self.assertIn("inputs.final_ready == true", body)
                self.assertIn("bash scripts/check_final_ready.sh", body)
        self.assertLess(native.index("bash scripts/check_final_ready.sh"),
                        native.index("Build or safely reuse LibreOffice native ARM64 engine"))
        self.assertLess(queue.index("bash scripts/check_final_ready.sh"),
                        queue.index("Retire only obsolete waiting native runs"))
        self.assertIn("inputs[final_ready]=true", queue)


if __name__ == "__main__":
    unittest.main()
