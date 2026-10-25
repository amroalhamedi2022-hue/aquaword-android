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

    def test_native_apk_packaging_requires_explicit_manual_or_added_marker(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        trigger = workflow.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertIn("workflow_dispatch:\n    inputs:", trigger)
        self.assertIn("final_ready:", trigger)
        self.assertIn("default: false", trigger)
        self.assertNotIn("pull_request:", trigger)
        self.assertIn("push:\n    branches: [fix/saf-save-failure-recovery-20261023]", trigger)
        self.assertIn("paths: ['.github/native-diagnostic-once.request']", trigger)
        marker = "github.event.head_commit.message == 'AquaWordNativeDiagnosticRetryOnce'"
        self.assertIn(marker, workflow)
        self.assertIn("github.event_name == 'push' && " + marker, workflow)
        self.assertIn("ONE_SHOT_REQUEST_MATCH: ${{ " + marker + " }}", workflow)

    def test_diagnostic_compile_only_keeps_native_output_unverified(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("diagnostic_compile_only:", workflow)
        self.assertIn("DIAGNOSTIC_COMPILE_ONLY: ${{ inputs.diagnostic_compile_only }}", workflow)
        self.assertIn("inputs.diagnostic_compile_only == true && inputs.diagnostic_build != true", workflow)
        self.assertIn("DIAGNOSTIC_COMPILE_ONLY", workflow)
        marker = "github.event_name == 'push' && github.event.head_commit.message == 'AquaWordNativeDiagnosticRetryOnce'"
        self.assertIn("!(inputs.diagnostic_build == true && inputs.diagnostic_compile_only == true) && !(" + marker + ")", workflow)
        self.assertIn("success() && !(inputs.diagnostic_build == true && inputs.diagnostic_compile_only == true) && !(" + marker + ")", workflow)
        self.assertIn("failure() && hashFiles('output/SHA256SUMS') != '' && !(inputs.diagnostic_build == true && inputs.diagnostic_compile_only == true) && !(" + marker + ")", workflow)
        self.assertIn("bash scripts/publish_qa_draft.sh --unverified", workflow)
        self.assertIn("uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9", workflow)
        self.assertIn("retention-days: 1", workflow)
        self.assertIn("compression-level: 0", workflow)
        self.assertIn("steps.diagnostic_apk_artifact.outputs.artifact-url", workflow)
        self.assertIn("No automatic native build dispatch on push", (ROOT / ".github/workflows/queue-current-native-once.yml").read_text(encoding="utf-8"))

    def test_diagnostic_apk_contains_arm64_native_engine_not_just_java(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        verifier = (ROOT / "scripts/verify_native_apk.py").read_text(encoding="utf-8")
        invocation = 'python3 scripts/verify_native_apk.py --apk "$apk" --engine-dir collabora/engine --abi "$ABI"'
        self.assertIn(invocation, workflow)
        self.assertIn('member_name = f"lib/{abi}/liblo-native-code.so"', verifier)
        self.assertIn('("classes.dex", member_name)', verifier)
        self.assertIn("load_segments(extracted, total, abi)", verifier)
        self.assertIn("load_segments(source, expected[\"size\"], abi)", verifier)
        self.assertLess(workflow.index(invocation),
                        workflow.index("Record real APK metadata and source provenance"))
        self.assertLess(workflow.index(invocation),
                        workflow.index("Retain valid compiled APK when emulator certification is blocked"))


    def test_compile_only_apk_upload_is_pinned_short_retention_and_does_not_call_release_api(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        verifier = workflow.index('python3 scripts/verify_native_apk.py --apk "$apk" --engine-dir collabora/engine --abi "$ABI"')
        uploader = workflow.index("- name: Upload compile-only native APK for short-lived download")
        report = workflow.index("- name: Report diagnostic artifact availability")
        runtime = workflow.index("- name: Verify installation and Arabic DOCX on a real Android emulator")
        self.assertLess(verifier, uploader)
        self.assertLess(uploader, report)
        self.assertLess(report, runtime)
        self.assertIn("id: diagnostic_apk_artifact", workflow)
        self.assertIn("uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9", workflow)
        self.assertIn("retention-days: 1", workflow)
        self.assertIn("compression-level: 0", workflow)
        self.assertIn("steps.diagnostic_apk_artifact.outputs.artifact-url", workflow)
        retention = workflow.split("- name: Retain valid compiled APK when emulator certification is blocked", 1)[1]
        condition = next(line for line in retention.splitlines() if line.strip().startswith("if:"))
        self.assertIn("failure() && hashFiles('output/SHA256SUMS') != ''", condition)
        self.assertIn("!(github.event_name == 'push' && github.event.head_commit.message == 'AquaWordNativeDiagnosticRetryOnce')", condition)
        self.assertIn("continue-on-error: true", workflow.split("- name: Preserve emulator-verified APK in an unpublished QA draft", 1)[1].split("- name:", 1)[0])

    def test_diagnostic_build_requires_reason_and_excludes_final_ready(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("inputs.diagnostic_build == true && inputs.final_ready != true && inputs.diagnostic_reason != ''", workflow)
        self.assertIn('[ "$DIAGNOSTIC_BUILD" = \'true\' ] && [ "$FINAL_READY" != \'true\' ]', workflow)
        self.assertIn('"${DIAGNOSTIC_REASON//[[:space:]]/}"', workflow)
        self.assertIn("bash scripts/check_final_ready.sh", workflow)
        self.assertIn("timeout-minutes: 360", workflow)


if __name__ == "__main__":
    unittest.main()
