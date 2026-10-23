"""Never promote a compiled-only APK to a verified or published app."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class QaDraftPolicyTests(unittest.TestCase):
    def test_verified_mode_still_requires_android_proof(self):
        text=(ROOT/'scripts/publish_qa_draft.sh').read_text()
        self.assertIn('if [ "$MODE" = "--verified" ]; then',text)
        self.assertIn('smoke-evidence/roundtrip-result.txt',text)
        self.assertIn('focusModeFunctional',text)
        self.assertIn('smoke-evidence/reopened-writer-state.json',text)
        self.assertIn('--draft',text)
        self.assertIn('--latest=false',text)

    def test_unverified_mode_is_separate_draft_and_never_release(self):
        text=(ROOT/'scripts/publish_qa_draft.sh').read_text()
        self.assertIn('qa-unverified-$shortsha',text)
        self.assertIn('ANDROID RUNTIME NOT VERIFIED',text)
        self.assertIn('Do not publish this draft',text)
        self.assertIn('sha256sum -c SHA256SUMS',text)

    def test_native_ci_retains_only_after_packaging_and_never_masks_failure(self):
        yaml=(ROOT/'.github/workflows/android-native.yml').read_text()
        self.assertIn('if: failure()',yaml)
        self.assertIn('if test -s output/SHA256SUMS; then',yaml)
        self.assertIn('bash scripts/publish_qa_draft.sh --unverified',yaml)
        self.assertIn('bash scripts/publish_qa_draft.sh\n',yaml)
        self.assertIn('if: success()',yaml)


if __name__=="__main__":
    unittest.main()
