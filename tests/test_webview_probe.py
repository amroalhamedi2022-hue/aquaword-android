"""Contract tests: real Android WebView proof must be a loaded Writer."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "scripts/verify_editor_webview.py"
spec = importlib.util.spec_from_file_location("aquaword_webview_probe", PATH)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class WebviewProofTests(unittest.TestCase):
    def test_verified_real_writer_document(self):
        actual={"docType": "text", "documentLayer": True,
                "documentContainer": True, "mapCanvas": True,
                "focusControl": True, "renderedPageNodes": 9}
        self.assertTrue(probe.proves_writer_ready(actual))

    def test_dont_accept_android_home_or_fake_browser(self):
        self.assertFalse(probe.proves_writer_ready({}))
        self.assertFalse(probe.proves_writer_ready({"docType": "text"}))

    def test_writer_without_rendered_document_layer_fails(self):
        ready={"docType": "text", "documentLayer": True,
               "documentContainer": True, "mapCanvas": True,
               "focusControl": True}
        for key in ready:
            bad=ready.copy()
            bad[key] = False if key != "docType" else "spreadsheet"
            self.assertFalse(probe.proves_writer_ready(bad),key)

    def test_focus_mode_requires_real_reversible_toggle(self):
        functional={"focusModeFunctional": True, "entered": True,
                    "exited": True, "pageKeptVisible": True}
        self.assertTrue(probe.focus_mode_ready(functional))
        for key in list(functional):
            invalid=functional.copy()
            invalid[key]=False
            self.assertFalse(probe.focus_mode_ready(invalid),key)
        self.assertFalse(probe.focus_mode_ready({}))

    def test_cdp_errors_are_not_silently_accepted(self):
        with self.assertRaisesRegex(RuntimeError, "failed"):
            probe.result_from_response({"error":{"code":-32000,"message":"target closed"}})
        with self.assertRaisesRegex(ValueError,"No JSON"):
            probe.result_from_response({"result": {"result": {"type":"undefined"}}})

    def test_json_probe_parsing(self):
        result={"docType":"text","documentLayer":True,
                "documentContainer":True,"mapCanvas":True,"focusControl":True}
        import json
        response={"result":{"result":{"value":json.dumps(result)}}}
        self.assertEqual(probe.result_from_response(response),result)


if __name__=="__main__":
    unittest.main()
