"""Prevent passing a splash icon as a finished Android UI."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "quality"))
from check_android_ui import verify_ui


class InteractiveUiEvidenceTests(unittest.TestCase):
    def test_settings_splash_fails(self):
        with TemporaryDirectory() as folder:
            f=Path(folder)/"splash.xml"
            f.write_text('<hierarchy><node text="" content-desc="Settings" clickable="false"/></hierarchy>')
            with self.assertRaisesRegex(ValueError,"Unready/splash"):
                verify_ui(f)

    def test_real_accessible_ui_passes(self):
        with TemporaryDirectory() as folder:
            f=Path(folder)/"settings.xml"
            f.write_text('''<hierarchy>
                <node text="Settings" clickable="false"/>
                <node text="Network and internet" clickable="true"/>
                <node text="Apps" clickable="true"/>
                <node text="Battery" clickable="true"/>
                <node content-desc="Search Settings" clickable="true"/>
            </hierarchy>''')
            labels,interactive=verify_ui(f)
            self.assertEqual(labels,5)
            self.assertEqual(interactive,4)


if __name__=="__main__":
    unittest.main()
