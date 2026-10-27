"""Unit tests for the native APK signature-report gate."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_apk_signature import SignatureReportError, verify_signature_report


HEX = "0123456789abcdef" * 4
COLON_HEX = ":".join(HEX[i:i + 2] for i in range(0, len(HEX), 2))


class VerifyApkSignatureTests(unittest.TestCase):
    def test_accepts_numbered_signer_label(self):
        report = (
            "Verified using v2 scheme (APK Signature Scheme v2): true\n"
            f"Signer #1 certificate SHA-256 digest: {HEX}\n"
        )
        self.assertEqual(verify_signature_report(report), (HEX,))

    def test_accepts_v2_signer_label_and_colon_separated_digest(self):
        report = (
            "Verified using v2 scheme (APK Signature Scheme v2): true\n"
            f"V2 Signer: certificate SHA-256 digest: {COLON_HEX}\n"
        )
        self.assertEqual(verify_signature_report(report), (HEX,))

    def test_rejects_false_v2_result(self):
        with self.assertRaisesRegex(SignatureReportError, "not explicitly true"):
            verify_signature_report(
                f"Verified using v2 scheme (APK Signature Scheme v2): false\n"
                f"Signer #1 certificate SHA-256 digest: {HEX}\n"
            )

    def test_rejects_missing_certificate_digest(self):
        with self.assertRaisesRegex(SignatureReportError, "No certificate"):
            verify_signature_report("Verified using v2 scheme (APK Signature Scheme v2): true\n")

    def test_rejects_malformed_certificate_digest(self):
        with self.assertRaisesRegex(SignatureReportError, "malformed"):
            verify_signature_report(
                "Verified using v2 scheme (APK Signature Scheme v2): true\n"
                "V2 Signer: certificate SHA-256 digest: abc123\n"
            )

    def test_rejects_unknown_digest_label(self):
        with self.assertRaisesRegex(SignatureReportError, "Unrecognized"):
            verify_signature_report(
                "Verified using v2 scheme (APK Signature Scheme v2): true\n"
                f"Other Signer: certificate SHA-256 digest: {HEX}\n"
            )


if __name__ == "__main__":
    unittest.main()
