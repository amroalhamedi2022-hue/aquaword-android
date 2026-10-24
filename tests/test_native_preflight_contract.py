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

    def test_pdf_export_source_gate_before_native_packaging(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        overlay = OVERLAY.read_text(encoding="utf-8")
        fast = (ROOT / ".github/workflows/fast-source-contract.yml").read_text(encoding="utf-8")
        self.assertIn("def patch_native_export_writeback(", overlay)
        self.assertIn("AQUAWORD_VERIFIED_ASYNC_EXPORT", overlay)
        self.assertIn("grep -q 'AQUAWORD_VERIFIED_ASYNC_EXPORT'", workflow)
        self.assertIn("javalang.parse.parse(native_source)", fast)
        self.assertIn("native_source.count('AQUAWORD_VERIFIED_ASYNC_EXPORT') == 1", fast)
        self.assertLess(workflow.index("grep -q 'AQUAWORD_VERIFIED_ASYNC_EXPORT'"),
                        workflow.index("- name: Build or safely reuse LibreOffice native ARM64 engine"))

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
        self.assertTrue(trigger.strip().startswith("workflow_dispatch:\n    inputs:"), trigger)
        self.assertIn("final_ready:", trigger)
        self.assertIn("default: false", trigger)
        self.assertNotIn("pull_request:", trigger)
        self.assertNotIn("push:", trigger)

    def test_diagnostic_compile_only_keeps_native_output_unverified(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("diagnostic_compile_only:", workflow)
        self.assertIn("DIAGNOSTIC_COMPILE_ONLY: ${{ inputs.diagnostic_compile_only }}", workflow)
        self.assertIn("inputs.diagnostic_compile_only == true && inputs.diagnostic_build != true", workflow)
        self.assertIn('"$DIAGNOSTIC_COMPILE_ONLY" != \'true\'', workflow)
        self.assertIn("if: ${{ !(inputs.diagnostic_build == true && inputs.diagnostic_compile_only == true) }}", workflow)
        self.assertIn("if: ${{ success() && !(inputs.diagnostic_build == true && inputs.diagnostic_compile_only == true) }}", workflow)
        self.assertIn("if: ${{ failure() || (success() && inputs.diagnostic_build == true && inputs.diagnostic_compile_only == true) }}", workflow)
        self.assertIn("bash scripts/publish_qa_draft.sh --unverified", workflow)
        self.assertIn("No automatic native build dispatch on push", (ROOT / ".github/workflows/queue-current-native-once.yml").read_text(encoding="utf-8"))

    def test_diagnostic_build_requires_reason_and_excludes_final_ready(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("inputs.diagnostic_build == true && inputs.final_ready != true && inputs.diagnostic_reason != ''", workflow)
        self.assertIn('[ "$DIAGNOSTIC_BUILD" = \'true\' ] && [ "$FINAL_READY" != \'true\' ]', workflow)
        self.assertIn('"${DIAGNOSTIC_REASON//[[:space:]]/}"', workflow)
        self.assertIn("bash scripts/check_final_ready.sh", workflow)
        self.assertIn("timeout-minutes: 360", workflow)


if __name__ == "__main__":
    unittest.main()
