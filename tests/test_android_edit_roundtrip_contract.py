"""Static contract tests for the real Android Writer edit/save smoke harness.

These checks guard the test itself: native edit mode, an actual pointer event,
and the Android wrapper's SAVE callback must all be proven before persistence
can pass. A queued UNO command or core-only .uno:Save is not sufficient.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "scripts" / "android_edit_roundtrip.py").read_text(encoding="utf-8")


def expression(name):
    return SOURCE.split(f'{name} = r"""', 1)[1].split('"""', 1)[0]


class AndroidEditRoundtripContractTests(unittest.TestCase):
    def test_real_mobile_edit_button_is_clicked_before_any_uno_mutation(self):
        click_expression = expression("CLICK_EDIT_EXPRESSION")
        edit_expression = expression("EDIT_EXPRESSION")
        save_expression = expression("SAVE_EXPRESSION")

        self.assertIn("document.getElementById('mobile-edit-button')", click_expression)
        self.assertIn("button.click()", click_expression)
        self.assertNotIn(".uno:InsertText", click_expression)
        self.assertIn(".uno:InsertText", edit_expression)
        self.assertNotIn(".uno:Save", save_expression)
        self.assertIn("editor.save(false, false)", save_expression)

    def test_native_edit_mode_and_real_canvas_focus_are_required(self):
        enter_body = SOURCE.split("def enter_edit_mode(directory: Path) -> None:", 1)[1].split(
            "def tap_document_canvas(directory: Path)", 1
        )[0]
        run_body = SOURCE.split("def run(directory: Path, timeout: int) -> None:", 1)[1]

        click_at = enter_body.index("evaluate_on_real_editor(9223, CLICK_EDIT_EXPRESSION)")
        wait_at = enter_body.index("wait_for_edit_mode(25)")
        state_at = enter_body.index("evaluate_on_real_editor(9223, READ_ONLY_STATE_EXPRESSION)")
        self.assertLess(click_at, wait_at)
        self.assertLess(wait_at, state_at)
        self.assertIn('state.get("readOnly") is not False', SOURCE)
        self.assertIn('call("shell", "input", "tap"', SOURCE)

        enter_at = run_body.index("enter_edit_mode(directory)")
        tap_at = run_body.index("tap_document_canvas(directory)")
        cursor_at = run_body.index("evaluate_on_real_editor(port, GO_TO_END_EXPRESSION)")
        insert_at = run_body.index("evaluate_on_real_editor(port, EDIT_EXPRESSION)")
        save_at = run_body.index("evaluate_on_real_editor(port, SAVE_EXPRESSION)")
        self.assertLess(enter_at, tap_at)
        self.assertLess(tap_at, cursor_at)
        self.assertLess(cursor_at, insert_at)
        self.assertLess(insert_at, save_at)

        self.assertIn('"postMobileMessage: EDITMODE on" in latest', SOURCE)
        self.assertIn('"setviewreadonly value=false" in latest', SOURCE)
        self.assertIn("Native Writer did not confirm edit mode", SOURCE)

    def test_roundtrip_remains_byte_and_content_verified(self):
        self.assertIn("hashlib.sha256(payload).hexdigest() == original_checksum", SOURCE)
        self.assertIn("validate_document(payload, require_saved_text=SENTINEL)", SOURCE)
        self.assertIn('directory/"edit-mode-screen.png"', SOURCE)
        self.assertIn('directory/"edit-mode-logcat.txt"', SOURCE)
        self.assertIn('directory/"edit-mode-state.json"', SOURCE)
        self.assertIn('directory/"roundtrip-result.txt"', SOURCE)
        self.assertIn('call("shell", "input", "keyevent", "KEYCODE_HOME")', SOURCE)

        smoke = (ROOT / "scripts" / "run_android_smoke.sh").read_text(encoding="utf-8")
        self.assertIn("cold-reopened-document.docx", smoke)
        self.assertIn('"edit-mode-screen.png"', smoke)
        self.assertIn('"edit-mode-logcat.txt"', smoke)
        self.assertIn('"edit-mode-state.json"', smoke)


if __name__ == "__main__":
    unittest.main()
