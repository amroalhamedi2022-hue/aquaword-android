"""Static contract tests for the real Android Writer edit/save smoke harness.

These checks guard the test itself: a UNO command issued in view mode is not
proof of editing, so the harness must click Collabora's visible mobile edit
control and wait for a native edit-mode acknowledgement first.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "scripts" / "android_edit_roundtrip.py").read_text(encoding="utf-8")


class AndroidEditRoundtripContractTests(unittest.TestCase):
    def test_real_mobile_edit_button_is_clicked_before_any_uno_mutation(self):
        click_expression = SOURCE.split('CLICK_EDIT_EXPRESSION = r"""', 1)[1].split('"""', 1)[0]
        edit_expression = SOURCE.split('EDIT_EXPRESSION = r"""', 1)[1].split('"""', 1)[0]

        self.assertIn("document.getElementById('mobile-edit-button')", click_expression)
        self.assertIn("button.click()", click_expression)
        self.assertNotIn(".uno:InsertText", click_expression)
        self.assertIn(".uno:InsertText", edit_expression)
        self.assertIn(".uno:Save", edit_expression)

    def test_native_edit_mode_acknowledgement_is_required_before_uno(self):
        run_body = SOURCE.split("def run(directory: Path, timeout: int) -> None:", 1)[1]
        click_at = run_body.index("evaluate_on_real_editor(port, CLICK_EDIT_EXPRESSION)")
        wait_at = run_body.index("wait_for_edit_mode(min(timeout, 25))")
        edit_at = run_body.index("evaluate_on_real_editor(port, EDIT_EXPRESSION)")
        self.assertLess(click_at, wait_at)
        self.assertLess(wait_at, edit_at)

        self.assertIn('"EDITMODE on" in latest', SOURCE)
        self.assertIn('"setviewreadonly value=false" in latest', SOURCE)
        self.assertIn("Native Writer did not confirm edit mode", SOURCE)

    def test_roundtrip_remains_byte_and_content_verified(self):
        self.assertIn("hashlib.sha256(payload).hexdigest() == original_checksum", SOURCE)
        self.assertIn("validate_document(payload, require_saved_text=SENTINEL)", SOURCE)
        self.assertIn("cold-reopened-document.docx", (ROOT / "scripts" / "run_android_smoke.sh").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
