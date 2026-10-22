"""AquaWord real-evidence quality gate, with fail-closed tests."""
from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "quality"))
from audit import audit, secure_evidence_file, validate_receipt, markdown, AuditError  # noqa: E402

MATRIX = json.loads((Path(__file__).resolve().parents[1] / "quality/requirements.json").read_text(encoding="utf-8"))


class AcceptanceAuditTests(unittest.TestCase):
    def test_no_apk_means_no_feature_verified(self):
        with TemporaryDirectory() as dirname:
            rows, approved = audit(MATRIX, Path(dirname))
        self.assertFalse(approved)
        self.assertEqual(len(rows), 32)
        self.assertTrue(all(row["actual_status"] == "NOT_VERIFIED" for row in rows))
        self.assertIn("ممنوع", markdown(rows, approved))

    def test_receipt_requires_existing_sha256_checked_evidence(self):
        with TemporaryDirectory() as dirname:
            root = Path(dirname)
            (root / "device-output.txt").write_text("adb install Success", encoding="utf-8")
            receipt = self.receipt("APP-01", "emulator", "device-output.txt", root)
            valid, reason = validate_receipt(root, receipt)
            self.assertTrue(valid, reason)
            (root / "device-output.txt").write_text("different data", encoding="utf-8")
            valid, reason = validate_receipt(root, receipt)
            self.assertFalse(valid)
            self.assertIn("digest mismatch", reason)

    def test_emulator_evidence_not_physical_pass(self):
        with TemporaryDirectory() as dirname:
            root = Path(dirname)
            (root / "evidence.txt").write_text("checked process", encoding="utf-8")
            receipt = self.receipt("APP-01", "emulator", "evidence.txt", root)
            (root / "receipts.json").write_text(json.dumps([receipt]), encoding="utf-8")
            rows, release = audit(MATRIX, root)
            row = next(x for x in rows if x["id"] == "APP-01")
            self.assertEqual(row["actual_status"], "EMULATOR_ONLY")
            self.assertFalse(release)

    def test_missing_visual_review_does_not_pass(self):
        with TemporaryDirectory() as dirname:
            root = Path(dirname)
            (root / "visual.png").write_bytes(b"fake screenshot")
            record = self.receipt("UI-01", "emulator", "visual.png", root)
            (root / "receipts.json").write_text(json.dumps([record]), encoding="utf-8")
            rows, release = audit(MATRIX, root)
            self.assertFalse(release)
            self.assertEqual(next(x for x in rows if x["id"] == "UI-01")["actual_status"], "EMULATOR_ONLY")

    def test_cannot_escape_evidence_folder(self):
        with TemporaryDirectory() as dirname:
            root = Path(dirname)
            with self.assertRaises(AuditError):
                secure_evidence_file(root, "../secret.txt")
            with self.assertRaises(AuditError):
                secure_evidence_file(root, "/etc/passwd")

    def test_unknown_requirements_refused(self):
        with TemporaryDirectory() as dirname:
            root = Path(dirname)
            (root / "receipts.json").write_text('[{"requirement_id":"UNKNOWN"}]', encoding="utf-8")
            with self.assertRaises(AuditError):
                audit(MATRIX, root)

    @staticmethod
    def receipt(rid, device, path, root):
        return {
            "requirement_id": rid,
            "result": "PASS",
            "tester": "CI",
            "device_class": device,
            "device": "Android Emulator API35",
            "method": "adb process & screenshot",
            "observed": "Successful app start",
            "time_utc": "2026-10-22T08:00:00Z",
            "evidence_files": [{"path":path, "sha256":sha256((root / path).read_bytes()).hexdigest()}],
        }


if __name__ == "__main__":
    unittest.main()
