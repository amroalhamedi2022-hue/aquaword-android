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
        make('browser/src/main.js', "window.addEventListener('beforeunload', function () { });")
        make('browser/css/toolbar.css', '.toolbar { display: flex; }')
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
        make('android/app/src/main/res/menu/view_menu.xml', '''<menu>
    <item android:id="@+id/action_open_file" android:title="Open" />
</menu>''')
        make('android/app/src/main/res/values/strings.xml', '<resources></resources>')
        # The production patch also requires activity menu, open(), and result handlers.
        activity=self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java'
        activity.write_text(activity.read_text() + """
    private static final int OPEN_FILE_REQUEST_CODE = 43;
    void open(Uri uri) {
        addDocumentToRecents(uri);

        Intent i = getIntentToEdit(uri);
        startActivityForResult(i, LO_ACTIVITY_REQUEST_CODE);
    }
    public boolean onOptionsItemSelected(MenuItem item) {
        if (item.getItemId() == R.id.action_open_file) {
            openDocument();
            return true;
        }
    }
    /** File name extensions for which an empty document template is bundled in the assets. */
    public void onActivityResult(int requestCode, int resultCode, Intent data) {
        switch (requestCode) {
            case LO_ACTIVITY_REQUEST_CODE: {
            }
        }
    }
""")
        activity.write_text(activity.read_text() + """
    private void createNewFile(final Uri uri, final String extension) {
        // old UI-thread behavior:
        class CreateThread extends Thread {
            @Override public void run() {
            }
        }
        CreateThread thread = new CreateThread();
        thread.run();
        try {
            thread.join();
        } catch (Exception e) {
        }
    }

    /** Context menu item handling. */
    void doCreate() {
                createNewFile(uri, extension);

                open(uri);
    }
""")
        grant=('getContentResolver().takePersistableUriPermission(uri, ' +
               'Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);')
        activity.write_text(activity.read_text(encoding='utf-8') +
                            '\n' + grant + '\n' + grant + '\n', encoding='utf-8')
    def run_phase(self,phase):
        r=subprocess.run([sys.executable,str(ROOT/'scripts/apply_to_collabora.py'),'--repo',str(self.path),'--phase',phase],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,(r.stdout,r.stderr))
    def test_saf_readonly_or_temporary_provider_supported(self):
        self.run_phase('source')
        self.run_phase('source')
        s=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        self.assertEqual(s.count('AQUAWORD_SAFE_SAF_PERMISSIONS'),1)
        self.assertEqual(s.count('persistDocumentPermission(uri, data);'),2)
        self.assertIn('Intent.FLAG_GRANT_READ_URI_PERMISSION',s)
        self.assertIn('SecurityException | IllegalArgumentException',s)

    def test_saf_upstream_drift_rejected(self):
        p=self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java'
        p.write_text('class Changed {}',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_saf_permission_handling(p)

    def test_async_document_creation(self):
        self.run_phase('source')
        self.run_phase('source')
        activity=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        self.assertEqual(activity.count('AQUAWORD_ASYNC_DOCUMENT_CREATE'),1)
        self.assertIn('AquaWordCreateBlank', activity)
        self.assertIn('OutputStream output = getContentResolver().openOutputStream(uri, "w")', activity)
        self.assertNotIn('thread.run();', activity)
        self.assertNotIn('thread.join();', activity)
        self.assertIn('if (completed)\n                    open(uri);', activity)
        self.assertNotIn('createNewFile(uri, extension);\n\n                open(uri);', activity)

    def test_async_create_rejects_changed_upstream(self):
        path=self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java'
        path.write_text('public class Changed {}', encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_async_new_document_creation(path)

    def test_focus_source_is_idempotent(self):
        self.run_phase('source')
        self.run_phase('source')
        main=(self.path/'browser/src/main.js').read_text(encoding='utf-8')
        css=(self.path/'browser/css/toolbar.css').read_text(encoding='utf-8')
        self.assertEqual(main.count('AQUAWORD_FOCUS_BOOTSTRAP_BEGIN'),1)
        self.assertEqual(css.count('AQUAWORD_FOCUS_CSS_BEGIN'),1)
        self.assertIn('ThisIsTheAndroidApp',main)
        self.assertIn('aquaword-focus-active',css)
        self.assertNotIn('body.aquaword-focus-active #map',css)
        self.assertNotIn('body.aquaword-focus-active #document-container',css)

    def test_focus_upstream_drift_is_rejected(self):
        main=self.path/'browser/src/main.js'
        main.write_text('console.log("new upstream entrypoint")',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_focus_bootstrap(main)

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
    def test_history_integration(self):
        self.run_phase('source')
        self.run_phase('source')
        activity=(self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java').read_text()
        self.assertEqual(activity.count('AQUAWORD_PREEDIT_COPY'),1)
        self.assertIn('AquaWordHistory.capture(',activity)
        self.assertIn('AquaWordHistory.restore(',activity)
        self.assertIn('R.id.action_aquaword_history',activity)
        self.assertTrue((self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/AquaWordHistory.java').is_file())
        menu=(self.path/'android/app/src/main/res/menu/view_menu.xml').read_text()
        self.assertEqual(menu.count('AQUAWORD_HISTORY_MENU'),1)
        ar=(self.path/'android/app/src/main/res/values-ar/aquaword_strings.xml')
        self.assertTrue(ar.is_file())
        self.assertIn('نسخ الأمان',ar.read_text(encoding='utf-8'))
        self.assertIn('wordprocessingml.document',activity)

    def test_missing_safety_copy_menu_aborts(self):
        path=self.path/'android/app/src/main/res/menu/view_menu.xml'
        path.write_text('<menu />',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_history_menu(path)

    def test_missing_activity_handler_aborts(self):
        path=self.path/'android/app/src/main/java/org/libreoffice/androidapp/ui/LibreOfficeUIActivity.java'
        path.write_text('class Changed {}',encoding='utf-8')
        with self.assertRaises(M.PatchError):
            M.patch_history_activity(path)

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
