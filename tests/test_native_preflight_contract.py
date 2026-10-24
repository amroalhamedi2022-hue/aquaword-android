"""Source-only guard for the manually dispatched native Android preflight.

The test does NOT compile Collabora, run Gradle, package APKs, or certify Android.
It prevents stale upstream SAVE signatures from silently blocking the one final
native build after all product and source acceptance gates are complete.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/android-native.yml"
OVERLAY = ROOT / "scripts/apply_to_collabora.py"

EXPECTED = (
    "private boolean copyTempBackToIntent(java.io.File sourceFile, Uri destination, java.io.File resolvedAtSave)",
    "private boolean copyTempBackToFile(java.io.File sourceFile, java.io.File resolvedFile)",
    "copyTempBackToIntent(checkpoint.file, original, resolvedAtSave)",
    "AquaWordHistory.verifyProviderWriteback(checkpoint, providerReadback)",
)


class NativePreflightContractTests(unittest.TestCase):
    def test_preflight_matches_current_generated_save_methods(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        overlay = OVERLAY.read_text(encoding="utf-8")
        for signature in EXPECTED:
            with self.subTest(signature=signature):
                self.assertIn(signature, overlay)
                self.assertIn("grep -Fq '" + signature + "'", workflow)
        self.assertNotIn("grep -q 'private boolean copyTempBackToIntent()'", workflow)
        self.assertNotIn("grep -q 'private boolean copyTempBackToFile()'", workflow)
        self.assertNotIn("grep -q 'if (copyTempBackToIntent())'", workflow)

    def test_preflight_runs_before_expensive_native_engine(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        preflight = workflow.index("grep -Fq '" + EXPECTED[0] + "'")
        native_engine = workflow.index("- name: Build or safely reuse LibreOffice native ARM64 engine")
        packaging = workflow.index("- name: Build AquaWord APK with Gradle")
        self.assertLess(preflight, native_engine)
        self.assertLess(native_engine, packaging)

    def test_native_apk_packaging_requires_manual_dispatch(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        trigger = workflow.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertEqual(trigger.strip(), "workflow_dispatch:")
        self.assertNotIn("pull_request:", trigger)
        self.assertNotIn("push:", trigger)


if __name__ == "__main__":
    unittest.main()
