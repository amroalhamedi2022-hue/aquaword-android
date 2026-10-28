"""Source contract for the isolated SAF silent-truncation runtime test.

This protects the test fixture and ensures it never builds or packages a
different AquaWord product APK. It does not replace the Android runtime run.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "quality/saf_fault_provider/src/main/java/com/aquaword/saffaultprovider/TruncatingContentProvider.java"
MANIFEST = ROOT / "quality/saf_fault_provider/src/main/AndroidManifest.xml"
HARNESS = ROOT / "scripts/android_saf_fault_roundtrip.py"
WORKFLOW = ROOT / ".github/workflows/android-saf-fault-once.yml"


class SafFaultProviderContractTests(unittest.TestCase):
    def test_provider_silently_truncates_but_drains_the_write_pipe(self):
        source = PROVIDER.read_text(encoding="utf-8")
        self.assertIn("KEEP_BYTES = 128", source)
        self.assertIn("ParcelFileDescriptor.createPipe()", source)
        self.assertIn("new ParcelFileDescriptor.AutoCloseInputStream(pipe[0])", source)
        self.assertIn("int keep = Math.min(count, remaining)", source)
        self.assertIn("completed.countDown()", source)
        self.assertIn("completed.await(15, TimeUnit.SECONDS)", source)
        self.assertIn("QA_PROVIDER_TRUNCATED_WRITE_COMPLETE", source)

    def test_provider_is_isolated_to_a_separate_debug_test_package(self):
        manifest = MANIFEST.read_text(encoding="utf-8")
        build = (ROOT / "quality/saf_fault_provider/build.gradle").read_text(encoding="utf-8")
        self.assertIn('android:authorities="com.aquaword.saffaultprovider.documents"', manifest)
        self.assertIn('android:exported="true"', manifest)
        self.assertIn("applicationId 'com.aquaword.saffaultprovider'", build)
        self.assertNotIn("TruncatingContentProvider", (ROOT / "quality/debug_android/AndroidManifest.xml").read_text(encoding="utf-8"))

    def test_runtime_requires_failed_save_and_valid_private_recovery_bytes(self):
        source = HARNESS.read_text(encoding="utf-8")
        self.assertIn("AquaWord SAVE not acknowledged", source)
        self.assertIn("provider-truncated.docx", source)
        self.assertIn("latest_recovery_with_sentinel", source)
        self.assertIn("recovered-edited-document.docx", source)
        self.assertIn('"save_acknowledged": False', source)
        self.assertIn("zipfile.is_zipfile(io.BytesIO(truncated))", source)

    def test_one_shot_workflow_reuses_pinned_product_apk_and_builds_only_provider(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("github.event.head_commit.message == 'AquaWordSafProviderFaultOnce'", workflow)
        self.assertIn("AQUAWORD_APK_SHA256: 25f19bd79d35af4157384718d7f1036de8b0e65bbab8b93a928c71a9a5bad736", workflow)
        self.assertIn("gradle", workflow)
        self.assertIn("quality/saf_fault_provider assembleDebug", workflow)
        self.assertIn("No AquaWord/native engine rebuild performed.", workflow)
        self.assertIn("AquaWord SAF silent-truncation runtime acceptance", workflow)
        self.assertIn("retention-days: 1", workflow)


if __name__ == "__main__":
    unittest.main()
