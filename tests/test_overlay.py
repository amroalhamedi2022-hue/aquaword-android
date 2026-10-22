"""Contract tests for the pinned Collabora Android overlay (not native build tests)."""
import pathlib
import subprocess
import sys
import tempfile
import unittest
from importlib.util import spec_from_file_location, module_from_spec

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=spec_from_file_location('aquaword_overlay',ROOT/'scripts/apply_to_collabora.py')
M=module_from_spec(spec)
spec.loader.exec_module(M)

class AquaWordIntegrationTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.path=pathlib.Path(t.name)
        def make(path,content):
            dest=self.path/path
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(content,encoding='utf-8')
        make('engine/README','native')
        make('browser/css/notebookbar.css','.notebookbar {color: blue}')
        make('browser/css/mobilewizard.css','.mobile-wizard {color: blue}')
        make('android/app/build.gradle','''android {
 defaultConfig { resValue "string", "app_name", "${coAppName}" }
 buildTypes { debug { resValue "string", "app_name", "${coAppName} Debug" } }
}''')
        make('android/app/src/main/AndroidManifest.xml','<application android:icon="${appIcon}" />')
        make('android/app/appSettings.gradle.in',"android.defaultConfig { applicationId '@APP_PACKAGE_NAME@' }")
        make('android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java', """editFAB.setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View v) {
                if (isFabMenuOpen)
                    collapseFabMenu();
                else
                    expandFabMenu();
            }
        });""")
    def run_phase(self,phase):
        r=subprocess.run([sys.executable,str(ROOT/'scripts/apply_to_collabora.py'),'--repo',str(self.path),'--phase',phase],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,(r.stdout,r.stderr))
    def test_idempotent_source(self):
        self.run_phase('source')
        self.run_phase('source')
        self.assertEqual((self.path/'browser/css/notebookbar.css').read_text().count('AQUAWORD_AURORA_BEGIN'),1)
        self.assertEqual((self.path/'browser/css/mobilewizard.css').read_text().count('AQUAWORD_AURORA_BEGIN'),1)
    def test_new_document_native_writer_only(self):
        self.run_phase('source')
        self.run_phase('source')
        c=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        self.assertEqual(c.count('AQUAWORD_WRITER_ONLY_NEW'),1)
        self.assertIn('CREATE_DOCUMENT_REQUEST_CODE',c)
        self.assertNotIn('expandFabMenu();',c)
    def test_reject_missing_new_document_handler(self):
        path=self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java'
        path.write_text('class Changed {}',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_writer_only_home(path)
    def test_gradle_labels(self):
        self.run_phase('source')
        s=(self.path/'android/app/build.gradle').read_text()
        self.assertIn('AquaWord Debug',s)
        self.assertIn('"AquaWord"',s)
    def test_template_id(self):
        self.run_phase('source')
        self.assertIn(M.APP_ID,(self.path/'android/app/appSettings.gradle.in').read_text())
    def test_manifest_icon(self):
        self.run_phase('source')
        self.assertIn('@mipmap/aquaword_launcher',(self.path/'android/app/src/main/AndroidManifest.xml').read_text())
    def test_five_icons(self):
        self.run_phase('source')
        for density in ['mdpi','hdpi','xhdpi','xxhdpi','xxxhdpi']:
            self.assertTrue((self.path/f'android/app/src/main/res/mipmap-{density}/aquaword_launcher.png').is_file())
    def test_configured_id(self):
        self.run_phase('source')
        (self.path/'android/app/appSettings.gradle').write_text("android.defaultConfig { applicationId 'com.aquaword.app' }",encoding='utf-8')
        self.run_phase('postconfigure')
    def test_reject_unexpanded(self):
        self.run_phase('source')
        (self.path/'android/app/appSettings.gradle').write_text("applicationId '@APP_PACKAGE_NAME@'",encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.configured(self.path)
    def test_reject_wrong_id(self):
        self.run_phase('source')
        (self.path/'android/app/appSettings.gradle').write_text("applicationId 'org.libreoffice.androidapp'",encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.configured(self.path)
    def test_reject_gradle_change(self):
        path=self.path/'android/app/build.gradle'
        path.write_text('android {}',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_gradle_labels(path)
    def test_reject_manifest_change(self):
        path=self.path/'android/app/src/main/AndroidManifest.xml'
        path.write_text('<application/>',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_manifest_icon(path)
    def test_preflight_failure(self):
        (self.path/'android/app/appSettings.gradle.in').unlink()
        with self.assertRaises(M.PatchError):
            M.source(self.path)
        self.assertNotIn('AQUAWORD_AURORA_BEGIN',(self.path/'browser/css/notebookbar.css').read_text())
    def test_css_drift(self):
        self.run_phase('source')
        path=self.path/'browser/css/notebookbar.css'
        path.write_text('AQUAWORD_AURORA_BEGIN',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.append_css(path,ROOT/'branding/notebookbar.aurora.css')
    def test_requires_native_editor(self):
        (self.path/'engine').rename(self.path/'old-engine')
        with self.assertRaises(M.PatchError):
            M.validate_repo(self.path)
    def test_android_only(self):
        self.assertFalse((ROOT/'windows').exists())
    def test_document_canvas_unmodified(self):
        css=(ROOT/'branding/notebookbar.aurora.css').read_text()
        for selector in ['.leaflet-tile','.document-container','#map']:
            self.assertNotIn(selector,css)
    def test_patcher_no_shell_or_network(self):
        code=(ROOT/'scripts/apply_to_collabora.py').read_text()
        for snippet in ['subprocess.run(', 'requests.get(', 'os.system(']:
            self.assertNotIn(snippet,code)

if __name__=='__main__':
    unittest.main()
